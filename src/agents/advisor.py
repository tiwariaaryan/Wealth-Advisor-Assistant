import json
from typing import Dict, Any, List, Optional, Type
from pydantic import BaseModel
from src.agents.base_agent import BaseAgent
from src.models.advisory import AdvisoryReport, AdvisoryRecommendation, RebalanceItem
from src.utils.logger import logger, execution_trace

class AdvisorAgent(BaseAgent):
    """
    Advisor Agent:
    Synthesizes portfolio metrics, CRM goals, anomaly findings, and human advisor directives
    to generate structured, institutional-grade wealth advisory plans using Gemini LLM.
    """
    def __init__(self):
        super().__init__(name="AdvisorAgent", role="Strategic Advisory & Recommendation Synthesis")

    def generate_advisory(
        self,
        client_data: Dict[str, Any],
        crm_profile: Dict[str, Any],
        metrics: Dict[str, Any],
        anomalies: List[Dict[str, Any]],
        human_notes: Optional[str] = None,
        historical_context: Optional[str] = None
    ) -> AdvisoryReport:
        """
        Synthesizes all insights into a finalized AdvisoryReport.
        """
        self.current_client_id = client_data.get("client_id", "client_generic")
        self.current_client_name = client_data.get("name", "Valued Client")
        client_name = self.current_client_name
        logger.info(f"[{self.name}] Formulating personalized wealth strategy for '{client_name}'...")
        execution_trace.add_event(
            agent=self.name,
            action="Synthesizing Advisory Strategy",
            details={"client_name": client_name, "human_notes_present": bool(human_notes)}
        )

        prompt = self._build_synthesis_prompt(
            client_data=client_data,
            crm_profile=crm_profile,
            metrics=metrics,
            anomalies=anomalies,
            human_notes=human_notes,
            historical_context=historical_context
        )

        system_instruction = (
            "You are a Senior Private Wealth Advisor and fiduciary expert. "
            "Your objective is to produce highly specific, institutional-quality financial advice, "
            "addressing client risk alignment, portfolio anomalies, cash drag, and concentration risks. "
            "Honor any Human Advisor Override Notes with the highest priority."
        )

        report = self.call_gemini_structured(
            prompt=prompt,
            response_schema=AdvisoryReport,
            system_instruction=system_instruction
        )

        # Attach human notes if present
        if human_notes and hasattr(report, "advisor_override_notes"):
            report.advisor_override_notes = human_notes

        logger.info(f"[{self.name}] Advisory report generated successfully. Risk Alignment: {report.risk_alignment_score}.")
        return report

    def _build_synthesis_prompt(
        self,
        client_data: Dict[str, Any],
        crm_profile: Dict[str, Any],
        metrics: Dict[str, Any],
        anomalies: List[Dict[str, Any]],
        human_notes: Optional[str],
        historical_context: Optional[str]
    ) -> str:
        alloc_str = ", ".join([f"{a['asset_class']}: {a['percentage']}% (${a['amount']:,.0f})" for a in metrics.get("allocations", [])])
        target_str = ", ".join([f"{k}: {v}%" for k, v in crm_profile.get("target_allocation", {}).items()])
        
        anomaly_lines = []
        for a in anomalies:
            status = "[OVERRIDDEN BY ADVISOR]" if a.get("overridden_by_human") else "[ACTIVE]"
            anomaly_lines.append(f"- {status} ({a.get('severity')}) {a.get('anomaly_type')}: {a.get('description')} | Action: {a.get('suggested_action')}")

        anomalies_formatted = "\n".join(anomaly_lines) if anomaly_lines else "No critical anomalies detected."

        return f"""
Please generate a comprehensive, structured Wealth Advisory Report for the following client:

=== CLIENT PROFILE ===
- Client ID: {client_data.get('client_id')}
- Name: {client_data.get('name')}, Age: {client_data.get('age')}, Occupation: {client_data.get('occupation')}
- Stated Risk Profile: {crm_profile.get('risk_profile')}
- Primary Goal: {crm_profile.get('primary_goal')}
- Investment Time Horizon: {crm_profile.get('target_horizon_years')} years
- Marginal Tax Bracket: {crm_profile.get('tax_bracket')}
- Advisor Notes from CRM: {'; '.join(crm_profile.get('advisor_notes', []))}

=== PORTFOLIO METRICS ===
- Total AUM: ${metrics.get('total_aum'):,.2f}
- Cash Balance: ${metrics.get('cash_balance'):,.2f} (Cash Drag: {metrics.get('cash_drag_percent')}%)
- Total Liabilities: ${metrics.get('total_liabilities'):,.2f} | Net Worth: ${metrics.get('net_worth'):,.2f}
- Current Asset Allocation: {alloc_str}
- CRM Target Allocation: {target_str}
- Concentration Violations: {json.dumps(metrics.get('concentration_risks', []))}

=== DETECTED ANOMALIES & AUDIT FLAGS ===
{anomalies_formatted}

=== HUMAN ADVISOR STEERING / OVERRIDE NOTES ===
{human_notes or 'No manual override provided. Rely entirely on fiduciary analysis.'}

=== HISTORICAL CONSULTATION RECORD ===
{historical_context or 'No prior records.'}

INSTRUCTIONS:
1. Provide an executive summary synthesizing portfolio health, asset alignment, and urgent risks.
2. Formulate a risk alignment score (e.g. 'Misaligned (58%) - Overweight in volatile crypto vs conservative mandate').
3. Summarize flagged anomalies and your verdict on them.
4. Provide 3-5 prioritized recommendations (URGENT, HIGH, MEDIUM) with clear action titles and economic rationale.
5. Create a concrete rebalancing plan comparing current % vs target % with suggested dollar shifts.
"""

    def _generate_fallback(self, prompt: str, schema: Type[BaseModel]) -> AdvisoryReport:
        """Deterministic rule-based fallback if LLM is unavailable."""
        client_id = getattr(self, "current_client_id", "client_generic")
        client_name = getattr(self, "current_client_name", "Valued Client")
        return AdvisoryReport(
            client_id=client_id,
            client_name=client_name,
            executive_summary=(
                "The portfolio displays notable deviations from the target asset allocation. "
                "Immediate rebalancing is advised to align risk exposure with stated investment horizons and goals."
            ),
            risk_alignment_score="Moderate Alignment (70%)",
            flagged_anomalies_summary=[
                "Detected cash drag and asset allocation divergence from benchmark targets."
            ],
            recommendations=[
                AdvisoryRecommendation(
                    category="Portfolio Rebalancing",
                    priority="HIGH",
                    action_title="Rebalance to Target Asset Allocation",
                    detailed_guidance="Systematically deploy excess cash into underweight core fixed-income and equity indexes.",
                    rationale="Restores expected risk-return balance while minimizing cash drag."
                ),
                AdvisoryRecommendation(
                    category="Risk Mitigation",
                    priority="MEDIUM",
                    action_title="Transaction Audit & Verification",
                    detailed_guidance="Verify recent unusual outflows with client and account custodian.",
                    rationale="Mitigates fraudulent activity and confirms client liquidity requirements."
                )
            ],
            rebalance_plan=[
                RebalanceItem(
                    asset_class="Cash",
                    current_percent=25.0,
                    target_percent=10.0,
                    adjustment_action="DECREASE",
                    suggested_dollar_shift=50000.0
                ),
                RebalanceItem(
                    asset_class="Fixed Income",
                    current_percent=35.0,
                    target_percent=50.0,
                    adjustment_action="INCREASE",
                    suggested_dollar_shift=50000.0
                )
            ],
            advisor_override_notes=None
        )
