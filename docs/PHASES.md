# FraudGraph AI — Phase-by-Phase Development Lifecycle

This document chronicles the complete development lifecycle of **FraudGraph AI**, from initial dataset discovery to final benchmark evaluation and user interface deployment.

---

## Phase 1 — Analysis & Problem Formulation

### Objective
Examine the Hacker House Goa 2026 challenge specification, profile the IEEE-CIS Fraud Detection dataset, formulate the multi-layer graph architecture, and map all 14 policy actions and judging criteria.

### Implementation
- Conducted deep schema analysis of 590,540 raw transactions, 144,233 identity records, and 5,565 closed cases.
- Defined the 7 core vertex types: `Customer`, `Card`, `Transaction`, `DeviceProfile`, `EmailDomain`, `BillingRegion`, and `ClosedCase`.
- Defined the 9 directional graph relationships.
- Mapped all 14 official policy actions and the three-tier approval routing system (`auto`, `L1`, `L2`).

### Important Files
- `docs/PROJECT_ANALYSIS_VALIDATED.md`: Complete system design document, schema specification, policy action definitions, and judging metric alignment.
- `docs/DATASET_AVAILABILITY_REPORT.md`: Comprehensive profiling of raw CSV schemas, row counts, memory requirements, and missing value distributions.

### Verification & Outcome
- Verified dataset structural integrity and identified that binary labels were intentionally withheld from `case_pack.csv`.
- Outcome: Validated architecture approved with 0 invented attributes or relationships.

---

## Phase 2A — Reproducible Data Pipeline & Graph Files

### Objective
Build a modular, memory-efficient data engineering pipeline to transform raw IEEE-CIS CSVs into validated, graph-ready vertex and edge load files.

### Implementation
- `src/data/config.py`: Centralized directory paths, chunk sizes, and type mappings.
- `src/data/loaders.py`: Chunked, low-memory CSV reader with pandas streaming.
- `src/data/transformers.py`: Entity extraction and deterministic synthetic primary key generation (e.g. `Customer`, `Card`, `DeviceProfile`).
- `src/data/relationships.py`: Edge derivation for `OWNS`, `MADE`, `FROM_DEVICE`, `BILLED_IN`, `PURCHASER_EMAIL`, and intra-card temporal sequence chaining (`NEXT`).
- `src/data/validators.py`: Strict schema validator asserting zero dangling edges, non-null primary keys, and relationship invariants.
- `scripts/prepare_graph_data.py`: CLI driver generating all vertex and edge CSVs in `data/graph_load/`.

### Important Files
- `data/graph_load/vertices/`: 7 vertex CSV files (`Customer.csv`, `Card.csv`, `Transaction.csv`, `DeviceProfile.csv`, `EmailDomain.csv`, `BillingRegion.csv`, `ClosedCase.csv`).
- `data/graph_load/edges/`: 9 edge CSV files (`OWNS.csv`, `MADE.csv`, `FROM_DEVICE.csv`, `PURCHASER_EMAIL.csv`, `BILLED_IN.csv`, `NEXT.csv`, `INVOLVES.csv`, `ON_CARD.csv`, `CONNECTED_TO.csv`).
- `docs/DATA_QUALITY_REPORT.md`: Data profiling report with vertex counts, edge counts, and null distributions.

### Verification & Test Results
- Ran 12 automated unit tests across loaders, transformers, and validators.
- Test Results: **12 / 12 PASSED (0 failures, 0 errors)**.
- Invariants: 100% referential integrity; 0 dangling edges.

---

## Phase 2B — Relationship Audit

### Objective
Resolve relationship count anomalies (`OWNS`, `ON_CARD`, `CONNECTED_TO`, and `NEXT`), audit source columns, derivation rules, and ensure perfect graph consistency prior to GSQL ingestion.

### Implementation
- Audited `OWNS` edge derivation: Resolved card ID prefix matching (`C01234` from `C01234-K1`).
- Audited `ON_CARD` (5,565 edges) vs `CONNECTED_TO` (92 multi-card compromise edges) in `closed_cases_history.csv`.
- Audited `NEXT` temporal transaction chains: verified strictly ordered by timestamp (`ts`) within each card without inter-card leakage.
- Verified directed edge semantics: `Card -> MADE -> Transaction`, `Transaction -> FROM_DEVICE -> DeviceProfile`.

### Important Files
- `docs/RELATIONSHIP_AUDIT_REPORT.md`: Comprehensive audit document certifying all 9 relationships as `VERIFIED`.
- `tests/test_relationship_invariants.py`: Invariant test suite verifying referential integrity, foreign key consistency, and temporal monotonicity.

### Verification & Test Results
- Ran full data pipeline tests: **18 / 18 PASSED (0 failures, 0 errors)**.
- Outcome: Graph relationship model certified as **RELATIONSHIP STATUS: VERIFIED**.

---

## Phase 3 — TigerGraph Schema & GSQL Queries

### Objective
Implement the production TigerGraph schema, loading jobs, and parameterized GSQL queries matching the verified 7-vertex, 9-edge data model.

### Implementation
- `tigergraph/schema/fraud_graph.gsql`: GSQL schema definition script for `FraudGraph` with all 7 vertex types and 9 directed edge types.
- `tigergraph/schema/update_schema.gsql`: Schema-change job for incremental modifications in TigerGraph Savanna.
- `tigergraph/loading/load_fraud_graph.gsql`: High-performance GSQL loading job mapping `data/graph_load/` CSVs to vertices and edges.
- `tigergraph/queries/`: Parameterized GSQL investigation queries:
  - `get_transaction_details.gsql`
  - `get_card_history.gsql`
  - `get_connected_cards_and_customers.gsql`
  - `get_connected_transactions.gsql`
  - `get_transaction_neighborhood.gsql`
  - `get_historical_closed_cases.gsql`

### Important Files
- `docs/data-model.md`: Detailed data dictionary and attribute schema.
- `docs/TIGERGRAPH_LIVE_VALIDATION.md`: Connection audit determining live instance status and defining the offline fallback contract.

### Verification & Test Results
- Verified syntax against TigerGraph 4.2.5 GSQL specification.
- Verified live TigerGraph status: Environment inspected; live endpoint unconfigured (`TIGERGRAPH LIVE STATUS: NOT CONFIGURED`).
- Test Results: **3 / 3 schema tests PASSED**.

---

## Phase 4 — TigerGraph MCP & Investigation Tools

### Objective
Implement the 10 core graph investigation tools following the Model Context Protocol (MCP) specification, backed by an in-memory indexed `LocalGraphClient` with automatic live TigerGraph RESTPP routing.

### Implementation
- `src/graph/client.py`: High-performance `LocalGraphClient` building 12 dictionary indexes on load for $O(1)$ vertex and edge traversals.
- `src/graph/live_client.py`: `LiveTigerGraphClient` implementing RESTPP endpoints (`/query/FraudGraph/...`, `/graph/FraudGraph/...`) with health-check fallback.
- `src/graph/queries.py`: `GraphQueryEngine` dispatcher routing queries to live TigerGraph when reachable, falling back cleanly to `LocalGraphClient`.
- `src/tools/mcp_server.py`: `TigerGraphMCPServer` exposing all 10 tools with standardized JSON envelope `{status, error_code, message, data, execution_mode}`:
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

### Important Files
- `src/tools/mcp_server.py`: MCP tool definitions and module-level function aliases.
- `tests/test_mcp_tools.py`: 19 unit tests verifying all 10 tools, error codes, and index integrity.

### Verification & Test Results
- MCP suite: **19 / 19 PASSED**.
- Full project regression: **37 / 37 PASSED (0 failures, 0 errors)**.

---

## Phase 5 — Policy Engine & GraphRAG

### Objective
Implement the deterministic fraud policy engine (R1 through R10), lightweight vector store indexing 5,590 documents, and hybrid GraphRAG retriever.

### Implementation
- `src/policy/engine.py`: Deterministic rule evaluator for Policy Version 1.0 (R1–R10), approval routing (`auto`, `L1`, `L2`), initial vs. final Next Best Actions, stopping criteria, and `what_changed` explanation. No LLM used.
- `src/rag/vector_store.py`: Scikit-learn TF-IDF + Cosine Similarity vector store indexing:
  - 5,565 closed cases (`closed_cases_history.csv`)
  - 5 documented fraud patterns
  - 10 regulatory references (FinCEN, FFIEC)
  - 10 policy rules (R1–R10)
  - Total: 5,590 indexed documents
- `src/rag/retriever.py`: `HybridGraphRAGRetriever` combining Phase 4 graph tools with vector search to assemble provenanced evidence items (`claim`, `source`, `ref`, `entity_ids`).

### Important Files
- `tests/test_policy_engine.py`: 47 tests verifying R1–R10, initial/final NBA, stopping, and approval routing.
- `tests/test_rag.py`: 35 tests verifying indexing counts, similarity ranking, source filters, and hybrid evidence compilation.

### Verification & Test Results
- Policy Engine: **47 / 47 PASSED**.
- Vector Store & Retriever: **35 / 35 PASSED**.
- Full project regression: **119 / 119 PASSED (0 failures, 0 errors)**.

---

## Phase 6 — LangGraph Stateful Investigation Agent

### Objective
Build a production stateful agent orchestrator using LangGraph managing the full investigation lifecycle through an 8-node state machine.

### Implementation
- `src/agent/state.py`: `InvestigationState` TypedDict preserving alert metadata, graph evidence, vector evidence, risk metrics, evidence requests, policy decisions, SAR data, telemetry, and stopping state.
- `src/agent/orchestrator.py`: `FraudInvestigationOrchestrator` implementing:
  - Node 1: `trigger_handler` (validates alert, initializes state & telemetry)
  - Node 2: `evidence_gatherer` (invokes Phase 4 graph tools)
  - Node 3: `pattern_matcher` (detects known/novel fraud typologies)
  - Node 4: `rag_retriever` (invokes Phase 5 hybrid GraphRAG)
  - Node 5: `risk_assessor` (computes fraud probability, exposure, signal count)
  - Node 6: `sufficiency_evaluator` (evaluates stopping criteria & simulates verification requests)
  - Node 7: `policy_evaluator` (invokes Phase 5 policy engine, generates NBA & SAR)
  - Node 8: `case_updater` (persists case into graph memory with offline fallback)
- Strict stopping criteria (Section 6) and deterministic verification simulation (Section 5).

### Important Files
- `tests/test_agent_orchestration.py`: 16 tests covering initialization, graph traversal, stopping conditions, simulation, and 3-part schema formatting.

### Verification & Test Results
- Agent Orchestration: **16 / 16 PASSED**.
- Full project regression: **135 / 135 PASSED (0 failures, 0 errors)**.

---

## Phase 7 — Benchmark Evaluation & Streamlit UI

### Objective
Execute all 20 official exam benchmark cases (`HHG-001` through `HHG-020`), generate verified answer files, evaluate Plain RAG vs. GraphRAG vs. Agentic GraphRAG, and build an interactive Streamlit UI.

### Implementation
- `scripts/evaluate_benchmarks.py`: Benchmark execution script comparing Plain RAG, GraphRAG, and Agentic GraphRAG; generates `cases/HHG-001.json` through `cases/HHG-020.json`; runs recursive schema validation; outputs `reports/benchmark_results.json` and `docs/BENCHMARK_REPORT.md`.
- `ui/app.py` & `app.py`: Streamlit application providing:
  - Case Investigation Dashboard (all 20 cases with verdict, metrics, evidence trail, SAR, and NBA)
  - Interactive SVG-rendered entity-relationship graph visualization
  - 3-Mode benchmark comparison table
  - Policy and regulatory reference explorer
- `tests/test_benchmark_evaluation.py`: 10 tests verifying answer files, schema conformance, and uncomputable metric handling.
- `tests/test_ui_data.py`: 6 tests verifying UI loaders, missing file resilience, and credential safety.

### Important Files
- `cases/HHG-001.json` ... `cases/HHG-020.json`: 20 official answer files.
- `reports/benchmark_results.json`: Machine-readable benchmark comparison.
- `docs/BENCHMARK_REPORT.md`: Comprehensive benchmark report.
- `ui/app.py` & `app.py`: Streamlit web dashboard.

### Verification & Test Results
- Answer File Validation: **20 / 20 PASSED (100% schema compliance)**.
- Phase 7 Tests: **16 / 16 PASSED**.
- Streamlit Web Server: Started and verified with **HTTP 200 OK (7,260 bytes served)**.
- Full Project Regression: **151 / 151 PASSED (0 failures, 0 errors)**.
