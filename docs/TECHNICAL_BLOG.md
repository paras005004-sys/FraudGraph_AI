# FraudGraph AI: Building an Agentic GraphRAG Fraud Investigation Platform with TigerGraph and LangGraph

**Team:** NexusForge  
**Submission:** TigerGraph × HHGoa 2026 Hackathon  
**Repository:** [https://github.com/Mokshith-11/FraudGraph-AI](https://github.com/Mokshith-11/FraudGraph-AI)  
**Primary Tech Stack:** TigerGraph Savanna / GSQL 4.2.5, LangGraph StateGraph, Python 3.14, Scikit-learn TF-IDF, Streamlit  

---

## 1. Introduction

Financial fraud detection systems operate under extreme operational tension. Traditional machine learning classifiers score millions of transactions per second, flagging anomalies with high precision on point-in-time attributes. However, when a transaction alert triggers, human Level 1 (L1) and Level 2 (L2) fraud analysts face an arduous, fragmented investigative process. Analysts must pivot across disparate relational databases, customer relationship management (CRM) records, device fingerprints, and compliance databases to determine whether a suspicious charge represents an isolated account compromise, a benign customer traveler, or part of a distributed, multi-card syndicated fraud ring.

Recent efforts to automate fraud operations using standard Retrieval-Augmented Generation (RAG) collapse when confronted with relational topologies. Standard vector search retrieves text documents based on semantic keyword proximity; it possesses zero native awareness of cyclic transaction loops, device-sharing clusters across unrelated customer accounts, or temporal transaction hops along a payment card.

To solve this, **NexusForge** developed **FraudGraph AI**, an end-to-end agentic graph-augmented fraud investigation platform. Built for the **TigerGraph × HHGoa 2026** challenge, FraudGraph AI unites the massive multi-hop traversal power of **TigerGraph 4.2.5**, the structured tool contracts of the **Model Context Protocol (MCP)**, a deterministic **R1–R10 Fraud Policy Engine**, and a stateful **LangGraph** orchestrator. The platform executes autonomous, provenance-tracked investigations that generate legally grounded Suspicious Activity Reports (SAR) and actionable Next-Best-Action (NBA) directives with human-in-the-loop approval routing.

---

## 2. Problem Statement

Modern enterprise fraud investigation is hindered by four architectural bottlenecks:

1. **Topological Blindness**: Standard tabular tabular fraud models evaluate transactions as independent, identically distributed ($i.i.d.$) vectors. They cannot natively trace when ten distinct card numbers across five customer profiles share a single mobile hardware identifier (`DeviceProfile`) or pass through the same digital payment proxy.
2. **LLM Hallucinations in Compliance & Regulatory Reporting**: Deploying unconstrained Large Language Models directly to compliance decisions introduces non-deterministic hallucinations. Regulated financial entities operating under BSA/AML (Bank Secrecy Act / Anti-Money Laundering) and FinCEN standards require deterministic policy enforcement, mathematical auditability, and clear evidence provenance.
3. **Investigation Workflow Fragility**: Human analysts handle hundreds of alerts daily. Ad-hoc investigative scripts lack structured state management, error recovery, deterministic stopping thresholds, and standardized simulation protocols for cardholder outreach.
4. **Disconnection Between Knowledge Retrieval and Graph Intelligence**: Text-based retrieval systems index historical case summaries and regulatory manuals, while graph databases hold the structural transaction topology. Without a unified hybrid retrieval layer, neither system can enrich the other during run-time reasoning.

---

## 3. Why a Graph-Based Fraud Investigation Architecture

In relational schemas, discovering whether an alert transaction is connected to another compromised account requires expensive recursive multi-table SQL `JOIN` operations across transaction logs, card accounts, and identity tables. As the neighborhood depth grows beyond 2 hops, relational query execution times degrade exponentially.

A Native Parallel Graph (NPG) database such as TigerGraph represents accounts, transactions, devices, and regulatory entities as vertices connected by explicit directional edges. In TigerGraph, multi-hop relationship traversals execute in sub-millisecond parallel memory lookups:
- **Device Rings**: Traversing `Transaction -> FROM_DEVICE -> DeviceProfile <- FROM_DEVICE <- Transaction <- MADE <- Card` reveals multi-card fraud rings within 4 graph hops.
- **Card Testing Velocity**: Traversing `Card -> MADE -> Transaction -> NEXT -> Transaction` reveals rapid micro-authorization sequences ($<\$5.00$) executed immediately prior to major merchant purchases.
- **Historical Recidivism**: Traversing `Card <- ON_CARD <- ClosedCase` immediately links active alerts to prior confirmed compromise dockets and regulatory filings.

---

## 4. Dataset and Data Engineering

FraudGraph AI is engineered upon the benchmark **HHGOA_IEEE** dataset (derived from the IEEE-CIS Fraud Detection benchmark and augmented for complex enterprise fraud workflows). The raw input data encompasses:
- `transactions.csv` (590,742 rows, 397 columns, 675 MB): Financial amounts, card attributes, merchant features, calendar timestamps (`ts`), and channel designations (`in_person`, `online`).
- `identity.csv` (144,432 rows, 41 columns, 25.5 MB): Device hardware signatures, operating systems, mobile browser strings, screen resolutions, and proxy statuses.
- `closed_cases_history.csv` (5,565 rows, 15 columns, 2.58 MB): Historic bank investigation outcomes (July–October 2016) containing 4,665 confirmed fraud cases and 900 cleared cases with analyst notes and regulatory outcomes.
- `case_pack.csv` (20 rows, 8 columns, 10 KB): Official blind benchmark cases (`HHG-001` through `HHG-020`) containing trigger texts, flagged transactions, and associated cards.

### Memory-Efficient Data Pipeline

To transform 675 MB of dense tabular records into pristine graph load files without Out-Of-Memory (OOM) faults, we implemented a chunked streaming pipeline in `src/data/`:
1. **`DataLoader`** (`loaders.py`): Streams raw CSVs using chunked generators with unified column typing.
2. **`DataTransformer`** (`transformers.py`): Synthesizes clean primary keys, extracting deterministic `Customer` identifiers and generating composite string hashes for `DeviceProfile` records.
3. **`RelationshipDeriver`** (`relationships.py`): Computes all directed relationships. Specifically, it groups transactions per payment card and sorts them chronologically by timestamp `ts`, emitting monotonic `NEXT` transaction transitions.
4. **`DataValidator`** (`validators.py`): Performs invariant assertions, guaranteeing 100% referential integrity with zero dangling edges.

The pipeline outputs 16 verified CSV files into `data/graph_load/`: 7 vertex files and 9 edge files.

---

## 5. Fraud Graph Data Model

The verified graph model consists of **7 vertex types** and **9 directed edge types**, audited and certified in `docs/RELATIONSHIP_AUDIT_REPORT.md` and `docs/data-model.md`.

### Graph Model Specification

| Vertex Type | Primary Key | Key Attributes | Verified Count |
|---|---|---|---|
| **`Customer`** | `customer_id` | `customer_id` | 13,553 |
| **`Card`** | `card_id` | `card_id`, `customer_id`, `card1`, `card_network`, `card_type` | 13,933 |
| **`Transaction`** | `TransactionID` | `ts`, `channel`, `risk_score`, `amount`, `product_cd`, `C1`..`C14`, `D1`..`D15` | 590,742 |
| **`DeviceProfile`**| `device_profile_id` | `device_type`, `device_info`, `os`, `browser`, `screen`, `proxy_status` | 9,706 |
| **`EmailDomain`** | `domain_name` | `domain_name` | 60 |
| **`BillingRegion`**| `addr1` | `addr1`, `country_code` (`addr2`) | 332 |
| **`ClosedCase`** | `case_id` | `customer_id`, `card_id`, `opened_at`, `closed_at`, `outcome`, `pattern`, `exposure_usd`, `report_filed` | 5,565 |

### Graph Relationships (Edges)

```
       ┌──────────┐
       │ Customer │
       └────┬─────┘
            │ OWNS (13,933)
            ▼
       ┌──────────┐            NEXT (577,189)
       │   Card   │◄────────────────────────────────┐
       └────┬─────┘                                 │
            │ MADE (590,742)                        │
            ▼                                       │
       ┌─────────────┐──────────────────────────────┘
       │ Transaction │
       └──┬───┬───┬──┘
          │   │   │ FROM_DEVICE (144,432)
          │   │   └──────────────────────► ┌───────────────┐
          │   │ PURCHASER_EMAIL (496,262)  │ DeviceProfile │
          │   └──────────────────────────► └───────────────┘
          │ BILLED_IN (525,003)            ┌───────────────┐
          └──────────────────────────────► │  EmailDomain  │
                                           └───────────────┘
       ┌────────────┐                      ┌───────────────┐
       │ ClosedCase │                      │ BillingRegion │
       └──┬───┬───┬─┘                      └───────────────┘
          │   │   │ INVOLVES (14,955)
          │   │   └──────────────────────► [ Transaction ]
          │   │ ON_CARD (5,565)
          │   └──────────────────────────► [ Card ]
          │ CONNECTED_TO (92)
          └──────────────────────────────► [ Card ]
```

- **`OWNS`** (`Customer -> Card`): 13,933 directed ownership assignments.
- **`MADE`** (`Card -> Transaction`): 590,742 transaction creation records.
- **`FROM_DEVICE`** (`Transaction -> DeviceProfile`): 144,432 identity links connecting transactions to device fingerprints.
- **`PURCHASER_EMAIL`** (`Transaction -> EmailDomain`): 496,262 email domain links.
- **`BILLED_IN`** (`Transaction -> BillingRegion`): 525,003 billing jurisdiction mappings.
- **`NEXT`** (`Transaction -> Transaction`): 577,189 chronological sequence edges tracking cardholder transaction flow over time.
- **`INVOLVES`** (`ClosedCase -> Transaction`): 14,955 historical transaction attachments.
- **`ON_CARD`** (`ClosedCase -> Card`): 5,565 historical primary compromised card associations.
- **`CONNECTED_TO`** (`ClosedCase -> Card`): 92 secondary compromised card links across historical syndicated fraud rings.

---

## 6. TigerGraph Architecture

The system provides dual-mode execution via a clean client abstraction layer in `src/graph/`:

```
                    ┌────────────────────────────┐
                    │      GraphQueryEngine      │
                    │   (Unified Dispatcher)     │
                    └─────────────┬──────────────┘
                                  │
                  Is TigerGraph Live Reachable?
                                  │
                     ┌────────────┴────────────┐
                 YES │                         │ NO (Fallback)
                     ▼                         ▼
        ┌─────────────────────────┐ ┌─────────────────────────┐
        │  LiveTigerGraphClient   │ │    LocalGraphClient     │
        │   RESTPP Port 9000      │ │   In-Memory Indexing    │
        │   GSQL Pre-compiled     │ │   12 Dictionary Stores  │
        └─────────────────────────┘ └─────────────────────────┘
```

1. **`LiveTigerGraphClient`** (`live_client.py`): Interfaces with TigerGraph Savanna or self-hosted Docker instances over RESTPP API endpoints (`/query/FraudGraph/...` and `/graph/FraudGraph/...`). Queries are defined in pre-compiled GSQL (`tigergraph/queries/`).
2. **`LocalGraphClient`** (`client.py`): An optimized, in-memory graph engine loading `data/graph_load/` CSVs. It instantiates 12 internal hash dictionary indices, resolving vertex lookups, multi-hop traversals, and temporal sequence queries in sub-millisecond offline execution.
3. **`GraphQueryEngine`** (`queries.py`): The dynamic dispatcher. Upon initialization, it probes TigerGraph endpoints (`/echo` and `/version`). If unconfigured or unreachable, it falls back gracefully to `LocalGraphClient`, logging the active mode without system disruption.

---

## 7. MCP Graph Investigation Tools

FraudGraph AI exposes **10 standardized graph tools** in `src/tools/mcp_server.py` complying with the Model Context Protocol specification. Every tool call returns a structured envelope containing explicit status flags, error codes, execution modes, and strongly typed data payloads:

```json
{
  "status": "success",
  "error_code": null,
  "message": "Successfully retrieved details for transaction '3514030'",
  "data": { ... },
  "execution_mode": "offline_local"
}
```

### The 10 MCP Tools

1. **`get_transaction_details(txn_id)`**: Retrieves vertex attributes (amount, timestamp, channel, risk score, C/D features) and connected edges for a specific transaction.
2. **`get_card_history(card_id, limit)`**: Fetches the card vertex and its reverse-chronological transaction history.
3. **`get_connected_cards_and_customers(card_id)`**: Traverses ownership relationships to identify secondary cards belonging to the cardholder and shared entities.
4. **`find_shared_devices(card_id)`**: Performs a multi-hop traversal to identify all `DeviceProfile` vertices associated with the card and discovers all other payment cards that transacted on those same devices.
5. **`get_transaction_neighborhood(txn_id, depth)`**: Extracts the $k$-hop subgraph (depth 1 to 3) surrounding a transaction, collecting adjacent cards, device profiles, email domains, and billing regions.
6. **`get_connected_transactions(card_id)`**: Traverses chronological `NEXT` edges to return the exact sequential payment journey executed on a card.
7. **`get_historical_closed_cases(card_id, limit)`**: Queries `ON_CARD` and `CONNECTED_TO` edges to retrieve prior resolved fraud cases and analyst outcomes involving the card.
8. **`detect_card_testing_pattern(card_id)`**: Algorithmic detector searching for 3 or more micro-authorizations ($<\$5.00$) within a 1-hour rolling window preceding a larger transaction.
9. **`detect_out_of_region_pattern(card_id)`**: Cross-references transaction billing regions against the cardholder's historical modal home region (`addr1`), flagging geographic anomalies.
10. **`write_case_to_graph(case_data)`**: Upserts a resolved investigation case as a new `ClosedCase` vertex and creates `INVOLVES`, `ON_CARD`, and `CONNECTED_TO` edges in graph memory.

---

## 8. Hybrid GraphRAG Architecture

To ground reasoning in both institutional memory and topological evidence, FraudGraph AI implements a specialized **Hybrid GraphRAG** architecture (`src/rag/`).

### Document Corpus Indexing
Rather than using external, black-box embedding APIs, the vector store (`vector_store.py`) indexes **5,590 authoritative documents** directly from the project repository using Scikit-Learn TF-IDF vectorization with cosine similarity ranking:
- **5,565 Historical Closed Cases** (`closed_cases_history.csv`): Real past fraud dispositions, analyst notes, and outcomes.
- **5 Recognized Fraud Typologies**: Formally defining `card_testing`, `card_not_present_fraud`, `card_not_present_new_device`, `out_of_region_use`, and `account_takeover`.
- **10 Regulatory Standards**: Verbatim guidance from FinCEN SAR narrative guidelines and the FFIEC BSA/AML Examination Manual.
- **10 Policy Rules**: Institutional operational definitions of Rules R1 through R10.

### Hybrid Retrieval Fusion
The `HybridGraphRAGRetriever` (`retriever.py`) merges topological entity facts gathered by MCP graph tools with semantic matches returned by the vector store. Every retrieved item is formatted into an immutable **Evidence Item** bearing strict provenance metadata:

```json
{
  "claim": "Card C12382-K1 shares device profile(s) with 258 other card(s)",
  "source": "graph",
  "ref": "tool:find_shared_devices(card_id=C12382-K1)",
  "entity_ids": ["C12382-K1", "C00232-K1", "C00235-K1"]
}
```

---

## 9. Deterministic R1–R10 Policy Engine

Fraud compliance requires absolute determinism. Delegating blocking directives or SAR filings to an LLM prompt invites hallucinated reasoning, non-reproducible decisions, and regulatory exposure. 

FraudGraph AI features a completely deterministic, zero-LLM policy engine (`src/policy/engine.py`) implementing **Fraud Policy Version 1.0**:

### The 10 Evaluated Policy Rules

- **`R1: Verify before you block on a weak signal`**: If an investigation rests on a single signal and fraud probability $< 0.70$, the system mandates `VERIFY_WITH_CUSTOMER` or `STEP_UP_AUTH` before any card block.
- **`R2: Customer denies the transaction`**: When cardholder denies activity, mandates `BLOCK_CARD` and `CREATE_CASE`. Escalates to `FILE_REPORT` if exposure $> \$1,000$, devices are shared, or syndication is detected.
- **`R3: Customer confirms the transaction`**: When cardholder validates activity, mandates `CLOSE_NO_FRAUD`.
- **`R4: No reply within 24 hours`**: Recommends `MONITOR_CARD` and `DECLINE_TRANSACTION` for pending authorizations. If exposure $> \$500$, triggers `ESCALATE_TO_ANALYST`.
- **`R5: Card testing`**: Detects micro-authorizations. Recommends `DECLINE_TRANSACTION` and `STEP_UP_AUTH`. If a subsequent purchase $> \$100$ cleared, upgrades immediately to `BLOCK_CARD`.
- **`R6: Shared origin ring`**: When multiple cards share devices, billing regions, or emails with fraud probability $\ge 0.30$, mandates `CREATE_CASE`, `FILE_REPORT`, and `MONITOR_CONNECTED_CARDS`.
- **`R7: Disputed but legitimate charge`**: If a disputed charge matches historical recurring intervals (merchant, amount, period), mandates `CREATE_CASE` and `WARN_CUSTOMER` without card blocking.
- **`R8: Escalate when uncertain and exposed`**: If verdict is `uncertain` and exposure $> \$500$, or if evidence signals conflict, mandates `ESCALATE_TO_ANALYST`.
- **`R9: Undocumented pattern`**: When novel, unclassified coordinated abuse is detected, triggers `CREATE_CASE`, `FILE_REPORT`, and `ESCALATE_TO_ANALYST`.
- **`R10: Never BLOCK_ALL_CARDS unless qualified`**: Strictly forbids `BLOCK_ALL_CARDS` unless $\ge 2$ cards of a customer have confirmed fraud or customer credentials are confirmed compromised.

### Three-Tier Approval Routing

Every recommended action is assigned an enforceable operational tier:
1. **`auto`**: Autonomous system execution (`ALLOW_TRANSACTION`, `MONITOR_CARD`, `WARN_CUSTOMER`, `VERIFY_WITH_CUSTOMER`, `STEP_UP_AUTH`, `CREATE_CASE`, `CLOSE_NO_FRAUD`).
2. **`L1` (Team Lead)**: Moderate intervention (`DECLINE_TRANSACTION`, `BLOCK_CARD` when exposure $\le \$2,500$).
3. **`L2` (Fraud Operations Manager)**: High-risk intervention (`BLOCK_CARD` when exposure $> \$2,500$, `BLOCK_ALL_CARDS`, `FILE_REPORT`).

### Initial vs. Final Next-Best-Action (NBA)

The engine evaluates policy twice per investigation:
- **Initial NBA**: Determined when the alert is first ingested prior to cardholder verification (e.g., recommend `VERIFY_WITH_CUSTOMER` and `MONITOR_CARD`).
- **Final NBA**: Determined after evidence gathering and simulated cardholder response (e.g., cardholder denies transaction $\to$ upgrade to `BLOCK_CARD` and `FILE_REPORT`).
- **`what_changed`**: An audited textual explanation contrasting the initial and final action queues.

---

## 10. LangGraph Investigation Agent

To orchestrate the end-to-end investigation, FraudGraph AI builds a stateful directed execution graph using **LangGraph** (`src/agent/orchestrator.py`). The state machine is governed by an immutable typed state container (`InvestigationState`) tracking alert triggers, graph evidence, vector search hits, risk scores, simulated customer responses, stopping criteria, and telemetry.

### Architecture at a Glance

```
                         ┌────────────────────┐
                         │  1. trigger_handler│
                         └─────────┬──────────┘
                                   │
                                   ▼
                         ┌────────────────────┐
                         │2. evidence_gatherer│
                         └─────────┬──────────┘
                                   │
                                   ▼
                         ┌────────────────────┐
                         │ 3. pattern_matcher │
                         └─────────┬──────────┘
                                   │
                                   ▼
                         ┌────────────────────┐
                         │  4. rag_retriever  │
                         └─────────┬──────────┘
                                   │
                                   ▼
                         ┌────────────────────┐
                         │  5. risk_assessor  │
                         └─────────┬──────────┘
                                   │
                                   ▼
                         ┌────────────────────┐
                         │6. sufficiency_eval │
                         └─────────┬──────────┘
                                   │
                                   ▼
                         ┌────────────────────┐
                         │ 7. policy_evaluator│
                         └─────────┬──────────┘
                                   │
                                   ▼
                         ┌────────────────────┐
                         │  8. case_updater   │
                         └─────────┬──────────┘
                                   │
                                   ▼
                                [ END ]
```

---

## 11. Investigation Workflow (The 8 LangGraph Nodes)

Every investigation traverses 8 discrete, auditable nodes:

1. **`trigger_handler`**: Validates the input alert, extracts the flagged transaction ID and payment card ID, initializes the `InvestigationState`, and logs the initial telemetry timestamp.
2. **`evidence_gatherer`**: Dispatches calls to Phase 4 MCP tools (`get_transaction_details`, `get_card_history`, `get_connected_cards_and_customers`, `find_shared_devices`, `get_transaction_neighborhood`, `get_connected_transactions`, `get_historical_closed_cases`), accumulating graph evidence claims.
3. **`pattern_matcher`**: Evaluates card testing sequences (Tool 8), out-of-region use (Tool 9), and multi-card shared device clusters, classifying the primary typology (`card_not_present_new_device`, `card_testing`, `out_of_region_use`, or `none`).
4. **`rag_retriever`**: Queries the Hybrid GraphRAG vector store using contextual query strings, fetching similar historical closed cases, regulatory guidance notes, and policy references.
5. **`risk_assessor`**: Aggregates affected transaction values to compute `exposure_usd`, evaluates independent evidence signals, computes `fraud_probability`, and assigns an initial verdict (`fraud`, `legitimate`, or `uncertain`).
6. **`sufficiency_evaluator`**: Simulates cardholder verification responses (confirm/deny/unresponsive) and enforces formal stopping criteria (Section 6 of Policy).
7. **`policy_evaluator`**: Executes the deterministic Policy Engine, comparing initial vs. final NBA queues, mapping `auto`/`L1`/`L2` approval routes, and generating a compliant SAR narrative if filing thresholds are met.
8. **`case_updater`**: Writes the final investigation record back to graph memory via `write_case_to_graph` (Tool 10), completing the lifecycle and stamping execution telemetry.

---

## 12. Evidence Provenance and Explainability

In financial crimes enforcement, a black-box probability score is legally indefensible. FraudGraph AI enforces a rigorous **Four-Source Provenance Standard** across all generated answer files:

| Source Code | Origin Description | Example Reference |
|---|---|---|
| **`graph`** | Direct graph traversal from TigerGraph / LocalGraphClient | `tool:get_transaction_details(txn_id=3514030)` |
| **`document`**| Vector store retrieval from closed case or policy store | `tool:vector_search::closed_cases` |
| **`customer`**| Simulated cardholder outreach / verification response | `evidence_request:1` |
| **`external`**| External sanction lists, merchant registries, or AML feeds | `external:consortium_registry` |

Every claim in the final case docket points to its exact source and entity ID list. Suspicious Activity Reports (SAR) generated by the agent detail the full timeline, subjects, exposure, and typologies, linking directly to the underlying graph evidence trail.

---

## 13. Benchmark Evaluation

The complete platform was evaluated across all **20 official exam benchmark cases** (`HHG-001` through `HHG-020`) using the automated benchmarking driver (`scripts/evaluate_benchmarks.py`).

### Verification & Schema Compliance

All 20 cases generated comprehensive JSON answer files saved to `cases/HHG-001.json` through `cases/HHG-020.json`.

| Check | Expected | Actual | Compliance Status |
|---|---|---|---|
| Benchmark Cases Evaluated | 20 | 20 | **100% PASS** |
| Answer JSON Files Generated | 20 | 20 | **100% PASS** |
| JSON Syntax & Formatting | 20 | 20 | **100% PASS** |
| 3-Part Schema (`case`, `sar`, `next_best_actions`)| 20 | 20 | **100% PASS** |
| Approval Route Verification (`auto`, `L1`, `L2`)| 20 | 20 | **100% PASS** |
| Evidence Provenance (`graph`, `document`, etc.) | 20 | 20 | **100% PASS** |

---

## 14. Plain RAG vs GraphRAG vs Agentic GraphRAG

To measure the architectural value of graph traversals and agentic state management, the 20 benchmark cases were executed across three distinct operational modes. The measured metrics from `docs/BENCHMARK_REPORT.md` are presented below:

### Three-Mode Operational Comparison Table

| Operational Metric | Plain RAG | GraphRAG | Agentic GraphRAG (Phase 6) |
|---|---|---|---|
| **Graph Tool Calls (Total / Avg)** | 0 / 0.0 | 180 / 9.0 | 180 / 9.0 |
| **Evidence Items per Case (Avg)** | 5.0 | 8.9 | 6.9 |
| **SARs Filed (out of 20)** | 0 | 0 | 20 |
| **Evidence Provenance Compliance** | 100.0% | 100.0% | 100.0% |
| **Average Latency per Case** | **0.011s** | 0.059s | 0.062s |
| **Ground Truth Accuracy** | *NOT COMPUTABLE* | *NOT COMPUTABLE* | *NOT COMPUTABLE* |

### Architectural Trade-Off Analysis

1. **Plain RAG (Baseline)**: Operates strictly on semantic text matching against historical documents. While exhibiting the lowest latency (0.011s), it is completely blind to topological device sharing, transaction velocities, and card connections. Consequently, it gathers fewer evidence items and lacks the structural confidence to formulate compliance filings.
2. **GraphRAG (Direct Hybrid)**: Augments text retrieval with 9 graph tool calls per case, gathering the highest volume of raw evidence items (8.9 per case). However, without stateful orchestration or stopping logic, it cannot evaluate dynamic customer outreach or resolve conflicting signals.
3. **Agentic GraphRAG (Phase 6 Full Orchestration)**: Combines graph traversals with stateful multi-node reasoning. The agent applies stopping criteria to prune redundant evidence, simulates customer confirmation outreach, triggers deterministic policy actions, and generates complete, audit-ready SAR packages for 20/20 cases with minimal latency overhead (0.062s per case).

---

## 15. Streamlit Investigation Dashboard

FraudGraph AI includes an interactive, browser-based investigation dashboard (`ui/app.py` and `app.py`) built with **Streamlit**:

```
┌─────────────────────────────────────────────────────────────────────────┐
│ FraudGraph AI — Autonomous Fraud Investigation Platform                │
├────────────────────────────────┬────────────────────────────────────────┤
│ Active Case: HHG-001           │ Verdict: CONFIRMED FRAUD (0.86)        │
│ Card: C12382-K1                │ Pattern: card_not_present_new_device   │
│ Customer: C12382               │ Total Exposure: $77.07 USD             │
├────────────────────────────────┴────────────────────────────────────────┤
│ Entity Subgraph Visualization (SVG Render)                              │
│   [Customer C12382] ──OWNS──► [Card C12382-K1] ──MADE──► [Txn 3514030] │
│                                      │                                  │
│                                 SHARED_DEVICE                           │
│                                      ▼                                  │
│                          [Device iOS Mobile Safari]                     │
│                                      ▲                                  │
│                                 SHARED_DEVICE                           │
│                                      │                                  │
│                        [258 Connected Cards Ring]                       │
├─────────────────────────────────────────────────────────────────────────┤
│ Evidence Provenance Log (Graph, Document, Customer)                     │
│ SAR Filing Narrative & Regulatory Export (FinCEN Format)                │
│ Next-Best-Action Policy Queue (Initial vs Final, auto / L1 / L2 Routes) │
└─────────────────────────────────────────────────────────────────────────┘
```

The UI provides:
- **Case Investigation Inspector**: Instant filtering across all 20 benchmark cases, displaying fraud probability, risk tier, pattern classification, exposure amounts, and stopping rationales.
- **Interactive SVG Subgraph Visualizer**: Dynamically draws the local entity network, connecting customers, payment cards, flagged transactions, shared devices, and prior closed cases.
- **Evidence Provenance Audit Trail**: Categorized view of all evidence claims tagged by origin (`graph`, `document`, `customer`).
- **SAR & Policy Explorer**: Interactive viewing of generated SAR narratives and real-time inspection of Rules R1–R10.
- **Benchmark Comparison Dashboard**: Interactive comparison of Plain RAG, GraphRAG, and Agentic GraphRAG operational performance.

---

## 16. Testing and Validation

System correctness and regression resistance were verified across 12 automated test suites:

- `tests/test_loaders.py`: Chunked CSV streaming and column integrity.
- `tests/test_transformers.py`: Entity extraction and primary key determinism.
- `tests/test_relationships.py`: Edge derivation logic.
- `tests/test_relationship_invariants.py`: Referential integrity and zero-dangling-edge invariants.
- `tests/test_tigergraph_schema.py`: GSQL schema syntax, loading jobs, and query contracts.
- `tests/test_mcp_tools.py`: All 10 MCP graph tools, error envelopes, and index queries.
- `tests/test_policy_engine.py`: Rules R1–R10, initial/final NBA, approval routes, and stopping thresholds.
- `tests/test_rag.py`: Vector store indexing (5,590 docs), cosine similarity ranking, and hybrid retrieval.
- `tests/test_agent_orchestration.py`: LangGraph state machine, node transitions, and evidence simulation.
- `tests/test_benchmark_evaluation.py`: 20 benchmark answer files and schema compliance.
- `tests/test_ui_data.py`: Streamlit data loaders, error resilience, and credential safety.

### Final Verification Result

```text
Ran 151 tests in 352.535s

OK (0 failures, 0 errors)
```

The entire system passed **151 / 151 automated tests** with zero failures and zero errors.

---

## 17. Benchmark Limitations

In keeping with rigorous engineering standards, two key benchmark limitations are documented factually:

1. **Ground-Truth Accuracy Metrics (Precision, Recall, F1-Score)**:
   - **Status**: *NOT COMPUTABLE FROM AVAILABLE GROUND TRUTH*.
   - **Rationale**: In accordance with the official challenge specification (`dataset/HHGOA_IEEE/README.md`), the 20 benchmark cases in `case_pack.csv` intentionally withhold true binary fraud labels to serve as a blind evaluation test pack. Fabricating an accuracy or F1 score without the official competition answer key is scientifically invalid.
2. **Live TigerGraph RESTPP Benchmark**:
   - **Status**: *NOT COMPUTABLE IN TEST ENVIRONMENT*.
   - **Rationale**: A live TigerGraph Savanna or self-hosted enterprise instance was not configured in the local execution environment (`TIGERGRAPH LIVE STATUS: NOT CONFIGURED`). All graph traversals were executed via the verified `LocalGraphClient` offline engine, which implements identical query contracts.

---

## 18. Lessons Learned

1. **Deterministic Logic Trumps LLM Prompts for Compliance**: Embedding policy rules (R1–R10) inside Python classes with mathematical threshold checks eliminated 100% of hallucinations and guaranteed reproducible compliance routing.
2. **Chronological Edge Derivation Unlocks High-Yield Patterns**: Synthesizing the `NEXT` transaction sequence edge during data engineering enabled sub-millisecond card testing detection ($<\$5.00$ micro-auths) that would have required cumbersome window functions in relational SQL.
3. **Graph Topology Is Essential for Evidence Provenance**: Associating evidence claims directly with graph tool calls (`tool:find_shared_devices`) provides legal defensibility that vector-only RAG cannot match.
4. **Offline Dual-Client Architecture Accelerates Development**: Building `LocalGraphClient` with identical interfaces to `LiveTigerGraphClient` allowed comprehensive unit testing, benchmark evaluation, and UI development without continuous network dependencies on remote graph clusters.

---

## 19. Future Enhancements

1. **Live TigerGraph Savanna Deployment**: Complete cloud cluster provisioning to benchmark distributed GSQL query latency against massive billion-edge transaction graphs.
2. **Dynamic Graph Neural Network (GNN) Embeddings**: Integrate TigerGraph Graph Data Science (GDS) library algorithms (such as Node2Vec or FastRP) to pass structural graph embeddings into the hybrid retrieval layer.
3. **Active Directory & Multi-Tenant RBAC**: Expand approval routing (`auto`, `L1`, `L2`) into enterprise Single Sign-On (SSO) workflows with cryptographic analyst signatures for L2 SAR filings.
4. **Automated Feedback Loop Ingestion**: Feed resolved, analyst-edited cases back into TigerGraph in real time, automatically expanding the vector store's historical index.

---

## 20. Conclusion

FraudGraph AI demonstrates that the future of enterprise fraud investigation lies at the intersection of **Native Parallel Graphs**, **Hybrid Retrieval-Augmented Generation**, and **Deterministic Stateful Agents**. By replacing disjoint manual analyst pivots with an automated, provenance-aware LangGraph state machine backed by TigerGraph 4.2.5, the platform bridges the gap between raw anomaly detection and legally defensible compliance action.

---

## Key Takeaways

- **Graph Power**: 7 vertices and 9 directed edges represent 590K+ transactions, identifying complex multi-card device-sharing syndicates within 4 hops.
- **MCP Tool Standardization**: 10 Model Context Protocol tools expose graph traversals with uniform JSON error-handling envelopes.
- **Zero-Hallucination Policy**: Deterministic R1–R10 engine enforces compliance actions and three-tier (`auto`, `L1`, `L2`) approval routes without LLM hallucinations.
- **Hybrid GraphRAG**: Indexes 5,590 documents (cases, typologies, regulations, rules), merging semantic relevance with topological graph evidence.
- **End-to-End Verification**: 20/20 benchmark cases generated with 100% schema compliance, supported by 151/151 passing automated tests.

---

## Team

**Team:** NexusForge  
**Project:** FraudGraph AI  
**Competition:** TigerGraph × HHGoa 2026 Hackathon  
**Repository:** [https://github.com/Mokshith-11/FraudGraph-AI](https://github.com/Mokshith-11/FraudGraph-AI)
