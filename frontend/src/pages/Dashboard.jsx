// Dashboard — the main page.
// Upload CSVs or paste JSON → get full drift report, heatmap, charts, explanation.

import React, { useState, useCallback } from "react";
import { api } from "../api/api";
import StatCards        from "../components/StatCards";
import FeatureHeatmap   from "../components/FeatureHeatmap";
import DistributionChart from "../components/DistributionChart";
import SchemaPanel      from "../components/SchemaPanel";
import ExplanationCard  from "../components/ExplanationCard";

// ── Helpers ───────────────────────────────────────────────────────────────────

function csvToJson(csvText) {
  const lines  = csvText.trim().split("\n");
  const headers = lines[0].split(",").map(h => h.trim().replace(/"/g, ""));
  return lines.slice(1).map(line => {
    const vals = line.split(",");
    return Object.fromEntries(
      headers.map((h, i) => [h, isNaN(vals[i]) ? vals[i]?.trim() : Number(vals[i])])
    );
  });
}

async function readFile(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload  = e => resolve(e.target.result);
    reader.onerror = reject;
    reader.readAsText(file);
  });
}

// ── Styles ────────────────────────────────────────────────────────────────────

const FONT  = "'IBM Plex Mono', 'Courier New', monospace";
const BG    = "#080c08";
const PANEL = "#0d1117";
const BORDER= "#1a2a1c";

const panelStyle = {
  background:   PANEL,
  border:       `1px solid ${BORDER}`,
  borderRadius: "4px",
  padding:      "20px 24px",
};

const labelStyle = {
  fontSize:      "9px",
  color:         "#2a5a2e",
  textTransform: "uppercase",
  letterSpacing: "0.12em",
  marginBottom:  "12px",
  fontFamily:    FONT,
};

// ── Upload zone ───────────────────────────────────────────────────────────────

function UploadZone({ label, onData, data }) {
  const [drag, setDrag] = useState(false);

  async function handleFile(file) {
    const text = await readFile(file);
    try {
      onData(csvToJson(text));
    } catch {
      alert(`Could not parse ${file.name}. Make sure it's a valid CSV.`);
    }
  }

  return (
    <div
      onDragOver={e => { e.preventDefault(); setDrag(true); }}
      onDragLeave={() => setDrag(false)}
      onDrop={async e => {
        e.preventDefault(); setDrag(false);
        const file = e.dataTransfer.files[0];
        if (file) handleFile(file);
      }}
      onClick={() => document.getElementById(`file-${label}`).click()}
      style={{
        flex:         1,
        border:       `1px dashed ${drag ? "#30a050" : data ? "#1a5c28" : "#1a2a1c"}`,
        borderRadius: "4px",
        padding:      "20px",
        cursor:       "pointer",
        textAlign:    "center",
        background:   data ? "#0a1a0e" : drag ? "#0a1a0e" : "transparent",
        transition:   "all 0.15s",
        fontFamily:   FONT,
      }}
    >
      <input
        id={`file-${label}`}
        type="file"
        accept=".csv"
        style={{ display: "none" }}
        onChange={e => e.target.files[0] && handleFile(e.target.files[0])}
      />
      <div style={{ fontSize: "20px", marginBottom: "8px", color: data ? "#30a050" : "#1a3a1e" }}>
        {data ? "✓" : "⊕"}
      </div>
      <div style={{ fontSize: "11px", color: data ? "#30a050" : "#2a4a2e" }}>
        {data ? `${data.length} rows loaded` : `Drop ${label} CSV`}
      </div>
    </div>
  );
}

// ── Feature detail modal ──────────────────────────────────────────────────────

function FeatureModal({ feature, data, onClose }) {
  if (!feature) return null;
  return (
    <div
      onClick={onClose}
      style={{
        position:   "fixed", inset: 0,
        background: "rgba(0,0,0,0.85)",
        display:    "flex", alignItems: "center", justifyContent: "center",
        zIndex:     100,
      }}
    >
      <div
        onClick={e => e.stopPropagation()}
        style={{
          background:   PANEL,
          border:       `1px solid ${BORDER}`,
          borderRadius: "6px",
          padding:      "28px",
          width:        "min(640px, 90vw)",
          fontFamily:   FONT,
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "20px" }}>
          <div style={{ fontSize: "13px", color: "#d4e8d4", fontWeight: 600 }}>{feature}</div>
          <button onClick={onClose} style={{
            background: "none", border: "none",
            color: "#444", cursor: "pointer", fontSize: "18px",
          }}>×</button>
        </div>
        <DistributionChart featureName={feature} featureData={data} />
        <div style={{ marginTop: "20px", fontSize: "11px", color: "#3a5a3c" }}>
          {data.type === "numerical" && (
            <>
              <div>PSI: {data.psi} &nbsp;|&nbsp; KL: {data.kl_divergence} &nbsp;|&nbsp; JS: {data.js_distance}</div>
              <div style={{ marginTop: "6px" }}>
                KS test: p={data.ks_test?.p_value} &nbsp;
                (drifted={String(data.ks_test?.drifted)})
              </div>
            </>
          )}
          {data.type === "categorical" && (
            <div>Chi² p-value: {data.chi2_test?.p_value} &nbsp; (drifted={String(data.chi2_test?.drifted)})</div>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Main Dashboard ─────────────────────────────────────────────────────────────

export default function Dashboard() {
  const [trainData,    setTrainData]    = useState(null);
  const [servingData,  setServingData]  = useState(null);
  const [labelColumn,  setLabelColumn]  = useState("");
  const [report,       setReport]       = useState(null);
  const [loading,      setLoading]      = useState(false);
  const [explLoading,  setExplLoading]  = useState(false);
  const [error,        setError]        = useState(null);
  const [activeTab,    setActiveTab]    = useState("features");
  const [selectedFeat, setSelectedFeat] = useState(null);
  const [selectedData, setSelectedData] = useState(null);

  async function runCheck() {
    if (!trainData || !servingData) return;
    setLoading(true);
    setError(null);
    setReport(null);

    try {
      const result = await api.check({
        training:     trainData,
        serving:      servingData,
        label_column: labelColumn || undefined,
        explain:      false,
      });
      setReport(result);
      setActiveTab("features");
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  async function fetchExplanation() {
    if (!report) return;
    setExplLoading(true);
    try {
      const exp = await api.explain({ report, feature: null });
      setReport(prev => ({ ...prev, explanation: exp }));
      setActiveTab("explain");
    } catch (e) {
      setError(e.message);
    } finally {
      setExplLoading(false);
    }
  }

  function openFeature(name, data) {
    setSelectedFeat(name);
    setSelectedData(data);
  }

  const TABS = ["features", "schema", "explain"];

  return (
    <div style={{
      minHeight:  "100vh",
      background: BG,
      color:      "#8ab890",
      fontFamily: FONT,
      padding:    "0",
    }}>

      {/* Header */}
      <div style={{
        borderBottom: `1px solid ${BORDER}`,
        padding:      "16px 32px",
        display:      "flex",
        alignItems:   "center",
        gap:          "20px",
        background:   "#090d09",
      }}>
        <div style={{ display: "flex", alignItems: "baseline", gap: "12px" }}>
          <span style={{ fontSize: "18px", color: "#30a050", fontWeight: 700, letterSpacing: "0.04em" }}>
            DRIFTWATCH
          </span>
          <span style={{ fontSize: "10px", color: "#2a4a2e", letterSpacing: "0.12em" }}>
            v0.1.0 / training–serving skew detector
          </span>
        </div>

        {report && (
          <div style={{
            marginLeft:    "auto",
            fontSize:      "11px",
            color:         report.overall_severity === "critical" ? "#f07030"
                         : report.overall_severity === "warning"  ? "#c9a020"
                         : "#30a050",
            border:        `1px solid currentColor`,
            borderRadius:  "2px",
            padding:       "3px 10px",
            letterSpacing: "0.08em",
          }}>
            {report.overall_severity?.toUpperCase()}
          </div>
        )}
      </div>

      <div style={{ padding: "28px 32px", maxWidth: "1100px", margin: "0 auto" }}>

        {/* Upload + config row */}
        <div style={{ ...panelStyle, marginBottom: "20px" }}>
          <div style={labelStyle}>Data Input</div>
          <div style={{ display: "flex", gap: "12px", marginBottom: "16px", flexWrap: "wrap" }}>
            <UploadZone label="training" onData={setTrainData}   data={trainData}   />
            <UploadZone label="serving"  onData={setServingData} data={servingData} />
          </div>

          <div style={{ display: "flex", gap: "12px", alignItems: "center", flexWrap: "wrap" }}>
            <input
              placeholder="label column (optional)"
              value={labelColumn}
              onChange={e => setLabelColumn(e.target.value)}
              style={{
                background:   "#080c08",
                border:       `1px solid ${BORDER}`,
                borderRadius: "3px",
                padding:      "8px 12px",
                color:        "#8ab890",
                fontFamily:   FONT,
                fontSize:     "12px",
                outline:      "none",
                flex:         "1",
                minWidth:     "200px",
              }}
            />
            <button
              onClick={runCheck}
              disabled={!trainData || !servingData || loading}
              style={{
                background:    trainData && servingData ? "#0a2a0e" : "#080c08",
                border:        `1px solid ${trainData && servingData ? "#30a050" : BORDER}`,
                borderRadius:  "3px",
                padding:       "8px 24px",
                color:         trainData && servingData ? "#30a050" : "#2a4a2e",
                fontFamily:    FONT,
                fontSize:      "12px",
                cursor:        trainData && servingData ? "pointer" : "default",
                letterSpacing: "0.08em",
                transition:    "all 0.15s",
              }}
            >
              {loading ? "ANALYSING..." : "RUN CHECK"}
            </button>
          </div>
        </div>

        {/* Error */}
        {error && (
          <div style={{
            background: "#3d1a0a", border: "1px solid #c0440a44",
            borderRadius: "4px", padding: "12px 16px",
            color: "#f07030", fontSize: "12px", marginBottom: "20px",
          }}>
            Error: {error}
          </div>
        )}

        {/* Stat cards */}
        <div style={{ marginBottom: "20px" }}>
          <StatCards report={report} />
        </div>

        {/* Tabs + content */}
        {report && (
          <div style={panelStyle}>

            {/* Tab bar */}
            <div style={{ display: "flex", gap: "0", marginBottom: "20px", borderBottom: `1px solid ${BORDER}` }}>
              {TABS.map(tab => (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab)}
                  style={{
                    background:    "none",
                    border:        "none",
                    borderBottom:  activeTab === tab ? "2px solid #30a050" : "2px solid transparent",
                    padding:       "8px 20px",
                    color:         activeTab === tab ? "#30a050" : "#2a5a2e",
                    fontFamily:    FONT,
                    fontSize:      "11px",
                    textTransform: "uppercase",
                    letterSpacing: "0.1em",
                    cursor:        "pointer",
                    marginBottom:  "-1px",
                    transition:    "color 0.15s",
                  }}
                >
                  {tab}
                  {tab === "features" && report.drifted_count > 0 && (
                    <span style={{ marginLeft: "6px", color: "#f07030" }}>
                      {report.drifted_count}
                    </span>
                  )}
                  {tab === "schema" && (report.schema?.critical_count + report.schema?.warning_count) > 0 && (
                    <span style={{ marginLeft: "6px", color: "#c9a020" }}>
                      {report.schema.critical_count + report.schema.warning_count}
                    </span>
                  )}
                </button>
              ))}

              {/* Explain button */}
              <button
                onClick={fetchExplanation}
                disabled={explLoading}
                style={{
                  marginLeft:    "auto",
                  background:    "none",
                  border:        `1px solid ${BORDER}`,
                  borderRadius:  "3px",
                  padding:       "4px 14px",
                  color:         "#2a5a2e",
                  fontFamily:    FONT,
                  fontSize:      "10px",
                  textTransform: "uppercase",
                  letterSpacing: "0.1em",
                  cursor:        "pointer",
                  alignSelf:     "center",
                  marginBottom:  "4px",
                }}
              >
                {explLoading ? "..." : "⟳ explain"}
              </button>
            </div>

            {/* Features tab */}
            {activeTab === "features" && (
              <div>
                <div style={{ fontSize: "11px", color: "#2a5a2e", marginBottom: "16px" }}>
                  Click any feature for distribution detail
                </div>
                <FeatureHeatmap
                  features={report.features}
                  onFeatureClick={openFeature}
                />
              </div>
            )}

            {/* Schema tab */}
            {activeTab === "schema" && (
              <SchemaPanel schema={report.schema} />
            )}

            {/* Explain tab */}
            {activeTab === "explain" && (
              <ExplanationCard
                explanation={report.explanation}
                loading={explLoading}
              />
            )}
          </div>
        )}

        {/* Empty state */}
        {!report && !loading && (
          <div style={{
            ...panelStyle,
            textAlign:  "center",
            padding:    "60px 32px",
            color:      "#1a3a1e",
            fontSize:   "12px",
            lineHeight: 2,
          }}>
            <div style={{ fontSize: "32px", marginBottom: "16px", color: "#1a3a1e" }}>◈</div>
            <div>Upload your training and serving CSVs to begin</div>
            <div style={{ fontSize: "11px", marginTop: "8px", color: "#142a16" }}>
              supports CSV · Parquet via CLI · JSON via API
            </div>
          </div>
        )}
      </div>

      {/* Feature detail modal */}
      <FeatureModal
        feature={selectedFeat}
        data={selectedData}
        onClose={() => { setSelectedFeat(null); setSelectedData(null); }}
      />

    </div>
  );
}