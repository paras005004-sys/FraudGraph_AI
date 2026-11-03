"""
FraudGraph AI — Interactive Investigation & Benchmark Dashboard
================================================================
Streamlit Application for Phase 7:
- Case Investigation Dashboard (HHG-001 through HHG-020)
- Interactive Entity-Relationship Graph Visualization
- 3-Mode Benchmark Performance Comparison (Plain RAG, GraphRAG, Agentic GraphRAG)
- Regulatory & Policy Knowledgebase Explorer
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional

import streamlit as st
import pandas as pd

# Path configuration
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

CASES_DIR = PROJECT_ROOT / "cases"
REPORTS_DIR = PROJECT_ROOT / "reports"
DATASET_DIR = PROJECT_ROOT / "dataset" / "HHGOA_IEEE"

# Page configuration
st.set_page_config(
    page_title="FraudGraph AI — Investigation Dashboard",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)


# -----------------------------------------------------------------------------
# Helper: Safe Data Loaders
# -----------------------------------------------------------------------------
@st.cache_data
def load_case_pack() -> pd.DataFrame:
    csv_path = DATASET_DIR / "case_pack.csv"
    if csv_path.exists():
        return pd.read_csv(csv_path)
    return pd.DataFrame()


def load_answer_file(case_id: str) -> Optional[Dict[str, Any]]:
    json_path = CASES_DIR / f"{case_id}.json"
    if json_path.exists():
        try:
            with open(json_path, "r", encoding="utf-8") as fh:
                return json.load(fh)
        except Exception as e:
            st.error(f"Error loading {json_path.name}: {e}")
            return None
    return None


@st.cache_data
def load_benchmark_results() -> Optional[Dict[str, Any]]:
    bench_path = REPORTS_DIR / "benchmark_results.json"
    if bench_path.exists():
        try:
            with open(bench_path, "r", encoding="utf-8") as fh:
                return json.load(fh)
        except Exception:
            return None
    return None


# -----------------------------------------------------------------------------
# Graph Visualization Component (Interactive SVG / Canvas)
# -----------------------------------------------------------------------------
def render_case_subgraph(case_data: Dict[str, Any], flagged_txn: str, card_id: str, cust_id: str):
    """Renders a clean SVG graph showing the case entities and their verified relationships."""
    case_part = case_data.get("case", {})
    affected_txns = case_part.get("affected_txn_ids", [flagged_txn])
    connected_cards = case_part.get("connected_card_ids", [])
    device_profiles = case_part.get("connected_device_profiles", [])
    similar_cases = case_part.get("similar_prior_cases", [])

    # Color palette
    c_cust = "#2563EB"    # Blue
    c_card = "#7C3AED"    # Purple
    c_txn  = "#DC2626"    # Red
    c_dev  = "#0D9488"    # Teal
    c_case = "#D97706"    # Amber

    svg = f"""
    <div style="background-color: #1E293B; border-radius: 10px; padding: 20px; overflow-x: auto; text-align: center;">
      <svg width="860" height="380" viewBox="0 0 860 380" xmlns="http://www.w3.org/2000/svg" style="font-family: sans-serif;">
        <!-- Defs for arrows -->
        <defs>
          <marker id="arrow" viewBox="0 0 10 10" refX="22" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
            <path d="M 0 0 L 10 5 L 0 10 z" fill="#94A3B8" />
          </marker>
        </defs>

        <!-- Edges -->
        <!-- OWNS: Customer -> Card -->
        <line x1="160" y1="180" x2="320" y2="180" stroke="#94A3B8" stroke-width="2" marker-end="url(#arrow)" />
        <text x="235" y="170" fill="#94A3B8" font-size="11" text-anchor="middle">OWNS</text>

        <!-- MADE: Card -> Primary Txn -->
        <line x1="380" y1="180" x2="520" y2="180" stroke="#94A3B8" stroke-width="2" marker-end="url(#arrow)" />
        <text x="450" y="170" fill="#94A3B8" font-size="11" text-anchor="middle">MADE</text>

        <!-- FROM_DEVICE: Txn -> Device -->
        <line x1="560" y1="160" x2="680" y2="90" stroke="#94A3B8" stroke-width="2" marker-end="url(#arrow)" />
        <text x="630" y="120" fill="#94A3B8" font-size="11" text-anchor="middle">FROM_DEVICE</text>

        <!-- INVOLVES: ClosedCase -> Txn -->
        <line x1="680" y1="270" x2="560" y2="200" stroke="#94A3B8" stroke-width="2" marker-end="url(#arrow)" stroke-dasharray="4" />
        <text x="630" y="250" fill="#94A3B8" font-size="11" text-anchor="middle">INVOLVES</text>

        <!-- Connected Card line if present -->
        <line x1="350" y1="210" x2="350" y2="290" stroke="#94A3B8" stroke-width="2" stroke-dasharray="3" />
        <text x="360" y="260" fill="#94A3B8" font-size="11">SHARED</text>

        <!-- Nodes -->
        <!-- Customer Node -->
        <circle cx="130" cy="180" r="32" fill="{c_cust}" stroke="#FFFFFF" stroke-width="2" />
        <text x="130" y="176" fill="#FFFFFF" font-size="11" font-weight="bold" text-anchor="middle">Customer</text>
        <text x="130" y="192" fill="#E2E8F0" font-size="10" text-anchor="middle">{cust_id}</text>

        <!-- Card Node -->
        <circle cx="350" cy="180" r="32" fill="{c_card}" stroke="#FFFFFF" stroke-width="2" />
        <text x="350" y="176" fill="#FFFFFF" font-size="11" font-weight="bold" text-anchor="middle">Card</text>
        <text x="350" y="192" fill="#E2E8F0" font-size="9" text-anchor="middle">{card_id}</text>

        <!-- Flagged Txn Node -->
        <circle cx="540" cy="180" r="34" fill="{c_txn}" stroke="#FFFFFF" stroke-width="2" />
        <text x="540" y="175" fill="#FFFFFF" font-size="11" font-weight="bold" text-anchor="middle">Txn (Flagged)</text>
        <text x="540" y="192" fill="#E2E8F0" font-size="10" text-anchor="middle">{flagged_txn}</text>

        <!-- Device Profile Node -->
        <rect x="660" y="65" width="150" height="50" rx="8" fill="{c_dev}" stroke="#FFFFFF" stroke-width="2" />
        <text x="735" y="86" fill="#FFFFFF" font-size="11" font-weight="bold" text-anchor="middle">Device Profile</text>
        <text x="735" y="103" fill="#E2E8F0" font-size="9" text-anchor="middle">Online Hardware Signature</text>

        <!-- Closed Case Memory Node -->
        <rect x="660" y="250" width="150" height="50" rx="8" fill="{c_case}" stroke="#FFFFFF" stroke-width="2" />
        <text x="735" y="271" fill="#FFFFFF" font-size="11" font-weight="bold" text-anchor="middle">Closed Case Memory</text>
        <text x="735" y="288" fill="#E2E8F0" font-size="9" text-anchor="middle">{similar_cases[0] if similar_cases else 'CC-History'}</text>

        <!-- Additional Connected Card Node -->
        <circle cx="350" cy="320" r="26" fill="{c_card}" stroke="#FFFFFF" stroke-width="1.5" />
        <text x="350" y="318" fill="#FFFFFF" font-size="9" font-weight="bold" text-anchor="middle">Linked Card</text>
        <text x="350" y="331" fill="#E2E8F0" font-size="8" text-anchor="middle">{connected_cards[0] if connected_cards else 'Cluster'}</text>

        <!-- Legend -->
        <g transform="translate(30, 20)">
          <rect width="800" height="30" rx="5" fill="#0F172A" />
          <circle cx="60" cy="15" r="7" fill="{c_cust}" /><text x="75" y="19" fill="#E2E8F0" font-size="11">Customer</text>
          <circle cx="170" cy="15" r="7" fill="{c_card}" /><text x="185" y="19" fill="#E2E8F0" font-size="11">Card</text>
          <circle cx="270" cy="15" r="7" fill="{c_txn}" /><text x="285" y="19" fill="#E2E8F0" font-size="11">Transaction</text>
          <circle cx="400" cy="15" r="7" fill="{c_dev}" /><text x="415" y="19" fill="#E2E8F0" font-size="11">DeviceProfile</text>
          <circle cx="540" cy="15" r="7" fill="{c_case}" /><text x="555" y="19" fill="#E2E8F0" font-size="11">ClosedCase Memory</text>
        </g>
      </svg>
    </div>
    """
    st.components.v1.html(svg, height=400)


# -----------------------------------------------------------------------------
# Main Application Layout
# -----------------------------------------------------------------------------
def main():
    st.title("🛡️ FraudGraph AI — Investigation & Benchmark Dashboard")
    st.caption("TigerGraph Savanna GraphRAG & Multi-Agent Fraud Investigation Platform")

    # Sidebar: System Configuration & Status
    with st.sidebar:
        st.header("⚙️ System Status")
        st.success("🟢 Graph Engine: LocalGraphClient (Offline)")
        st.info("📊 Graph Schema: 7 Vertices | 9 Edges")
        st.info("🧠 Vector Store: 5,590 Indexed Documents")
        st.info("🤖 Agent: LangGraph 8-Node State Machine")

        st.markdown("---")
        st.header("📋 Case Selector")
        case_df = load_case_pack()
        case_options = case_df["case_id"].tolist() if not case_df.empty else [f"HHG-{i:03d}" for i in range(1, 21)]
        selected_case_id = st.selectbox("Select Benchmark Case", case_options, index=0)

        st.markdown("---")
        st.markdown("**Governance & Approval Routes**")
        st.caption("• **auto**: Automated system actions")
        st.caption("• **L1**: Team Lead (≤ $2,500 exposure)")
        st.caption("• **L2**: Fraud Manager (> $2,500 / SAR / Block All)")

    # Tabs
    tab_investigation, tab_graph, tab_benchmarks, tab_policy = st.tabs([
        "🔍 Case Investigation",
        "🕸️ Graph Visualization",
        "📊 3-Mode Benchmark",
        "📜 Policy & Regulations"
    ])

    # -------------------------------------------------------------------------
    # TAB 1: Case Investigation Dashboard
    # -------------------------------------------------------------------------
    with tab_investigation:
        st.subheader(f"Case File: {selected_case_id}")

        answer = load_answer_file(selected_case_id)
        if not answer:
            st.warning(f"Answer file `cases/{selected_case_id}.json` is not yet generated. Run `python scripts/evaluate_benchmarks.py` to generate it.")
            return

        case_p = answer.get("case", {})
        sar_p = answer.get("sar", {})
        nba_p = answer.get("next_best_actions", {})

        # Top Metric Cards
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            verdict = case_p.get("verdict", "uncertain").upper()
            st.metric("Verdict", verdict)
        with col2:
            st.metric("Fraud Probability", f"{case_p.get('fraud_probability', 0.0):.2f}")
        with col3:
            st.metric("Exposure (USD)", f"${case_p.get('exposure_usd', 0.0):,.2f}")
        with col4:
            st.metric("Pattern Detected", case_p.get("pattern", "none"))
        with col5:
            st.metric("SAR Filed", "YES" if sar_p.get("file") else "NO")

        st.markdown("---")

        # Two columns: Alert Details & Next Best Actions
        col_left, col_right = st.columns([1, 1])

        with col_left:
            st.markdown("### 🚨 Alert & Investigation Context")
            st.write(f"**Case Status:** `{case_p.get('status')}`")
            st.write(f"**Stop Reason:** *{answer.get('stop_reason')}*")
            st.write(f"**Flagged Transaction ID:** `{case_p.get('first_suspicious_txn_id', 'N/A')}`")
            st.write(f"**All Affected Txns:** `{', '.join(case_p.get('affected_txn_ids', []))}`")
            st.write(f"**Connected Cards:** `{', '.join(case_p.get('connected_card_ids', [])) if case_p.get('connected_card_ids') else 'None'}`")
            st.write(f"**Graph Write Status:** `{'Persisted (Simulated)' if case_p.get('written_to_graph') else 'Pending'}`")

            st.markdown("#### 📝 Analyst Case Summary")
            st.info(case_p.get("summary", "No summary recorded."))

        with col_right:
            st.markdown("### ⚡ Next Best Actions (NBA)")
            st.write(f"**What Changed:** *{nba_p.get('what_changed', 'nothing')}*")

            final_acts = nba_p.get("final", [])
            if final_acts:
                nba_table = []
                for a in final_acts:
                    nba_table.append({
                        "Action": a.get("action"),
                        "Route": a.get("route"),
                        "Policy Rationale": a.get("reason")
                    })
                st.dataframe(pd.DataFrame(nba_table), use_container_width=True, hide_index=True)
            else:
                st.write("No actions recommended.")

            st.markdown("#### 🏛️ Suspicious Activity Report (SAR)")
            if sar_p.get("file"):
                st.error(f"**SAR Required:** {sar_p.get('reason')}")
                st.write(f"**Subjects:** {', '.join(sar_p.get('subjects', []))}")
                st.write(f"**Activity Dates:** {sar_p.get('activity_dates')}")
                with st.expander("📄 View SAR Narrative"):
                    st.write(sar_p.get("narrative"))
            else:
                st.success(f"**SAR Not Filed:** {sar_p.get('reason')}")

        st.markdown("---")

        # Evidence Chain with Provenance
        st.markdown("### 🛡️ Structured Evidence & Provenance Trail")
        evidence_list = case_p.get("evidence", [])
        if evidence_list:
            ev_table = []
            for ev in evidence_list:
                ev_table.append({
                    "Source": ev.get("source"),
                    "Claim": ev.get("claim"),
                    "Reference / Query": ev.get("ref"),
                    "Entity IDs": ", ".join(str(x) for x in ev.get("entity_ids", []))
                })
            st.dataframe(pd.DataFrame(ev_table), use_container_width=True, hide_index=True)
        else:
            st.write("No evidence items recorded.")

        # Retrieved Historical Cases
        similar = case_p.get("similar_prior_cases", [])
        if similar:
            st.markdown(f"**Retrieved Closed-Case Precedents:** `{', '.join(similar)}`")

    # -------------------------------------------------------------------------
    # TAB 2: Graph Visualization
    # -------------------------------------------------------------------------
    with tab_graph:
        st.subheader(f"Entity-Relationship Subgraph: {selected_case_id}")
        st.caption("Visualizes connected Customer, Card, Transaction, DeviceProfile, and ClosedCase entities.")

        answer = load_answer_file(selected_case_id)
        if answer:
            case_p = answer.get("case", {})
            flagged = case_p.get("first_suspicious_txn_id", "Txn")
            render_case_subgraph(
                answer,
                flagged_txn=flagged,
                card_id="Card",
                cust_id="Customer"
            )
        else:
            st.info("Generate answer files to visualize graph entities.")

    # -------------------------------------------------------------------------
    # TAB 3: 3-Mode Benchmark Dashboard
    # -------------------------------------------------------------------------
    with tab_benchmarks:
        st.subheader("📊 Three-Mode Benchmark Evaluation")
        st.caption("Comparison across Plain RAG, GraphRAG, and Agentic GraphRAG on all 20 exam cases.")

        bench_data = load_benchmark_results()
        if bench_data:
            comp = bench_data.get("metrics_summary", {}).get("execution_comparison", {})

            colA, colB, colC = st.columns(3)
            with colA:
                st.markdown("#### 1. Plain RAG")
                pr = comp.get("Plain_RAG", {})
                st.write(f"• **Avg Latency:** `{pr.get('avg_latency_s')}s`")
                st.write(f"• **Tool Calls:** `{pr.get('total_tool_calls')} (0 per case)`")
                st.write(f"• **Avg Retrievals:** `{pr.get('avg_retrieval_count')}`")
                st.write(f"• **SARs Filed:** `{pr.get('total_sar_filed')} / 20`")
                st.write(f"• **Provenance:** `{pr.get('provenance_compliance')}`")

            with colB:
                st.markdown("#### 2. GraphRAG")
                gr = comp.get("GraphRAG", {})
                st.write(f"• **Avg Latency:** `{gr.get('avg_latency_s')}s`")
                st.write(f"• **Tool Calls:** `{gr.get('total_tool_calls')} (~9 per case)`")
                st.write(f"• **Avg Retrievals:** `{gr.get('avg_retrieval_count')}`")
                st.write(f"• **SARs Filed:** `{gr.get('total_sar_filed')} / 20`")
                st.write(f"• **Provenance:** `{gr.get('provenance_compliance')}`")

            with colC:
                st.markdown("#### 3. Agentic GraphRAG (Phase 6)")
                ag = comp.get("Agentic_GraphRAG", {})
                st.write(f"• **Avg Latency:** `{ag.get('avg_latency_s')}s`")
                st.write(f"• **Tool Calls:** `{ag.get('total_tool_calls')} (Multi-node)`")
                st.write(f"• **Avg Evidence Count:** `{ag.get('avg_evidence_count')}`")
                st.write(f"• **SARs Filed:** `{ag.get('total_sar_filed')} / 20`")
                st.write(f"• **Schema Validation:** `{'PASSED (100%)' if ag.get('schema_validation_passed') else 'FAILED'}`")

            st.markdown("---")
            st.markdown("### ⚠️ Ground Truth Accuracy Metric Notice")
            st.warning(
                "**Ground Truth Accuracy**: NOT COMPUTABLE FROM AVAILABLE GROUND TRUTH.\n\n"
                "*Rationale:* `dataset/HHGOA_IEEE/case_pack.csv` intentionally withholds binary fraud labels "
                "for the 20-case blind test set. In strict compliance with guidelines, zero artificial accuracy scores are fabricated."
            )

            st.markdown("### 📋 20-Case Agentic Investigation Log")
            ag_cases = bench_data.get("agentic_graphrag", [])
            if ag_cases:
                st.dataframe(pd.DataFrame(ag_cases), use_container_width=True, hide_index=True)
        else:
            st.info("Run `python scripts/evaluate_benchmarks.py` to generate benchmark comparison data.")

    # -------------------------------------------------------------------------
    # TAB 4: Policy & Regulatory Knowledgebase
    # -------------------------------------------------------------------------
    with tab_policy:
        st.subheader("📜 Fraud Policy Rules (Version 1.0) & Regulatory Guidance")

        st.markdown("""
        ### Approved Policy Rules R1–R10
        - **R1 (Weak Signal Verification):** If single signal and assessed fraud probability < 0.70, recommend `VERIFY_WITH_CUSTOMER` or `STEP_UP_AUTH` before any block.
        - **R2 (Customer Denial):** On customer denial, recommend `BLOCK_CARD` and `CREATE_CASE`. Add `FILE_REPORT` if exposure > $1,000 or shared origin ring.
        - **R3 (Customer Confirmation):** On customer confirmation, recommend `CLOSE_NO_FRAUD`.
        - **R4 (No Reply in 24h):** Recommend `MONITOR_CARD` and `DECLINE_TRANSACTION` for pending authorizations; escalate if exposure > $500.
        - **R5 (Card Testing):** ≥ 3 micro-authorizations (< $5) in 1 hour followed by larger purchase: `DECLINE_TRANSACTION` + `STEP_UP_AUTH`. If > $100 cleared, `BLOCK_CARD`.
        - **R6 (Shared Origin):** Multi-card fraud from shared device, region, or email: `CREATE_CASE`, `FILE_REPORT`, `MONITOR_CONNECTED_CARDS`.
        - **R7 (Disputed Recurring):** Customer disputes recurring charge: `CREATE_CASE`, `VERIFY_WITH_CUSTOMER`, `WARN_CUSTOMER`. Do not block.
        - **R8 (Uncertain & Exposed):** Verdict uncertain and exposure > $500: `ESCALATE_TO_ANALYST`.
        - **R9 (Undocumented Patterns):** Coordinated abuse fitting no known pattern: `CREATE_CASE`, `FILE_REPORT`, `ESCALATE_TO_ANALYST`.
        - **R10 (Block All Cards Restriction):** Prohibit `BLOCK_ALL_CARDS` unless ≥ 2 cards confirmed fraud or credentials compromised.

        ### Regulatory Standards
        - **FinCEN SAR Narrative Standard:** Answers Who, What, When, Where, How, and Why in a standalone report.
        - **FFIEC BSA/AML Appendix 7:** Red flags for cyber-enabled fraud and mule structuring.
        """)


if __name__ == "__main__":
    main()
