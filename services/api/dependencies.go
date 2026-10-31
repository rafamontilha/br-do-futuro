package main

import (
	"context"
	"log/slog"
	"net/http"
	"time"
)

type DependencyNode struct {
	ID            string    `json:"id"`
	NodeType      string    `json:"node_type"`
	CanonicalName string    `json:"canonical_name"`
	DomainID      *int      `json:"domain_id,omitempty"`
	Description   string    `json:"description"`
	CreatedAt     time.Time `json:"created_at"`
}

type DependencyEdge struct {
	ID               string    `json:"id"`
	SourceNodeID     string    `json:"source_node_id"`
	TargetNodeID     string    `json:"target_node_id"`
	RelationshipType string    `json:"relationship_type"`
	MaterialityRule  string    `json:"materiality_rule"`
	ThresholdValue   float64   `json:"threshold_value"`
	CreatedAt        time.Time `json:"created_at"`
}

type DependencyGraphResponse struct {
	Nodes []DependencyNode `json:"nodes"`
	Edges []DependencyEdge `json:"edges"`
}

var fallbackCanonicalGraph = DependencyGraphResponse{
	Nodes: []DependencyNode{
		{ID: "indicator:br.debt.gross_pct_gdp", NodeType: "indicator", CanonicalName: "Dívida Bruta (% PIB)", Description: "Dívida Bruta do Governo Geral em proporção do PIB"},
		{ID: "indicator:br.ipca.12m", NodeType: "indicator", CanonicalName: "IPCA 12 Meses", Description: "Inflação oficial acumulada em 12 meses"},
		{ID: "indicator:br.selic.target_annual", NodeType: "indicator", CanonicalName: "Taxa Selic Meta", Description: "Meta da taxa Selic definida pelo Copom"},
		{ID: "indicator:br.gdp.quarterly_yoy", NodeType: "indicator", CanonicalName: "PIB Trimestral (YoY)", Description: "Crescimento real interanual do PIB"},
		{ID: "indicator:br.fx.usd_brl.ptax", NodeType: "indicator", CanonicalName: "Câmbio USD/BRL (PTAX)", Description: "Taxa de câmbio comercial PTAX"},
		{ID: "indicator:br.labor.unemployment_rate", NodeType: "indicator", CanonicalName: "Taxa de Desocupação", Description: "Taxa de desocupação PNAD Contínua"},
		{ID: "model:fiscal_path_v1", NodeType: "model", CanonicalName: "Identidade Fiscal v1", Description: "Modelo canônico da evolução da dívida/PIB"},
		{ID: "scenario:continuity", NodeType: "scenario", CanonicalName: "Cenário Continuidade", Description: "Trajetória inercial fiscal sem alterações"},
		{ID: "scenario:alternative", NodeType: "scenario", CanonicalName: "Cenário Alternativo", Description: "Trajetória com ajuste fiscal estrutural"},
		{ID: "scenario:adverse", NodeType: "scenario", CanonicalName: "Cenário Adverso", Description: "Trajetória de estresse macroeconômico"},
		{ID: "scenario:dynamic_simulations", NodeType: "scenario", CanonicalName: "Simulações Dinâmicas", Description: "Mecanismo de simulação de premissas interativas"},
		{ID: "guidance_target:debt_stabilization", NodeType: "guidance_target", CanonicalName: "Estabilização da Dívida", Description: "Meta de estabilização da Dívida/PIB até 2030"},
		{ID: "guidance_target:inflation_target_cmn", NodeType: "guidance_target", CanonicalName: "Meta Contínua de Inflação", Description: "Meta CMN 3,00% com banda de 1,5 p.p."},
		{ID: "guidance_target:selic_neutral_band", NodeType: "guidance_target", CanonicalName: "Banda Neutra de Juros", Description: "Faixa referencial neutra de juros reais"},
	},
	Edges: []DependencyEdge{
		{ID: "edge:debt->fiscal_model", SourceNodeID: "indicator:br.debt.gross_pct_gdp", TargetNodeID: "model:fiscal_path_v1", RelationshipType: "direct_input", MaterialityRule: "delta_absolute", ThresholdValue: 0.50},
		{ID: "edge:fiscal_model->continuity", SourceNodeID: "model:fiscal_path_v1", TargetNodeID: "scenario:continuity", RelationshipType: "accounting_identity", MaterialityRule: "delta_absolute", ThresholdValue: 0.50},
		{ID: "edge:fiscal_model->alternative", SourceNodeID: "model:fiscal_path_v1", TargetNodeID: "scenario:alternative", RelationshipType: "accounting_identity", MaterialityRule: "delta_absolute", ThresholdValue: 0.50},
		{ID: "edge:fiscal_model->adverse", SourceNodeID: "model:fiscal_path_v1", TargetNodeID: "scenario:adverse", RelationshipType: "accounting_identity", MaterialityRule: "delta_absolute", ThresholdValue: 0.50},
		{ID: "edge:debt->dynamic_sim", SourceNodeID: "indicator:br.debt.gross_pct_gdp", TargetNodeID: "scenario:dynamic_simulations", RelationshipType: "direct_input", MaterialityRule: "delta_absolute", ThresholdValue: 0.50},
		{ID: "edge:selic->fiscal_model", SourceNodeID: "indicator:br.selic.target_annual", TargetNodeID: "model:fiscal_path_v1", RelationshipType: "behavioral_elasticity", MaterialityRule: "delta_absolute", ThresholdValue: 0.25},
		{ID: "edge:gdp->fiscal_model", SourceNodeID: "indicator:br.gdp.quarterly_yoy", TargetNodeID: "model:fiscal_path_v1", RelationshipType: "direct_input", MaterialityRule: "delta_absolute", ThresholdValue: 0.50},
		{ID: "edge:continuity->debt_target", SourceNodeID: "scenario:continuity", TargetNodeID: "guidance_target:debt_stabilization", RelationshipType: "target_benchmark", MaterialityRule: "target_breach", ThresholdValue: 0.50},
		{ID: "edge:ipca->cmn_target", SourceNodeID: "indicator:br.ipca.12m", TargetNodeID: "guidance_target:inflation_target_cmn", RelationshipType: "target_benchmark", MaterialityRule: "composite", ThresholdValue: 0.25},
		{ID: "edge:selic->neutral_band", SourceNodeID: "indicator:br.selic.target_annual", TargetNodeID: "guidance_target:selic_neutral_band", RelationshipType: "target_benchmark", MaterialityRule: "delta_absolute", ThresholdValue: 0.25},
	},
}

func (a *API) handleGetDependencies(w http.ResponseWriter, r *http.Request, ctx context.Context, meta map[string]any) {
	if a.db == nil {
		meta["node_count"] = len(fallbackCanonicalGraph.Nodes)
		meta["edge_count"] = len(fallbackCanonicalGraph.Edges)
		write(w, http.StatusOK, map[string]any{
			"meta": meta,
			"data": fallbackCanonicalGraph,
		})
		return
	}

	nodesSQL := `SELECT id, node_type, canonical_name, domain_id, description, created_at FROM dependency_graph_nodes ORDER BY node_type, id`
	rows, err := a.db.Query(ctx, nodesSQL)
	if err != nil {
		slog.Warn("query_dependency_nodes_failed; using fallback", "error", err)
		meta["node_count"] = len(fallbackCanonicalGraph.Nodes)
		meta["edge_count"] = len(fallbackCanonicalGraph.Edges)
		write(w, http.StatusOK, map[string]any{
			"meta": meta,
			"data": fallbackCanonicalGraph,
		})
		return
	}
	defer rows.Close()

	var nodes []DependencyNode
	for rows.Next() {
		var n DependencyNode
		if err := rows.Scan(&n.ID, &n.NodeType, &n.CanonicalName, &n.DomainID, &n.Description, &n.CreatedAt); err != nil {
			slog.Error("scan_node_failed", "error", err)
			continue
		}
		nodes = append(nodes, n)
	}

	edgesSQL := `SELECT id, source_node_id, target_node_id, relationship_type, materiality_rule, threshold_value, created_at FROM dependency_graph_edges ORDER BY source_node_id, target_node_id`
	erows, err := a.db.Query(ctx, edgesSQL)
	if err != nil {
		slog.Warn("query_dependency_edges_failed; using fallback", "error", err)
		meta["node_count"] = len(nodes)
		meta["edge_count"] = len(fallbackCanonicalGraph.Edges)
		write(w, http.StatusOK, map[string]any{
			"meta": meta,
			"data": map[string]any{"nodes": nodes, "edges": fallbackCanonicalGraph.Edges},
		})
		return
	}
	defer erows.Close()

	var edges []DependencyEdge
	for erows.Next() {
		var e DependencyEdge
		if err := erows.Scan(&e.ID, &e.SourceNodeID, &e.TargetNodeID, &e.RelationshipType, &e.MaterialityRule, &e.ThresholdValue, &e.CreatedAt); err != nil {
			slog.Error("scan_edge_failed", "error", err)
			continue
		}
		edges = append(edges, e)
	}

	meta["node_count"] = len(nodes)
	meta["edge_count"] = len(edges)
	write(w, http.StatusOK, map[string]any{
		"meta": meta,
		"data": map[string]any{
			"nodes": nodes,
			"edges": edges,
		},
	})
}
