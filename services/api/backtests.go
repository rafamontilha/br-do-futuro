package main

import (
	"context"
	"encoding/json"
	"fmt"
	"log/slog"
	"net/http"
	"strconv"
	"time"
)

// Both the evaluation cutoff and its persistence must have been known at query time.
// Filters apply to this run, never to an older run selected for matching metrics.
const backtestRunCTE = `WITH chosen AS (
    SELECT id AS run_id, inputs_hash, code_version, as_of, min_sample, mode, created_at
    FROM backtest_run WHERE mode=$1 AND as_of <= $2 AND created_at <= $2
    ORDER BY as_of DESC, created_at DESC, id DESC LIMIT 1
)`

type backtestFilters struct {
	indicator string
	horizon   *int32
	target    string
	source    string
}

func parseBacktestFilters(r *http.Request) (backtestFilters, error) {
	q := r.URL.Query()
	f := backtestFilters{indicator: q.Get("indicator_id"), target: q.Get("target"), source: q.Get("forecast_source")}
	if q.Has("horizon") {
		value, err := strconv.ParseInt(q.Get("horizon"), 10, 32)
		if err != nil || value < 0 {
			return f, fmt.Errorf("horizon must be a non-negative 32-bit integer")
		}
		horizon := int32(value)
		f.horizon = &horizon
	}
	if f.target != "" && f.target != "first_release" && f.target != "latest" {
		return f, fmt.Errorf("target must be first_release or latest")
	}
	switch f.source {
	case "", "trajectory", "scenario_run", "benchmark_random_walk", "benchmark_seasonal_naive":
	default:
		return f, fmt.Errorf("invalid forecast_source")
	}
	return f, nil
}

func (a *API) handleGetBacktests(w http.ResponseWriter, r *http.Request, ctx context.Context, meta map[string]any, mode string, asOf time.Time) {
	filters, err := parseBacktestFilters(r)
	if err != nil {
		write(w, http.StatusBadRequest, map[string]string{"error": err.Error()})
		return
	}
	if a.db == nil {
		write(w, http.StatusServiceUnavailable, map[string]string{"error": "backtesting database unavailable"})
		return
	}
	query := backtestRunCTE + ` SELECT jsonb_build_object(
        'run', (SELECT to_jsonb(r) FROM chosen r),
        'data', COALESCE((SELECT jsonb_agg(to_jsonb(m) ORDER BY m.indicator_id,m.horizon,m.forecast_source,m.target,m.origin_kind)
            FROM backtest_metric m JOIN chosen r ON r.run_id=m.run_id
            WHERE ($3='' OR m.indicator_id=$3)
              AND ($4::integer IS NULL OR m.horizon=$4)
              AND ($5='' OR m.target=$5) AND ($6='' OR m.forecast_source=$6)), '[]'::jsonb))`
	var result struct {
		Run  json.RawMessage `json:"run"`
		Data json.RawMessage `json:"data"`
	}
	var raw []byte
	err = a.db.QueryRow(ctx, query, mode, asOf, filters.indicator, filters.horizon, filters.target, filters.source).Scan(&raw)
	if err == nil {
		err = json.Unmarshal(raw, &result)
	}
	if err != nil {
		slog.Error("query_backtests_failed", "error", err, "mode", mode)
		write(w, http.StatusServiceUnavailable, map[string]string{"error": "backtesting data temporarily unavailable"})
		return
	}
	meta["experimental"] = true
	meta["statement_type"] = "derived"
	meta["limitation"] = "Avaliação experimental por vintage capturada; não demonstra superioridade do modelo."
	write(w, http.StatusOK, map[string]any{"meta": meta, "run": result.Run, "data": result.Data, "experimental": true})
}

func (a *API) loadBacktestMonitoring(ctx context.Context, mode string, asOf time.Time) (json.RawMessage, error) {
	query := backtestRunCTE + ` SELECT jsonb_build_object(
        'experimental', true, 'mode', $1::text, 'as_of', $2::timestamptz,
        'ex_ante_snapshots_count', (SELECT count(*) FROM forecast_snapshot
            WHERE mode=$1 AND origin_kind='ex_ante' AND forecast_source IN ('trajectory','scenario_run')
              AND forecast_origin_at <= $2 AND created_at <= $2),
        'last_run', (SELECT to_jsonb(r) FROM chosen r),
        'backtested_indicators_count', (SELECT count(DISTINCT m.indicator_id)
            FROM backtest_metric m JOIN chosen r ON r.run_id=m.run_id),
        'backtested_indicator_ids', COALESCE((SELECT jsonb_agg(t.indicator_id ORDER BY t.indicator_id)
            FROM (SELECT DISTINCT m.indicator_id FROM backtest_metric m
                  JOIN chosen r ON r.run_id=m.run_id) t), '[]'::jsonb),
        'ex_ante_backtested_indicators_count', (SELECT count(DISTINCT m.indicator_id)
            FROM backtest_metric m JOIN chosen r ON r.run_id=m.run_id WHERE m.origin_kind='ex_ante'))`
	var data json.RawMessage
	err := a.db.QueryRow(ctx, query, mode, asOf).Scan(&data)
	return data, err
}
