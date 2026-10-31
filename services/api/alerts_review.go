package main

import (
	"context"
	"encoding/json"
	"fmt"
	"log/slog"
	"net/http"
	"strings"
	"time"
)

type AlertReviewRequestBody struct {
	Action        string `json:"action"` // "approve" or "reject"
	Justification string `json:"justification"`
}

func (a *API) handleAlertReview(w http.ResponseWriter, r *http.Request, ctx context.Context, alertID string, auth AuthContext) {
	if r.Method != http.MethodPost {
		write(w, http.StatusMethodNotAllowed, map[string]string{"error": "method not allowed"})
		return
	}

	// 1. Exige pelo menos o papel de 'reviewer' para validar impactos materiais
	if !requireRole(w, auth, RoleReviewer) {
		return
	}

	var req AlertReviewRequestBody
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		write(w, http.StatusBadRequest, map[string]string{"error": "invalid request body: " + err.Error()})
		return
	}

	action := strings.ToLower(strings.TrimSpace(req.Action))
	if action != "approve" && action != "reject" {
		write(w, http.StatusBadRequest, map[string]string{"error": "action must be either 'approve' or 'reject'"})
		return
	}

	justification := strings.TrimSpace(req.Justification)
	if len(justification) < 15 {
		write(w, http.StatusBadRequest, map[string]string{
			"error": "justification must be a formal technical rationale with at least 15 characters",
		})
		return
	}

	if a.db == nil {
		write(w, http.StatusServiceUnavailable, map[string]string{"error": "database unavailable"})
		return
	}

	tx, err := a.db.Begin(ctx)
	if err != nil {
		slog.Error("begin_tx_alert_review_failed", "error", err)
		write(w, http.StatusInternalServerError, map[string]string{"error": "could not start transaction"})
		return
	}
	defer tx.Rollback(ctx)

	// Serializa auditoria com advisory lock
	if _, err := tx.Exec(ctx, "SELECT pg_advisory_xact_lock(742910482)"); err != nil {
		slog.Error("audit_lock_failed", "error", err)
		write(w, http.StatusInternalServerError, map[string]string{"error": "could not acquire audit serialization lock"})
		return
	}

	// 2. Verifica se o alerta existe e seu estado atual
	var currentReviewStatus, severity string
	var evidenceJSON []byte
	err = tx.QueryRow(ctx, `
		SELECT review_status, severity, evidence FROM alert WHERE id = $1 FOR UPDATE
	`, alertID).Scan(&currentReviewStatus, &severity, &evidenceJSON)
	if err != nil {
		write(w, http.StatusNotFound, map[string]string{"error": "alert not found"})
		return
	}

	if currentReviewStatus != "pending_human_review" {
		write(w, http.StatusConflict, map[string]string{
			"error": fmt.Sprintf("alert already reviewed with status: %s", currentReviewStatus),
		})
		return
	}

	newStatus := "approved"
	auditAction := "review_alert_approved"
	if action == "reject" {
		newStatus = "rejected"
		auditAction = "review_alert_rejected"
	}

	now := time.Now().UTC()

	// 3. Atualiza o status do alerta
	_, err = tx.Exec(ctx, `
		UPDATE alert
		SET review_status = $1,
		    reviewed_by = $2,
		    review_justification = $3,
		    reviewed_at = $4,
		    status = 'reviewed'
		WHERE id = $5
	`, newStatus, auth.ActorID, justification, now, alertID)
	if err != nil {
		slog.Error("update_alert_status_failed", "error", err)
		write(w, http.StatusInternalServerError, map[string]string{"error": "could not update alert status"})
		return
	}

	// 4. Busca o hash do último registro da trilha imutável de auditoria
	var prevHash string
	err = tx.QueryRow(ctx, `
		SELECT payload_hash FROM decision_audit_log
		ORDER BY created_at DESC, id DESC
		LIMIT 1
	`).Scan(&prevHash)
	if err != nil {
		prevHash = "0000000000000000000000000000000000000000000000000000000000000000"
	}

	auditID := fmt.Sprintf("audit-rev-%s-%s", now.Format("20060102"), newUUID()[:8])

	var prevEvidence map[string]any
	if len(evidenceJSON) > 0 {
		_ = json.Unmarshal(evidenceJSON, &prevEvidence)
	}

	prevState := map[string]any{
		"review_status": currentReviewStatus,
		"severity":      severity,
		"evidence":      prevEvidence,
	}
	newState := map[string]any{
		"review_status":        newStatus,
		"reviewed_by":          auth.ActorID,
		"review_justification": justification,
		"reviewed_at":          now.Format(time.RFC3339),
	}

	canonicalPayload := map[string]any{
		"action":         auditAction,
		"actor_id":       auth.ActorID,
		"actor_role":     string(auth.Role),
		"entity_id":      alertID,
		"entity_type":    "alert",
		"event_id":       nil,
		"id":             auditID,
		"justification":  justification,
		"new_state":      newState,
		"prev_log_hash":  prevHash,
		"previous_state": prevState,
	}
	payloadHash := computePayloadHash(canonicalPayload)

	prevJSON, _ := json.Marshal(prevState)
	newJSON, _ := json.Marshal(newState)

	_, err = tx.Exec(ctx, `
		INSERT INTO decision_audit_log (
			id, event_id, actor_id, actor_role, action, entity_type, entity_id,
			justification, previous_state, new_state, payload_hash, prev_log_hash, created_at
		) VALUES ($1, NULL, $2, $3, $4, 'alert', $5, $6, $7, $8, $9, $10, $11)
	`, auditID, auth.ActorID, string(auth.Role), auditAction, alertID,
		justification, prevJSON, newJSON, payloadHash, prevHash, now)
	if err != nil {
		slog.Error("insert_alert_decision_audit_failed", "error", err)
		write(w, http.StatusInternalServerError, map[string]string{"error": "could not record decision audit trail"})
		return
	}

	if err := tx.Commit(ctx); err != nil {
		slog.Error("commit_alert_review_tx_failed", "error", err)
		write(w, http.StatusInternalServerError, map[string]string{"error": "could not commit transaction"})
		return
	}

	slog.Info("alert_reviewed_successfully", "alert_id", alertID, "review_status", newStatus, "actor_id", auth.ActorID)
	write(w, http.StatusOK, map[string]any{
		"data": map[string]any{
			"id":            alertID,
			"review_status": newStatus,
			"reviewed_by":   auth.ActorID,
			"reviewed_at":   now.Format(time.RFC3339),
			"justification": justification,
			"audit_id":      auditID,
			"payload_hash":  payloadHash,
		},
	})
}
