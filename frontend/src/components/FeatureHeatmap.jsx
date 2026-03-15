// FeatureHeatmap — grid of feature health cells.
// Each cell is colour-coded by severity and shows PSI / p-value.

import React, { useState } from "react";

const SEV_COLOR = {
  critical:     { bg: "#3d1a0a", border: "#c0440a", text: "#f07030", dot: "#f07030" },
  warning:      { bg: "#2a2206", border: "#8a6a00", text: "#c9a020", dot: "#c9a020" },
  stable:       { bg: "#0a1a0e", border: "#1a5c28", text: "#30a050", dot: "#30a050" },
  type_mismatch:{ bg: "#1a0a2a", border: "#6030a0", text: "#a060e0", dot: "#a060e0" },
};

function metric(data) {
  if (data.type === "numerical")  return `PSI ${data.psi?.toFixed(3) ?? "—"}`;
  if (data.type === "categorical") return `p=${data.chi2_test?.p_value?.toFixed(3) ?? "—"}`;
  return "type mismatch";
}

function meanDelta(data) {
  if (data.type !== "numerical") return null;
  const { ref_mean, cur_mean } = data;
  if (ref_mean == null || cur_mean == null || ref_mean === 0) return null;
  const pct = ((cur_mean - ref_mean) / Math.abs(ref_mean)) * 100;
  return pct;
}

export default function FeatureHeatmap({ features = {}, onFeatureClick }) {
  const [hovered, setHovered] = useState(null);

  const entries = Object.entries(features);
  if (!entries.length) return null;

  return (
    <div style={{ fontFamily: "'IBM Plex Mono', monospace" }}>
      <div style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))",
        gap: "8px",
      }}>
        {entries.map(([name, data]) => {
          const sev    = data.severity || "stable";
          const colors = SEV_COLOR[sev] || SEV_COLOR.stable;
          const delta  = meanDelta(data);
          const isHov  = hovered === name;

          return (
            <div
              key={name}
              onClick={() => onFeatureClick?.(name, data)}
              onMouseEnter={() => setHovered(name)}
              onMouseLeave={() => setHovered(null)}
              style={{
                background:   isHov ? colors.border + "22" : colors.bg,
                border:       `1px solid ${isHov ? colors.border : colors.border + "66"}`,
                borderRadius: "4px",
                padding:      "12px 14px",
                cursor:       "pointer",
                transition:   "all 0.15s ease",
                position:     "relative",
                overflow:     "hidden",
              }}
            >
              {/* severity dot */}
              <div style={{
                position:     "absolute",
                top: 10, right: 10,
                width: 7, height: 7,
                borderRadius: "50%",
                background:   colors.dot,
                boxShadow:    `0 0 6px ${colors.dot}`,
              }} />

              {/* feature name */}
              <div style={{
                fontSize: "11px",
                color:    colors.text,
                fontWeight: 600,
                marginBottom: "6px",
                textTransform: "uppercase",
                letterSpacing: "0.04em",
                paddingRight: "16px",
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: "nowrap",
              }}>
                {name}
              </div>

              {/* type badge */}
              <div style={{
                fontSize: "9px",
                color:    colors.text + "88",
                marginBottom: "8px",
                textTransform: "uppercase",
                letterSpacing: "0.06em",
              }}>
                {data.type}
              </div>

              {/* metric */}
              <div style={{
                fontSize: "13px",
                color:    colors.text,
                fontWeight: 500,
              }}>
                {metric(data)}
              </div>

              {/* mean delta for numerical */}
              {delta != null && (
                <div style={{
                  fontSize:  "11px",
                  color:     Math.abs(delta) > 20 ? colors.text : colors.text + "99",
                  marginTop: "4px",
                }}>
                  mean {delta > 0 ? "+" : ""}{delta.toFixed(1)}%
                </div>
              )}

              {/* severity label */}
              <div style={{
                fontSize:      "9px",
                color:         colors.text,
                marginTop:     "8px",
                textTransform: "uppercase",
                letterSpacing: "0.1em",
                fontWeight:    700,
              }}>
                {sev}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}