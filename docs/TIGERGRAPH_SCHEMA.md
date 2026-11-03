# FraudGraph AI — TigerGraph Schema Documentation

> **Graph Name:** `FraudGraph`
> **Authoritative Specification:** GSQL definition in `tigergraph/schema/fraud_graph.gsql`
> **Status:** FULLY VERIFIED & BENCHMARK VALIDATED

---

## 1. Graph Overview

FraudGraph AI models financial transaction networks, device sharing, billing region clusters, and historical case memory.

- **7 Vertices:** `Customer`, `Card`, `Transaction`, `DeviceProfile`, `EmailDomain`, `BillingRegion`, `ClosedCase`
- **9 Edges:** `OWNS`, `MADE`, `FROM_DEVICE`, `PURCHASER_EMAIL`, `BILLED_IN`, `NEXT`, `INVOLVES`, `ON_CARD`, `CONNECTED_TO`

---

## 2. Vertex Definitions (7 Types)

### 2.1 `Customer`
- **Primary ID:** `customer_id` (STRING)
- **Count:** 13,553
- **Description:** Bank customer account holder entity.

### 2.2 `Card`
- **Primary ID:** `card_id` (STRING)
- **Attributes:** `customer_id` (STRING), `card1` (STRING), `card_network` (STRING), `card_type` (STRING)
- **Count:** 13,933
- **Description:** Payment card linked to a customer.

### 2.3 `Transaction`
- **Primary ID:** `TransactionID` (STRING)
- **Attributes:** `customer_id` (STRING), `ts` (STRING), `channel` (STRING), `risk_score` (DOUBLE), `amount` (DOUBLE), `product_cd` (STRING), `C1` (DOUBLE), `C2` (DOUBLE), `D1` (DOUBLE), `D2` (DOUBLE)
- **Count:** 590,742
- **Description:** Financial transaction record (July 2 – Dec 31, 2016).

### 2.4 `DeviceProfile`
- **Primary ID:** `device_profile_id` (STRING, composite signature)
- **Attributes:** `device_type` (STRING), `device_info` (STRING), `os` (STRING), `browser` (STRING), `screen` (STRING), `proxy_status` (STRING), `device_status` (STRING)
- **Count:** 9,706
- **Description:** Digital device footprint from `identity.csv`.

### 2.5 `EmailDomain`
- **Primary ID:** `domain_name` (STRING)
- **Count:** 60
- **Description:** Purchaser email domain string (e.g. `gmail.com`).

### 2.6 `BillingRegion`
- **Primary ID:** `addr1` (STRING)
- **Attributes:** `country_code` (DOUBLE)
- **Count:** 332
- **Description:** Billing region code.

### 2.7 `ClosedCase`
- **Primary ID:** `case_id` (STRING)
- **Attributes:** `customer_id` (STRING), `card_id` (STRING), `opened_at` (STRING), `closed_at` (STRING), `outcome` (STRING), `pattern` (STRING), `first_fraud_txn_id` (STRING), `n_txns` (INT), `exposure_usd` (DOUBLE), `actions_taken` (STRING), `report_filed` (STRING), `analyst_notes` (STRING)
- **Count:** 5,565
- **Description:** Finished bank investigation case record (July–Oct 2016).

---

## 3. Edge Definitions (9 Types)

| Edge Type | Source Vertex → Target Vertex | Directed | Count | Description |
|---|---|---|---|---|
| **OWNS** | Customer → Card | DIRECTED | 13,933 | Customer ownership of cards |
| **MADE** | Card → Transaction | DIRECTED | 590,742 | Card executing a transaction |
| **FROM_DEVICE** | Transaction → DeviceProfile | DIRECTED | 144,432 | Online transaction joining device profile |
| **PURCHASER_EMAIL** | Transaction → EmailDomain | DIRECTED | 496,262 | Purchaser email domain linkage |
| **BILLED_IN** | Transaction → BillingRegion | DIRECTED | 525,003 | Billing region code |
| **NEXT** | Transaction → Transaction | DIRECTED | 577,189 | Chronological sequence per card |
| **INVOLVES** | ClosedCase → Transaction | DIRECTED | 14,955 | Historical case transactions |
| **ON_CARD** | ClosedCase → Card | DIRECTED | 5,565 | Primary target card in historical case |
| **CONNECTED_TO** | ClosedCase → Card | DIRECTED | 92 | Secondary connected cards in fraud ring |

---

## 4. GSQL Investigation Primitives

Defined in `tigergraph/queries/`:
1. `get_transaction_details.gsql`: Retrieves full transaction attributes, card, customer, device, email, billing region.
2. `get_historical_closed_cases.gsql`: Retrieves closed cases and connected cards for a target card.
3. `get_connected_transactions.gsql`: Traverses chronological `NEXT` transaction sequence.
4. `get_connected_cards_and_customers.gsql`: Traverses shared device profiles across cards/customers.
5. `get_transaction_neighborhood.gsql`: 2-hop subgraph expansion around a transaction.
