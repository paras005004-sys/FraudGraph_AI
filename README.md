# FraudGraph AI — Autonomous Graph Fraud Investigation Platform

[![Tests](https://img.shields.io/badge/tests-151%20passed-brightgreen.svg)]()
[![Python](https://img.shields.io/badge/python-3.14%2B-blue.svg)]()
[![Framework](https://img.shields.io/badge/LangGraph-1.2.12-orange.svg)]()
[![Graph](https://img.shields.io/badge/TigerGraph-Savanna%20%7C%20Local-purple.svg)]()
[![UI](https://img.shields.io/badge/Streamlit-1.64.0-red.svg)]()
[![License](https://img.shields.io/badge/license-MIT-green.svg)]()

> An enterprise-grade, agentic fraud investigation system built on **TigerGraph**, **LangGraph**, and **Hybrid GraphRAG**. FraudGraph AI investigates suspicious financial transactions, detects complex fraud typologies (card testing, account takeovers, cross-card device rings), deterministically enforces banking policy rules R1–R10, compiles regulatory Suspicious Activity Reports (SAR), and recommends approval-routed Next-Best-Actions (NBA).

---

## Table of Contents
1. [Project Overview](#1-project-overview)
2. [Problem Statement](#2-problem-statement)
3. [Project Objectives](#3-project-objectives)
4. [Key Features](#4-key-features)
5. [System Architecture](#5-system-architecture)
6. [Technology Stack](#6-technology-stack)
7. [Dataset Description](#7-dataset-description)
8. [Graph Data Model](#8-graph-data-model)
9. [TigerGraph Integration](#9-tigergraph-integration)
10. [MCP Graph Investigation Tools](#10-mcp-graph-investigation-tools)
11. [Policy Engine](#11-policy-engine)
12. [R1–R10 Policy Rules](#12-r1r10-policy-rules)
13. [GraphRAG Architecture](#13-graphrag-architecture)
14. [LangGraph Investigation Agent](#14-langgraph-investigation-agent)
15. [Investigation Workflow](#15-investigation-workflow)
16. [Evidence Provenance](#16-evidence-provenance)
17. [Verification Simulation](#17-verification-simulation)
18. [Benchmark Evaluation](#18-benchmark-evaluation)
19. [Plain RAG vs GraphRAG vs Agentic GraphRAG](#19-plain-rag-vs-graphrag-vs-agentic-graphrag)
20. [Streamlit Dashboard](#20-streamlit-dashboard)
21. [Graph Visualization](#21-graph-visualization)
22. [Project Structure](#22-project-structure)
23. [Phase-by-Phase Development](#23-phase-by-phase-development)
24. [Installation](#24-installation)
25. [Environment Configuration](#25-environment-configuration)
26. [Running the Application](#26-running-the-application)
27. [Running Tests](#27-running-tests)
28. [Running Benchmark Evaluation](#28-running-benchmark-evaluation)
29. [TigerGraph Configuration](#29-tigergraph-configuration)
30. [Offline LocalGraphClient Mode](#30-offline-localgraphclient-mode)
31. [Live TigerGraph Mode](#31-live-tigergraph-mode)
32. [Benchmark Limitations](#32-benchmark-limitations)
33. [Ground Truth Limitation](#33-ground-truth-limitation)
34. [Security / Secrets](#34-security--secrets)
35. [Future Enhancements](#35-future-enhancements)
36. [Contributors](#36-contributors)
37. [License](#37-license)

---

## 1. Project Overview
Financial fraud detection systems rely on machine learning models that generate transaction risk scores. However, a risk score is merely a reason to look—never a verdict. Half of flagged transactions are legitimate customer activity, and aggressive blocking causes severe customer friction. 

**FraudGraph AI** bridges the gap between raw statistical alerts and defensible decisions. Built for the Hacker House Goa 2026 challenge, it models financial entities as a connected property graph, executes graph traversals to uncover rings and device sharing, retrieves relevant precedent cases via hybrid GraphRAG, and executes a stateful LangGraph agent that deterministically enforces bank policy rules and compiles regulatory filings.

---

## 2. Problem Statement
Manual fraud investigation is slow, complex, and inconsistent:
- **Graph Blindness**: Relational tables isolate transactions, obscuring card testing sequences and multi-account device sharing.
- **Hallucination Risk**: Unconstrained LLMs hallucinate transaction amounts, invent fake customer replies, and ignore policy thresholds.
- **Regulatory Penalties**: Filing incomplete Suspicious Activity Reports (SAR) or arbitrarily blocking non-fraudulent cardholders violates federal banking compliance.
- **Approval Governance**: Tier-1 lead actions (`DECLINE_TRANSACTION`) versus Tier-2 manager escalations (`BLOCK_CARD > $2,500`, `BLOCK_ALL_CARDS`, `FILE_REPORT`) must be strictly routed.

---

## 3. Project Objectives
1. **Investigation Accuracy (25%)**: Reconstruct complete fraud episodes, uncover shared origin rings, and correctly assess final fraud probabilities.
2. **Next Best Action Compliance (25%)**: Produce initial and final recommendations adhering strictly to Fraud Policy Version 1.0 approval routes (`auto`, `L1`, `L2`).
3. **Agentic Design (15%)**: Implement a modular LangGraph state machine with deterministic verification simulation and strict stopping criteria.
4. **Graph Innovation (15%)**: Leverage a 7-vertex, 9-edge property graph with indexed $O(1)$ traversals and GSQL loading scripts.
5. **Explainability & Provenance (10%)**: Trace every evidence claim to an exact tool, query, document ID, or customer response with zero fabricated entity IDs.
6. **Production Demonstration (10%)**: Provide an interactive Streamlit UI with graph visualization and benchmark comparisons.

---

## 4. Key Features
- **Dual Execution Engine**: Operates seamlessly in live TigerGraph Savanna environments or offline via high-performance indexed `LocalGraphClient`.
- **10 MCP Investigation Tools**: Standardized Model Context Protocol graph investigation tools.
- **Deterministic Policy Engine**: Rules R1 through R10 evaluated with zero LLM hallucination.
- **Hybrid GraphRAG**: Indexes 5,565 closed case precedents, 5 fraud typologies, 10 regulatory guidelines, and 10 policy rules (5,590 total documents).
- **8-Node LangGraph State Machine**: Orchestrates trigger validation, evidence gathering, pattern matching, risk scoring, stopping evaluation, and case persistence.
- **Official 3-Part Answer Generation**: Produces validated JSON files (`cases/HHG-001.json` ... `cases/HHG-020.json`) compliant with challenge specifications.
- **Interactive Streamlit UI**: Rich visual dashboard featuring entity-relationship subgraphs, case inspection, and 3-mode performance benchmarking.

---

## 5. System Architecture
```
Dataset (transactions.csv, identity.csv, closed_cases.csv)
   │
   ▼
Data Pipeline (src/data/) ──> Graph Load Files (data/graph_load/)
                                     │
                                     ▼
                      TigerGraph / LocalGraphClient (src/graph/)
                                     │
                                     ▼
                      10 MCP Graph Tools (src/tools/mcp_server.py)
                                     │
                     ┌───────────────┴───────────────┐
                     ▼                               ▼
        Hybrid GraphRAG (src/rag/)     Policy Engine (src/policy/)
                     │                               │
                     └───────────────┬───────────────┘
                                     ▼
                    LangGraph Orchestrator (src/agent/)
                                     │
                     ┌───────────────┴───────────────┐
                     ▼                               ▼
       20 Benchmark Answer JSONs (cases/)   Streamlit UI (ui/app.py)
```
*See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for detailed data flow specifications.*

---

## 6. Technology Stack
- **Language**: Python 3.14+
- **Graph Database**: TigerGraph Savanna / GSQL 4.2.5 (Live) & `LocalGraphClient` (Offline fallback)
- **Agent Framework**: LangGraph 1.2.12 & LangChain Core 1.6.4
- **Vector Search**: Scikit-learn 1.8.0 TF-IDF + Cosine Similarity (Sublinear scaling)
- **Data Engineering**: Pandas 2.2+, NumPy 2.4+
- **Tool Protocol**: Model Context Protocol (MCP) standardized envelope
- **Web Interface**: Streamlit 1.64.0, SVG Canvas Graphics
- **Testing**: Python standard `unittest` framework (151 automated tests)

---

## 7. Dataset Description
Based on the IEEE-CIS Fraud Detection benchmark, augmented by TigerGraph for the Hacker House Goa 2026 task:
- `transactions.csv` (675 MB, 590,540 rows): Core transaction table with amounts, timestamps (`ts`), card identifiers, and masked model features.
- `identity.csv` (25.5 MB, 144,233 rows): Hardware and network telemetry (`DeviceInfo`, operating system, browser, screen resolution, proxy flags).
- `closed_cases_history.csv` (2.58 MB, 5,565 rows): Historical investigations with outcomes, patterns, exposure, and analyst narratives.
- `case_pack.csv` (10 KB, 20 rows): Benchmark test set (`HHG-001` through `HHG-020`) with alert trigger texts and initial risk scores.

---

## 8. Graph Data Model
A verified property graph consisting of **7 vertex types** and **9 directed relationship types**:

### Vertices (7)
1. **`Customer`**: Unique banking customer (`customer_id`).
2. **`Card`**: Credit or debit card (`card_id`, e.g., `C12382-K1`).
3. **`Transaction`**: Individual transaction (`TransactionID`, amount, timestamp, channel, risk_score).
4. **`DeviceProfile`**: Hardware signature (`DeviceInfo`, OS, browser, screen dimensions).
5. **`EmailDomain`**: Purchaser email domain (`email_domain`).
6. **`BillingRegion`**: Geographic billing region (`billing_region_id` from `addr1`).
7. **`ClosedCase`**: Past investigation records (`case_id`, outcome, pattern, exposure).

### Directed Edges (9)
- `Customer` ──`OWNS`──> `Card`
- `Card` ──`MADE`──> `Transaction`
- `Transaction` ──`FROM_DEVICE`──> `DeviceProfile`
- `Transaction` ──`PURCHASER_EMAIL`──> `EmailDomain`
- `Transaction` ──`BILLED_IN`──> `BillingRegion`
- `Transaction` ──`NEXT`──> `Transaction` (temporally chained within card)
- `ClosedCase` ──`INVOLVES`──> `Transaction`
- `ClosedCase` ──`ON_CARD`──> `Card`
- `ClosedCase` ──`CONNECTED_TO`──> `Card` (multi-card compromise linkage)

---

## 9. TigerGraph Integration
Production GSQL scripts are available in `tigergraph/`:
- **`tigergraph/schema/fraud_graph.gsql`**: Schema definition creating all vertices and edges.
- **`tigergraph/schema/update_schema.gsql`**: Incremental schema-change job for TigerGraph Savanna.
- **`tigergraph/loading/load_fraud_graph.gsql`**: High-speed loading job mapping `data/graph_load/` CSVs to the graph.
- **`tigergraph/queries/`**: Pre-compiled parameterized GSQL queries for real-time investigation traversal.

---

## 10. MCP Graph Investigation Tools
Exposed through `src/tools/mcp_server.py`:
1. `get_transaction_details(txn_id)`: Fetches transaction metadata, amount, channel, and risk score.
2. `get_card_history(card_id, limit)`: Traverses `MADE` edges to retrieve historical spending.
3. `get_connected_cards_and_customers(card_id)`: Uncovers co-owned cards and shared-device cards.
4. `find_shared_devices(card_id)`: Detects device profiles shared across multiple card accounts.
5. `get_transaction_neighborhood(txn_id, depth)`: Computes $k$-hop subgraph around a transaction.
6. `get_connected_transactions(card_id)`: Follows `NEXT` chains for velocity and burst analysis.
7. `get_historical_closed_cases(card_id, limit)`: Retrieves prior closed cases linked via `ON_CARD`.
8. `detect_card_testing_pattern(card_id)`: Identifies sequences of $\ge 3$ micro-authorizations ($< \$5$) within 1 hour.
9. `detect_out_of_region_pattern(card_id)`: Flags in-person purchases in unfamiliar billing regions.
10. `write_case_to_graph(case_data)`: Persists completed investigations into graph memory.

---

## 11. Policy Engine
Implemented in `src/policy/engine.py`, the policy engine operates deterministically without LLM hallucinations. It accepts an `InvestigationContext` and produces:
- Applicable rule triggers
- Documented approval routing (`auto`, `L1`, `L2`)
- Initial recommendations (pre-verification)
- Final recommendations (post-verification)
- Clear `what_changed` rationales

---

## 12. R1–R10 Policy Rules
Derived verbatim from Fraud Policy Version 1.0:
- **R1**: Single signal & fraud probability $< 0.70 \to$ `VERIFY_WITH_CUSTOMER` or `STEP_UP_AUTH` before any block.
- **R2**: Customer denies transaction $\to$ `BLOCK_CARD` + `CREATE_CASE`. Add `FILE_REPORT` if exposure $> \$1,000$ or connected to shared devices. Add `MONITOR_CONNECTED_CARDS`.
- **R3**: Customer confirms transaction $\to$ `CLOSE_NO_FRAUD`.
- **R4**: No customer reply within 24 hours $\to$ `MONITOR_CARD` + `DECLINE_TRANSACTION` for pending authorizations; escalate if exposure $> \$500$.
- **R5**: Card testing sequence detected $\to$ `DECLINE_TRANSACTION` + `STEP_UP_AUTH`. If purchase $> \$100$ cleared $\to$ `BLOCK_CARD`.
- **R6**: Shared origin across cards $\to$ `CREATE_CASE`, `FILE_REPORT`, `MONITOR_CONNECTED_CARDS`.
- **R7**: Disputed recurring charge matching history $\to$ `CREATE_CASE`, `VERIFY_WITH_CUSTOMER`, `WARN_CUSTOMER` (Do not block).
- **R8**: Uncertain verdict & exposure $> \$500$ or conflicting evidence $\to$ `ESCALATE_TO_ANALYST`.
- **R9**: Coordinated abuse fitting no known pattern $\to$ `CREATE_CASE`, `FILE_REPORT`, `ESCALATE_TO_ANALYST` (undocumented).
- **R10**: Never `BLOCK_ALL_CARDS` unless $\ge 2$ cards confirmed fraud or credentials confirmed compromised.

### Approval Routing Table
| Approval Route | Applicable Actions |
|---|---|
| **`auto`** | `ALLOW_TRANSACTION`, `MONITOR_CARD`, `MONITOR_CONNECTED_CARDS`, `WARN_CUSTOMER`, `VERIFY_WITH_CUSTOMER`, `STEP_UP_AUTH`, `GENERATE_REPORT`, `CREATE_CASE`, `ESCALATE_TO_ANALYST`, `CLOSE_NO_FRAUD` |
| **`L1` (Team Lead)** | `DECLINE_TRANSACTION`; `BLOCK_CARD` when exposure $\le \$2,500$ |
| **`L2` (Fraud Manager)**| `BLOCK_CARD` when exposure $> \$2,500$; `BLOCK_ALL_CARDS` always; `FILE_REPORT` always |

---

## 13. GraphRAG Architecture
`src/rag/retriever.py` unifies graph traversals with vector search:
1. Executes Phase 4 graph tools to extract transaction amounts, card velocity, and shared devices.
2. Formulates rich contextual search queries.
3. Queries `FraudVectorStore` across 5,590 indexed documents (5,565 closed cases, 5 patterns, 10 regulations, 10 policy rules).
4. Emits structured evidence items tagged with strict provenance (`graph`, `document`, `customer`, `external`).

---

## 14. LangGraph Investigation Agent
Implemented in `src/agent/orchestrator.py` using `langgraph.graph.StateGraph`:
- **State**: `InvestigationState` (`src/agent/state.py`) tracking case metadata, subgraphs, vector memory, risk metrics, evidence requests, policy decisions, SAR data, and telemetry.
- **Control**: Linear 8-node state machine guaranteeing execution bounded within maximum allowed steps.

---

## 15. Investigation Workflow
```
[trigger_handler]        Validates incoming alert and initializes state
       │
[evidence_gatherer]      Invokes Phase 4 graph tools for 360° entity context
       │
[pattern_matcher]        Evaluates card testing, out-of-region, and device clusters
       │
[rag_retriever]          Fetches historical closed cases, regulations, and rules
       │
[risk_assessor]          Computes fraud probability, exposure USD, and signal count
       │
[sufficiency_evaluator]  Enforces Section 6 stopping criteria & simulates verification
       │
[policy_evaluator]       Invokes PolicyEngine for NBA and SAR narrative generation
       │
[case_updater]           Persists case into graph memory (simulated/live)
       │
     (END)
```

---

## 16. Evidence Provenance
Every evidence item conforms to the required answer file specification:
```json
{
  "claim": "Flagged transaction 3514030: $77.07, ts=2016-12-05 01:55:28, channel=online, score=0.61",
  "source": "graph",
  "ref": "tool:get_transaction_details(txn_id=3514030)",
  "entity_ids": ["3514030"]
}
```
All entity IDs are strictly validated against existing graph data; zero IDs are fabricated.

---

## 17. Verification Simulation
Per Section 5 of the challenge rules, customer and analyst replies are simulated deterministically:
- `customer_report` triggers $\to$ Customer confirms unauthorized charge (`customer_verified = False`).
- `card_testing` confirmed $\to$ Customer denies micro-authorizations (`customer_verified = False`).
- Ambiguous alerts with low risk ($\le 0.30$) $\to$ Customer confirms transaction was legitimate (`customer_verified = True`).
- All simulated interactions are logged under `evidence_requests` with `asked_after_step` and `assumed_response`.

---

## 18. Benchmark Evaluation
`scripts/evaluate_benchmarks.py` evaluates all 20 cases (`HHG-001` through `HHG-020`) from `case_pack.csv`:
- Outputs `cases/HHG-001.json` through `cases/HHG-020.json`.
- Runs 100% recursive validation on all 20 answer files.
- Generates `reports/benchmark_results.json` and `docs/BENCHMARK_REPORT.md`.

---

## 19. Plain RAG vs GraphRAG vs Agentic GraphRAG
Measured comparison across the 20 benchmark exam cases:

| Operational Metric | Plain RAG | GraphRAG | Agentic GraphRAG (Phase 6) |
|---|---|---|---|
| **Average Latency per Case** | `0.011s` | `0.059s` | `0.062s` |
| **Total Graph Tool Calls** | `0` | `180` (9.0 / case) | `180` (9.0 / case) |
| **Average Document Retrievals**| `5.0` docs | `11.0` docs | `11.0` docs |
| **Average Evidence Claims** | `5.0` claims | `8.9` claims | `6.9` claims (synthesized) |
| **SAR Regulatory Filings** | `0` | `0` | `20` (compliant with Section 3a) |
| **Schema Validation** | Baseline | Baseline | **100.0% (20/20 PASS)** |
| **Provenance Compliance** | `100.0%` | `100.0%` | `100.0%` |
| **Ground Truth Accuracy** | *NOT COMPUTABLE* | *NOT COMPUTABLE* | *NOT COMPUTABLE* |

---

## 20. Streamlit Dashboard
Launch the web interface via:
```bash
python -m streamlit run ui/app.py
```
### Modules:
1. **Case Investigation**: Case selection dropdown (`HHG-001` to `HHG-020`), verdict card, fraud probability, exposure USD, pattern details, evidence table with provenance, retrieved historical cases, SAR report details, and Next Best Actions table with `auto`/`L1`/`L2` approval routes.
2. **Graph Visualization**: Interactive entity-relationship visualization of the active case's subgraph.
3. **3-Mode Benchmark**: Comparative metrics table with full 20-case execution log and explicit ground-truth limitation notices.
4. **Policy & Regulations**: Reference explorer for Rules R1–R10 and FinCEN/FFIEC standards.

---

## 21. Graph Visualization
Rendered via embedded SVG graphics in Streamlit, color-coded by vertex type:
- 🔵 **Customer** (`#2563EB`)
- 🟣 **Card** (`#7C3AED`)
- 🔴 **Transaction** (`#DC2626`)
- 🟢 **DeviceProfile** (`#0D9488`)
- 🟡 **ClosedCase Memory** (`#D97706`)

Displays directed relationships (`OWNS`, `MADE`, `FROM_DEVICE`, `INVOLVES`) connecting the active case entities.

---

## 22. Project Structure
```
FraudGraph-AI/
├── app.py                         # Streamlit root launcher
├── cases/                         # 20 official benchmark answer JSONs
│   ├── HHG-001.json
│   └── ... HHG-020.json
├── data/
│   └── graph_load/                # Generated graph load CSVs
│       ├── edges/                 # 9 relationship CSVs
│       └── vertices/              # 7 vertex CSVs
├── dataset/
│   └── HHGOA_IEEE/                # Raw benchmark files
│       ├── case_pack.csv          # 20 benchmark test cases
│       ├── closed_cases_history.csv # 5,565 closed cases
│       ├── identity.csv           # Device identity records
│       └── README.md              # Official challenge specification
├── docs/                          # Architecture & phase documentation
│   ├── ARCHITECTURE.md
│   ├── BENCHMARK_REPORT.md
│   ├── DATASET_AVAILABILITY_REPORT.md
│   ├── DATA_QUALITY_REPORT.md
│   ├── PHASES.md
│   ├── PROJECT_ANALYSIS_VALIDATED.md
│   ├── RELATIONSHIP_AUDIT_REPORT.md
│   └── TIGERGRAPH_LIVE_VALIDATION.md
├── reports/
│   └── benchmark_results.json     # Machine-readable benchmark comparison
├── requirements.txt               # Project dependencies
├── scripts/                       # Executable pipeline drivers
│   ├── evaluate_benchmarks.py     # Benchmark evaluator & answer generator
│   └── prepare_graph_data.py      # Data ingestion pipeline driver
├── src/
│   ├── agent/                     # LangGraph investigation agent
│   │   ├── orchestrator.py
│   │   └── state.py
│   ├── data/                      # Ingestion, validation & transformation
│   │   ├── config.py
│   │   ├── loaders.py
│   │   ├── profiler.py
│   │   ├── relationships.py
│   │   ├── transformers.py
│   │   └── validators.py
│   ├── graph/                     # Local and Live TigerGraph clients
│   │   ├── client.py              # Indexed LocalGraphClient
│   │   ├── live_client.py         # RESTPP LiveTigerGraphClient
│   │   └── queries.py             # GraphQueryEngine dispatcher
│   ├── policy/                    # Deterministic policy engine
│   │   └── engine.py              # Rules R1-R10 and approval routing
│   ├── rag/                       # Vector store & Hybrid GraphRAG
│   │   ├── retriever.py
│   │   └── vector_store.py
│   └── tools/                     # MCP standardized graph tools
│       └── mcp_server.py
├── tests/                         # Complete test suite (151 tests)
│   ├── test_agent_orchestration.py
│   ├── test_benchmark_evaluation.py
│   ├── test_loaders.py
│   ├── test_mcp_tools.py
│   ├── test_policy_engine.py
│   ├── test_rag.py
│   ├── test_relationship_invariants.py
│   ├── test_relationships.py
│   ├── test_tigergraph_schema.py
│   ├── test_transformers.py
│   ├── test_ui_data.py
│   └── test_validators.py
├── tigergraph/                    # Production GSQL scripts
│   ├── loading/
│   │   └── load_fraud_graph.gsql
│   ├── queries/                   # Parameterized GSQL queries
│   └── schema/
│       ├── fraud_graph.gsql
│       └── update_schema.gsql
└── ui/                            # Streamlit application
    └── app.py
```

---

## 23. Phase-by-Phase Development
For detailed implementation history and test counts for each phase, see [docs/PHASES.md](docs/PHASES.md):
- **Phase 1**: Problem Analysis & Architecture Formulation
- **Phase 2A**: Reproducible Ingestion Pipeline & Graph Generation
- **Phase 2B**: Comprehensive Relationship Audit (`RELATIONSHIP STATUS: VERIFIED`)
- **Phase 3**: TigerGraph Schema & Parameterized GSQL Queries
- **Phase 4**: TigerGraph MCP Server & Indexed `LocalGraphClient`
- **Phase 5**: Deterministic Policy Engine (R1–R10) & Hybrid GraphRAG
- **Phase 6**: LangGraph Stateful 8-Node Investigation Agent
- **Phase 7**: 20-Case Benchmark Evaluation & Streamlit UI

---

## 24. Installation
```bash
# Clone the repository
git clone https://github.com/paras005004-sys/FraudGraph_AI.git
cd FraudGraph-AI

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

---

## 25. Environment Configuration
Copy `.env.example` to `.env` to configure optional live TigerGraph credentials:
```bash
cp .env.example .env
```
Default configuration runs in offline mode using `LocalGraphClient`.

---

## 26. Running the Application
Launch the interactive Streamlit dashboard:
```bash
python -m streamlit run ui/app.py
```
Access the dashboard at `http://localhost:8501`.

---

## 27. Running Tests
Execute the complete test suite (151 unit and scenario tests):
```bash
python -m unittest discover -s tests
```
Expected output:
```text
Ran 151 tests in ~350s
OK
```

---

## 28. Running Benchmark Evaluation
To re-run the benchmark evaluation across all 20 cases and re-generate answer files:
```bash
python scripts/evaluate_benchmarks.py
```

---

## 29. TigerGraph Configuration
To connect to a live TigerGraph instance:
1. Update `.env`:
   ```env
   TIGERGRAPH_HOST=https://your-domain.i.tgcloud.io
   TIGERGRAPH_PORT=14240
   TIGERGRAPH_GRAPH_NAME=FraudGraph
   TIGERGRAPH_USERNAME=tigergraph
   TIGERGRAPH_PASSWORD=your-password
   ```
2. Deploy the schema:
   ```bash
   gsql tigergraph/schema/fraud_graph.gsql
   ```
3. Run the loading job:
   ```bash
   gsql tigergraph/loading/load_fraud_graph.gsql
   ```

---

## 30. Offline LocalGraphClient Mode
When `TIGERGRAPH_HOST` is unconfigured, the system automatically runs via `LocalGraphClient`. It loads `data/graph_load/` CSVs into memory and builds 12 dictionary indexes, executing $k$-hop traversals, device sharing detection, and pattern matching with zero external dependencies.

---

## 31. Live TigerGraph Mode
When a live TigerGraph instance is detected via `/echo`, `GraphQueryEngine` routes investigation queries directly to pre-installed GSQL queries via RESTPP, recording `execution_mode: "live_tigergraph"`.

---

## 32. Benchmark Limitations
- **Offline Simulation**: All 20 benchmark cases in this release were executed against `LocalGraphClient`.
- **Pre-set Case Pack**: Evaluations are based exclusively on the 20 cases provided in `case_pack.csv`.

---

## 33. Ground Truth Limitation
In accordance with `dataset/HHGOA_IEEE/README.md`:
> *"The yes/no fraud label is gone... Submit the 20 answer files. We score them against an answer key you don't have."*

`case_pack.csv` intentionally omits ground-truth binary classification labels. Consequently, **Ground Truth Accuracy (Precision/Recall/F1) is NOT COMPUTABLE FROM AVAILABLE GROUND TRUTH**. Fabricating an artificial accuracy score is strictly avoided to preserve benchmark integrity.

---

## 34. Security / Secrets
- All credentials, API keys, and environment files (`.env`) are excluded via `.gitignore`.
- Raw dataset files exceeding GitHub limits (`transactions.csv`, 675 MB) are excluded from version control.
- Simulated verification responses are explicitly marked as synthetic in `evidence_requests`.

---

## 35. Future Enhancements
- **Live GSQL Streaming**: Connect to TigerGraph 4.2+ Kafka loading pipelines for sub-second alert streaming.
- **Dynamic GNN Scoring**: Integrate TigerGraph Graph Convolutional Networks (GCN) for real-time node embedding inference.
- **Human-in-the-Loop Analyst Review**: Streamlit UI workflow allowing analysts to approve L1/L2 actions directly.

---

## 36. Contributors
- **Paras Singh** — Advanced Agentic Engineering & Graph Architecture
- **TigerGraph & IEEE CIS** — Dataset and benchmark challenge specifications

---

## 37. License
Distributed under the **MIT License**. See `LICENSE` for more information.
