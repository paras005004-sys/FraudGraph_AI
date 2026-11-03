# FraudGraph AI — Validated Project Analysis & Dataset Validation

> **Status:** FINAL DATASET VALIDATION COMPLETE (Pre-Implementation Gate Passed)
> **Authoritative Baseline:** HHGOA_IEEE Dataset & Hackathon README (`dataset/HHGOA_IEEE/`)
> **Date:** 2026-09-21

---

## 1. Official Challenge Requirements

The goal of the **TigerGraph Agentic Fraud Investigation System (FraudGraph AI)** is to construct an autonomous, agentic fraud investigation engine that:

1. Takes an incoming alert from the 20 exam cases in `case_pack.csv` (triggers: `risk_score`, `customer_report`, or `analyst_request`).
2. Performs **graph investigation** across connected entities (`Customer`, `Card`, `Transaction`, `DeviceProfile`, `EmailDomain`, `BillingRegion`, `ClosedCase`) in TigerGraph using GSQL and TigerGraph MCP tools.
3. Retrieves relevant **fraud policies**, **regulatory references**, and **closed cases history** (`closed_cases_history.csv`) via GraphRAG and Case Memory.
4. Assesses **fraud probability**, **risk factors**, and **confidence / uncertainty**.
5. Requests **simulated additional evidence** (`customer_validation`, `step_up_auth`, `analyst_info`) when policy calls for it (e.g. Rule R1).
6. Recommends policy-compliant **Next-Best-Actions (NBA)** and enforces deterministic approval routes (`auto`, `L1`, `L2`).
7. Produces an auditable 3-part answer file (`case`, `sar`, `next_best_actions`) for all 20 cases and updates TigerGraph case memory.

---

## 2. Official Judging Criteria

| Criterion | Weight | Key Expectations |
|---|---|---|
| **Investigation Accuracy** | **25%** | Correctness of fraud identification (`verdict`, `fraud_probability`), entity graph traversal, card/device linking, and velocity/pattern detection. |
| **Next Best Action** | **25%** | Quality, safety, appropriateness, and strict policy enforcement of initial and final actions (using the 14 exact policy action names and approval routes). |
| **Agentic Design and Engineering** | **15%** | Quality of state management (LangGraph), stopping criteria (Rule 6), tool selection, error handling, and agent orchestration. |
| **Innovation** | **15%** | Novel use of GraphRAG, TigerGraph MCP tools, uncertainty quantification, case memory retrieval, and discovery of undocumented patterns (Rule R9). |
| **Case Summary and Explainability** | **10%** | Clear, step-by-step evidence traceability, natural language summary, and transparent SAR narrative (who, what, when, where, how, why). |
| **Demo Quality and Completeness** | **10%** | Functional Streamlit UI dashboard, interactive network graph, evaluation metrics, and end-to-end execution. |

---

## 3. Dataset Inventory

The dataset is located at `dataset/HHGOA_IEEE/`:

| File Name | Size | Row Count | Column Count | Primary Key | Role |
|---|---|---|---|---|---|
| `README.md` | 38.6 KB | 473 lines | N/A | N/A | Task spec, policy, 5 patterns, answer format, 20 cases |
| `transactions.csv` | 675.1 MB | 590,742 | 397 | `TransactionID` | 6-month transaction dataset (July 2 – Dec 31, 2016) |
| `identity.csv` | 25.5 MB | 144,432 | 41 | `TransactionID` | Identity & device profiles for online transactions |
| `closed_cases_history.csv` | 2.6 MB | 5,565 | 15 | `case_id` | Labeled historical cases (July–Oct 2016): 4665 fraud / 900 cleared |
| `case_pack.csv` | 3.8 KB | 20 | 8 | `case_id` | 20 exam benchmark alerts (Nov–Dec 2016) |

---

## 4. Dataset Schema Details

### 4.1 `transactions.csv` (397 Columns)
- `TransactionID` (int): Unique transaction identifier (PK).
- `customer_id` (string): e.g. `C01234`. Customer identifier derived by bank.
- `ts` (timestamp string): `YYYY-MM-DD HH:MM:SS` (July 2 – Dec 31, 2016).
- `channel` (string): `in_person` (`ProductCD` = `W`) or `online` (`ProductCD` = `C`, `H`, `R`, `S`).
- `risk_score` (float): 0.0 to 1.0 score from bank detection model (**input, not ground truth**).
- `TransactionAmt` (float): Transaction amount in USD.
- `ProductCD` (string): Product code (`W`, `C`, `H`, `R`, `S`).
- `card1` to `card6` (mixed): Card details. `card1` issuer code; `card4` network (`visa`, `mastercard`, etc.); `card6` type (`credit`, `debit`).
- `addr1`, `addr2` (float): Billing region code (`addr1`) and country code (`addr2`, 87 = home).
- `P_emaildomain`, `R_emaildomain` (string): Purchaser and recipient email domains.
- `C1`–`C14` (float), `D1`–`D15` (float), `M1`–`M9` (string), `V1`–`V339` (float): Vesta features.

### 4.2 `identity.csv` (41 Columns)
- `TransactionID` (int): FK to `transactions.csv`.
- `DeviceType` (string): `mobile` or `desktop`.
- `DeviceInfo` (string): e.g. `SAMSUNG SM-G892A Build/NRD90M`.
- `id_15` (string): Device status (`New` / `Found`).
- `id_23` (string): Proxy type (`transparent`, `anonymous`, `hidden`).
- `id_30` (string): Operating system (e.g. `Android 7.0`, `iOS 11.0`).
- `id_31` (string): Browser (e.g. `chrome 62.0`, `samsung browser 6.2`).
- `id_33` (string): Screen resolution (e.g. `2220x1080`).

---

## 5. Entity Validation

Every vertex in the TigerGraph schema is strictly validated against the actual dataset:

### 5.1 Vertex: `Customer`
1. **Source file:** `transactions.csv` & `closed_cases_history.csv`
2. **Source column:** `customer_id`
3. **Data type:** `STRING` (e.g. `C01234`)
4. **Identifier/key:** `customer_id`
5. **Relationship:** `OWNS` -> `Card`
6. **Direct/Derived:** Directly present in HHGOA dataset
7. **Required/Optional:** Required

### 5.2 Vertex: `Card`
1. **Source file:** `closed_cases_history.csv` & `case_pack.csv` & derived from `transactions.csv`
2. **Source column:** `card_id` (e.g. `C01234-K1`)
3. **Data type:** `STRING`
4. **Identifier/key:** `card_id`
5. **Relationship:** `MADE` -> `Transaction`
6. **Direct/Derived:** Explicitly provided in `case_pack.csv` and `closed_cases_history.csv`
7. **Required/Optional:** Required

### 5.3 Vertex: `Transaction`
1. **Source file:** `transactions.csv`
2. **Source column:** `TransactionID`, `ts`, `TransactionAmt`, `ProductCD`, `channel`, `risk_score`
3. **Data type:** `STRING` / `INT` / `FLOAT`
4. **Identifier/key:** `TransactionID` (e.g. `3514030`)
5. **Relationship:** Connected to `Card`, `DeviceProfile`, `EmailDomain`, `BillingRegion`
6. **Direct/Derived:** Directly present
7. **Required/Optional:** Required

### 5.4 Vertex: `DeviceProfile`
1. **Source file:** `identity.csv`
2. **Source columns:** `DeviceInfo`, `id_30` (OS), `id_31` (Browser), `id_33` (Screen)
3. **Data type:** `STRING` (composite string e.g. `SAMSUNG SM-G892A Build/NRD90M | Android 7.0 | samsung browser 6.2 | 2220x1080`)
4. **Identifier/key:** Derived device profile signature string
5. **Relationship:** `FROM_DEVICE` from `Transaction` (online only)
6. **Direct/Derived:** Derived from `identity.csv`
7. **Required/Optional:** Optional (online transactions only)

### 5.5 Vertex: `EmailDomain`
1. **Source file:** `transactions.csv`
2. **Source columns:** `P_emaildomain`, `R_emaildomain`
3. **Data type:** `STRING` (e.g. `gmail.com`)
4. **Identifier/key:** `domain_name`
5. **Relationship:** `PURCHASER_EMAIL` / `RECIPIENT_EMAIL` from `Transaction`
6. **Direct/Derived:** Directly present
7. **Required/Optional:** Optional

### 5.6 Vertex: `BillingRegion`
1. **Source file:** `transactions.csv`
2. **Source column:** `addr1`
3. **Data type:** `STRING` (e.g. `addr_315.0`)
4. **Identifier/key:** `addr1`
5. **Relationship:** `BILLED_IN` from `Transaction`
6. **Direct/Derived:** Directly present
7. **Required/Optional:** Optional

### 5.7 Vertex: `ClosedCase`
1. **Source file:** `closed_cases_history.csv` & dynamically created
2. **Source columns:** `case_id`, `outcome`, `pattern`, `exposure_usd`, `actions_taken`
3. **Data type:** `STRING` (e.g. `CC-0001` or `CASE-2016-1187`)
4. **Identifier/key:** `case_id`
5. **Relationship:** `INVOLVES` -> `Transaction`, `ON_CARD` -> `Card`, `CONNECTED_TO` -> `Card`
6. **Direct/Derived:** Directly present in history & written back by agent
7. **Required/Optional:** Required

---

## 6. Relationship Validation

1. **`Customer` —[OWNS]→ `Card`**: Linked via `customer_id` and `card_id` (`C01234` owns `C01234-K1`).
2. **`Card` —[MADE]→ `Transaction`**: Linked via `card_id` and `TransactionID`.
3. **`Transaction` —[FROM_DEVICE]→ `DeviceProfile`**: Linked via `TransactionID` in `identity.csv` to composite device string.
4. **`Transaction` —[PURCHASER_EMAIL]→ `EmailDomain`**: Linked via `P_emaildomain`.
5. **`Transaction` —[BILLED_IN]→ `BillingRegion`**: Linked via `addr1`.
6. **`Transaction` —[NEXT]→ `Transaction`**: Temporal edge ordered by `ts` on the same `Card`.
7. **`ClosedCase` —[INVOLVES]→ `Transaction`**: Linked via `txn_ids` pipe-separated list.
8. **`ClosedCase` —[ON_CARD]→ `Card`**: Linked via `card_id`.
9. **`ClosedCase` —[CONNECTED_TO]→ `Card`**: Linked via `connected_card_ids`.

---

## 7. Fraud Patterns & Policy Engine Rules

### 7.1 Five Known Fraud Patterns
1. `card_testing`: ≥3 small online authorizations (<$5) within 1 hour, followed by larger purchase. Rule R5.
2. `card_not_present_fraud`: Online purchases inconsistent with cardholder history (burst of 2-4 within 48h). Rules R1-R4.
3. `card_not_present_new_device`: Same as above with `id_15` = `New`, sometimes behind proxy (`id_23`).
4. `out_of_region_use`: Card-present (`in_person`) transactions in a new billing region (`addr1`). Rules R2, R3.
5. `account_takeover`: Mixed-channel activity inconsistent with cardholder credentials.

### 7.2 Fourteen Policy Actions & Approval Routes
- **`auto`**: `ALLOW_TRANSACTION`, `MONITOR_CARD`, `MONITOR_CONNECTED_CARDS`, `WARN_CUSTOMER`, `VERIFY_WITH_CUSTOMER`, `STEP_UP_AUTH`, `GENERATE_REPORT`, `CREATE_CASE`, `ESCALATE_TO_ANALYST`, `CLOSE_NO_FRAUD`.
- **`L1` (Team Lead)**: `DECLINE_TRANSACTION`; `BLOCK_CARD` when exposure ≤ $2,500.
- **`L2` (Fraud Manager)**: `BLOCK_CARD` when exposure > $2,500; `BLOCK_ALL_CARDS` always; `FILE_REPORT` always.

---

## 8. Required Answer Output Structure

Every output file `<case_id>.json` (for `HHG-001` to `HHG-020`) must contain:
1. `case_id`: String (e.g. `HHG-001`).
2. `case`: Object containing `status`, `verdict`, `fraud_probability`, `pattern`, `pattern_description`, `affected_txn_ids`, `first_suspicious_txn_id`, `connected_card_ids`, `connected_device_profiles`, `exposure_usd`, `evidence`, `similar_prior_cases`, `summary`, `written_to_graph`, `graph_case_id`.
3. `evidence_requests`: List of objects (`type`, `asked_after_step`, `assumed_response`).
4. `next_best_actions`: Object containing `initial` (list), `final` (list), `what_changed` (string).
5. `sar`: Object containing `file` (boolean), `reason`, `narrative`, `subjects`, `total_amount_usd`, `activity_dates`.
6. `stop_reason`, `tool_calls`, `tokens`, `latency_s`.

---

## BLOCKERS BEFORE IMPLEMENTATION

**All hard blockers have been resolved:**
- ✅ `dataset/HHGOA_IEEE/` files present and profiled (`transactions.csv`, `identity.csv`, `closed_cases_history.csv`, `case_pack.csv`, `README.md`).
- ✅ Dataset schema, row counts, entity keys, policy rules, and 20 benchmark cases verified.
- ✅ Official judging criteria aligned (25% Investigation Accuracy, 25% Next Best Action, 15% Agentic Design, 15% Innovation, 10% Explainability, 10% Demo).

---

## DATASET STATUS: READY
