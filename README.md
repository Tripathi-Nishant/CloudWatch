<div align="center">

<img src="https://capsule-render.vercel.app/api?type=waving&color=0:00ff41,100:008f11&height=120&section=header&animation=fadeIn" width="100%"/>


### `v0.1.0` — Real-Time Training/Serving Skew Detector for ML Pipelines

<br/>

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776ab?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-61dafb?style=for-the-badge&logo=react&logoColor=black)](https://reactjs.org)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ed?style=for-the-badge&logo=docker&logoColor=white)](https://docker.com)
[![License](https://img.shields.io/badge/License-MIT-00ff41?style=for-the-badge)](LICENSE)
[![Claude](https://img.shields.io/badge/Claude-AI%20Powered-cc785c?style=for-the-badge&logo=anthropic&logoColor=white)](https://anthropic.com)

<br/>

> **Every ML team knows about training-serving skew.**
> **Nobody has a free, zero-config tool that catches it**
> **before it silently kills your model in production.**
>
> *DriftWatch is one `pip install` — works in 5 minutes on any pipeline.*

<br/>

```bash
pip install -r requirements.txt && python notebooks/demo.py
```

</div>

<br/>

---

## ⚡ The Problem

```
                    ┌─────────────────────────────────────────────┐
                    │           YOUR ML MODEL IN PRODUCTION        │
                    └─────────────────────────────────────────────┘
                                          │
              ┌───────────────────────────┼───────────────────────────┐
              │                           │                           │
        TRAINING DATA              SERVING DATA                  THE GAP
        (what it learned)          (what it sees now)          (nobody checks)
              │                           │                           │
    age: 25-35 yrs              age: 50-65 yrs               ← +51% shift
    txn: ₹100-200               txn: ₹1000-2000              ← +351% shift
    region: India               region: International         ← new category
    income: nulls 0%            income: nulls 30%             ← pipeline broke
              │                           │                           │
              └───────────────────────────┴───────────────────────────┘
                                          │
                                          ▼
                            ┌─────────────────────────┐
                            │  Model runs. No errors.  │
                            │  Accuracy: 94% → 61%     │
                            │  Nobody noticed.         │
                            └─────────────────────────┘
```

**DriftWatch catches this in `<1 second`. Before it costs you.**

<br/>

---

## 🎯 How It Works

```
┌──────────────────────────────────────────────────────────────────────┐
│                      DRIFTWATCH PIPELINE                             │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  train.csv ──┐                                                       │
│              ├──► Statistical Engine ──► Drift Report ──► Alert     │
│ serving.csv ─┘         │                      │              │      │
│                         │                      │              │      │
│              ┌──────────┘           ┌──────────┘      ┌──────┘      │
│              ▼                      ▼                  ▼            │
│         PSI · KL · JS          Schema Diff         LLM Explains     │
│         KS · Chi²              Type Changes        DIAGNOSIS        │
│         Per Feature            Null Explosions     IMPACT           │
│         Severity Score         Missing Columns     ACTION           │
└──────────────────────────────────────────────────────────────────────┘
```

<br/>

---

## 🚀 Quickstart

### Install

```bash
git clone https://github.com/YourUsername/driftwatch
cd driftwatch
pip install -r requirements.txt
```

### Run the demo

```bash
# Linux / Mac
PYTHONPATH=. python notebooks/demo.py

# Windows PowerShell
$env:PYTHONPATH="."; python notebooks/demo.py
```

### CLI

```bash
# Linux / Mac
PYTHONPATH=. python driftwatch/cli/main.py check \
  --training data/samples/train.csv \
  --serving  data/samples/serving_drifted.csv \
  --label    is_fraud \
  --explain

# Windows PowerShell
$env:PYTHONPATH="."; python driftwatch/cli/main.py check `
  --training data/samples/train.csv `
  --serving  data/samples/serving_drifted.csv `
  --label    is_fraud `
  --explain
```

### Expected output

```
  ──────────────────────────────────────────────────────
  DriftWatch Report   2026-03-15T08:20:37
  ──────────────────────────────────────────────────────
  Overall Status    CRITICAL
  Features Checked  7
  Drifted Features  4 / 7
  ──────────────────────────────────────────────────────
  [WARN] Null rate in 'income' increased by 30.0%

  transaction_amount   PSI=3.331022   [CRIT]   +351.5%
  age                  PSI=2.912127   [CRIT]    +50.9%
  credit_score         PSI=0.609455   [CRIT]     -8.4%
  region               p=0.0          [CRIT]

  Action required. Retrain recommended.
  ──────────────────────────────────────────────────────
  DIAGNOSIS  4 features drifted. transaction_amount +351%
  IMPACT     Model predictions unreliable for high-stakes decisions
  ACTION     1. Fix income pipeline  2. Retrain  3. Fix region encoding
```

<br/>

---

## 🐍 Python SDK

### Minimum — 3 lines

```python
from driftwatch.sdk import DriftWatcher

watcher = DriftWatcher(reference=train_df)
report  = watcher.check(serving_df)
```

### Production — with callbacks and CI/CD gate

```python
from driftwatch.sdk import DriftWatcher, DriftDetectedError

watcher = DriftWatcher(
    reference          = train_df,
    label_column       = "target",
    on_critical        = lambda r: slack_alert(r.drifted_features),
    on_warning         = lambda r: log_warning(r),
    raise_on_critical  = True,
    explain            = True,
)

try:
    report = watcher.check(serving_df, tag="batch_2025_W12")
except DriftDetectedError as e:
    print(f"Deployment blocked: {e}")
```

### Fingerprint workflow

```python
# At training time — save fingerprint
watcher = DriftWatcher(reference=X_train, label_column="target")
watcher.save_fingerprint("models/v3_fingerprint.json")

# At serving time — no raw training data needed
watcher = DriftWatcher(fingerprint_path="models/v3_fingerprint.json")
report  = watcher.check(serving_batch)
```

### Batch history tracking

```python
watcher = DriftWatcher(reference=train_df)

for week, batch in weekly_batches:
    report = watcher.check(batch, tag=week)

for entry in watcher.history:
    print(f"{entry['tag']} → {entry['severity']} → {entry['drifted']}")

# week_1 → stable   → []
# week_2 → stable   → []
# week_3 → critical → ['transaction_amount', 'age', 'region']
```

<br/>

---

## ⚙️ Statistical Engine

```
┌──────────────────┬───────────────────────────────────────────────────────┐
│ NUMERICAL                                                                │
├──────────────────┼───────────────────────────────────────────────────────┤
│ PSI              │ Industry standard. < 0.1 stable · > 0.2 critical      │
│ KL Divergence    │ Information loss reference → current                   │
│ JS Distance      │ Symmetric, bounded [0,1]. Best for dashboards          │
│ KS Test          │ Non-parametric. p < 0.05 = distributions differ        │
├──────────────────┼───────────────────────────────────────────────────────┤
│ CATEGORICAL                                                               │
├──────────────────┼───────────────────────────────────────────────────────┤
│ Chi-squared      │ Detects frequency distribution shifts                  │
├──────────────────┼───────────────────────────────────────────────────────┤
│ SCHEMA (first)                                                            │
├──────────────────┼───────────────────────────────────────────────────────┤
│ Missing columns  │ Feature in train, gone in serving                      │
│ Type changes     │ int64 → object, float → string                         │
│ Null explosion   │ Null rate increased > 20%                              │
│ Unseen categories│ New values in serving not seen in training             │
└──────────────────┴───────────────────────────────────────────────────────┘
```

<br/>

---

## 🌐 REST API

```bash
# Start server
$env:PYTHONPATH="."; python -m uvicorn driftwatch.api.main:app --reload --port 8000
# Swagger UI → http://localhost:8000/docs
```

```
┌─────────┬────────────────────────────┬──────────────────────────────────┐
│ Method  │ Endpoint                   │ Description                      │
├─────────┼────────────────────────────┼──────────────────────────────────┤
│ GET     │ /api/v1/health             │ API status                       │
│ POST    │ /api/v1/check              │ Direct drift analysis            │
│ POST    │ /api/v1/fingerprint        │ Save training fingerprint        │
│ GET     │ /api/v1/fingerprint/{id}   │ Get fingerprint metadata         │
│ POST    │ /api/v1/compare            │ Compare vs saved fingerprint     │
│ POST    │ /api/v1/explain            │ Generate LLM explanation         │
│ GET     │ /api/v1/stats              │ System stats                     │
└─────────┴────────────────────────────┴──────────────────────────────────┘
```

<br/>

---

## 🚦 CI/CD Integration

```bash
# Exit codes
# 0 → STABLE   → pipeline passes 
# 1 → CRITICAL → pipeline blocked 
# 2 → WARNING  → pipeline passes with log 
```

```yaml
# GitHub Actions example
- name: DriftWatch Gate
  run: |
    python driftwatch/cli/main.py check \
      --training data/train.csv \
      --serving  data/latest.csv \
      --label    target
  env:
    PYTHONPATH: .
# Critical drift → workflow fails → deployment blocked automatically
```

<br/>

---

## 🐳 Docker

```bash
cp .env.example .env          # add ANTHROPIC_API_KEY (optional)
docker-compose up --build

# Backend   → http://localhost:8000
# Swagger   → http://localhost:8000/docs
# Dashboard → http://localhost:3000
```

<br/>

---

## 📁 Project Structure

```
driftwatch/
├── driftwatch/
│   ├── engine.py                  ← DriftEngine + DriftReport
│   ├── detectors/
│   │   ├── statistical.py         ← PSI · KL · JS · KS · Chi-squared
│   │   └── schema.py              ← schema diff detector
│   ├── explainer/
│   │   ├── claude_client.py       ← Claude API + rule-based fallback
│   │   └── prompt_builder.py      ← context-aware prompts
│   ├── sdk/
│   │   └── pipeline.py            ← DriftWatcher 3-line SDK
│   ├── api/
│   │   ├── main.py                ← FastAPI app
│   │   ├── routes.py              ← 7 endpoints
│   │   └── models.py              ← Pydantic schemas
│   └── cli/
│       ├── main.py                ← entry point
│       ├── commands.py            ← check · fingerprint · compare
│       └── renderer.py            ← coloured terminal output
├── frontend/src/
│   ├── components/
│   │   ├── FeatureHeatmap.jsx     ← colour-coded feature health grid
│   │   ├── DistributionChart.jsx  ← ref vs serving overlay chart
│   │   ├── SchemaPanel.jsx        ← schema issues list
│   │   ├── ExplanationCard.jsx    ← LLM explanation display
│   │   └── StatCards.jsx          ← header metric cards
│   └── pages/Dashboard.jsx
├── notebooks/demo.py              ← end-to-end hackathon demo
├── tests/test_engine.py           ← 24 tests
├── requirements.txt
├── setup.py
├── Dockerfile
├── docker-compose.yml
└── .env.example
```

<br/>

---

<br/>

---

## 💰 Cost

```
Statistical engine        $0  — pure Python/NumPy
CLI + API + Dashboard     $0
Self-hosted               $0
LLM explanations          ~$0.0001 per call (Claude Haiku)
                          = $1 per 10,000 explanations
```

<br/>

---

## 🔮 Roadmap

```
v0.1.0  ✅  Core engine · CLI · SDK · API · Dashboard · Docker
v0.2.0  🔄  Streaming mode (Kafka integration)
v0.3.0  🔄  Per-model version history tracking
v0.4.0  🔄  Grafana plugin
v1.0.0  🔄  Hosted SaaS — zero setup, team dashboards, email alerts
```

<br/>

---

<div align="center">

**Built with obsession over a 48-hour sprint.**

*Because every ML team deserves production monitoring —*
*not just the ones who can afford $400/month.*

<br/>

[![Star on GitHub](https://img.shields.io/github/stars/YourUsername/driftwatch?style=for-the-badge&logo=github&color=00ff41)](https://github.com/Tripathi-Nishant/driftwatch)

<img src="https://capsule-render.vercel.app/api?type=waving&color=0:008f11,100:00ff41&height=120&section=footer&animation=fadeIn" width="100%"/>

</div>
