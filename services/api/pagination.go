package main

import (
	"encoding/json"
	"net/http"
	"strconv"
)

type PaginationParams struct {
	Limit  int `json:"limit"`
	Offset int `json:"offset"`
}

type PaginationMeta struct {
	Limit   int  `json:"limit"`
	Offset  int  `json:"offset"`
	Total   int  `json:"total"`
	HasMore bool `json:"has_more"`
}

func parsePaginationParams(r *http.Request) PaginationParams {
	limit := 50
	if l := r.URL.Query().Get("limit"); l != "" {
		if val, err := strconv.Atoi(l); err == nil && val > 0 {
			if val > 200 {
				limit = 200
			} else {
				limit = val
			}
		}
	}

	offset := 0
	if o := r.URL.Query().Get("offset"); o != "" {
		if val, err := strconv.Atoi(o); err == nil && val >= 0 {
			offset = val
		}
	}

	return PaginationParams{
		Limit:  limit,
		Offset: offset,
	}
}

// paginateJSONArray aplica paginação de forma segura em uma lista serializada em json.RawMessage
func paginateJSONArray(raw json.RawMessage, params PaginationParams) (json.RawMessage, PaginationMeta, error) {
	if len(raw) == 0 || string(raw) == "[]" {
		return json.RawMessage("[]"), PaginationMeta{
			Limit:   params.Limit,
			Offset:  params.Offset,
			Total:   0,
			HasMore: false,
		}, nil
	}

	var items []json.RawMessage
	if err := json.Unmarshal(raw, &items); err != nil {
		return raw, PaginationMeta{}, err
	}

	total := len(items)
	if params.Offset >= total {
		return json.RawMessage("[]"), PaginationMeta{
			Limit:   params.Limit,
			Offset:  params.Offset,
			Total:   total,
			HasMore: false,
		}, nil
	}

	end := params.Offset + params.Limit
	hasMore := false
	if end < total {
		hasMore = true
	} else {
		end = total
	}

	pagedItems := items[params.Offset:end]
	resBytes, err := json.Marshal(pagedItems)
	if err != nil {
		return raw, PaginationMeta{}, err
	}

	return json.RawMessage(resBytes), PaginationMeta{
		Limit:   params.Limit,
		Offset:  params.Offset,
		Total:   total,
		HasMore: hasMore,
	}, nil
}
