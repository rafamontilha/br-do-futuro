"use client";

import React from "react";

export type RoleType = "public" | "producer" | "reviewer" | "publisher";

export interface RoleConfig {
  id: RoleType;
  label: string;
  roleName: string;
  token: string;
  quotaRPM: number;
  badgeColor: string;
  badgeBg: string;
  permissions: string[];
}

export const ROLES: Record<RoleType, RoleConfig> = {
  public: {
    id: "public",
    label: "Público Visitante",
    roleName: "Visitante / Leitura",
    token: "",
    quotaRPM: 60,
    badgeColor: "#52675d",
    badgeBg: "#e9edea",
    permissions: ["Leitura de indicadores", "Consulta de cenários", "Simulação local"],
  },
  producer: {
    id: "producer",
    label: "Produtor de Dados",
    roleName: "Produtor (Data/Ingestion)",
    token: "bdf-producer-token-2026",
    quotaRPM: 120,
    badgeColor: "#1d5d85",
    badgeBg: "#e3f0f7",
    permissions: ["Captura de fontes", "Submissão de raw payloads", "Simulações preliminares"],
  },
  reviewer: {
    id: "reviewer",
    label: "Revisor Metodológico",
    roleName: "Revisor Independente",
    token: "bdf-reviewer-token-2026",
    quotaRPM: 200,
    badgeColor: "#85581d",
    badgeBg: "#faedd9",
    permissions: ["Revisão de anomalias", "Homologação de calibrações", "Acesso à auditoria"],
  },
  publisher: {
    id: "publisher",
    label: "Publicador de Políticas",
    roleName: "Publicador (Guidance & Policy)",
    token: "bdf-publisher-token-2026",
    quotaRPM: 300,
    badgeColor: "#1a5e3a",
    badgeBg: "#def0e5",
    permissions: ["Publicação de Guidance", "Replay operacional amplo", "Emissão de relatórios oficiais"],
  },
};

interface RoleSwitcherBadgeProps {
  currentRole: RoleType;
  onRoleChange: (role: RoleType) => void;
}

export function RoleSwitcherBadge({ currentRole, onRoleChange }: RoleSwitcherBadgeProps) {
  const current = ROLES[currentRole];

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        flexWrap: "wrap",
        gap: "12px",
        background: "#ffffff",
        border: "1px solid #d1dbd6",
        borderRadius: "6px",
        padding: "10px 16px",
        marginBottom: "24px",
      }}
      role="region"
      aria-label="Controle de Acesso e Papéis Institucionais (RBAC)"
    >
      <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
        <span
          style={{
            fontSize: "11px",
            fontWeight: 800,
            textTransform: "uppercase",
            letterSpacing: "1px",
            color: "var(--muted, #52675d)",
          }}
        >
          Papel Institucional Ativo:
        </span>
        <span
          style={{
            fontSize: "12px",
            fontWeight: 700,
            color: current.badgeColor,
            background: current.badgeBg,
            padding: "3px 10px",
            borderRadius: "4px",
            display: "inline-flex",
            alignItems: "center",
            gap: "6px",
          }}
        >
          <span style={{ width: "7px", height: "7px", borderRadius: "50%", background: current.badgeColor }} />
          {current.roleName}
        </span>
        <span style={{ fontSize: "11px", color: "var(--muted, #52675d)" }}>
          (Quota: {current.quotaRPM} req/min)
        </span>
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
        <span style={{ fontSize: "11.5px", color: "var(--muted, #52675d)", marginRight: "4px" }}>
          Alternar Papel:
        </span>
        {(Object.keys(ROLES) as RoleType[]).map((rKey) => {
          const cfg = ROLES[rKey];
          const isActive = rKey === currentRole;
          return (
            <button
              key={rKey}
              onClick={() => onRoleChange(rKey)}
              style={{
                fontSize: "11.5px",
                fontWeight: isActive ? 700 : 500,
                padding: "4px 10px",
                borderRadius: "4px",
                border: isActive ? `1.5px solid ${cfg.badgeColor}` : "1px solid #d1dbd6",
                background: isActive ? cfg.badgeBg : "#f7f9f8",
                color: isActive ? cfg.badgeColor : "var(--ink, #15342d)",
                cursor: "pointer",
                transition: "all 0.15s ease",
              }}
              title={`Permissões: ${cfg.permissions.join(", ")}`}
            >
              {cfg.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}
