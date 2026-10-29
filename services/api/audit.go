package main

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"log/slog"
	"net/http"
	"strings"
	"time"
)

type DecisionAuditRequest struct {
	EventID       *string        `json:"event_id,omitempty"`
	Action        string         `json:"action"`
	EntityType    string         `json:"entity_type"`
	EntityID      string         `json:"entity_id"`
	Justification string         `json:"justification"`
	PreviousState map[string]any `json:"previous_state,omitempty"`
	NewState      map[string]any `json:"new_state"`
}

func computePayloadHash(payload any) string {
	bytes, err := json.Marshal(payload)
	if err != nil {
		bytes = []byte(fmt.Sprintf("%v", payload))
	}
	h := sha256.Sum256(bytes)
	return hex.EncodeToString(h[:])
}

func (a *API) handleCreateDecisionAudit(w http.ResponseWriter, r *http.Request, ctx context.Context, auth AuthContext) {
	// Exige pelo menos o papel de 'reviewer' para homologar decisões auditáveis
	if !requireRole(w, auth, RoleReviewer) {
		return
	}

	var req DecisionAuditRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		write(w, http.StatusBadRequest, map[string]string{"error": "invalid request body: " + err.Error()})
		return
	}

	if strings.TrimSpace(req.Action) == "" {
		write(w, http.StatusBadRequest, map[string]string{"error": "action is required"})
		return
	}
	if strings.TrimSpace(req.EntityType) == "" {
		write(w, http.StatusBadRequest, map[string]string{"error": "entity_type is required"})
		return
	}
	if strings.TrimSpace(req.EntityID) == "" {
		write(w, http.StatusBadRequest, map[string]string{"error": "entity_id is required"})
		return
	}
	if strings.TrimSpace(req.Justification) == "" {
		write(w, http.StatusBadRequest, map[string]string{"error": "justification is required"})
		return
	}
	if req.NewState == nil {
		write(w, http.StatusBadRequest, map[string]string{"error": "new_state object is required"})
		return
	}

	if a.db == nil {
		write(w, http.StatusServiceUnavailable, map[string]string{"error": "database unavailable"})
		return
	}

	tx, err := a.db.Begin(ctx)
	if err != nil {
		slog.Error("begin_tx_audit_failed", "error", err)
		write(w, http.StatusInternalServerError, map[string]string{"error": "could not start transaction"})
		return
	}
	defer tx.Rollback(ctx)

	// Serializa inserções concorrentes na cadeia de auditoria via trava consultiva de transação
	if _, err := tx.Exec(ctx, "SELECT pg_advisory_xact_lock(742910482)"); err != nil {
		slog.Error("audit_advisory_lock_failed", "error", err)
		write(w, http.StatusInternalServerError, map[string]string{"error": "could not acquire audit serialization lock"})
		return
	}

	// Busca o hash do último registro da cadeia de auditoria
	var prevHash string
	err = tx.QueryRow(ctx, `
		SELECT payload_hash FROM decision_audit_log
		ORDER BY created_at DESC, id DESC
		LIMIT 1
	`).Scan(&prevHash)
	if err != nil {
		prevHash = "0000000000000000000000000000000000000000000000000000000000000000"
	}

	auditID := fmt.Sprintf("audit-dec-%s-%s", time.Now().UTC().Format("20060102"), newUUID()[:8])

	// Hashing canônico completo de todos os campos da decisão + hash predecessor
	canonicalPayload := map[string]any{
		"action":         req.Action,
		"actor_id":       auth.ActorID,
		"actor_role":     string(auth.Role),
		"entity_id":      req.EntityID,
		"entity_type":    req.EntityType,
		"event_id":       req.EventID,
		"id":             auditID,
		"justification":  strings.TrimSpace(req.Justification),
		"new_state":      req.NewState,
		"prev_log_hash":  prevHash,
		"previous_state": req.PreviousState,
	}
	payloadHash := computePayloadHash(canonicalPayload)

	prevJSON, _ := json.Marshal(req.PreviousState)
	newJSON, _ := json.Marshal(req.NewState)

	_, err = tx.Exec(ctx, `
		INSERT INTO decision_audit_log (
			id, event_id, actor_id, actor_role, action, entity_type, entity_id,
			justification, previous_state, new_state, payload_hash, prev_log_hash, created_at
		) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, clock_timestamp())
	`, auditID, req.EventID, auth.ActorID, string(auth.Role), req.Action, req.EntityType, req.EntityID,
		strings.TrimSpace(req.Justification), prevJSON, newJSON, payloadHash, prevHash)
	if err != nil {
		slog.Error("insert_audit_failed", "error", err)
		write(w, http.StatusInternalServerError, map[string]string{"error": "could not insert audit log"})
		return
	}

	if err := tx.Commit(ctx); err != nil {
		slog.Error("commit_audit_failed", "error", err)
		write(w, http.StatusInternalServerError, map[string]string{"error": "could not commit audit transaction"})
		return
	}

	slog.Info("decision_audit_recorded", "audit_id", auditID, "action", req.Action, "actor_id", auth.ActorID)
	write(w, http.StatusCreated, map[string]any{
		"data": map[string]any{
			"id":            auditID,
			"action":        req.Action,
			"entity_type":   req.EntityType,
			"entity_id":     req.EntityID,
			"actor_id":      auth.ActorID,
			"actor_role":    auth.Role,
			"payload_hash":  payloadHash,
			"prev_log_hash": prevHash,
			"status":        "recorded",
		},
	})
}

func (a *API) handleGetDecisionAudit(w http.ResponseWriter, r *http.Request, ctx context.Context, meta map[string]any, auth AuthContext) {
	// Leitura da trilha de auditoria restrita a usuários autorizados (mínimo reviewer)
	if !requireRole(w, auth, RoleReviewer) {
		return
	}

	if a.db == nil {
		write(w, http.StatusServiceUnavailable, map[string]string{"error": "database unavailable"})
		return
	}

	entityType := strings.TrimSpace(r.URL.Query().Get("entity_type"))
	actorID := strings.TrimSpace(r.URL.Query().Get("actor_id"))
	pagination := parsePaginationParams(r)

	sql := `SELECT COALESCE(jsonb_agg(to_jsonb(t)), '[]') FROM (
		SELECT id, event_id, actor_id, actor_role, action, entity_type, entity_id,
		       justification, previous_state, new_state, payload_hash, prev_log_hash, created_at
		FROM decision_audit_log
		WHERE ($1 = '' OR entity_type = $1)
		  AND ($2 = '' OR actor_id = $2)
		ORDER BY created_at DESC, id DESC
	) t`

	var allData json.RawMessage
	if err := a.db.QueryRow(ctx, sql, entityType, actorID).Scan(&allData); err != nil {
		slog.Error("query_audit_failed", "error", err)
		write(w, http.StatusServiceUnavailable, map[string]string{"error": "data temporarily unavailable"})
		return
	}

	pagedData, pageMeta, err := paginateJSONArray(allData, pagination)
	if err != nil {
		slog.Error("pagination_failed", "error", err)
		write(w, http.StatusInternalServerError, map[string]string{"error": "pagination error"})
		return
	}

	meta["pagination"] = pageMeta
	write(w, http.StatusOK, map[string]any{"meta": meta, "data": pagedData})
}
