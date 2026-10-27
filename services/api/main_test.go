package main

import (
	"net/http/httptest"
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
		t.Fatal(w.Code)
	}
}
