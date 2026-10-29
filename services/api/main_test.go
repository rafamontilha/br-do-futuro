package main

import (
	"bytes"
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
		expectedCode int
	}{
		{"invalid json", `{"reason":`, 400},
		{"empty reason", `{"reason": "   "}`, 400},
		{"missing reason", `{"triggered_by": "operator"}`, 400},
		{"valid reason returns 503 when db nil", `{"reason": "audit fix test"}`, 503},
	} {
		t.Run(tc.name, func(t *testing.T) {
			w := httptest.NewRecorder()
			r := httptest.NewRequest("POST", "/v1/admin/outbox/replay", bytes.NewBufferString(tc.payload))
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
