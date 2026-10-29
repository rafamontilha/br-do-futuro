package main

import (
	"context"
	"crypto/rand"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"log/slog"
	"math"
	"net/http"
	"os"
	"strconv"
	"strings"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"
)

type API struct {
	db      *pgxpool.Pool
	catalog json.RawMessage
}

func newUUID() string {
	var b [16]byte
	_, _ = rand.Read(b[:])
	b[6] = (b[6] & 0x0f) | 0x40
	b[8] = (b[8] & 0x3f) | 0x80
	return fmt.Sprintf("%08x-%04x-%04x-%04x-%012x", b[0:4], b[4:6], b[6:8], b[8:10], b[10:16])
}

func write(w http.ResponseWriter, status int, value any) {
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	w.Header().Set("Cache-Control", "no-store")
	w.Header().Set("X-Content-Type-Options", "nosniff")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(value)
}

func queryOptions(r *http.Request) (string, time.Time, error) {
	mode := r.URL.Query().Get("mode")
	if mode == "" {
		mode = "source"
	}
	if mode != "source" && mode != "fixture" {
		return "", time.Time{}, errors.New("mode must be source or fixture")
	}
	asOf := time.Now().UTC()
	if s := r.URL.Query().Get("as_of"); s != "" {
		var err error
		asOf, err = time.Parse(time.RFC3339Nano, s)
		if err != nil {
			return "", asOf, errors.New("as_of must be RFC3339 with timezone")
		}
	}
	return mode, asOf, nil
}

type FiscalSimulationRequest struct {
	BaseDebtPct string         `json:"base_debt_pct"`
	Assumptions map[string]any `json:"assumptions"`
}

func (a *API) handleCreateSimulation(w http.ResponseWriter, r *http.Request, ctx context.Context) {
	var req FiscalSimulationRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		write(w, http.StatusBadRequest, map[string]string{"error": "invalid request body: " + err.Error()})
		return
	}
	if req.BaseDebtPct == "" {
		write(w, http.StatusBadRequest, map[string]string{"error": "base_debt_pct is required"})
		return
	}
	baseDebt, err := strconv.ParseFloat(req.BaseDebtPct, 64)
	if err != nil || math.IsNaN(baseDebt) || math.IsInf(baseDebt, 0) || baseDebt < 0 {
		write(w, http.StatusBadRequest, map[string]string{"error": "base_debt_pct must be a non-negative finite number"})
		return
	}
	if req.Assumptions == nil {
		write(w, http.StatusBadRequest, map[string]string{"error": "assumptions object is required"})
		return
	}

	required := []string{"interest", "growth", "primary"}
	for _, k := range required {
		val, ok := req.Assumptions[k]
		if !ok || val == nil {
			write(w, http.StatusBadRequest, map[string]string{"error": fmt.Sprintf("missing assumption: %s", k)})
			return
		}
	}

	growthStr := fmt.Sprintf("%v", req.Assumptions["growth"])
	growth, err := strconv.ParseFloat(growthStr, 64)
	if err != nil || math.IsNaN(growth) || growth <= -1.0 {
		write(w, http.StatusBadRequest, map[string]string{"error": "growth must be finite and strictly greater than -100%"})
		return
	}

	horizon := 4
	if hVal, ok := req.Assumptions["horizon_years"]; ok && hVal != nil {
		hInt, err := strconv.Atoi(fmt.Sprintf("%v", hVal))
		if err != nil || hInt < 1 || hInt > 20 {
			write(w, http.StatusBadRequest, map[string]string{"error": "horizon_years must be an integer between 1 and 20"})
			return
		}
		horizon = hInt
	}
	req.Assumptions["horizon_years"] = horizon
	if _, ok := req.Assumptions["adjustment"]; !ok {
		req.Assumptions["adjustment"] = "0.00"
	}

	if a.db == nil {
		write(w, http.StatusServiceUnavailable, map[string]string{"error": "database unavailable"})
		return
	}

	assumptionsJSON, err := json.Marshal(req.Assumptions)
	if err != nil {
		write(w, http.StatusBadRequest, map[string]string{"error": "invalid assumptions format"})
		return
	}

	hasher := sha256.New()
	hasher.Write([]byte(fmt.Sprintf("%s:%s", req.BaseDebtPct, string(assumptionsJSON))))
	simID := hex.EncodeToString(hasher.Sum(nil))

	tx, err := a.db.Begin(ctx)
	if err != nil {
		slog.Error("tx_begin_failed", "error", err)
		write(w, http.StatusServiceUnavailable, map[string]string{"error": "database transaction failed"})
		return
	}
	defer tx.Rollback(ctx)

	_, err = tx.Exec(ctx, `
		INSERT INTO dynamic_simulations(simulation_id, base_debt_pct, assumptions, status)
		VALUES ($1, $2, $3, 'pending')
		ON CONFLICT (simulation_id) DO NOTHING
	`, simID, baseDebt, assumptionsJSON)
	if err != nil {
		slog.Error("insert_sim_failed", "error", err)
		write(w, http.StatusInternalServerError, map[string]string{"error": "could not create simulation"})
		return
	}

	eventID := newUUID()
	eventPayload := map[string]any{
		"simulation_id": simID,
		"base_debt_pct": req.BaseDebtPct,
		"assumptions":   req.Assumptions,
	}
	eventPayloadJSON, _ := json.Marshal(eventPayload)

	_, err = tx.Exec(ctx, `
		INSERT INTO outbox(id, event_type, payload)
		VALUES ($1, 'DynamicSimulationRequested', $2)
	`, eventID, eventPayloadJSON)
	if err != nil {
		slog.Error("insert_outbox_failed", "error", err)
		write(w, http.StatusInternalServerError, map[string]string{"error": "could not queue simulation"})
		return
	}

	if err := tx.Commit(ctx); err != nil {
		slog.Error("tx_commit_failed", "error", err)
		write(w, http.StatusInternalServerError, map[string]string{"error": "could not commit transaction"})
		return
	}

	write(w, http.StatusAccepted, map[string]any{
		"meta": map[string]any{
			"statement_type": "projected",
			"disclaimer":     "Simulação contábil condicional baseada na identidade fiscal; não constitui previsão oficial nem aconselhamento.",
		},
		"data": map[string]any{
			"simulation_id": simID,
			"status":        "pending",
			"message":       "Simulação fiscal dinâmica enfileirada para processamento assíncrono",
		},
	})
}

func (a *API) handleGetSimulation(w http.ResponseWriter, r *http.Request, ctx context.Context, meta map[string]any, simID string) {
	if a.db == nil {
		write(w, http.StatusServiceUnavailable, map[string]string{"error": "database unavailable"})
		return
	}
	var (
		baseDebt    float64
		assumptions json.RawMessage
		status      string
		results     *json.RawMessage
		simError    *string
		requestedAt time.Time
		completedAt *time.Time
	)
	err := a.db.QueryRow(ctx, `
		SELECT base_debt_pct, assumptions, status, results, error, requested_at, completed_at
		FROM dynamic_simulations WHERE simulation_id = $1
	`, simID).Scan(&baseDebt, &assumptions, &status, &results, &simError, &requestedAt, &completedAt)
	if err != nil {
		write(w, http.StatusNotFound, map[string]string{"error": "simulation not found"})
		return
	}

	meta["statement_type"] = "projected"
	meta["disclaimer"] = "Simulação contábil condicional baseada na identidade fiscal; não constitui previsão oficial nem aconselhamento."

	data := map[string]any{
		"simulation_id": simID,
		"base_debt_pct": baseDebt,
		"assumptions":   assumptions,
		"status":        status,
		"results":       results,
		"error":         simError,
		"requested_at":  requestedAt,
		"completed_at":  completedAt,
	}
	write(w, http.StatusOK, map[string]any{"meta": meta, "data": data})
}

func (a *API) handleGetInstitutions(w http.ResponseWriter, r *http.Request, ctx context.Context, meta map[string]any) {
	if a.db == nil {
		write(w, http.StatusServiceUnavailable, map[string]string{"error": "database unavailable"})
		return
	}
	var data json.RawMessage
	sql := `SELECT COALESCE(jsonb_agg(to_jsonb(t)), '[]') FROM (
		SELECT a.actor_id, a.name, a.sphere, a.legal_framework, a.description,
			COALESCE(
				(SELECT jsonb_agg(jsonb_build_object('indicator_id', r.indicator_id, 'role', r.role, 'notes', r.notes))
				 FROM indicator_institutional_roles r WHERE r.actor_id = a.actor_id),
				'[]'::jsonb
			) AS indicator_roles
		FROM institutional_actors a
		ORDER BY a.actor_id
	) t`
	if err := a.db.QueryRow(ctx, sql).Scan(&data); err != nil {
		slog.Error("query_institutions_failed", "error", err)
		write(w, http.StatusServiceUnavailable, map[string]string{"error": "data temporarily unavailable"})
		return
	}
	write(w, http.StatusOK, map[string]any{"meta": meta, "data": data})
}

func (a *API) handle(w http.ResponseWriter, r *http.Request) {
	ctx, cancel := context.WithTimeout(r.Context(), 5*time.Second)
	defer cancel()

	if r.URL.Path == "/healthz" {
		if r.Method != http.MethodGet {
			w.Header().Set("Allow", "GET")
			write(w, http.StatusMethodNotAllowed, map[string]string{"error": "method not allowed"})
			return
		}
		if a.db != nil {
			if err := a.db.Ping(ctx); err != nil {
				write(w, http.StatusServiceUnavailable, map[string]string{"status": "unavailable"})
				return
			}
		}
		write(w, http.StatusOK, map[string]string{"status": "ok"})
		return
	}

	if r.Method == http.MethodPost {
		if r.URL.Path == "/v1/simulations/fiscal" {
			a.handleCreateSimulation(w, r, ctx)
			return
		}
		w.Header().Set("Allow", "GET")
		write(w, http.StatusMethodNotAllowed, map[string]string{"error": "read-only API"})
		return
	}

	if r.Method != http.MethodGet {
		w.Header().Set("Allow", "GET")
		write(w, http.StatusMethodNotAllowed, map[string]string{"error": "read-only API"})
		return
	}

	mode, asOf, err := queryOptions(r)
	if err != nil {
		write(w, http.StatusBadRequest, map[string]string{"error": err.Error()})
		return
	}
	meta := map[string]any{
		"methodology_version": "constitution-1.3",
		"as_of":                asOf,
		"mode":                 mode,
		"freshness":            "not_verified_against_source",
		"baseline_status":      "not_validated",
		"publication_status":   "internal_pilot",
	}

	if r.URL.Path == "/v1/indicators" {
		write(w, http.StatusOK, map[string]any{"meta": meta, "data": a.catalog})
		return
	}

	if strings.HasPrefix(r.URL.Path, "/v1/simulations/fiscal/") {
		simID := strings.TrimPrefix(r.URL.Path, "/v1/simulations/fiscal/")
		a.handleGetSimulation(w, r, ctx, meta, simID)
		return
	}

	if r.URL.Path == "/v1/institutions" {
		a.handleGetInstitutions(w, r, ctx, meta)
		return
	}

	var sql string
	args := []any{mode, asOf}
	switch {
	case r.URL.Path == "/v1/observations":
		sql = `SELECT COALESCE(jsonb_agg(to_jsonb(t)), '[]') FROM (
   SELECT DISTINCT ON(o.indicator_id,o.reference_period) o.indicator_id,o.reference_period,o.value,o.unit,
    o.vintage_id,o.supersedes,v.known_at,v.published_at,v.quality_status,v.methodology_version,
    i.source_uri,i.raw_hash,i.captured_at
   FROM observation o JOIN vintage v ON v.id=o.vintage_id JOIN ingestion_run i ON i.id=v.run_id
   WHERE o.mode=$1 AND v.known_at <= $2 ORDER BY o.indicator_id,o.reference_period,v.known_at DESC) t`
	case strings.HasPrefix(r.URL.Path, "/v1/indicators/") && strings.HasSuffix(r.URL.Path, "/observations"):
		id := strings.TrimSuffix(strings.TrimPrefix(r.URL.Path, "/v1/indicators/"), "/observations")
		args = append(args, id)
		sql = `SELECT COALESCE(jsonb_agg(to_jsonb(t)), '[]') FROM (
   SELECT DISTINCT ON(o.reference_period) o.*,v.known_at,v.published_at,v.quality_status,
    v.methodology_version,i.source_uri,i.raw_hash,i.captured_at
   FROM observation o JOIN vintage v ON v.id=o.vintage_id JOIN ingestion_run i ON i.id=v.run_id
   WHERE o.mode=$1 AND v.known_at <= $2 AND o.indicator_id=$3
   ORDER BY o.reference_period,v.known_at DESC) t`
	case r.URL.Path == "/v1/scenarios":
		sql = `SELECT COALESCE(jsonb_agg(to_jsonb(t)), '[]') FROM (
   SELECT DISTINCT ON(scenario_id) * FROM scenario_run WHERE mode=$1 AND created_at <= $2
   ORDER BY scenario_id,created_at DESC) t`
	case r.URL.Path == "/v1/alerts":
		sql = `SELECT COALESCE(jsonb_agg(to_jsonb(t)), '[]') FROM (
   SELECT a.* FROM alert a JOIN scenario_run s ON a.scenario_run_id=s.id
   WHERE s.mode=$1 AND a.created_at <= $2 ORDER BY a.created_at DESC) t`
	default:
		write(w, http.StatusNotFound, map[string]string{"error": "not found"})
		return
	}
	var data json.RawMessage
	if err := a.db.QueryRow(ctx, sql, args...).Scan(&data); err != nil {
		slog.Error("query_failed", "path", r.URL.Path, "error", err)
		write(w, http.StatusServiceUnavailable, map[string]string{"error": "data temporarily unavailable"})
		return
	}
	write(w, http.StatusOK, map[string]any{"meta": meta, "data": data})
}

func main() {
	ctx := context.Background()
	pool, err := pgxpool.New(ctx, os.Getenv("DATABASE_URL"))
	if err != nil {
		slog.Error("database_config", "error", err)
		os.Exit(1)
	}
	defer pool.Close()
	catalogPath := os.Getenv("CATALOG_PATH")
	if catalogPath == "" {
		catalogPath = "../../catalog.json"
	}
	catalog, err := os.ReadFile(catalogPath)
	if err != nil || !json.Valid(catalog) {
		slog.Error("invalid_catalog")
		os.Exit(1)
	}
	a := &API{db: pool, catalog: catalog}
	server := &http.Server{
		Addr:              ":8080",
		Handler:           http.HandlerFunc(a.handle),
		ReadHeaderTimeout: 5 * time.Second,
		ReadTimeout:       10 * time.Second,
		WriteTimeout:      10 * time.Second,
		IdleTimeout:       60 * time.Second,
	}
	slog.Info("api_listening", "address", server.Addr)
	if err := server.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
		slog.Error("server_failed", "error", err)
		os.Exit(1)
	}
}
