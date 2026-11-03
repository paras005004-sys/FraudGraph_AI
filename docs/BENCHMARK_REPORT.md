# FraudGraph AI — Benchmark Evaluation Report

**Generated**: 2026-09-22T15:14:11.396133  
**Execution Environment**: Offline `LocalGraphClient` (TigerGraph Live: NOT CONFIGURED)  
**Cases Evaluated**: 20 cases (`HHG-001` through `HHG-020` from `case_pack.csv`)

---

## 1. Executive Summary

All 20 official Hacker House Goa 2026 exam cases were investigated across three distinct execution modes:
1. **Plain RAG**: Vector-only baseline without graph investigation tools.
2. **GraphRAG**: Hybrid retrieval combining graph tools and vector search without stateful orchestration.
3. **Agentic GraphRAG**: Full Phase 6 LangGraph agent orchestrating multi-node investigation, Phase 4 tools, Phase 5 policy engine, and deterministic verification simulation.

All **20 answer files** (`cases/HHG-001.json` through `cases/HHG-020.json`) were generated and rigorously verified against the documented schema.

---

## 2. Answer-File Schema Validation Results

| Check | Expected | Actual | Status |
|---|---|---|---|
| Total Cases | 20 | 20 | PASS |
| Answer Files Present | 20 | 20 | PASS |
| Files Missing | 0 | 0 | PASS |
| Valid JSON Syntax | 20 | 20 | PASS |
| Case ID & Flagged Txn Matches | 20 | 20 | PASS |
| 3-Part Schema Compliance (`case`, `sar`, `next_best_actions`) | 20 | 20 | PASS |
| Approval Route Verification (`auto`, `L1`, `L2`) | 20 | 20 | PASS |
| Evidence Provenance Compliance (`graph`, `document`, `customer`) | 20 | 20 | PASS |
| **Overall Validation** | **100%** | **100.0%** | **VERIFIED** |

---

## 3. Three-Mode Execution Comparison

The following table presents actual measured operational metrics across the 20 benchmark cases. As specified in project guidelines, no mode is artificially ranked or declared a winner.

| Operational Metric | Plain RAG | GraphRAG | Agentic GraphRAG (Phase 6) |
|---|---|---|---|
| **Graph Tool Calls (Total / Avg)** | 0 / 0.0 | 180 / 9.0 | 180 / 9.0 |
| **Evidence Items per Case (Avg)** | 5.0 | 8.9 | 6.9 |
| **SARs Filed (out of 20)** | 0 | 0 | 20 |
| **Evidence Provenance Compliance** | 100.0% | 100.0% | 100.0% |
| **Average Latency per Case** | 0.011s | 0.059s | 0.062s |
| **Ground Truth Accuracy** | *NOT COMPUTABLE FROM AVAILABLE GROUND TRUTH (competition benchmark answer key is withheld; no labels in case_pack.csv)* | *NOT COMPUTABLE FROM AVAILABLE GROUND TRUTH (competition benchmark answer key is withheld; no labels in case_pack.csv)* | *NOT COMPUTABLE FROM AVAILABLE GROUND TRUTH (competition benchmark answer key is withheld; no labels in case_pack.csv)* |

---

## 4. Case-by-Case Summary (Agentic GraphRAG)

| Case ID | Trigger Type | Pattern Identified | Assessed Verdict | Fraud Prob | Exposure (USD) | Stop Reason | SAR Filed |
|---|---|---|---|---|---|---|---|
| `HHG-001` | `N/A` | `card_not_present_new_device` | **fraud** | 0.86 | $77.07 | Fraud probability 0.86 >= 0.85 supported... | Yes |
| `HHG-002` | `N/A` | `card_not_present_new_device` | **fraud** | 0.86 | $292.36 | Fraud probability 0.86 >= 0.85 supported... | Yes |
| `HHG-003` | `N/A` | `card_not_present_new_device` | **fraud** | 0.89 | $49.00 | Fraud probability 0.89 >= 0.85 supported... | Yes |
| `HHG-004` | `N/A` | `card_not_present_new_device` | **fraud** | 0.89 | $128.33 | Fraud probability 0.89 >= 0.85 supported... | Yes |
| `HHG-005` | `N/A` | `card_not_present_new_device` | **fraud** | 0.86 | $100.07 | Fraud probability 0.86 >= 0.85 supported... | Yes |
| `HHG-006` | `N/A` | `card_not_present_new_device` | **fraud** | 0.89 | $482.12 | Fraud probability 0.89 >= 0.85 supported... | Yes |
| `HHG-007` | `N/A` | `card_not_present_new_device` | **fraud** | 0.86 | $111.92 | Fraud probability 0.86 >= 0.85 supported... | Yes |
| `HHG-008` | `N/A` | `card_not_present_new_device` | **fraud** | 0.89 | $55.68 | Fraud probability 0.89 >= 0.85 supported... | Yes |
| `HHG-009` | `N/A` | `card_not_present_new_device` | **fraud** | 0.89 | $30.02 | Fraud probability 0.89 >= 0.85 supported... | Yes |
| `HHG-010` | `N/A` | `card_not_present_new_device` | **fraud** | 0.86 | $1,000.03 | Fraud probability 0.86 >= 0.85 supported... | Yes |
| `HHG-011` | `N/A` | `card_testing` | **fraud** | 0.89 | $131.30 | Fraud probability 0.89 >= 0.85 supported... | Yes |
| `HHG-012` | `N/A` | `card_not_present_new_device` | **fraud** | 0.86 | $30.91 | Fraud probability 0.86 >= 0.85 supported... | Yes |
| `HHG-013` | `N/A` | `card_not_present_new_device` | **fraud** | 0.86 | $35.66 | Fraud probability 0.86 >= 0.85 supported... | Yes |
| `HHG-014` | `N/A` | `card_not_present_new_device` | **fraud** | 0.86 | $74.96 | Fraud probability 0.86 >= 0.85 supported... | Yes |
| `HHG-015` | `N/A` | `card_not_present_new_device` | **fraud** | 0.86 | $599.94 | Fraud probability 0.86 >= 0.85 supported... | Yes |
| `HHG-016` | `N/A` | `card_not_present_new_device` | **fraud** | 0.89 | $59.67 | Fraud probability 0.89 >= 0.85 supported... | Yes |
| `HHG-017` | `N/A` | `card_not_present_new_device` | **fraud** | 0.86 | $100.09 | Fraud probability 0.86 >= 0.85 supported... | Yes |
| `HHG-018` | `N/A` | `card_not_present_new_device` | **fraud** | 0.89 | $39.08 | Fraud probability 0.89 >= 0.85 supported... | Yes |
| `HHG-019` | `N/A` | `card_not_present_new_device` | **fraud** | 0.86 | $99.92 | Fraud probability 0.86 >= 0.85 supported... | Yes |
| `HHG-020` | `N/A` | `card_not_present_new_device` | **fraud** | 0.86 | $125.08 | Fraud probability 0.86 >= 0.85 supported... | Yes |

---

## 5. Uncomputable Metrics & Rationale

1. **Ground Truth Accuracy (Precision / Recall / F1)**:
   - *Status*: **NOT COMPUTABLE FROM AVAILABLE GROUND TRUTH**
   - *Rationale*: In accordance with `dataset/HHGOA_IEEE/README.md`, `case_pack.csv` intentionally withholds the binary fraud classification labels to serve as a blind evaluation test pack. Fabricating an accuracy score without the authoritative judge answer key is strictly prohibited.

2. **Live TigerGraph RESTPP Benchmark**:
   - *Status*: **NOT COMPUTABLE**
   - *Rationale*: A live TigerGraph Savanna/Cloud instance is not configured in this environment. All graph traversals were executed via `LocalGraphClient`.
