// DistributionChart — overlays reference and serving distributions.
// Shows visually where the shift happened.

import React from "react";
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer,
} from "recharts";

function buildHistogramData(refMean, refStd, curMean, curStd, bins = 30) {
  // Synthesise approximate normal distributions from mean/std
  // for visual comparison — real data would come from the API
  if (refMean == null || refStd == null) return [];

  const lo = Math.min(refMean - 3 * refStd, curMean - 3 * (curStd || refStd));
  const hi = Math.max(refMean + 3 * refStd, curMean + 3 * (curStd || refStd));
  const step = (hi - lo) / bins;

  function gaussian(x, mean, std) {
    return Math.exp(-0.5 * Math.pow((x - mean) / std, 2)) / (std * Math.sqrt(2 * Math.PI));
  }

  return Array.from({ length: bins }, (_, i) => {
    const x = lo + i * step + step / 2;
    return {
      x:        +x.toFixed(2),
      training: +gaussian(x, refMean, refStd).toFixed(5),
      serving:  +gaussian(x, curMean, curStd || refStd).toFixed(5),
    };
  });
}

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div style={{
      background: "#0d1117",
      border:     "1px solid #1e2d20",
      borderRadius: "3px",
      padding:    "8px 12px",
      fontFamily: "'IBM Plex Mono', monospace",
      fontSize:   "11px",
      color:      "#8ab890",
    }}>
      <div style={{ color: "#ccc", marginBottom: 4 }}>x = {label}</div>
      {payload.map(p => (
        <div key={p.dataKey} style={{ color: p.color }}>
          {p.dataKey}: {p.value?.toFixed(5)}
        </div>
      ))}
    </div>
  );
};

export default function DistributionChart({ featureName, featureData }) {
  if (!featureData || featureData.type !== "numerical") {
    return (
      <div style={{
        padding: "32px",
        textAlign: "center",
        color: "#444",
        fontFamily: "'IBM Plex Mono', monospace",
        fontSize: "12px",
      }}>
        Distribution chart available for numerical features only.
      </div>
    );
  }

  const { ref_mean, ref_std, cur_mean, cur_std } = featureData;
  const data = buildHistogramData(ref_mean, ref_std, cur_mean, cur_std);

  return (
    <div>
      <div style={{
        fontFamily:    "'IBM Plex Mono', monospace",
        fontSize:      "11px",
        color:         "#5a7a5c",
        marginBottom:  "16px",
        textTransform: "uppercase",
        letterSpacing: "0.08em",
      }}>
        {featureName} — distribution overlay
      </div>

      <div style={{
        display: "flex",
        gap: "24px",
        marginBottom: "12px",
        fontFamily: "'IBM Plex Mono', monospace",
        fontSize: "11px",
      }}>
        <div style={{ color: "#30a050" }}>
          train  μ={ref_mean?.toFixed(2)} σ={ref_std?.toFixed(2)}
        </div>
        <div style={{ color: "#f07030" }}>
          serve  μ={cur_mean?.toFixed(2)} σ={cur_std?.toFixed(2)}
        </div>
        {ref_mean && cur_mean && (
          <div style={{ color: "#888" }}>
            Δμ = {((cur_mean - ref_mean) / Math.abs(ref_mean) * 100).toFixed(1)}%
          </div>
        )}
      </div>

      <ResponsiveContainer width="100%" height={200}>
        <AreaChart data={data} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
          <defs>
            <linearGradient id="trainGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%"  stopColor="#30a050" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#30a050" stopOpacity={0.02} />
            </linearGradient>
            <linearGradient id="serveGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%"  stopColor="#f07030" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#f07030" stopOpacity={0.02} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#1a2a1c" vertical={false} />
          <XAxis
            dataKey="x"
            tick={{ fill: "#3a5a3c", fontSize: 10, fontFamily: "IBM Plex Mono" }}
            axisLine={{ stroke: "#1a3a1e" }}
            tickLine={false}
          />
          <YAxis
            tick={{ fill: "#3a5a3c", fontSize: 10, fontFamily: "IBM Plex Mono" }}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip content={<CustomTooltip />} />
          <Area
            type="monotone"
            dataKey="training"
            stroke="#30a050"
            strokeWidth={1.5}
            fill="url(#trainGrad)"
            dot={false}
          />
          <Area
            type="monotone"
            dataKey="serving"
            stroke="#f07030"
            strokeWidth={1.5}
            fill="url(#serveGrad)"
            dot={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}