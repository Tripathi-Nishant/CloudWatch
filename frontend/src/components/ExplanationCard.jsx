// ExplanationCard — renders DIAGNOSIS / IMPACT / ACTION from the LLM.

import React, { useState } from "react";

function Section({ label, content }) {
  const LABELS = {
    DIAGNOSIS: { color: "#c9a020", icon: "▸" },
    IMPACT:    { color: "#f07030", icon: "▸" },
    ACTION:    { color: "#30a050", icon: "▸" },
  };
  const style = LABELS[label] || { color: "#888", icon: "▸" };

  return (
    <div style={{ marginBottom: "20px" }}>
      <div style={{
        fontSize:      "10px",
        color:         style.color,
        textTransform: "uppercase",
        letterSpacing: "0.12em",
        fontWeight:    700,
        marginBottom:  "8px",
        display:       "flex",
        alignItems:    "center",
        gap:           "6px",
      }}>
        <span>{style.icon}</span> {label}
      </div>
      <div style={{
        fontSize:   "13px",
        color:      "#8a9a8c",
        lineHeight: 1.7,
        paddingLeft:"12px",
        borderLeft: `2px solid ${style.color}33`,
      }}>
        {content.split("\n").map((line, i) => (
          line.trim() ? <div key={i} style={{ marginBottom: "4px" }}>{line.trim()}</div> : null
        ))}
      </div>
    </div>
  );
}

function parseExplanation(text) {
  // Split full_text into DIAGNOSIS / IMPACT / ACTION sections
  const sections = {};
  let current = null;
  const lines = text.split("\n");

  for (const line of lines) {
    const trimmed = line.trim();
    if (trimmed.startsWith("DIAGNOSIS")) { current = "DIAGNOSIS"; sections[current] = []; }
    else if (trimmed.startsWith("IMPACT")) { current = "IMPACT"; sections[current] = []; }
    else if (trimmed.startsWith("ACTION")) { current = "ACTION"; sections[current] = []; }
    else if (current && trimmed) {
      sections[current].push(trimmed);
    }
  }

  return {
    DIAGNOSIS: (sections.DIAGNOSIS || []).join("\n"),
    IMPACT:    (sections.IMPACT    || []).join("\n"),
    ACTION:    (sections.ACTION    || []).join("\n"),
  };
}

export default function ExplanationCard({ explanation, loading }) {
  if (loading) {
    return (
      <div style={{
        fontFamily: "'IBM Plex Mono', monospace",
        padding:    "24px",
        color:      "#3a5a3c",
        fontSize:   "12px",
        display:    "flex",
        gap:        "10px",
        alignItems: "center",
      }}>
        <span style={{ animation: "pulse 1.2s ease-in-out infinite" }}>◈</span>
        Generating explanation...
      </div>
    );
  }

  if (!explanation) {
    return (
      <div style={{
        fontFamily: "'IBM Plex Mono', monospace",
        padding:    "24px",
        color:      "#2a3a2c",
        fontSize:   "12px",
        textAlign:  "center",
      }}>
        Run a drift check to generate an explanation.
      </div>
    );
  }

  const { summary, full_text, used_llm, model } = explanation;
  const sections = parseExplanation(full_text || "");

  return (
    <div style={{ fontFamily: "'IBM Plex Mono', monospace" }}>

      {/* Summary headline */}
      <div style={{
        fontSize:     "14px",
        color:        "#d4e8d4",
        lineHeight:   1.5,
        marginBottom: "20px",
        paddingBottom:"16px",
        borderBottom: "1px solid #1a2a1c",
      }}>
        {summary}
      </div>

      {/* Sections */}
      {sections.DIAGNOSIS && <Section label="DIAGNOSIS" content={sections.DIAGNOSIS} />}
      {sections.IMPACT    && <Section label="IMPACT"    content={sections.IMPACT}    />}
      {sections.ACTION    && <Section label="ACTION"    content={sections.ACTION}    />}

      {/* Model badge */}
      <div style={{
        marginTop:     "16px",
        paddingTop:    "12px",
        borderTop:     "1px solid #1a2a1c",
        fontSize:      "10px",
        color:         "#2a4a2c",
        display:       "flex",
        alignItems:    "center",
        gap:           "8px",
      }}>
        <span style={{
          background:   used_llm ? "#0a2a0e" : "#1a1a1a",
          border:       `1px solid ${used_llm ? "#1a5a1e" : "#333"}`,
          borderRadius: "2px",
          padding:      "2px 8px",
          color:        used_llm ? "#30a050" : "#555",
        }}>
          {used_llm ? `claude / ${model}` : "rule-based"}
        </span>
        {!used_llm && (
          <span style={{ color: "#2a4a2c" }}>
            set ANTHROPIC_API_KEY for LLM explanations
          </span>
        )}
      </div>
    </div>
  );
}