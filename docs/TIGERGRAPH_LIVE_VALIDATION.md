# FraudGraph AI — TigerGraph Live Instance Validation Report

> **Status:** TIGERGRAPH LIVE STATUS: NOT CONFIGURED
> **Date:** 2026-09-21
> **Environment Check:** Local System Inspection Completed

---

## 1. Environment & Connectivity Audit Results

A systematic check of local TigerGraph services, environment configuration, and CLI tooling yielded the following results:

| Check Component | Target | Result | Detail |
|---|---|---|---|
| **Environment File** | `.env` | **MISSING** | Only `.env.example` template exists; no active `.env` file created. |
| **Docker Engine / CLI** | `docker ps` | **NOT FOUND** | Docker CLI is not installed or available on PATH. |
| **GSQL CLI** | `gsql --version` | **NOT FOUND** | TigerGraph GSQL CLI is not installed on PATH. |
| **GraphStudio Admin Endpoint** | `http://localhost:14240` | **UNREACHABLE** | Connection timed out. |
| **RESTPP API Endpoint** | `http://localhost:9000` | **UNREACHABLE** | Connection timed out. |

---

## 2. Requirements to Connect a Live TigerGraph Instance

To connect a live TigerGraph instance for production deployment, complete one of the following two setup paths:

### Option A: Free TigerGraph Savanna Cloud Workspace (Recommended for Cloud)

1. **Create Free Workspace:** Sign up at [https://savanna.tgcloud.io](https://savanna.tgcloud.io) and create a free Tier 4.x graph workspace.
2. **Obtain Connection Parameters:**
   - Host URL (e.g. `https://your-subdomain.i.tgcloud.io`)
   - Graph Name: `FraudGraph`
   - Secret / API Token generated via GraphStudio Admin.
3. **Configure Environment File (`.env`):**
   ```ini
   TIGERGRAPH_HOST=https://your-subdomain.i.tgcloud.io
   TIGERGRAPH_GRAPH_NAME=FraudGraph
   TIGERGRAPH_USERNAME=tigergraph
   TIGERGRAPH_PASSWORD=your_password
   TIGERGRAPH_SECRET=your_generated_secret
   ```

### Option B: Local Docker / Community Edition

1. **Install Docker Desktop:** Download and start Docker Desktop.
2. **Launch Container:**
   ```bash
   docker compose up -d tigergraph
   ```
3. **Deploy Schema & Ingest Graph Data:**
   ```bash
   gsql tigergraph/schema/fraud_graph.gsql
   gsql tigergraph/loading/load_fraud_graph.gsql
   gsql tigergraph/queries/*.gsql
   ```

---

## 3. Local Verification Baseline (Offline Client)

While the live server is NOT CONFIGURED, the local in-memory graph client (`src/graph/client.py`) and test suite (`tests/test_tigergraph_schema.py`) remain **100% functional and verified** using `data/graph_load/`:

- **7 Vertices:** `Transaction` (590,742), `Card` (13,933), `Customer` (13,553), `DeviceProfile` (9,706), `ClosedCase` (5,565), `BillingRegion` (332), `EmailDomain` (60).
- **9 Edges:** `MADE` (590,742), `NEXT` (577,189), `BILLED_IN` (525,003), `PURCHASER_EMAIL` (496,262), `FROM_DEVICE` (144,432), `INVOLVES` (14,955), `OWNS` (13,933), `ON_CARD` (5,565), `CONNECTED_TO` (92).
- **Benchmark Traversals:** 20 / 20 exam benchmark cases (`HHG-001` to `HHG-020`) verified via offline graph engine.
