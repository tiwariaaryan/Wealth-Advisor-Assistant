from typing import Dict, Any, Type
from pydantic import BaseModel
from src.agents.base_agent import BaseAgent
from src.tools.portfolio_tool import PortfolioMetricsTool
from src.tools.anomaly_tool import AnomalyDetectionTool
from src.models.analysis import AnalysisResult, PortfolioMetrics, AnomalyItem
from src.utils.logger import logger, execution_trace

class AnalyzerAgent(BaseAgent):
    """
    Analyzer Agent:
    Performs deterministic quantitative portfolio analysis and executes
    multi-dimensional anomaly detection on transaction patterns and asset allocations.
    """
    def __init__(self):
        super().__init__(name="AnalyzerAgent", role="Portfolio Analytics & Anomaly Detection")
        self.portfolio_tool = PortfolioMetricsTool()
        self.anomaly_tool = AnomalyDetectionTool()

    def analyze(self, financial_data: Dict[str, Any], crm_profile: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes financial ratio calculations and anomaly detection.
        """
        client_name = financial_data.get("name", "Unknown Client")
        client_id = financial_data.get("client_id", "unknown")
        logger.info(f"[{self.name}] Initiating portfolio analytics for '{client_name}'...")

        # 1. Run Quantitative Portfolio Metrics Tool
        execution_trace.add_event(
            agent=self.name,
            action="Computing Portfolio Metrics",
            details={"tool": self.portfolio_tool.name}
        )
        metrics_res = self.portfolio_tool.run(
            cash_balance=financial_data.get("cash_balance", 0.0),
            holdings=financial_data.get("holdings", []),
            liabilities=financial_data.get("liabilities", [])
        )

        if not metrics_res.success:
            raise RuntimeError(f"Portfolio calculation failed: {metrics_res.error}")

        portfolio_metrics = metrics_res.data

        # 2. Run Anomaly Detection Tool
        execution_trace.add_event(
            agent=self.name,
            action="Running Anomaly Detection Algorithms",
            details={"tool": self.anomaly_tool.name}
        )
        anomaly_res = self.anomaly_tool.run(
            portfolio_metrics=portfolio_metrics,
            transactions=financial_data.get("recent_transactions", []),
            crm_profile=crm_profile
        )

        if not anomaly_res.success:
            raise RuntimeError(f"Anomaly detection failed: {anomaly_res.error}")

        anomalies = anomaly_res.data

        # Determine if human checkpoint is required
        has_high_risk = any(a.get("severity") in ("CRITICAL", "HIGH") for a in anomalies)

        logger.info(f"[{self.name}] Analysis complete. Metrics computed. Detected {len(anomalies)} anomalies (High-Risk: {has_high_risk}).")
        execution_trace.add_event(
            agent=self.name,
            action="Analysis Completed",
            details={
                "total_aum": portfolio_metrics.get("total_aum"),
                "net_worth": portfolio_metrics.get("net_worth"),
                "anomaly_count": len(anomalies),
                "requires_review": has_high_risk
            },
            status="SUCCESS" if not has_high_risk else "WARNING"
        )

        return {
            "client_id": client_id,
            "client_name": client_name,
            "metrics": portfolio_metrics,
            "anomalies": anomalies,
            "requires_human_review": has_high_risk
        }

    def _generate_fallback(self, prompt: str, schema: Type[BaseModel]) -> BaseModel:
        pass
