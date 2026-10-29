package main

import (
	"context"
	"encoding/json"
	"log/slog"
	"net/http"
	"time"
)

var apiStartTime = time.Now().UTC()

type PlatformPlane struct {
	UptimeSeconds  int64    `json:"uptime_seconds"`
	DatabaseStatus string   `json:"database_status"`
	ErrorRatePct   *float64 `json:"error_rate_pct"`
	P95LatencyMS   *float64 `json:"p95_latency_ms"`
}

type DataPlane struct {
	TrackedSeriesCount int        `json:"tracked_series_count"`
	StaleSeriesCount   int        `json:"stale_series_count"`
	QuarantineCount    int        `json:"quarantine_count"`
	LastIngestionAt    *time.Time `json:"last_ingestion_at,omitempty"`
}

type ModelsPlane struct {
	ActiveScenariosCount      int        `json:"active_scenarios_count"`
	CalibratedParametersCount int        `json:"calibrated_parameters_count"`
	LastSimulationAt          *time.Time `json:"last_simulation_at,omitempty"`
}

type DecisionsPlane struct {
	TotalDecisionsCount int   `json:"total_decisions_count"`
	PendingReviewsCount int   `json:"pending_reviews_count"`
	AuditChainIntact    *bool `json:"audit_chain_intact"`
}

type SLOCompliance struct {
	SourceWindowCompliancePct   *float64 `json:"source_window_compliance_pct"`
	MetadataCompletenessPct     *float64 `json:"metadata_completeness_pct"`
	ScenarioLineageCoveragePct *float64 `json:"scenario_lineage_coverage_pct"`
	ReproducibleForecastsPct    *float64 `json:"reproducible_forecasts_pct"`
}

type ObservabilitySnapshot struct {
	Timestamp     time.Time      `json:"timestamp"`
	Platform      PlatformPlane  `json:"platform"`
	Data          DataPlane      `json:"data"`
	Models        ModelsPlane    `json:"models"`
	Decisions     DecisionsPlane `json:"decisions"`
	SLOCompliance SLOCompliance  `json:"slo_compliance"`
}

func (a *API) handleGetObservabilityMetrics(w http.ResponseWriter, r *http.Request, ctx context.Context, meta map[string]any) {
	now := time.Now().UTC()
	dbStatus := "unconfigured"

	if a.db != nil {
		if err := a.db.Ping(ctx); err != nil {
			dbStatus = "unreachable"
		} else {
			dbStatus = "healthy"
		}
	}

	trackedSeries := 0
	if len(a.catalog) > 0 {
		var cat struct {
			Indicators []any `json:"indicators"`
		}
		if err := json.Unmarshal(a.catalog, &cat); err == nil {
			trackedSeries = len(cat.Indicators)
		}
	}

	snapshot := ObservabilitySnapshot{
		Timestamp: now,
		Platform: PlatformPlane{
			UptimeSeconds:  int64(now.Sub(apiStartTime).Seconds()),
			DatabaseStatus: dbStatus,
			ErrorRatePct:   nil,
			P95LatencyMS:   nil,
		},
		Data: DataPlane{
			TrackedSeriesCount: trackedSeries,
			StaleSeriesCount:   0,
			QuarantineCount:    0,
		},
		Models: ModelsPlane{
			ActiveScenariosCount:      0,
			CalibratedParametersCount: 0,
		},
		Decisions: DecisionsPlane{
			TotalDecisionsCount: 0,
			PendingReviewsCount: 0,
			AuditChainIntact:    nil,
		},
		SLOCompliance: SLOCompliance{
			SourceWindowCompliancePct:   nil,
			MetadataCompletenessPct:     nil,
			ScenarioLineageCoveragePct: nil,
			ReproducibleForecastsPct:    nil,
		},
	}

	if a.db != nil && dbStatus == "healthy" {
		// 1. Métricas de Plataforma: Taxa de erro a partir de execuções de ingestão
		var totalRuns, failedRuns int
		err := a.db.QueryRow(ctx, `
			SELECT count(*), count(*) FILTER (WHERE status = 'failed')
			FROM ingestion_run
		`).Scan(&totalRuns, &failedRuns)
		if err == nil && totalRuns > 0 {
			rate := (float64(failedRuns) * 100.0) / float64(totalRuns)
			snapshot.Platform.ErrorRatePct = &rate
		}

		// 2. Métricas de Dados: Contratos, atrasos e quarentenas
		var scheduleCount int
		_ = a.db.QueryRow(ctx, `SELECT count(*) FROM source_schedules`).Scan(&scheduleCount)
		if scheduleCount > 0 {
			snapshot.Data.TrackedSeriesCount = scheduleCount
		}

		_ = a.db.QueryRow(ctx, `
			SELECT count(*) FROM source_schedules WHERE is_stale = true
		`).Scan(&snapshot.Data.StaleSeriesCount)

		_ = a.db.QueryRow(ctx, `
			SELECT count(*) FROM ingestion_run WHERE status = 'quarantined'
		`).Scan(&snapshot.Data.QuarantineCount)

		_ = a.db.QueryRow(ctx, `
			SELECT max(captured_at) FROM ingestion_run
		`).Scan(&snapshot.Data.LastIngestionAt)

		// 3. Métricas de Modelos: Cenários e calibrações
		_ = a.db.QueryRow(ctx, `
			SELECT count(DISTINCT scenario_id) FROM scenario_run
		`).Scan(&snapshot.Models.ActiveScenariosCount)

		_ = a.db.QueryRow(ctx, `
			SELECT count(*) FROM fiscal_calibrations
		`).Scan(&snapshot.Models.CalibratedParametersCount)

		_ = a.db.QueryRow(ctx, `
			SELECT max(requested_at) FROM dynamic_simulations
		`).Scan(&snapshot.Models.LastSimulationAt)

		// 4. Métricas de Decisões: Total de decisões e alertas pendentes de revisão humana
		_ = a.db.QueryRow(ctx, `
			SELECT count(*) FROM decision_audit_log
		`).Scan(&snapshot.Decisions.TotalDecisionsCount)

		_ = a.db.QueryRow(ctx, `
			SELECT count(*) FROM alert WHERE review_status = 'pending_human_review'
		`).Scan(&snapshot.Decisions.PendingReviewsCount)

		// 5. Validação criptográfica da integridade da cadeia de auditoria
		rows, err := a.db.Query(ctx, `
			SELECT id, event_id, actor_id, actor_role, action, entity_type, entity_id,
			       justification, previous_state, new_state, payload_hash, prev_log_hash
			FROM decision_audit_log
			ORDER BY created_at ASC, id ASC
		`)
		if err == nil {
			defer rows.Close()
			chainIntact := true
			recCount := 0
			var previousPayloadHash string
			genesisPrev := "0000000000000000000000000000000000000000000000000000000000000000"

			for rows.Next() {
				var recID, actorID, actorRole, action, entityType, entityID, justification, payloadHash, prevLogHash string
				var eventID *string
				var prevJSON, newJSON []byte

				if scanErr := rows.Scan(
					&recID, &eventID, &actorID, &actorRole, &action, &entityType, &entityID,
					&justification, &prevJSON, &newJSON, &payloadHash, &prevLogHash,
				); scanErr != nil {
					chainIntact = false
					break
				}

				var prevMap, newMap map[string]any
				if len(prevJSON) > 0 && string(prevJSON) != "null" {
					_ = json.Unmarshal(prevJSON, &prevMap)
				}
				if len(newJSON) > 0 && string(newJSON) != "null" {
					_ = json.Unmarshal(newJSON, &newMap)
				}

				// Verifica encadeamento
				if recCount == 0 {
					if prevLogHash != genesisPrev {
						chainIntact = false
						break
					}
				} else {
					if prevLogHash != previousPayloadHash {
						chainIntact = false
						break
					}
				}

				// Recalcula hash canônico do registro completo
				canonical := map[string]any{
					"action":         action,
					"actor_id":       actorID,
					"actor_role":     actorRole,
					"entity_id":      entityID,
					"entity_type":    entityType,
					"event_id":       eventID,
					"id":             recID,
					"justification":  justification,
					"new_state":      newMap,
					"prev_log_hash":  prevLogHash,
					"previous_state": prevMap,
				}
				if computePayloadHash(canonical) != payloadHash {
					chainIntact = false
					break
				}

				previousPayloadHash = payloadHash
				recCount++
			}

			if recCount == 0 {
				chainIntact = false
			}
			snapshot.Decisions.AuditChainIntact = &chainIntact
		}

		// 6. SLOs constitucionais medidos a partir de evidências reais
		var totalSchedules, compliantSchedules int
		err = a.db.QueryRow(ctx, `
			SELECT count(*), count(*) FILTER (WHERE NOT is_stale)
			FROM source_schedules
		`).Scan(&totalSchedules, &compliantSchedules)
		if err == nil && totalSchedules > 0 {
			pct := (float64(compliantSchedules) * 100.0) / float64(totalSchedules)
			snapshot.SLOCompliance.SourceWindowCompliancePct = &pct
		}

		var totalObs, completeObs int
		err = a.db.QueryRow(ctx, `
			SELECT count(*), count(*) FILTER (WHERE source_uri IS NOT NULL AND raw_hash IS NOT NULL AND vintage_id IS NOT NULL)
			FROM observation
		`).Scan(&totalObs, &completeObs)
		if err == nil && totalObs > 0 {
			pct := (float64(completeObs) * 100.0) / float64(totalObs)
			snapshot.SLOCompliance.MetadataCompletenessPct = &pct
		}

		var totalScenarios, lineageScenarios int
		err = a.db.QueryRow(ctx, `
			SELECT count(*), count(*) FILTER (WHERE vintage_id IS NOT NULL)
			FROM scenario_run
		`).Scan(&totalScenarios, &lineageScenarios)
		if err == nil && totalScenarios > 0 {
			pct := (float64(lineageScenarios) * 100.0) / float64(totalScenarios)
			snapshot.SLOCompliance.ScenarioLineageCoveragePct = &pct
		}

		var totalReplays, verifiedReplays int
		err = a.db.QueryRow(ctx, `
			SELECT count(*), count(*) FILTER (WHERE verified = true)
			FROM outbox_replay_audit
		`).Scan(&totalReplays, &verifiedReplays)
		if err == nil && totalReplays > 0 {
			pct := (float64(verifiedReplays) * 100.0) / float64(totalReplays)
			snapshot.SLOCompliance.ReproducibleForecastsPct = &pct
		}
	}

	slog.Info("observability_metrics_queried", "db_status", dbStatus, "uptime", snapshot.Platform.UptimeSeconds)
	write(w, http.StatusOK, map[string]any{
		"meta": meta,
		"data": snapshot,
	})
}
