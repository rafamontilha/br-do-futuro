"use client";

import React, { useState, useEffect } from "react";

export interface DependencyNode {
  id: string;
  node_type: "indicator" | "model" | "scenario" | "guidance_target" | string;
  canonical_name: string;
  domain_id?: number;
  description: string;
}

export interface DependencyEdge {
  id: string;
  source_node_id: string;
  target_node_id: string;
  relationship_type: string;
  materiality_rule: string;
  threshold_value: number;
}

interface DependencyGraphVisualizerProps {
  isOpen: boolean;
  onClose: () => void;
}

const relationshipLabels: Record<string, string> = {
  direct_input: "Entrada Direta",
  accounting_identity: "Identidade Contábil",
  behavioral_elasticity: "Elasticidade Comportamental",
  target_benchmark: "Benchmark de Meta",
};

const materialityRuleLabels: Record<string, string> = {
  delta_absolute: "Variação Absoluta (Δ)",
  target_breach: "Ruptura de Meta",
  composite: "Composta (Δ + Meta)",
};

const nodeTypeColors: Record<string, { bg: string; text: string; border: string }> = {
  indicator: { bg: "#e3f0f7", text: "#1d5d85", border: "#93c5e0" },
  model: { bg: "#f3e8ff", text: "#6b21a8", border: "#d8b4fe" },
  scenario: { bg: "#fef3c7", text: "#92400e", border: "#fde68a" },
  guidance_target: { bg: "#def0e5", text: "#1a5e3a", border: "#86efac" },
};

export function DependencyGraphVisualizer({ isOpen, onClose }: DependencyGraphVisualizerProps) {
  const [nodes, setNodes] = useState<DependencyNode[]>([]);
  const [edges, setEdges] = useState<DependencyEdge[]>([]);
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    if (!isOpen) return;
    setLoading(true);
    fetch("/api/v1/dependencies")
      .then((res) => res.json())
      .then((payload) => {
        if (payload?.data) {
          setNodes(payload.data.nodes || []);
          setEdges(payload.data.edges || []);
        }
      })
      .catch((err) => console.error("Failed to load dependencies:", err))
      .finally(() => setLoading(false));
  }, [isOpen]);

  if (!isOpen) return null;

  const indicators = nodes.filter((n) => n.node_type === "indicator");
  const modelsAndScenarios = nodes.filter(
    (n) => n.node_type === "model" || n.node_type === "scenario"
  );
  const targets = nodes.filter((n) => n.node_type === "guidance_target");

  const filteredEdges = selectedNode
    ? edges.filter(
        (e) => e.source_node_id === selectedNode || e.target_node_id === selectedNode
      )
    : edges;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="dag-modal-title"
      style={{
        position: "fixed",
        inset: 0,
        backgroundColor: "rgba(10, 20, 15, 0.65)",
        backdropFilter: "blur(4px)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 1000,
        padding: "16px",
      }}
      onClick={onClose}
    >
      <div
        style={{
          background: "#ffffff",
          borderRadius: "10px",
          maxWidth: "1080px",
          width: "100%",
          maxHeight: "90vh",
          overflowY: "auto",
          padding: "24px 28px",
          boxShadow: "0 20px 25px -5px rgba(0, 0, 0, 0.2)",
          border: "1px solid #d1dbd6",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "flex-start",
            borderBottom: "1px solid #e5eae7",
            paddingBottom: "16px",
            marginBottom: "20px",
          }}
        >
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <span
                style={{
                  fontSize: "11px",
                  fontWeight: 800,
                  textTransform: "uppercase",
                  background: "#e3f0f7",
                  color: "#1d5d85",
                  padding: "2px 8px",
                  borderRadius: "4px",
                }}
              >
                DAG de Causalidade & Impacto
              </span>
              <span style={{ fontSize: "12px", color: "var(--muted, #52675d)" }}>
                Fase 1 · Item 3
              </span>
            </div>
            <h2 id="dag-modal-title" style={{ fontSize: "20px", fontWeight: 700, margin: "6px 0 0 0" }}>
              Grafo de Dependências e Recálculo Seletivo
            </h2>
          </div>
          <button
            onClick={onClose}
            aria-label="Fechar visualizador"
            style={{
              background: "transparent",
              border: "none",
              fontSize: "24px",
              cursor: "pointer",
              color: "#52675d",
              padding: "4px 8px",
            }}
          >
            ×
          </button>
        </div>

        <div
          style={{
            background: "#f8faf9",
            border: "1px solid #e1e8e5",
            borderRadius: "6px",
            padding: "12px 16px",
            marginBottom: "20px",
            fontSize: "13px",
            lineHeight: 1.5,
            color: "#2c3e35",
          }}
        >
          <strong>Como funciona o Motor de Dependências:</strong> Quando uma série do núcleo P0 é atualizada ou revisada, o motor calcula o caminho topológico e executa <em>apenas</em> os modelos e cenários a jusante diretamente afetados. Se a variação projetada ultrapassar o limiar de materialidade ou violar a banda de uma meta institucional, um alerta com bloqueio de publicação é acionado automaticamente para revisão humana formal.
        </div>

        {loading ? (
          <p style={{ textAlign: "center", padding: "40px", color: "#52675d" }}>
            Carregando estrutura formal do DAG...
          </p>
        ) : (
          <>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
                gap: "16px",
                marginBottom: "24px",
              }}
            >
              {/* Coluna 1: Indicadores P0 */}
              <div style={{ background: "#fafbfc", border: "1px solid #e2e8f0", borderRadius: "8px", padding: "14px" }}>
                <h3 style={{ fontSize: "13px", fontWeight: 700, color: "#1d5d85", margin: "0 0 12px 0", textTransform: "uppercase", letterSpacing: "0.5px" }}>
                  1. Indicadores Oficiais P0 (Origem)
                </h3>
                <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                  {indicators.map((n) => {
                    const isSelected = selectedNode === n.id;
                    const colors = nodeTypeColors[n.node_type] || { bg: "#f3f4f6", text: "#111827", border: "#d1d5db" };
                    return (
                      <div
                        key={n.id}
                        onClick={() => setSelectedNode(isSelected ? null : n.id)}
                        style={{
                          padding: "10px 12px",
                          borderRadius: "6px",
                          background: isSelected ? "#bae6fd" : colors.bg,
                          border: `1.5px solid ${isSelected ? "#0284c7" : colors.border}`,
                          cursor: "pointer",
                          transition: "all 0.15s ease",
                        }}
                      >
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                          <strong style={{ fontSize: "12.5px", color: colors.text }}>{n.canonical_name}</strong>
                          <span style={{ fontSize: "10.5px", background: "#ffffff", padding: "1px 6px", borderRadius: "4px", color: "#64748b" }}>
                            {n.id.replace("indicator:", "")}
                          </span>
                        </div>
                        <p style={{ fontSize: "11.5px", color: "#475569", margin: "4px 0 0 0" }}>{n.description}</p>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Coluna 2: Modelos e Cenários */}
              <div style={{ background: "#fafbfc", border: "1px solid #e2e8f0", borderRadius: "8px", padding: "14px" }}>
                <h3 style={{ fontSize: "13px", fontWeight: 700, color: "#6b21a8", margin: "0 0 12px 0", textTransform: "uppercase", letterSpacing: "0.5px" }}>
                  2. Modelos & Cenários (Processamento)
                </h3>
                <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                  {modelsAndScenarios.map((n) => {
                    const isSelected = selectedNode === n.id;
                    const colors = nodeTypeColors[n.node_type] || { bg: "#f3f4f6", text: "#111827", border: "#d1d5db" };
                    return (
                      <div
                        key={n.id}
                        onClick={() => setSelectedNode(isSelected ? null : n.id)}
                        style={{
                          padding: "10px 12px",
                          borderRadius: "6px",
                          background: isSelected ? "#e9d5ff" : colors.bg,
                          border: `1.5px solid ${isSelected ? "#9333ea" : colors.border}`,
                          cursor: "pointer",
                          transition: "all 0.15s ease",
                        }}
                      >
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                          <strong style={{ fontSize: "12.5px", color: colors.text }}>{n.canonical_name}</strong>
                          <span style={{ fontSize: "10.5px", background: "#ffffff", padding: "1px 6px", borderRadius: "4px", color: "#64748b" }}>
                            {n.node_type}
                          </span>
                        </div>
                        <p style={{ fontSize: "11.5px", color: "#475569", margin: "4px 0 0 0" }}>{n.description}</p>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Coluna 3: Metas e Compromissos */}
              <div style={{ background: "#fafbfc", border: "1px solid #e2e8f0", borderRadius: "8px", padding: "14px" }}>
                <h3 style={{ fontSize: "13px", fontWeight: 700, color: "#1a5e3a", margin: "0 0 12px 0", textTransform: "uppercase", letterSpacing: "0.5px" }}>
                  3. Metas do Guidance & CMN (Destino)
                </h3>
                <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                  {targets.map((n) => {
                    const isSelected = selectedNode === n.id;
                    const colors = nodeTypeColors[n.node_type] || { bg: "#f3f4f6", text: "#111827", border: "#d1d5db" };
                    return (
                      <div
                        key={n.id}
                        onClick={() => setSelectedNode(isSelected ? null : n.id)}
                        style={{
                          padding: "10px 12px",
                          borderRadius: "6px",
                          background: isSelected ? "#bbf7d0" : colors.bg,
                          border: `1.5px solid ${isSelected ? "#16a34a" : colors.border}`,
                          cursor: "pointer",
                          transition: "all 0.15s ease",
                        }}
                      >
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                          <strong style={{ fontSize: "12.5px", color: colors.text }}>{n.canonical_name}</strong>
                          <span style={{ fontSize: "10.5px", background: "#ffffff", padding: "1px 6px", borderRadius: "4px", color: "#64748b" }}>
                            Meta Oficial
                          </span>
                        </div>
                        <p style={{ fontSize: "11.5px", color: "#475569", margin: "4px 0 0 0" }}>{n.description}</p>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>

            {/* Arestas e Relações de Materialidade */}
            <div>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
                <h4 style={{ fontSize: "13px", fontWeight: 700, margin: 0 }}>
                  Arestas de Causalidade & Limiares de Materialidade ({filteredEdges.length})
                </h4>
                {selectedNode && (
                  <button
                    onClick={() => setSelectedNode(null)}
                    style={{
                      background: "#e2e8f0",
                      border: "none",
                      borderRadius: "4px",
                      padding: "4px 8px",
                      fontSize: "11px",
                      cursor: "pointer",
                    }}
                  >
                    Limpar Filtro ({selectedNode})
                  </button>
                )}
              </div>
              <div style={{ maxHeight: "240px", overflowY: "auto", border: "1px solid #e2e8f0", borderRadius: "6px" }}>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "12px", textAlign: "left" }}>
                  <thead style={{ background: "#f1f5f9", position: "sticky", top: 0 }}>
                    <tr>
                      <th style={{ padding: "8px 10px" }}>Origem (Montante)</th>
                      <th style={{ padding: "8px 10px" }}>Destino (Jusante)</th>
                      <th style={{ padding: "8px 10px" }}>Natureza da Relação</th>
                      <th style={{ padding: "8px 10px" }}>Regra de Materialidade</th>
                      <th style={{ padding: "8px 10px" }}>Limiar de Disparo</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredEdges.map((e) => (
                      <tr key={e.id} style={{ borderBottom: "1px solid #f1f5f9" }}>
                        <td style={{ padding: "8px 10px", fontWeight: 600 }}><code>{e.source_node_id}</code></td>
                        <td style={{ padding: "8px 10px", fontWeight: 600 }}><code>{e.target_node_id}</code></td>
                        <td style={{ padding: "8px 10px" }}>
                          <span style={{ background: "#f1f5f9", padding: "2px 6px", borderRadius: "4px" }}>
                            {relationshipLabels[e.relationship_type] || e.relationship_type}
                          </span>
                        </td>
                        <td style={{ padding: "8px 10px" }}>
                          {materialityRuleLabels[e.materiality_rule] || e.materiality_rule}
                        </td>
                        <td style={{ padding: "8px 10px", fontWeight: 700, color: "#b91c1c" }}>
                          {e.threshold_value} p.p.
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </>
        )}

        <div style={{ marginTop: "20px", display: "flex", justifyContent: "flex-end" }}>
          <button
            onClick={onClose}
            style={{
              background: "#1d5d85",
              color: "#ffffff",
              border: "none",
              borderRadius: "6px",
              padding: "8px 18px",
              fontSize: "13px",
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            Fechar
          </button>
        </div>
      </div>
    </div>
  );
}
