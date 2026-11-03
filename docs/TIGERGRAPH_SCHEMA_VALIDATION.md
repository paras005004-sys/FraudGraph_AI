# FraudGraph AI — TigerGraph Schema Validation Report

> **Status:** SCHEMA VALIDATED & BENCHMARK TESTED
> **Verdict:** TIGERGRAPH STATUS: READY
> **Date:** 2026-09-21

---

## 1. Schema Completeness Check

- **Vertex Types Verified:** 7 / 7 (`Customer`, `Card`, `Transaction`, `DeviceProfile`, `EmailDomain`, `BillingRegion`, `ClosedCase`)
- **Edge Types Verified:** 9 / 9 (`OWNS`, `MADE`, `FROM_DEVICE`, `PURCHASER_EMAIL`, `BILLED_IN`, `NEXT`, `INVOLVES`, `ON_CARD`, `CONNECTED_TO`)
- **GSQL Schema File:** `tigergraph/schema/fraud_graph.gsql`
- **Loading Job File:** `tigergraph/loading/load_fraud_graph.gsql`
- **GSQL Queries Directory:** `tigergraph/queries/`

---

## 2. Vertex & Edge Count Validation Matrix

| Entity / Relationship | Expected Count | Actual Ingested Count | Match Status |
|---|---|---|---|
| **Customer** | 13,553 | 13,553 | 100% Match |
| **Card** | 13,933 | 13,933 | 100% Match |
| **Transaction** | 590,742 | 590,742 | 100% Match |
| **DeviceProfile** | 9,706 | 9,706 | 100% Match |
| **EmailDomain** | 60 | 60 | 100% Match |
| **BillingRegion** | 332 | 332 | 100% Match |
| **ClosedCase** | 5,565 | 5,565 | 100% Match |
| **OWNS** | 13,933 | 13,933 | 100% Match |
| **MADE** | 590,742 | 590,742 | 100% Match |
| **FROM_DEVICE** | 144,432 | 144,432 | 100% Match |
| **PURCHASER_EMAIL** | 496,262 | 496,262 | 100% Match |
| **BILLED_IN** | 525,003 | 525,003 | 100% Match |
| **NEXT** | 577,189 | 577,189 | 100% Match |
| **INVOLVES** | 14,955 | 14,955 | 100% Match |
| **ON_CARD** | 5,565 | 5,565 | 100% Match |
| **CONNECTED_TO** | 92 | 92 | 100% Match |

---

## 3. Endpoint Integrity & Benchmark Traversal Verification

All 20 exam benchmark cases (`HHG-001` through `HHG-020`) in `case_pack.csv` were verified using the 10 investigation primitives:

- **Flagged Transaction Resolution:** 20 / 20 transactions resolved to valid `Transaction` vertices.
- **Card Endpoint Resolution:** 20 / 20 transactions resolved to matching `Card` vertices (e.g. `HHG-001` -> `TransactionID 3514030` -> `Card C12382-K1`).
- **Customer Endpoint Resolution:** 20 / 20 transactions resolved to matching `Customer` vertices.
- **Orphan Edge Detection:** 0 orphan edges. Every edge endpoint in `data/graph_load/edges/` connects to an existing vertex in `data/graph_load/vertices/`.

---

## 4. Test Runner Execution Results

Unit and schema tests executed via `python -m unittest discover tests`:

```text
Ran 18 tests in 62.140s — OK
```

---

## 5. Conclusion

TIGERGRAPH STATUS: READY

The TigerGraph schema, loading jobs, GSQL investigation primitives, and test suite are 100% validated and ready for Phase 4 MCP / Agentic GraphRAG integration.
