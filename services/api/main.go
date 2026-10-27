package main

import (
	"context"
	"encoding/json"
	"errors"
	"log/slog"
	"net/http"
	"os"
	"strings"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"
)

type API struct {
	db      *pgxpool.Pool
	catalog json.RawMessage
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
func (a *API) handle(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		w.Header().Set("Allow", "GET")
		write(w, 405, map[string]string{"error": "read-only API"})
		return
	}
	ctx, cancel := context.WithTimeout(r.Context(), 5*time.Second)
	defer cancel()
	if r.URL.Path == "/healthz" {
		if err := a.db.Ping(ctx); err != nil {
			write(w, 503, map[string]string{"status": "unavailable"})
			return
		}
		write(w, 200, map[string]string{"status": "ok"})
		return
	}
	mode, asOf, err := queryOptions(r)
	if err != nil {
		write(w, 400, map[string]string{"error": err.Error()})
		return
	}
	meta := map[string]any{"methodology_version": "constitution-1.3", "as_of": asOf, "mode": mode,
		"freshness": "not_verified_against_source", "baseline_status": "not_validated", "publication_status": "internal_pilot"}
	if r.URL.Path == "/v1/indicators" {
		write(w, 200, map[string]any{"meta": meta, "data": a.catalog})
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
		write(w, 404, map[string]string{"error": "not found"})
		return
	}
	var data json.RawMessage
	if err := a.db.QueryRow(ctx, sql, args...).Scan(&data); err != nil {
		slog.Error("query_failed", "path", r.URL.Path, "error", err)
		write(w, 503, map[string]string{"error": "data temporarily unavailable"})
		return
	}
	write(w, 200, map[string]any{"meta": meta, "data": data})
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
	server := &http.Server{Addr: ":8080", Handler: http.HandlerFunc(a.handle), ReadHeaderTimeout: 5 * time.Second,
		ReadTimeout: 10 * time.Second, WriteTimeout: 10 * time.Second, IdleTimeout: 60 * time.Second}
	slog.Info("api_listening", "address", server.Addr)
	if err := server.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
		slog.Error("server_failed", "error", err)
		os.Exit(1)
	}
}
