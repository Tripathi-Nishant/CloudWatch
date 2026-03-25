// SchemaPanel — displays schema drift issues in a clean list.

import React from "react";

const ISSUE_ICONS = {
  missing_column:    "⬡",
  extra_column:      "⬢",
  type_change:       "⟳",
  null_rate_increase:"↑",
  unseen_categories: "?",
};

const SEV = {
  critical: { color: "#f07030", bg: "#3d1a0a", border: "#c0440a44" },
  warning:  { color: "#c9a020", bg: "#2a2206", border: "#8a6a0044" },
  stable:   { color: "#30a050", bg: "#0a1a0e", border: "#1a5c2844" },
};

export default function SchemaPanel({ schema }) {
  if (!schema) return null;

  const { has_drift, critical_count, warning_count, issues = [] } = schema;

  return (
    <div style={{ fontFamily: "'IBM Plex Mono', monospace" }}>

      {/* Summary bar */}
      <div style={{
        display:       "flex",
        gap:           "20px",
        marginBottom:  "16px",
        fontSize:      "12px",
      }}>
        <span style={{ color: has_drift ? "#f07030" : "#30a050" }}>
          {has_drift ? "schema issues detected" : "schema ok"}
        </span>
        {critical_count > 0 && (
          <span style={{ color: "#f07030" }}>{critical_count} critical</span>
        )}
        {warning_count > 0 && (
          <span style={{ color: "#c9a020" }}>{warning_count} warning</span>
        )}
      </div>

      {/* Issue list */}
      {issues.length === 0 ? (
        <div style={{
          padding:      "20px",
          textAlign:    "center",
          color:        "#2a5a2e",
          fontSize:     "12px",
          border:       "1px solid #1a3a1e",
          borderRadius: "4px",
        }}>
          No schema issues detected
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
          {issues.map((issue, i) => {
            const s = SEV[issue.severity] || SEV.warning;
            const icon = ISSUE_ICONS[issue.issue] || "!";
            return (
              <div key={i} style={{
                background:   s.bg,
                border:       `1px solid ${s.border}`,
                borderRadius: "3px",
                padding:      "10px 14px",
                display:      "flex",
                gap:          "12px",
                alignItems:   "flex-start",
              }}>
                {/* icon + type */}
                <div style={{
                  color:      s.color,
                  fontSize:   "16px",
                  lineHeight: 1,
                  minWidth:   "16px",
                  marginTop:  "1px",
                }}>
                  {icon}
                </div>
                <div style={{ flex: 1 }}>
                  <div style={{
                    fontSize:      "10px",
                    color:         s.color,
                    textTransform: "uppercase",
                    letterSpacing: "0.08em",
                    marginBottom:  "4px",
                    fontWeight:    700,
                  }}>
                    {issue.issue.replace(/_/g, " ")} — {issue.column}
                  </div>
                  <div style={{
                    fontSize:   "12px",
                    color:      "#8a9a8c",
                    lineHeight: 1.5,
                  }}>
                    {issue.detail}
                  </div>
                </div>
                {/* severity badge */}
                <div style={{
                  fontSize:      "9px",
                  color:         s.color,
                  border:        `1px solid ${s.color}44`,
                  borderRadius:  "2px",
                  padding:       "2px 6px",
                  textTransform: "uppercase",
                  letterSpacing: "0.08em",
                  whiteSpace:    "nowrap",
                  alignSelf:     "center",
                }}>
                  {issue.severity}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}