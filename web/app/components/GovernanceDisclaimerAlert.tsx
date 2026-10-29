"use client";

import React from "react";

export function GovernanceDisclaimerAlert() {
  return (
    <div
      style={{
        background: "#fbfaf2",
        border: "1px solid #d4c89a",
        borderLeft: "4px solid #98711c",
        borderRadius: "4px",
        padding: "16px 20px",
        margin: "32px 0",
        color: "var(--ink, #15342d)",
      }}
      role="region"
      aria-label="Aviso de Governança e Neutralidade Institucional"
    >
      <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "6px" }}>
        <span
          style={{
            fontSize: "10px",
            letterSpacing: "1.5px",
            textTransform: "uppercase",
            fontWeight: 800,
            background: "#efe4be",
            color: "#6b4f12",
            padding: "2px 8px",
            borderRadius: "3px",
          }}
        >
          Governança Constitucional & Neutralidade
        </span>
        <span style={{ fontSize: "12px", color: "var(--muted, #52675d)" }}>
          Princípios Invariantes — specs/mission.md & governance.md
        </span>
      </div>
      <p style={{ margin: 0, fontSize: "13.5px", lineHeight: "1.55" }}>
        <strong>Aviso Legal e Metodológico:</strong> Todas as propostas do Policy Lab e metas do Guidance Brasil são hipóteses analíticas independentes para fins de estudo e simulação contrafactual. 
        Não constituem compromissos oficiais do Estado brasileiro, planos governamentais vigentes ou conselho de investimento. 
        Nenhuma validação econômica ou ratificação de gate é declarada de forma automática pelo sistema sem parecer humano formal.
      </p>
    </div>
  );
}
