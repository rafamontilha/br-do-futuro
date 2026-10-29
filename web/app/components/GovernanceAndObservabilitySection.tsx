"use client";

import React, { useState } from "react";
import { RoleSwitcherBadge, RoleType } from "./RoleSwitcherBadge";
import { ObservabilityPlanesPanel, ObservabilityData } from "./ObservabilityPlanesPanel";

interface GovernanceAndObservabilitySectionProps {
  initialMetrics?: ObservabilityData;
}

export function GovernanceAndObservabilitySection({
  initialMetrics,
}: GovernanceAndObservabilitySectionProps) {
  const [currentRole, setCurrentRole] = useState<RoleType>("public");

  return (
    <div style={{ margin: "24px 0" }}>
      <RoleSwitcherBadge
        currentRole={currentRole}
        onRoleChange={setCurrentRole}
      />
      <ObservabilityPlanesPanel
        currentRole={currentRole}
        initialMetrics={initialMetrics}
      />
    </div>
  );
}
