package main

import (
	"context"
	"encoding/json"
	"net/http/httptest"
	"os"
	"path/filepath"
	"testing"
	"time"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
)

// Only bdf_test is writable. A private schema avoids touching Python fixtures or
// any locally collected payloads; the API pool runs under its actual reader role.
func backtestTestDB(t *testing.T) (*pgx.Conn, *API) {
	t.Helper()
	dsn := os.Getenv("TEST_DATABASE_URL")
	if dsn == "" {
		t.Skip("TEST_DATABASE_URL required for PostgreSQL integration")
	}
	ctx := context.Background()
	cfg, err := pgx.ParseConfig(dsn)
	if err != nil {
		t.Fatal(err)
	}
	if cfg.Database != "bdf_test" {
		t.Fatal("Refuse integration writes outside bdf_test")
	}
	admin, err := pgx.ConnectConfig(ctx, cfg)
	if err != nil {
		t.Fatal(err)
	}
	var database string
	if err = admin.QueryRow(ctx, "SELECT current_database()").Scan(&database); err != nil || database != "bdf_test" {
		admin.Close(ctx)
		t.Fatal("Refuse integration writes outside bdf_test", err)
	}
	schema := "backtest_api_" + newUUID()[:8]
	quoted := pgx.Identifier{schema}.Sanitize()
	if _, err = admin.Exec(ctx, "CREATE SCHEMA "+quoted); err != nil {
		admin.Close(ctx)
		t.Fatal(err)
	}
	t.Cleanup(func() {
		if _, err := admin.Exec(ctx, "DROP SCHEMA "+quoted+" CASCADE"); err != nil {
			t.Error(err)
		}
		admin.Close(ctx)
	})
	if _, err = admin.Exec(ctx, "SET search_path TO "+quoted); err != nil {
		t.Fatal(err)
	}
	for _, migration := range []string{"001_foundation.sql", "009_forecast_backtesting.sql"} {
		body, err := os.ReadFile(filepath.Join("..", "..", "db", migration))
		if err != nil {
			t.Fatal(err)
		}
		if _, err = admin.Exec(ctx, string(body)); err != nil {
			t.Fatal(err)
		}
	}
	if _, err = admin.Exec(ctx, "GRANT USAGE ON SCHEMA "+quoted+" TO bdf_reader"); err != nil {
		t.Fatal(err)
	}
	readCfg, err := pgxpool.ParseConfig(dsn)
	if err != nil {
		t.Fatal(err)
	}
	readCfg.ConnConfig.RuntimeParams["search_path"] = schema
	readCfg.AfterConnect = func(ctx context.Context, conn *pgx.Conn) error {
		_, err := conn.Exec(ctx, "SET ROLE bdf_reader")
		return err
	}
	reader, err := pgxpool.NewWithConfig(ctx, readCfg)
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(reader.Close)
	return admin, &API{db: reader}
}

func mustTime(t *testing.T, value string) time.Time {
	t.Helper()
	parsed, err := time.Parse("2006-01-02Z", value)
	if err != nil {
		t.Fatal(err)
	}
	return parsed
}

func TestBacktestsPostgreSQL(t *testing.T) {
	admin, a := backtestTestDB(t)
	ctx := context.Background()
	exec := func(sql string, args ...any) {
		t.Helper()
		if _, err := admin.Exec(ctx, sql, args...); err != nil {
			t.Fatal(err)
		}
	}
	get := func(path string, status int) map[string]any {
		t.Helper()
		w := httptest.NewRecorder()
		a.handle(w, httptest.NewRequest("GET", path, nil))
		if w.Code != status {
			t.Fatalf("%s: want %d got %d: %s", path, status, w.Code, w.Body)
		}
		var body map[string]any
		if err := json.Unmarshal(w.Body.Bytes(), &body); err != nil {
			t.Fatal(err)
		}
		return body
	}
	getData := func(path string, want int, run string) map[string]any {
		t.Helper()
		body := get(path, 200)
		if len(body["data"].([]any)) != want {
			t.Fatalf("unexpected metrics: %v", body)
		}
		if body["experimental"] != true {
			t.Fatal("missing experimental flag")
		}
		if run == "" {
			if body["run"] != nil {
				t.Fatalf("expected no run: %v", body)
			}
		} else if body["run"].(map[string]any)["run_id"] != run {
			t.Fatalf("wrong run: %v", body)
		}
		return body
	}
	var role string
	if err := a.db.QueryRow(ctx, "SELECT current_user").Scan(&role); err != nil || role != "bdf_reader" {
		t.Fatalf("API integration must use reader role: %s %v", role, err)
	}
	base := "/v1/backtests?as_of=2026-01-01T00:00:00Z"
	getData(base, 0, "")
	old, newer, future, late, fixture := newUUID(), newUUID(), newUUID(), newUUID(), newUUID()
	addRun := func(id, cutoff, created, mode string) {
		exec(`INSERT INTO backtest_run(id,inputs_hash,code_version,as_of,min_sample,mode,created_at)
            VALUES ($1,$5,'test-engine-v1',$2,8,$4,$3)`, id, mustTime(t, cutoff), mustTime(t, created), mode, id)
	}
	addRun(old, "2025-01-01Z", "2025-01-02Z", "source")
	addRun(newer, "2025-02-01Z", "2025-02-02Z", "source")
	addRun(future, "2027-01-01Z", "2025-02-03Z", "source")
	addRun(late, "2025-03-01Z", "2027-01-01Z", "source")
	addRun(fixture, "2025-05-01Z", "2025-05-02Z", "fixture")
	addMetric := func(run, indicator, source, target, kind string, horizon int) {
		exec(`INSERT INTO backtest_metric(run_id,indicator_id,horizon,forecast_source,target,origin_kind,
            unit,n_obs,mae,rmse,bias,interval_coverage,relative_mae_vs_rw,insufficient_sample)
            VALUES ($1,$2,$6,$3,$4,$5,'percent_year',2,4,5,-2,NULL,1.6,true)`, run, indicator, source, target, kind, horizon)
	}
	addMetric(old, "only.old", "trajectory", "first_release", "ex_ante", 1)
	addMetric(newer, "br.ipca.12m", "trajectory", "first_release", "ex_ante", 12)
	addMetric(newer, "br.ipca.12m", "scenario_run", "latest", "reconstructed", 2)
	addMetric(newer, "br.debt.gross_pct_gdp", "scenario_run", "first_release", "ex_ante", 12)
	addMetric(fixture, "fixture.only", "trajectory", "latest", "reconstructed", 1)
	getData(base, 3, newer)
	getData(base+"&indicator_id=br.ipca.12m", 2, newer)
	filtered := getData(base+"&indicator_id=br.ipca.12m&horizon=12&target=first_release&forecast_source=trajectory", 1, newer)
	metric := filtered["data"].([]any)[0].(map[string]any)
	if metric["interval_coverage"] != nil || metric["insufficient_sample"] != true || metric["unit"] != "percent_year" || metric["bias"] != float64(-2) {
		t.Fatalf("metric values lost: %v", metric)
	}
	getData(base+"&indicator_id=only.old", 0, newer) // never fall back to an older run
	getData(base+"&horizon=0", 0, newer)
	getData(base+"&mode=fixture", 1, fixture)
	getData("/v1/backtests?as_of=2025-01-15T00:00:00Z", 1, old)
	getData("/v1/backtests?as_of=2025-02-01T12:00:00Z", 1, old) // new run not yet persisted
	getData("/v1/backtests?as_of=2024-01-01T00:00:00Z", 0, "")
	// Two synthetic forecasts and one benchmark; only forecasts count as coverage.
	for _, source := range []string{"trajectory", "scenario_run", "benchmark_random_walk"} {
		exec(`INSERT INTO forecast_snapshot(id,indicator_id,target_period,forecast_origin_at,horizon,frequency,
            forecast_source,model_version,point_value,unit,origin_kind,mode,created_at)
            VALUES ($1,'br.ipca.12m','2025-01-01','2024-01-01Z',12,'monthly',$2,'test-v1',3,'percent_year','ex_ante','source','2024-01-02Z')`, newUUID(), source)
	}
	exec(`INSERT INTO forecast_snapshot(id,indicator_id,target_period,forecast_origin_at,horizon,frequency,
        forecast_source,model_version,point_value,unit,origin_kind,mode,created_at)
        VALUES ($1,'br.ipca.12m','2025-01-01','2024-01-01Z',12,'monthly','trajectory','future-v1',3,'percent_year','ex_ante','source','2027-01-01Z')`, newUUID())
	monitor := func(query string) map[string]any {
		body := get("/v1/observability/metrics?"+query, 200)
		models := body["data"].(map[string]any)["models"].(map[string]any)
		if models["backtesting_status"] != "available" {
			t.Fatalf("monitor unavailable: %v", models)
		}
		return models["backtesting"].(map[string]any)
	}
	historical := monitor("as_of=2023-01-01T00:00:00Z")
	if historical["ex_ante_snapshots_count"] != float64(0) || historical["last_run"] != nil {
		t.Fatalf("future snapshots/run leaked: %v", historical)
	}
	monitoring := monitor("as_of=2026-01-01T00:00:00Z")
	if monitoring["ex_ante_snapshots_count"] != float64(2) || monitoring["backtested_indicators_count"] != float64(2) || monitoring["last_run"].(map[string]any)["run_id"] != newer {
		t.Fatalf("incorrect coverage/cutoff: %v", monitoring)
	}
	monitoring = monitor("mode=fixture&as_of=2026-01-01T00:00:00Z")
	if monitoring["ex_ante_snapshots_count"] != float64(0) || monitoring["ex_ante_backtested_indicators_count"] != float64(0) || monitoring["backtested_indicators_count"] != float64(1) {
		t.Fatalf("mode isolation broken: %v", monitoring)
	}
	empty := newUUID()
	addRun(empty, "2025-12-01Z", "2025-12-02Z", "source")
	getData(base, 0, empty)
	monitoring = monitor("as_of=2026-01-01T00:00:00Z")
	if monitoring["backtested_indicators_count"] != float64(0) {
		t.Fatalf("coverage borrowed from old run: %v", monitoring)
	}
	exec("ALTER TABLE backtest_metric RENAME TO unavailable_metric")
	get(base, 503)
	get("/v1/observability/metrics?as_of=2026-01-01T00:00:00Z", 503)
}
