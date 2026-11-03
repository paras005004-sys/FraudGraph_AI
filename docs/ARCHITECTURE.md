# FraudGraph AI — System Architecture & Data Flow

This document details the end-to-end architecture of **FraudGraph AI**, describing how raw transactional records flow through graph derivation, hybrid retrieval, agentic orchestration, and interactive presentation.

```
                    ┌─────────────────────────┐
                    │ Raw IEEE-CIS Dataset    │
                    │ transactions / identity │
                    └────────────┬────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │ Data Ingestion Pipeline │
                    │ clean, derive & validate│
                    └────────────┬────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │ Graph Load Files (CSVs) │
                    │ 7 Vertices | 9 Edges    │
                    └────────────┬────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │ Hybrid Graph Layer      │
                    │ Live TG / Local Client  │
                    └────────────┬────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │ MCP Graph Tools (10x)   │
                    │ standard JSON envelope  │
                    └────────────┬────────────┘
                                 │
         ┌───────────────────────┴───────────────────────┐
         │                                               │
         ▼                                               ▼
┌─────────────────────────┐                 ┌─────────────────────────┐
│ Vector Store (TF-IDF)   │                 │ Deterministic Policy    │
│ 5,590 indexed documents │                 │ Engine (Rules R1 - R10) │
└────────────┬────────────┘                 └────────────┬────────────┘
         │                                               │
         └───────────────────────┬───────────────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │ LangGraph Orchestrator  │
                    │ 8-Node Stateful Machine │
                    └────────────┬────────────┘
                                 │
         ┌───────────────────────┴───────────────────────┐
         │                                               │
         ▼                                               ▼
┌─────────────────────────┐                 ┌─────────────────────────┐
│ Benchmark Evaluation    │                 │ Streamlit UI Dashboard  │
│ 20 Answer JSONs (cases/)│                 │ Graph Viz & Audit Logs  │
└─────────────────────────┘                 └─────────────────────────┘
```

---

## 1. Raw Dataset Layer (`dataset/HHGOA_IEEE/`)
The foundational data originates from the IEEE-CIS Fraud Detection benchmark augmented with real-time risk scores, synthetic customers, calendar dates, channel attributes, and historical closed cases:
- `transactions.csv` (675 MB, 590,540 rows): Transaction amounts, timestamps, card attributes, and masked features ($V, C, D, M$).
- `identity.csv` (25.5 MB, 144,233 rows): Hardware signatures, operating systems, browsers, screen resolutions, and proxy flags ($id\_15, id\_23$).
- `closed_cases_history.csv` (2.58 MB, 5,565 rows): Historical confirmed fraud cases and cleared alerts with analyst notes and investigation outcomes.
- `case_pack.csv` (10 KB, 20 rows): Benchmark exam cases (`HHG-001` through `HHG-020`) with trigger texts and flagged transactions.

---

## 2. Data Pipeline Layer (`src/data/`)
Transforms raw tabular data into structured graph vertices and edges using chunked streaming:
- **`DataLoader`** (`loaders.py`): Memory-efficient chunked reader preventing OOM errors on large CSVs.
- **`DataTransformer`** (`transformers.py`): Extracts deterministic entity IDs (`Customer` ID from Card prefix, `DeviceProfile` composite string hash).
- **`RelationshipDeriver`** (`relationships.py`): Synthesizes the 9 approved graph relationships. Orders transactions chronologically (`NEXT` chain) per card.
- **`DataValidator`** (`validators.py`): Asserts zero dangling edges, non-null primary keys, and relationship invariants.

---

## 3. Graph Load Files Layer (`data/graph_load/`)
Generates 16 clean, schema-conformant CSV files:
- **7 Vertices**:
  - `Customer` (13,553)
  - `Card` (13,933)
  - `Transaction` (590,742)
  - `DeviceProfile` (9,706)
  - `EmailDomain` (60)
  - `BillingRegion` (332)
  - `ClosedCase` (5,565)
- **9 Directed Edges**:
  - `OWNS` (`Customer -> Card`): 13,933
  - `MADE` (`Card -> Transaction`): 590,742
  - `FROM_DEVICE` (`Transaction -> DeviceProfile`): 144,432
  - `PURCHASER_EMAIL` (`Transaction -> EmailDomain`): 496,262
  - `BILLED_IN` (`Transaction -> BillingRegion`): 525,003
  - `NEXT` (`Transaction -> Transaction`): 577,189
  - `INVOLVES` (`ClosedCase -> Transaction`): 14,955
  - `ON_CARD` (`ClosedCase -> Card`): 5,565
  - `CONNECTED_TO` (`ClosedCase -> Card`): 92

---

## 4. Hybrid Graph Engine Layer (`src/graph/`)
Provides dual execution capability:
- **`LocalGraphClient`** (`client.py`): High-performance in-memory graph engine building 12 dictionary indexes on load. Performs sub-millisecond graph traversals ($k$-hop neighborhoods, temporal transaction sequences, device sharing clusters).
- **`LiveTigerGraphClient`** (`live_client.py`): Connects to TigerGraph Savanna / Cloud instances via RESTPP (`/query/FraudGraph/...` and `/graph/FraudGraph/...`).
- **`GraphQueryEngine`** (`queries.py`): Automatically detects TigerGraph reachability; routes queries to live GSQL when available or falls back cleanly to `LocalGraphClient`.

---

## 5. Model Context Protocol (MCP) Graph Tools (`src/tools/mcp_server.py`)
Exposes 10 standardized graph tools following the Model Context Protocol specification:
1. `get_transaction_details(txn_id)`
2. `get_card_history(card_id, limit)`
3. `get_connected_cards_and_customers(card_id)`
4. `find_shared_devices(card_id)`
5. `get_transaction_neighborhood(txn_id, depth)`
6. `get_connected_transactions(card_id)`
7. `get_historical_closed_cases(card_id, limit)`
8. `detect_card_testing_pattern(card_id)`
9. `detect_out_of_region_pattern(card_id)`
10. `write_case_to_graph(case_data)`

Every tool returns a strict standardized JSON schema:
```json
{
  "status": "success" | "error",
  "error_code": null | "NOT_FOUND" | "INVALID_INPUT",
  "message": "...",
  "data": { ... },
  "execution_mode": "live_tigergraph" | "offline_local"
}
```

---

## 6. Vector Store & Hybrid GraphRAG Layer (`src/rag/`)
- **`FraudVectorStore`** (`vector_store.py`): Scikit-learn TF-IDF + Cosine Similarity indexing 5,590 documents:
  - 5,565 historical closed case records (`closed_cases_history.csv`)
  - 5 recognized fraud typologies (`card_testing`, `card_not_present_fraud`, `card_not_present_new_device`, `out_of_region_use`, `account_takeover`)
  - 10 regulatory guidance references (FinCEN SAR Narrative Standard, FFIEC BSA/AML)
  - 10 policy rules (R1 through R10)
- **`HybridGraphRAGRetriever`** (`retriever.py`): Combines graph traversals with vector search to compile provenanced evidence items:
  ```json
  {
    "claim": "...",
    "source": "graph" | "document" | "customer" | "external",
    "ref": "tool:... / doc:...",
    "entity_ids": ["..."]
  }
  ```

---

## 7. Deterministic Policy Engine Layer (`src/policy/engine.py`)
Implements Fraud Policy Version 1.0 without LLM hallucinations:
- **Rules Evaluated**: R1 through R10.
- **Approval Routes Enforced**:
  - `auto`: Automated agent actions (`ALLOW_TRANSACTION`, `MONITOR_CARD`, `WARN_CUSTOMER`, `VERIFY_WITH_CUSTOMER`, `STEP_UP_AUTH`, `CREATE_CASE`, `CLOSE_NO_FRAUD`).
  - `L1` (Team Lead): `DECLINE_TRANSACTION`, `BLOCK_CARD` when exposure $\le \$2,500$.
  - `L2` (Fraud Manager): `BLOCK_CARD` when exposure $> \$2,500$, `BLOCK_ALL_CARDS`, `FILE_REPORT`.
- **Next Best Actions (NBA)**: Compares initial recommendation before evidence arrives with final recommendation after customer reply, detailing `what_changed`.

---

## 8. LangGraph Investigation Agent Layer (`src/agent/`)
Stateful 8-node state machine orchestrating end-to-end investigations:
1. `trigger_handler`: Validates input alert; initializes `InvestigationState`.
2. `evidence_gatherer`: Executes graph tools to collect entity context.
3. `pattern_matcher`: Detects card testing, out-of-region use, shared device rings.
4. `rag_retriever`: Fetches relevant past closed cases and policy rules.
5. `risk_assessor`: Computes fraud probability, exposure USD, and signal count.
6. `sufficiency_evaluator`: Enforces Section 6 stopping criteria and simulates Section 5 customer verification responses.
7. `policy_evaluator`: Invokes deterministic policy engine; formats NBA and SAR.
8. `case_updater`: Persists case vertex and edges to graph memory.

---

## 9. Benchmark & Evaluation Layer (`scripts/evaluate_benchmarks.py`)
- Evaluates the 20 benchmark cases (`HHG-001` to `HHG-020`) across three modes:
  1. Plain RAG (Vector-only)
  2. GraphRAG (Direct hybrid)
  3. Agentic GraphRAG (Full Phase 6 agent)
- Saves the 20 official answer files to `cases/HHG-001.json` ... `cases/HHG-020.json`.
- Validates all files against the official 3-part schema.
- Outputs `reports/benchmark_results.json` and `docs/BENCHMARK_REPORT.md`.

---

## 10. User Interface Layer (`ui/app.py` & `app.py`)
Interactive Streamlit application providing:
- **Case Investigation Dashboard**: Interactive case inspector displaying verdict, exposure, pattern, evidence trail with provenance, SAR report, and NBA routing.
- **Entity Subgraph Visualization**: SVG diagram rendering connected Customer, Card, Transaction, DeviceProfile, and ClosedCase entities.
- **3-Mode Benchmark Dashboard**: Measured performance metrics across Plain RAG, GraphRAG, and Agentic GraphRAG.
- **Policy Explorer**: Interactive knowledgebase for Rules R1–R10 and regulatory standards.
