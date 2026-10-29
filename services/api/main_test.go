package main

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

func TestQueryOptions(t *testing.T) {
	for _, tc := range []struct {
		url   string
		valid bool
		mode  string
	}{
		{"/?mode=fixture&as_of=2025-01-01T00:00:00Z", true, "fixture"},
		{"/", true, "source"}, {"/?mode=invalid", false, ""}, {"/?as_of=2025-01-01", false, ""},
	} {
		mode, _, err := queryOptions(httptest.NewRequest("GET", tc.url, nil))
		if (err == nil) != tc.valid || (tc.valid && mode != tc.mode) {
			t.Errorf("unexpected result for %s: %s %v", tc.url, mode, err)
		}
	}
}

func TestRejectWrites(t *testing.T) {
	a := &API{}
	w := httptest.NewRecorder()
	a.handle(w, httptest.NewRequest("POST", "/v1/indicators", nil))
	if w.Code != 405 {
		t.Fatalf("expected 405, got %d", w.Code)
	}

	wPut := httptest.NewRecorder()
	a.handle(wPut, httptest.NewRequest("PUT", "/v1/simulations/fiscal", nil))
	if wPut.Code != 405 {
		t.Fatalf("expected 405, got %d", wPut.Code)
	}
}

func TestValidateSimulationRequests(t *testing.T) {
	a := &API{db: nil} // db nil will test validation before db access or return 503 if validation passes
	for _, tc := range []struct {
		name         string
		payload      string
		expectedCode int
	}{
		{"invalid json", `{"invalid":`, 400},
		{"missing base debt", `{"assumptions": {"interest":"0.10","growth":"0.05","primary":"0.00"}}`, 400},
		{"invalid base debt", `{"base_debt_pct": "-10", "assumptions": {"interest":"0.10","growth":"0.05","primary":"0.00"}}`, 400},
		{"missing assumptions", `{"base_debt_pct": "75.0"}`, 400},
		{"missing interest", `{"base_debt_pct": "75.0", "assumptions": {"growth":"0.05","primary":"0.00"}}`, 400},
		{"bad growth constraint", `{"base_debt_pct": "75.0", "assumptions": {"interest":"0.10","growth":"-1.5","primary":"0.00"}}`, 400},
		{"bad horizon", `{"base_debt_pct": "75.0", "assumptions": {"interest":"0.10","growth":"0.05","primary":"0.00","horizon_years":50}}`, 400},
	} {
		t.Run(tc.name, func(t *testing.T) {
			w := httptest.NewRecorder()
			r := httptest.NewRequest("POST", "/v1/simulations/fiscal", bytes.NewBufferString(tc.payload))
			a.handle(w, r)
			if w.Code != tc.expectedCode {
				t.Fatalf("for %s: expected %d, got %d", tc.name, tc.expectedCode, w.Code)
			}
		})
	}
}

func TestNewUUID(t *testing.T) {
	u1 := newUUID()
	u2 := newUUID()
	if len(u1) != 36 || len(u2) != 36 {
		t.Fatalf("invalid uuid length: %s, %s", u1, u2)
	}
	if u1 == u2 {
		t.Fatal("expected distinct uuids")
	}
	if strings.Count(u1, "-") != 4 {
		t.Fatalf("malformed uuid structure: %s", u1)
	}
}

func TestValidateOutboxReplay(t *testing.T) {
	a := &API{db: nil}
	for _, tc := range []struct {
		name         string
		payload      string
		token        string
		expectedCode int
	}{
		{"unauthenticated returns 401", `{"reason": "test"}`, "", 401},
		{"producer role returns 403", `{"reason": "test"}`, "bdf-producer-token-2026", 403},
		{"invalid json", `{"reason":`, "bdf-reviewer-token-2026", 400},
		{"empty reason", `{"reason": "   "}`, "bdf-reviewer-token-2026", 400},
		{"missing reason", `{"triggered_by": "operator"}`, "bdf-reviewer-token-2026", 400},
		{"valid reason returns 503 when db nil", `{"reason": "audit fix test"}`, "bdf-reviewer-token-2026", 503},
	} {
		t.Run(tc.name, func(t *testing.T) {
			w := httptest.NewRecorder()
			r := httptest.NewRequest("POST", "/v1/admin/outbox/replay", bytes.NewBufferString(tc.payload))
			if tc.token != "" {
				r.Header.Set("Authorization", "Bearer "+tc.token)
			}
			a.handle(w, r)
			if w.Code != tc.expectedCode {
				t.Fatalf("for %s: expected %d, got %d", tc.name, tc.expectedCode, w.Code)
			}
		})
	}
}

func TestSourceHealthWithoutDB(t *testing.T) {
	a := &API{db: nil}
	w := httptest.NewRecorder()
	r := httptest.NewRequest("GET", "/v1/health/sources", nil)
	a.handle(w, r)
	if w.Code != 503 {
		t.Fatalf("expected 503 when db nil, got %d", w.Code)
	}
}

func TestProposalsEndpointsWithoutDB(t *testing.T) {
	a := &API{db: nil}

	wList := httptest.NewRecorder()
	rList := httptest.NewRequest("GET", "/v1/proposals", nil)
	a.handle(wList, rList)
	if wList.Code != 503 {
		t.Fatalf("expected 503 when db nil, got %d", wList.Code)
	}

	wDetail := httptest.NewRecorder()
	rDetail := httptest.NewRequest("GET", "/v1/proposals/prop-fiscal-mandatory-spending", nil)
	a.handle(wDetail, rDetail)
	if wDetail.Code != 503 {
		t.Fatalf("expected 503 when db nil, got %d", wDetail.Code)
	}

	wEmpty := httptest.NewRecorder()
	rEmpty := httptest.NewRequest("GET", "/v1/proposals/%20", nil)
	a.handle(wEmpty, rEmpty)
	if wEmpty.Code != 404 {
		t.Fatalf("expected 404 for empty proposal id, got %d", wEmpty.Code)
	}
}

func TestGuidanceCommitmentsWithoutDB(t *testing.T) {
	a := &API{db: nil}
	w := httptest.NewRecorder()
	r := httptest.NewRequest("GET", "/v1/guidance/commitments", nil)
	a.handle(w, r)
	if w.Code != 503 {
		t.Fatalf("expected 503 when db nil, got %d", w.Code)
	}
}

func TestFiscalCalibrationsWithoutDB(t *testing.T) {
	a := &API{db: nil}
	w := httptest.NewRecorder()
	r := httptest.NewRequest("GET", "/v1/scenarios/calibrations", nil)
	a.handle(w, r)
	if w.Code != 503 {
		t.Fatalf("expected 503 when db nil, got %d", w.Code)
	}
}

func TestGuidanceAndProposalsAsOfValidation(t *testing.T) {
	a := &API{db: nil}
	for _, path := range []string{
		"/v1/guidance/commitments?as_of=invalid-date",
		"/v1/proposals?as_of=not-a-timestamp",
		"/v1/scenarios/calibrations?as_of=2020-99-99",
	} {
		w := httptest.NewRecorder()
		r := httptest.NewRequest("GET", path, nil)
		a.handle(w, r)
		if w.Code != 400 {
			t.Fatalf("expected 400 bad request for %s, got %d", path, w.Code)
		}
	}
}

func TestDecisionAuditValidation(t *testing.T) {
	a := &API{db: nil}
	for _, tc := range []struct {
		name         string
		method       string
		path         string
		payload      string
		token        string
		expectedCode int
	}{
		{"POST audit unauthenticated returns 401", "POST", "/v1/admin/audit/decisions", `{"action":"test"}`, "", 401},
		{"POST audit producer role returns 403", "POST", "/v1/admin/audit/decisions", `{"action":"test"}`, "bdf-producer-token-2026", 403},
		{"POST audit reviewer invalid json", "POST", "/v1/admin/audit/decisions", `{"action":`, "bdf-reviewer-token-2026", 400},
		{"POST audit reviewer missing action", "POST", "/v1/admin/audit/decisions", `{"entity_type":"calib","entity_id":"c1","justification":"ok","new_state":{}}`, "bdf-reviewer-token-2026", 400},
		{"POST audit reviewer missing new_state", "POST", "/v1/admin/audit/decisions", `{"action":"approve","entity_type":"calib","entity_id":"c1","justification":"ok"}`, "bdf-reviewer-token-2026", 400},
		{"POST audit reviewer valid returns 503 without db", "POST", "/v1/admin/audit/decisions", `{"action":"approve","entity_type":"calib","entity_id":"c1","justification":"ok","new_state":{"status":"ok"}}`, "bdf-reviewer-token-2026", 503},
		{"GET audit unauthenticated returns 401", "GET", "/v1/admin/audit/decisions", "", "", 401},
		{"GET audit producer role returns 403", "GET", "/v1/admin/audit/decisions", "", "bdf-producer-token-2026", 403},
		{"GET audit reviewer returns 503 without db", "GET", "/v1/admin/audit/decisions", "", "bdf-reviewer-token-2026", 503},
	} {
		t.Run(tc.name, func(t *testing.T) {
			w := httptest.NewRecorder()
			var r *http.Request
			if tc.payload != "" {
				r = httptest.NewRequest(tc.method, tc.path, bytes.NewBufferString(tc.payload))
			} else {
				r = httptest.NewRequest(tc.method, tc.path, nil)
			}
			if tc.token != "" {
				r.Header.Set("Authorization", "Bearer "+tc.token)
			}
			a.handle(w, r)
			if w.Code != tc.expectedCode {
				t.Fatalf("for %s: expected %d, got %d", tc.name, tc.expectedCode, w.Code)
			}
		})
	}
}

func TestObservabilityMetricsEndpoint(t *testing.T) {
	a := &API{db: nil}
	w := httptest.NewRecorder()
	r := httptest.NewRequest("GET", "/v1/observability/metrics", nil)
	a.handle(w, r)
	if w.Code != 200 {
		t.Fatalf("expected 200 for observability metrics, got %d", w.Code)
	}
	body := w.Body.String()
	for _, key := range []string{"platform", "data", "models", "decisions", "slo_compliance", "database_status"} {
		if !strings.Contains(body, key) {
			t.Errorf("missing expected key in observability response: %s", key)
		}
	}
}

func TestRateLimiterLogic(t *testing.T) {
	rl := NewRateLimiter()
	// Test with 2 RPM limit
	allowed, remaining, _ := rl.Allow("client-test-1", 2)
	if !allowed || remaining != 1 {
		t.Fatalf("expected first request allowed with 1 token remaining, got %v, %d", allowed, remaining)
	}
	allowed2, remaining2, _ := rl.Allow("client-test-1", 2)
	if !allowed2 || remaining2 != 0 {
		t.Fatalf("expected second request allowed with 0 tokens remaining, got %v, %d", allowed2, remaining2)
	}
	allowed3, _, retryAfter := rl.Allow("client-test-1", 2)
	if allowed3 {
		t.Fatalf("expected third request to be rejected by rate limiter")
	}
	if retryAfter <= 0 {
		t.Fatalf("expected positive retry-after duration, got %v", retryAfter)
	}
}

func TestPaginationJSONArray(t *testing.T) {
	raw := []byte(`[{"id": 1}, {"id": 2}, {"id": 3}, {"id": 4}, {"id": 5}]`)
	paged, meta, err := paginateJSONArray(raw, PaginationParams{Limit: 2, Offset: 0})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if meta.Total != 5 || !meta.HasMore || meta.Limit != 2 || meta.Offset != 0 {
		t.Fatalf("unexpected pagination meta: %+v", meta)
	}
	if string(paged) != `[{"id":1},{"id":2}]` {
		t.Fatalf("unexpected paged data: %s", string(paged))
	}

	pagedLast, metaLast, err := paginateJSONArray(raw, PaginationParams{Limit: 2, Offset: 4})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if metaLast.HasMore || string(pagedLast) != `[{"id":5}]` {
		t.Fatalf("expected single last item with has_more=false, got: %s, meta: %+v", string(pagedLast), metaLast)
	}
}

func TestCanonicalGenesisHash(t *testing.T) {
	m := map[string]any{
		"action":         "initialize_audit_ledger",
		"actor_id":       "system-genesis",
		"actor_role":     "system",
		"entity_id":      "bdf-foundation",
		"entity_type":    "system",
		"event_id":       nil,
		"id":             "audit-genesis-0000",
		"justification":  "Gênese da trilha imutável de auditoria de decisões do Brasil do Futuro (Incremento 04)",
		"new_state":      map[string]any{"status": "initialized", "version": "v1.4"},
		"prev_log_hash":  "0000000000000000000000000000000000000000000000000000000000000000",
		"previous_state": nil,
	}
	bytes, err := json.Marshal(m)
	if err != nil {
		t.Fatalf("failed to marshal: %v", err)
	}
	t.Logf("Go JSON: %s", string(bytes))
	h := computePayloadHash(m)
	t.Logf("Go Hash: %s", h)
}
