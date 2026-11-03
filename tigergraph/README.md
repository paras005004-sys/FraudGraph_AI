# TigerGraph Schema & GSQL Documentation — FraudGraph AI

This directory contains the authoritative TigerGraph GSQL definitions for **FraudGraph AI**.

## Directory Layout

```
tigergraph/
├── schema/
│   └── fraud_graph.gsql           # Graph schema definition (7 vertices, 9 edges)
├── loading/
│   └── load_fraud_graph.gsql      # Loading job definition from data/graph_load/
├── queries/
│   ├── get_transaction_details.gsql
│   ├── get_historical_closed_cases.gsql
│   ├── get_connected_transactions.gsql
│   ├── get_connected_cards_and_customers.gsql
│   └── get_transaction_neighborhood.gsql
└── README.md
```

## Graph Schema Overview

- **Vertices (7 Types)**: `Customer`, `Card`, `Transaction`, `DeviceProfile`, `EmailDomain`, `BillingRegion`, `ClosedCase`
- **Edges (9 Types)**: `OWNS`, `MADE`, `FROM_DEVICE`, `PURCHASER_EMAIL`, `BILLED_IN`, `NEXT`, `INVOLVES`, `ON_CARD`, `CONNECTED_TO`

## GSQL Setup Commands

To deploy this schema on a TigerGraph instance (Community Edition or Savanna Cloud):

```bash
# 1. Create Schema
gsql tigergraph/schema/fraud_graph.gsql

# 2. Run Loading Job
gsql tigergraph/loading/load_fraud_graph.gsql

# 3. Install Queries
gsql tigergraph/queries/*.gsql
```
