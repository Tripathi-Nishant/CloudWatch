// StatCards — the four header metric cards at the top of the dashboard.

import React from "react";

const SEV_STYLES = {
  critical: { color: "#f07030", bg: "#3d1a0a", border: "#c0440a66", glow: "#f0703020" },
  warning:  { color: "#c9a020", bg: "#2a2206", border: "#8a6a0066", glow: "#c9a02020" },
  stable:   { color: "#30a050", bg: "#0a1a0e", border: "#1a5c2866", glow: "#30a05020" },
};

function Card({ label, value, sub, severity }) {
  const s = SEV_STYLES[severity] || SEV_STYLES.stable;
  return (
    <div style={{
      background:   s.bg,
      border:       `1px solid ${s.border}`,
      borderRadius: "4px",
      padding:      "16px 20px",
      flex:         1,
      minWidth:     "140px",
      boxShadow:    `0 0 20px ${s.glow}`,
    }}>
      <div style={{
        fontSize:      "9px",
        color:         s.color + "99",
        textTransform: "uppercase",
        letterSpacing: "0.12em",
        marginBottom:  "8px",
        fontFamily:    "'IBM Plex Mono', monospace",
      }}>
        {label}
      </div>
      <div style={{
        fontSize:   "28px",
        color:      s.color,
        fontFamily: "'IBM Plex Mono', monospace",
        fontWeight: 600,
        lineHeight: 1,
        marginBottom: "4px",
      }}>
        {value}
      </div>
      {sub && (
        <div style={{
          fontSize:   "11px",
          color:      s.color + "66",
          fontFamily: "'IBM Plex Mono', monospace",
        }}>
          {sub}
        </div>
      )}
    </div>
  );
}

export default function StatCards({ report }) {
  if (!report) {
    return (
      <div style={{ display: "flex", gap: "12px", flexWrap: "wrap" }}>
        {["Overall Status", "Features Checked", "Drifted", "Schema Issues"].map(label => (
          <div key={label} style={{
            flex: 1, minWidth: "140px",
            background: "#0d1117",
            border: "1px solid #1a2a1c",
            borderRadius: "4px",
            padding: "16px 20px",
            height: "80px",
          }} />
        ))}
      </div>
    );
  }

  const {
    overall_severity,
    features_checked,
    drifted_count,
    schema,
    reference_rows,
    current_rows,
  } = report;

  const schemaIssues = (schema?.critical_count || 0) + (schema?.warning_count || 0);

  return (
    <div style={{ display: "flex", gap: "12px", flexWrap: "wrap" }}>
      <Card
        label="Overall Status"
        value={overall_severity?.toUpperCase()}
        sub={`${reference_rows?.toLocaleString()} train / ${current_rows?.toLocaleString()} serving`}
        severity={overall_severity}
      />
      <Card
        label="Features Checked"
        value={features_checked}
        sub="total features analysed"
        severity="stable"
      />
      <Card
        label="Drifted"
        value={`${drifted_count} / ${features_checked}`}
        sub={drifted_count === 0 ? "all stable" : "need attention"}
        severity={drifted_count === 0 ? "stable" : drifted_count > features_checked / 2 ? "critical" : "warning"}
      />
      <Card
        label="Schema Issues"
        value={schemaIssues}
        sub={`${schema?.critical_count || 0} critical · ${schema?.warning_count || 0} warning`}
        severity={schema?.overall_severity || "stable"}
      />
    </div>
  );
}