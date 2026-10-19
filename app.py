import streamlit as st
import json
import os
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
from src.config import config
from src.agents.orchestrator import OrchestratorAgent
from src.hitl.checkpoint import HumanDecision
from src.utils.logger import execution_trace

st.set_page_config(
    page_title="Wealth Advisor Assistant",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for executive look & feel
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1E3A8A;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1rem;
        color: #4B5563;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background-color: #F8FAFC;
        border-radius: 10px;
        padding: 16px;
        border-left: 5px solid #2563EB;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    .anomaly-critical {
        background-color: #FEE2E2;
        border-left: 5px solid #DC2626;
        padding: 12px;
        border-radius: 8px;
        margin-bottom: 10px;
    }
    .anomaly-high {
        background-color: #FEF3C7;
        border-left: 5px solid #D97706;
        padding: 12px;
        border-radius: 8px;
        margin-bottom: 10px;
    }
    .anomaly-medium {
        background-color: #EFF6FF;
        border-left: 5px solid #2563EB;
        padding: 12px;
        border-radius: 8px;
        margin-bottom: 10px;
    }
</style>
""", unsafe_allow_html=True)

# Initialize Session State
if "orchestrator" not in st.session_state:
    st.session_state.orchestrator = OrchestratorAgent()
if "stage_one_complete" not in st.session_state:
    st.session_state.stage_one_complete = False
if "stage_one_data" not in st.session_state:
    st.session_state.stage_one_data = None
if "final_report" not in st.session_state:
    st.session_state.final_report = None
if "hitl_submitted" not in st.session_state:
    st.session_state.hitl_submitted = False

# Sidebar Controls
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/bank-building.png", width=64)
    st.title("Advisor Controls")

    # API Key Configuration
    st.subheader("🔑 Gemini LLM Settings")
    api_key_input = st.text_input(
        "Gemini API Key",
        value=config.GEMINI_API_KEY if config.GEMINI_API_KEY != "your_gemini_api_key_here" else "",
        type="password",
        help="Enter your Google Gemini API key. If left blank, system runs with deterministic fallback."
    )
    if api_key_input:
        config.GEMINI_API_KEY = api_key_input
        os.environ["GEMINI_API_KEY"] = api_key_input

    model_choice = st.selectbox(
        "Model Selection",
        ["gemini-2.5-flash", "gemini-1.5-pro", "gemini-1.5-flash"],
        index=0
    )
    config.GEMINI_MODEL = model_choice

    st.markdown("---")
    st.subheader("👤 Client Selection")
    data_source = st.radio("Data Source", ["Preset Scenarios", "Upload Custom JSON"], index=0)

    sample_clients_data = {}
    if config.SAMPLE_CLIENTS_PATH.exists():
        with open(config.SAMPLE_CLIENTS_PATH, "r") as f:
            sample_clients_data = json.load(f)

    selected_client_id = "client_001"
    client_financial_payload = None

    if data_source == "Preset Scenarios":
        preset_options = {
            "client_001": "Arthur Pendleton (Retiree, $50k Crypto Outflow Anomaly)",
            "client_002": "Elena Rostova (Tech VP, 65% NVDA Concentration)",
            "client_003": "Dr. Marcus Chen (Cardiologist, Options Trading Spike)"
        }
        selected_client_id = st.selectbox(
            "Select Client Profile",
            options=list(preset_options.keys()),
            format_func=lambda x: preset_options.get(x, x)
        )
        client_financial_payload = sample_clients_data.get(selected_client_id)
    else:
        uploaded_file = st.file_uploader("Upload Client Financial JSON", type=["json"])
        if uploaded_file is not None:
            try:
                client_financial_payload = json.load(uploaded_file)
                selected_client_id = client_financial_payload.get("client_id", "custom_client")
            except Exception as e:
                st.error(f"Error reading JSON: {e}")

    st.markdown("---")
    if st.button("🔄 Reset Analysis", use_container_width=True):
        st.session_state.stage_one_complete = False
        st.session_state.stage_one_data = None
        st.session_state.final_report = None
        st.session_state.hitl_submitted = False
        st.rerun()

# Main Interface
st.markdown('<div class="main-header">🏛️ Wealth Advisor Assistant</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Multi-Agent Autonomous Advisory System powered by Google Gemini</div>', unsafe_allow_html=True)

# Live Gemini LLM Status Banner
api_key_configured = bool(config.GEMINI_API_KEY and config.GEMINI_API_KEY != "your_gemini_api_key_here")
if api_key_configured:
    st.markdown(
        f'<div style="background-color:#ECFDF5; border:1px solid #10B981; border-radius:8px; padding:10px 16px; margin-bottom:18px; display:flex; align-items:center;">'
        f'<span style="font-size:1.2rem; margin-right:8px;">🟢</span> '
        f'<strong style="color:#065F46;">Gemini LLM Engine Active:</strong>&nbsp;<span style="color:#047857;">Connected to <code>{config.GEMINI_MODEL}</code></span>'
        f'</div>',
        unsafe_allow_html=True
    )
else:
    st.markdown(
        '<div style="background-color:#FFFBEB; border:1px solid #F59E0B; border-radius:8px; padding:10px 16px; margin-bottom:18px;">'
        '<span style="font-size:1.2rem; margin-right:8px;">🟡</span> '
        '<strong style="color:#92400E;">Gemini LLM in Offline Demo Mode:</strong> '
        '<span style="color:#B45309;">Enter your <strong>Gemini API Key</strong> in the left sidebar to enable live Gemini reasoning. (Running with deterministic fallback).</span>'
        '</div>',
        unsafe_allow_html=True
    )

# Visual Multi-Agent Architecture Pipeline Stepper
st.markdown("""
<div style="background-color:#F1F5F9; border-radius:8px; padding:12px; margin-bottom:20px; font-size:0.9rem;">
    <strong>🤖 Multi-Agent Workflow:</strong> 
    <code>1. DataFetcherAgent (Ingestion & CRM)</code> ➔ 
    <code>2. AnalyzerAgent (Math & Anomalies)</code> ➔ 
    <code>3. Human-in-the-Loop (Advisor Review)</code> ➔ 
    <code>4. AdvisorAgent (Gemini Strategic Synthesis)</code>
</div>
""", unsafe_allow_html=True)

if not client_financial_payload:
    st.info("👈 Please select a client profile or upload a financial JSON dataset from the sidebar to begin.")
    st.stop()

# Action Trigger
col1, col2 = st.columns([3, 1])
with col1:
    st.write(f"**Loaded Profile:** `{client_financial_payload.get('name')}` | **ID:** `{selected_client_id}` | **Net Liquid Cash:** `${client_financial_payload.get('cash_balance', 0):,.2f}`")
with col2:
    start_btn = st.button("🚀 Run Stage 1 (Agents & Tools)", type="primary", use_container_width=True)

if start_btn:
    with st.spinner("Executing Stage 1: Data Ingestion & Quantitative Anomaly Detection..."):
        try:
            res = st.session_state.orchestrator.run_stage_one_analysis(
                financial_input=client_financial_payload,
                client_id=selected_client_id
            )
            st.session_state.stage_one_data = res
            st.session_state.stage_one_complete = True
            st.session_state.final_report = None
            st.session_state.hitl_submitted = False
            st.success("Stage 1 Analysis Complete!")
        except Exception as e:
            st.error(f"Execution Error: {e}")

# Render Stage 1 Analysis Results
if st.session_state.stage_one_complete and st.session_state.stage_one_data:
    stage_data = st.session_state.stage_one_data
    metrics = stage_data["metrics"]
    crm = stage_data["crm_profile"]
    anomalies = stage_data["anomalies"]

    # 1. Top Metrics Banner
    st.markdown("### 📊 Portfolio Snapshot")
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("Total AUM", f"${metrics['total_aum']:,.2f}")
    with m2:
        st.metric("Net Worth", f"${metrics['net_worth']:,.2f}")
    with m3:
        st.metric("Cash Drag %", f"{metrics['cash_drag_percent']:.1f}%", delta=f"{metrics['cash_drag_percent']-10:.1f}% vs Target", delta_color="inverse")
    with m4:
        st.metric("Risk Profile (CRM)", crm.get("risk_profile", "Moderate"))

    # 2. Charts: Current vs Target Allocations
    c_chart1, c_chart2 = st.columns(2)
    with c_chart1:
        alloc_data = metrics["allocations"]
        fig_alloc = px.pie(
            values=[a["amount"] for a in alloc_data],
            names=[a["asset_class"] for a in alloc_data],
            title="Current Asset Class Breakdown",
            hole=0.4,
            color_discrete_sequence=px.colors.qualitative.Safe
        )
        st.plotly_chart(fig_alloc, use_container_width=True)

    with c_chart2:
        # Comparison bar chart
        current_pcts = {a["asset_class"]: a["percentage"] for a in alloc_data}
        target_pcts = crm.get("target_allocation", {})
        all_classes = sorted(list(set(list(current_pcts.keys()) + list(target_pcts.keys()))))

        fig_comp = go.Figure(data=[
            go.Bar(name='Current %', x=all_classes, y=[current_pcts.get(c, 0.0) for c in all_classes], marker_color='#3B82F6'),
            go.Bar(name='CRM Target %', x=all_classes, y=[target_pcts.get(c, 0.0) for c in all_classes], marker_color='#10B981')
        ])
        fig_comp.update_layout(title="Allocation vs CRM Benchmark Target (%)", barmode='group')
        st.plotly_chart(fig_comp, use_container_width=True)

    # 3. Anomaly Detection Feed
    st.markdown("### ⚠️ Anomaly & Audit Risk Signals")
    if not anomalies:
        st.success("No anomalies detected. Portfolio is within normal parameters.")
    else:
        for anom in anomalies:
            sev = anom.get("severity")
            css_class = "anomaly-critical" if sev == "CRITICAL" else ("anomaly-high" if sev == "HIGH" else "anomaly-medium")
            st.markdown(f"""
            <div class="{css_class}">
                <strong>[{sev}] {anom.get('id')} — {anom.get('anomaly_type')}</strong><br/>
                {anom.get('description')}<br/>
                <em>Recommended Action:</em> {anom.get('suggested_action')}
            </div>
            """, unsafe_allow_html=True)

    # 4. Human-In-The-Loop (HITL) Checkpoint Card (Bonus Requirement)
    st.markdown("---")
    st.markdown("### 🛑 Step 3: Human-in-the-Loop Advisor Review")
    st.info("As the supervising Wealth Advisor, you can override false positives and write steering directives. In Step 4, **Google Gemini LLM** synthesizes your feedback with the financial data.")

    with st.form("hitl_form"):
        anomaly_options = [f"{a['id']} ({a['severity']}): {a['anomaly_type']}" for a in anomalies]
        selected_overrides = st.multiselect(
            "Select Anomalies to Override / Mark as Authorized (False Positives):",
            options=anomaly_options,
            help="Select any anomaly that client has already explained or pre-approved."
        )

        advisor_notes = st.text_area(
            "Advisor Guidance / Steering Directives for Gemini LLM:",
            placeholder="e.g., Client confirmed $50k wire is for daughter's medical emergency. Maintain defensive cash reserve of $50k and invest the rest into aggregate bonds.",
            height=90
        )

        approve_and_generate = st.form_submit_button("🤖 Run Step 4: Synthesize Advisory Report with Gemini LLM", type="primary", use_container_width=True)

        if approve_and_generate:
            override_ids = [opt.split(" ")[0] for opt in selected_overrides]
            decision = HumanDecision(
                action="OVERRIDE" if override_ids else "APPROVE",
                approved=True,
                overridden_anomaly_ids=override_ids,
                advisor_notes=advisor_notes or None
            )

            with st.spinner("Invoking Gemini LLM (gemini-2.5-flash) to synthesize fiduciary strategy..."):
                try:
                    report = st.session_state.orchestrator.run_stage_two_advisory(human_decision=decision)
                    st.session_state.final_report = report
                    st.session_state.hitl_submitted = True
                    st.success("Gemini LLM Advisory Report Generated Successfully!")
                except Exception as e:
                    st.error(f"Error during advisory synthesis: {e}")

# 5. Render Final Structured Advisory Report
if st.session_state.final_report:
    report = st.session_state.final_report
    st.markdown("---")
    st.markdown(f"## 📋 Final Wealth Advisory Report: {report.client_name}")

    # Executive Summary Card
    st.markdown(f"""
    <div style="background-color: #F0FDF4; border-left: 5px solid #16A34A; padding: 18px; border-radius: 8px; margin-bottom: 20px;">
        <h4 style="margin-top:0; color: #166534;">Executive Summary</h4>
        <p style="font-size: 1.05rem; line-height: 1.5;">{report.executive_summary}</p>
        <strong>Risk Alignment:</strong> {report.risk_alignment_score} | <em>Generated at {report.generated_at}</em>
    </div>
    """, unsafe_allow_html=True)

    if report.advisor_override_notes:
        st.markdown(f"**Human Advisor Steering Directive Incorporated:** `{report.advisor_override_notes}`")

    # Recommendations
    st.markdown("### 💡 Prioritized Recommendations")
    for rec in report.recommendations:
        badge_color = "red" if rec.priority == "URGENT" else ("orange" if rec.priority == "HIGH" else "blue")
        with st.expander(f":{badge_color}[{rec.priority}] **{rec.action_title}** ({rec.category})", expanded=True):
            st.markdown(f"**Guidance:** {rec.detailed_guidance}")
            st.markdown(f"**Economic / Risk Rationale:** *{rec.rationale}*")

    # Rebalance Plan Table
    if report.rebalance_plan:
        st.markdown("### ⚖️ Portfolio Rebalancing Action Matrix")
        reb_data = []
        for r in report.rebalance_plan:
            reb_data.append({
                "Asset Class": r.asset_class,
                "Current %": f"{r.current_percent:.1f}%",
                "Target %": f"{r.target_percent:.1f}%",
                "Action": r.adjustment_action,
                "Suggested Shift ($)": f"${r.suggested_dollar_shift:,.2f}"
            })
        st.table(reb_data)

    st.caption(f"🔒 {report.compliance_disclaimer}")

    # Export Report Options
    st.markdown("### 💾 Export Options")
    exp_col1, exp_col2 = st.columns(2)
    with exp_col1:
        st.download_button(
            label="📥 Download Structured Report (JSON)",
            data=json.dumps(report.model_dump(), indent=2),
            file_name=f"advisory_report_{report.client_id}.json",
            mime="application/json",
            use_container_width=True
        )
    with exp_col2:
        markdown_content = f"""# Wealth Advisory Report - {report.client_name}
**Client ID:** {report.client_id}  
**Date:** {report.generated_at}  
**Risk Alignment:** {report.risk_alignment_score}  

## Executive Summary
{report.executive_summary}

## Key Recommendations
""" + "\n".join([f"### [{r.priority}] {r.action_title}\n- **Category:** {r.category}\n- **Guidance:** {r.detailed_guidance}\n- **Rationale:** {r.rationale}\n" for r in report.recommendations])
        st.download_button(
            label="📄 Download Report (Markdown)",
            data=markdown_content,
            file_name=f"advisory_report_{report.client_id}.md",
            mime="text/markdown",
            use_container_width=True
        )

    # Interactive Gemini Assistant Q&A
    st.markdown("---")
    st.markdown("### 💬 Ask Gemini Wealth Assistant (Interactive)")
    st.caption("Directly ask Google Gemini any question regarding this portfolio, macroeconomic sensitivities, or tax planning.")
    
    col_q1, col_q2 = st.columns([4, 1])
    with col_q1:
        user_q = st.text_input(
            "Your Question for Gemini:",
            placeholder="e.g. How would a 50 bps interest rate cut impact Arthur's fixed income yields?",
            label_visibility="collapsed"
        )
    with col_q2:
        ask_btn = st.button("Ask Gemini 🤖", type="secondary", use_container_width=True)

    if ask_btn and user_q:
        advisor_client = st.session_state.orchestrator.advisor.client
        if not advisor_client:
            st.warning("⚠️ Please provide a valid Gemini API Key in the sidebar to enable live interactive Q&A.")
        else:
            with st.spinner(f"Querying {config.GEMINI_MODEL}..."):
                try:
                    context_prompt = (
                        f"You are the Lead Wealth Advisor for {report.client_name}.\n"
                        f"Portfolio Summary:\n{report.executive_summary}\n"
                        f"Risk Alignment: {report.risk_alignment_score}\n"
                        f"User Query: {user_q}\n"
                        f"Provide a clear, concise, institutional wealth management recommendation."
                    )
                    ans = advisor_client.models.generate_content(
                        model=config.GEMINI_MODEL,
                        contents=context_prompt
                    )
                    st.markdown(f"""
                    <div style="background-color:#F8FAFC; border:1px solid #CBD5E1; border-radius:8px; padding:16px; margin-top:10px;">
                        <strong>🤖 Gemini Response:</strong><br/>
                        {ans.text}
                    </div>
                    """, unsafe_allow_html=True)
                except Exception as e:
                    st.error(f"Gemini API Error: {e}")

# 6. Observability & Agent Trace Drawer
with st.expander("🔍 Observability: Agent Execution Trace & Logs", expanded=False):
    events = execution_trace.get_events()
    if events:
        for ev in reversed(events):
            status_emoji = "✅" if ev["status"] == "SUCCESS" else ("⚠️" if ev["status"] == "WARNING" else "ℹ️")
            st.text(f"[{ev['timestamp']}] {status_emoji} [{ev['agent']}] {ev['action']} - Details: {ev.get('details')}")
    else:
        st.text("No active execution traces logged yet.")
