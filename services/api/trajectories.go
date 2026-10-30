package main

import (
	_ "embed"
	"context"
	"encoding/json"
	"log/slog"
	"net/http"
	"os"
	"strings"
	"time"
)

//go:embed trajectories.json
var embeddedTrajectoriesJSON []byte

type TrajectoryPoint struct {
	ID                string     `json:"id"`
	IndicatorID       string     `json:"indicator_id"`
	PeriodDate        string     `json:"period_date"`
	PeriodLabel       string     `json:"period_label"`
	ActualValue       *float64   `json:"actual_value"`
	BaselineValue     *float64   `json:"baseline_value"`
	ForecastValue     *float64   `json:"forecast_value"`
	ForecastLower     *float64   `json:"forecast_lower"`
	ForecastUpper     *float64   `json:"forecast_upper"`
	TargetValue       *float64   `json:"target_value"`
	ContinuityValue   *float64   `json:"continuity_value"`
	Unit              string     `json:"unit"`
	CalibrationStatus string     `json:"calibration_status"`
	SourceAgency      string     `json:"source_agency"`
	Mode              string     `json:"mode"`
	AsOfValidUntil    *time.Time `json:"as_of_valid_until"`
}

func loadTrajectoriesFixture() ([]TrajectoryPoint, error) {
	paths := []string{
		os.Getenv("TRAJECTORIES_FIXTURE_PATH"),
		"../../fixtures/trajectories.json",
		"fixtures/trajectories.json",
		"../fixtures/trajectories.json",
		"trajectories.json",
	}
	var data []byte
	var err error
	for _, p := range paths {
		if p == "" {
			continue
		}
		data, err = os.ReadFile(p)
		if err == nil && len(data) > 0 {
			break
		}
	}
	if len(data) == 0 && len(embeddedTrajectoriesJSON) > 0 {
		data = embeddedTrajectoriesJSON
	}
	if len(data) == 0 {
		return nil, os.ErrNotExist
	}
	var points []TrajectoryPoint
	if err := json.Unmarshal(data, &points); err != nil {
		return nil, err
	}
	return points, nil
}

func (a *API) handleGetTrajectories(w http.ResponseWriter, r *http.Request, ctx context.Context, meta map[string]any, mode string, asOf time.Time) {
	indicatorID := r.URL.Query().Get("indicator_id")
	if strings.HasPrefix(r.URL.Path, "/v1/trajectories/") {
		indicatorID = strings.TrimPrefix(r.URL.Path, "/v1/trajectories/")
	}

	// Se estiver em modo fixture e sem banco, usar fallback hermético
	if mode == "fixture" && a.db == nil {
		fixtures, err := loadTrajectoriesFixture()
		if err != nil {
			slog.Error("load_trajectories_fixture_failed", "error", err)
			write(w, http.StatusServiceUnavailable, map[string]string{"error": "trajectory fixtures unavailable"})
			return
		}
		var filtered []TrajectoryPoint
		for _, pt := range fixtures {
			if indicatorID != "" && pt.IndicatorID != indicatorID {
				continue
			}
			// Aplica isolamento temporal bitemporal (as_of)
			if pt.AsOfValidUntil != nil && pt.AsOfValidUntil.After(asOf) {
				pt.ActualValue = nil
			}
			filtered = append(filtered, pt)
		}
		if indicatorID != "" && len(filtered) == 0 {
			write(w, http.StatusNotFound, map[string]string{"error": "indicator trajectory not found"})
			return
		}
		write(w, http.StatusOK, map[string]any{"meta": meta, "data": filtered})
		return
	}

	// Se modo for source e banco indisponível, falhar com 503 (NUNCA cair em fixture)
	if mode == "source" && a.db == nil {
		write(w, http.StatusServiceUnavailable, map[string]string{"error": "source database unavailable"})
		return
	}

	// Com banco de dados disponível: filtrar estritamente por mode = $3
	sql := `SELECT COALESCE(jsonb_agg(to_jsonb(t)), '[]') FROM (
		SELECT id, indicator_id, period_date, period_label,
		       CASE WHEN as_of_valid_until IS NOT NULL AND as_of_valid_until > $2 THEN NULL ELSE actual_value END AS actual_value,
		       baseline_value, forecast_value, forecast_lower, forecast_upper,
		       target_value, continuity_value, unit, calibration_status, source_agency, mode,
		       as_of_valid_until
		FROM indicator_trajectories
		WHERE ($1 = '' OR indicator_id = $1)
		  AND mode = $3
		  AND created_at <= $2
		ORDER BY indicator_id ASC, period_date ASC
	) t`

	var data json.RawMessage
	err := a.db.QueryRow(ctx, sql, indicatorID, asOf, mode).Scan(&data)
	if err != nil {
		slog.Warn("query_trajectories_db_failed", "error", err, "mode", mode)
		if mode == "fixture" {
			fixtures, ferr := loadTrajectoriesFixture()
			if ferr == nil {
				var filtered []TrajectoryPoint
				for _, pt := range fixtures {
					if indicatorID != "" && pt.IndicatorID != indicatorID {
						continue
					}
					if pt.AsOfValidUntil != nil && pt.AsOfValidUntil.After(asOf) {
						pt.ActualValue = nil
					}
					filtered = append(filtered, pt)
				}
				if indicatorID != "" && len(filtered) == 0 {
					write(w, http.StatusNotFound, map[string]string{"error": "indicator trajectory not found"})
					return
				}
				write(w, http.StatusOK, map[string]any{"meta": meta, "data": filtered})
				return
			}
		}
		write(w, http.StatusServiceUnavailable, map[string]string{"error": "data temporarily unavailable"})
		return
	}

	var rawList []json.RawMessage
	_ = json.Unmarshal(data, &rawList)
	if indicatorID != "" && len(rawList) == 0 && mode == "fixture" {
		write(w, http.StatusNotFound, map[string]string{"error": "indicator trajectory not found"})
		return
	}

	write(w, http.StatusOK, map[string]any{"meta": meta, "data": data})
}
