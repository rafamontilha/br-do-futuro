"""Formal Dependency Graph (DAG) and Selective Recalculation Engine for Brasil do Futuro."""
import logging
from collections import deque
from decimal import Decimal
from typing import Any, Dict, List, Set, Tuple

from psycopg.types.json import Jsonb

from .scenario import fingerprint

logger = logging.getLogger(__name__)

# Canonical fallback graph definitions in case database tables are being initialized
CANONICAL_NODES: List[Dict[str, Any]] = [
    {"id": "indicator:br.debt.gross_pct_gdp", "node_type": "indicator", "canonical_name": "Dívida Bruta (% PIB)", "domain_id": 5, "description": "Dívida Bruta do Governo Geral em proporção do PIB"},
    {"id": "indicator:br.ipca.12m", "node_type": "indicator", "canonical_name": "IPCA 12 Meses", "domain_id": 2, "description": "Inflação oficial acumulada em 12 meses"},
    {"id": "indicator:br.selic.target_annual", "node_type": "indicator", "canonical_name": "Taxa Selic Meta", "domain_id": 3, "description": "Meta da taxa Selic definida pelo Copom"},
    {"id": "indicator:br.gdp.quarterly_yoy", "node_type": "indicator", "canonical_name": "PIB Trimestral (YoY)", "domain_id": 1, "description": "Crescimento real interanual do PIB"},
    {"id": "indicator:br.fx.usd_brl.ptax", "node_type": "indicator", "canonical_name": "Câmbio USD/BRL (PTAX)", "domain_id": 4, "description": "Taxa de câmbio comercial PTAX"},
    {"id": "indicator:br.labor.unemployment_rate", "node_type": "indicator", "canonical_name": "Taxa de Desocupação", "domain_id": 6, "description": "Taxa de desocupação PNAD Contínua"},
    {"id": "model:fiscal_path_v1", "node_type": "model", "canonical_name": "Identidade Fiscal v1", "domain_id": 5, "description": "Modelo canônico da evolução da dívida/PIB"},
    {"id": "scenario:continuity", "node_type": "scenario", "canonical_name": "Cenário Continuidade", "domain_id": 5, "description": "Trajetória inercial fiscal sem alterações"},
    {"id": "scenario:alternative", "node_type": "scenario", "canonical_name": "Cenário Alternativo", "domain_id": 5, "description": "Trajetória com ajuste fiscal estrutural"},
    {"id": "scenario:adverse", "node_type": "scenario", "canonical_name": "Cenário Adverso", "domain_id": 5, "description": "Trajetória de estresse macroeconômico"},
    {"id": "scenario:dynamic_simulations", "node_type": "scenario", "canonical_name": "Simulações Dinâmicas", "domain_id": 5, "description": "Mecanismo de simulação de premissas interativas"},
    {"id": "guidance_target:debt_stabilization", "node_type": "guidance_target", "canonical_name": "Estabilização da Dívida", "domain_id": 5, "description": "Meta de estabilização da Dívida/PIB até 2030"},
    {"id": "guidance_target:inflation_target_cmn", "node_type": "guidance_target", "canonical_name": "Meta Contínua de Inflação", "domain_id": 2, "description": "Meta CMN 3,00% com banda de 1,5 p.p."},
    {"id": "guidance_target:selic_neutral_band", "node_type": "guidance_target", "canonical_name": "Banda Neutra de Juros", "domain_id": 3, "description": "Faixa referencial neutra de juros reais"}
]

CANONICAL_EDGES: List[Dict[str, Any]] = [
    {"source_node_id": "indicator:br.debt.gross_pct_gdp", "target_node_id": "model:fiscal_path_v1", "relationship_type": "direct_input", "materiality_rule": "delta_absolute", "threshold_value": Decimal("0.50")},
    {"source_node_id": "model:fiscal_path_v1", "target_node_id": "scenario:continuity", "relationship_type": "accounting_identity", "materiality_rule": "delta_absolute", "threshold_value": Decimal("0.50")},
    {"source_node_id": "model:fiscal_path_v1", "target_node_id": "scenario:alternative", "relationship_type": "accounting_identity", "materiality_rule": "delta_absolute", "threshold_value": Decimal("0.50")},
    {"source_node_id": "model:fiscal_path_v1", "target_node_id": "scenario:adverse", "relationship_type": "accounting_identity", "materiality_rule": "delta_absolute", "threshold_value": Decimal("0.50")},
    {"source_node_id": "indicator:br.debt.gross_pct_gdp", "target_node_id": "scenario:dynamic_simulations", "relationship_type": "direct_input", "materiality_rule": "delta_absolute", "threshold_value": Decimal("0.50")},
    {"source_node_id": "indicator:br.selic.target_annual", "target_node_id": "model:fiscal_path_v1", "relationship_type": "behavioral_elasticity", "materiality_rule": "delta_absolute", "threshold_value": Decimal("0.25")},
    {"source_node_id": "indicator:br.gdp.quarterly_yoy", "target_node_id": "model:fiscal_path_v1", "relationship_type": "direct_input", "materiality_rule": "delta_absolute", "threshold_value": Decimal("0.50")},
    {"source_node_id": "scenario:continuity", "target_node_id": "guidance_target:debt_stabilization", "relationship_type": "target_benchmark", "materiality_rule": "target_breach", "threshold_value": Decimal("0.50")},
    {"source_node_id": "indicator:br.ipca.12m", "target_node_id": "guidance_target:inflation_target_cmn", "relationship_type": "target_benchmark", "materiality_rule": "composite", "threshold_value": Decimal("0.25")},
    {"source_node_id": "indicator:br.selic.target_annual", "target_node_id": "guidance_target:selic_neutral_band", "relationship_type": "target_benchmark", "materiality_rule": "delta_absolute", "threshold_value": Decimal("0.25")}
]


def load_graph(conn) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, List[Dict[str, Any]]]]:
    """Loads nodes and adjacency list (edges) from database with fallback to canonical definitions."""
    nodes: Dict[str, Dict[str, Any]] = {}
    adj: Dict[str, List[Dict[str, Any]]] = {}

    try:
        cur_nodes = conn.execute("SELECT id, node_type, canonical_name, domain_id, description FROM dependency_graph_nodes").fetchall()
        for r in cur_nodes:
            nodes[r[0]] = {
                "id": r[0],
                "node_type": r[1],
                "canonical_name": r[2],
                "domain_id": r[3],
                "description": r[4]
            }
        
        cur_edges = conn.execute("SELECT source_node_id, target_node_id, relationship_type, materiality_rule, threshold_value FROM dependency_graph_edges").fetchall()
        for e in cur_edges:
            adj.setdefault(e[0], []).append({
                "source_node_id": e[0],
                "target_node_id": e[1],
                "relationship_type": e[2],
                "materiality_rule": e[3],
                "threshold_value": Decimal(str(e[4]))
            })
    except Exception as exc:
        logger.warning("Could not read dependency graph from database; using canonical fallback: %s", exc)

    if not nodes:
        for n in CANONICAL_NODES:
            nodes[n["id"]] = n
        for e in CANONICAL_EDGES:
            adj.setdefault(e["source_node_id"], []).append(e)

    return nodes, adj


def get_downstream_nodes(adj: Dict[str, List[Dict[str, Any]]], start_node: str) -> List[Dict[str, Any]]:
    """Returns all downstream nodes reachable from start_node in topological order."""
    visited: Set[str] = set()
    order: List[Dict[str, Any]] = []
    queue: deque = deque([start_node])

    while queue:
        curr = queue.popleft()
        for edge in adj.get(curr, []):
            target = edge["target_node_id"]
            if target not in visited:
                visited.add(target)
                order.append(edge)
                queue.append(target)
    return order


def resolve_recalculation_plan(conn, event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Given an ingestion event, computes downstream affected components
    and registers an immutable recalculation plan in the database.
    """
    p = event["payload"]
    indicator_id = p.get("indicator_id")
    if not indicator_id:
        return {"trigger_indicator_id": None, "affected_nodes": [], "status": "skipped", "rationale": "No indicator_id"}

    start_node = f"indicator:{indicator_id}"
    nodes, adj = load_graph(conn)
    edges = get_downstream_nodes(adj, start_node)

    affected_nodes: List[Dict[str, Any]] = []
    seen: Set[str] = set()
    for e in edges:
        target_id = e["target_node_id"]
        if target_id not in seen:
            seen.add(target_id)
            node_meta = nodes.get(target_id, {"id": target_id, "node_type": "unknown", "canonical_name": target_id})
            affected_nodes.append({
                "node_id": target_id,
                "node_type": node_meta.get("node_type"),
                "canonical_name": node_meta.get("canonical_name"),
                "relationship": e.get("relationship_type"),
                "materiality_rule": e.get("materiality_rule"),
                "threshold_value": str(e.get("threshold_value"))
            })

    rationale = f"Recálculo seletivo disparado por {event.get('event_type', 'Update')} em {indicator_id}. {len(affected_nodes)} nós a jusante afetados."
    plan_id = fingerprint({"event_id": str(event.get("id")), "trigger": indicator_id, "affected_count": len(affected_nodes)})

    status = "executed" if affected_nodes else "skipped"

    # Verify if event_id actually exists in outbox to satisfy FK constraint
    event_id = event.get("id")
    valid_event_id = None
    if event_id:
        try:
            if conn.execute("SELECT 1 FROM outbox WHERE id=%s", (event_id,)).fetchone():
                valid_event_id = event_id
        except Exception:
            pass

    try:
        conn.execute("""
            INSERT INTO recalculation_plan (id, event_id, trigger_indicator_id, affected_nodes, rationale, status)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING
        """, (plan_id, valid_event_id, indicator_id, Jsonb(affected_nodes), rationale, status))
    except Exception as exc:
        logger.error("Failed to persist recalculation plan: %s", exc)

    return {
        "id": plan_id,
        "trigger_indicator_id": indicator_id,
        "affected_nodes": affected_nodes,
        "rationale": rationale,
        "status": status
    }
