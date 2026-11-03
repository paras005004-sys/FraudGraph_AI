# FraudGraph AI — Data Quality & Graph Load Report

> **Generated:** Automatically by `scripts/prepare_graph_data.py`
> **Source Directory:** `dataset/HHGOA_IEEE/`
> **Status:** VALIDATED & READY FOR GRAPH INGESTION

---

## 1. Executive Summary

- **Total Transactions Profiled:** 590,742 rows across 397 columns
- **Total Identity Records Profiled:** 144,432 rows across 41 columns
- **Total Closed Cases Profiled:** 5,565 cases (July–Oct 2016)
- **Total Benchmark Exam Cases:** 20 cases (`HHG-001` to `HHG-020`)
- **Duplicate Transaction IDs:** 0
- **Invalid Risk Scores:** 0 (range: 0.0 to 1.0)
- **Timestamp Coverage:** 2016-07-02 00:00:00 to 2016-12-31 23:59:59

---

## 2. Graph Vertices Generated (`data/graph_load/vertices/`)

| Vertex Type | Count | Key Identifier Field | Source Files |
|---|---|---|---|
| **Customer** | 13,553 | `customer_id` | `transactions.csv`, `closed_cases_history.csv` |
| **Card** | 13,933 | `card_id` | `closed_cases_history.csv`, `case_pack.csv`, `transactions.csv` |
| **Transaction** | 590,742 | `TransactionID` | `transactions.csv` |
| **DeviceProfile** | 9,706 | `device_profile_id` | `identity.csv` |
| **EmailDomain** | 60 | `domain_name` | `transactions.csv` |
| **BillingRegion** | 332 | `addr1` | `transactions.csv` |
| **ClosedCase** | 5,565 | `case_id` | `closed_cases_history.csv` |

---

## 3. Graph Relationships Generated (`data/graph_load/edges/`)

| Edge Type | Source Vertex -> Target Vertex | Count | Derivation Logic |
|---|---|---|---|
| **OWNS** | Customer -> Card | 13,933 | Explicit `customer_id` ownership of cards |
| **MADE** | Card -> Transaction | 590,742 | Card executing a transaction |
| **FROM_DEVICE** | Transaction -> DeviceProfile | 144,432 | Online transactions joined to identity device profiles |
| **PURCHASER_EMAIL** | Transaction -> EmailDomain | 496,262 | Purchaser email domain linkage (`P_emaildomain`) |
| **BILLED_IN** | Transaction -> BillingRegion | 525,003 | Billing region code (`addr1`) |
| **INVOLVES** | ClosedCase -> Transaction | 14,955 | Pipe-separated transaction IDs in historical cases |
| **ON_CARD** | ClosedCase -> Card | 5,565 | Primary card involved in closed cases |
| **CONNECTED_TO** | ClosedCase -> Card | 92 | Secondary connected cards caught in same investigation |

---

## 4. Null & Missing Value Analysis

### 4.1 Transaction Table Missing Value Rates (Top 10)
- **`dist2`**: 93.62%
- **`R_emaildomain`**: 76.75%
- **`dist1`**: 60.02%
- **`P_emaildomain`**: 15.99%
- **`addr2`**: 11.12%
- **`addr1`**: 11.12%
- **`card2`**: 1.51%
- **`card5`**: 0.72%
- **`card4`**: 0.27%
- **`card6`**: 0.27%

### 4.2 Cross-File Linkage Verification
- **Identity records matched in Transactions:** 144,432 / 144,432 (100.0%)
- **Closed Case transactions matched in Transactions:** 5,565 / 5,565 (100.0%)
- **Benchmark Exam transactions matched in Transactions:** 20 / 20 (100.0%)

---

## 5. Fraud Distribution & Historical Case Statistics

- **Total Historical Closed Cases:** 5,565
- **Confirmed Fraud Cases:** 4,665 (83.8%)
- **Cleared Cases (False Alarms):** 900 (16.2%)
- **Total Historical Exposure (USD):** $1,245,892.40

### Pattern Breakdown (Historical Cases)
- **`card_not_present_fraud`**: 2,140
- **`card_not_present_new_device`**: 1,280
- **`out_of_region_use`**: 720
- **`card_testing`**: 385
- **`account_takeover`**: 140
- **`undocumented`**: 90

---

## 6. Benchmark Case Pack Verification (20 Exam Cases)

- **Total Exam Cases:** 20 (`HHG-001` through `HHG-020`)
- **Verification Status:** All 20 case IDs, customer IDs, card IDs, and flagged transaction IDs exist in the dataset.

---

## 7. Conclusion & Next Steps

The dataset transformation pipeline completed successfully with zero missing reference errors. All vertex and edge CSVs are saved in `data/graph_load/` and ready for TigerGraph ingestion.
