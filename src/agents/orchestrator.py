from typing import Dict, Any, Optional, Union
from src.agents.data_fetcher import DataFetcherAgent
from src.agents.analyzer import AnalyzerAgent
from src.agents.advisor import AdvisorAgent
from src.memory.short_term import ShortTermMemory
from src.memory.long_term import LongTermMemory
from src.hitl.checkpoint import HumanInTheLoopCheckpoint, HumanDecision
from src.models.advisory import AdvisoryReport
from src.utils.logger import logger, execution_trace

class OrchestratorAgent:
    """
    Orchestrator Agent:
    Central coordinator of the Wealth Advisor Assistant system.
    Controls execution flow, coordinates task routing between specialized agents,
    manages short-term and long-term memory, and coordinates Human-in-the-Loop checkpoints.
    """
    def __init__(self):
        self.data_fetcher = DataFetcherAgent()
        self.analyzer = AnalyzerAgent()
        self.advisor = AdvisorAgent()
        self.hitl_checkpoint = HumanInTheLoopCheckpoint()
        self.long_term_memory = LongTermMemory()
        self.short_term_memory = ShortTermMemory()

    def run_stage_one_analysis(
        self,
        financial_input: Union[Dict[str, Any], str],
        client_id: str
    ) -> Dict[str, Any]:
        """
        Stage 1: Ingestion & Analysis.
        Executes DataFetcher -> Analyzer, saves state to short-term memory,
        and halts if Human-in-the-Loop review is required.
        """
        execution_trace.clear()
        self.short_term_memory = ShortTermMemory()
        self.short_term_memory.client_id = client_id

        logger.info(f"=== Starting Orchestration Pipeline for Client: {client_id} ===")
        execution_trace.add_event(
            agent="Orchestrator",
            action="Pipeline Initiated",
            details={"client_id": client_id}
        )

        try:
            # 1. Route to Data Fetcher Agent
            enriched_data = self.data_fetcher.process(financial_input=financial_input, client_id=client_id)
            self.short_term_memory.raw_financial_data = enriched_data["financial_data"]
            self.short_term_memory.crm_data = enriched_data["crm_profile"]

            # 2. Route to Analyzer Agent
            analysis_output = self.analyzer.analyze(
                financial_data=enriched_data["financial_data"],
                crm_profile=enriched_data["crm_profile"]
            )
            self.short_term_memory.portfolio_metrics = analysis_output["metrics"]
            self.short_term_memory.detected_anomalies = analysis_output["anomalies"]

            # 3. Check Human-in-the-Loop Requirement
            needs_review = self.hitl_checkpoint.requires_checkpoint(analysis_output["anomalies"])

            execution_trace.add_event(
                agent="Orchestrator",
                action="Stage 1 Analysis Complete",
                details={"requires_human_review": needs_review},
                status="SUCCESS"
            )

            return {
                "client_id": client_id,
                "financial_data": enriched_data["financial_data"],
                "crm_profile": enriched_data["crm_profile"],
                "metrics": analysis_output["metrics"],
                "anomalies": analysis_output["anomalies"],
                "requires_human_review": needs_review
            }

        except Exception as e:
            logger.error(f"[Orchestrator] Error during Stage 1 execution: {e}")
            execution_trace.add_event(
                agent="Orchestrator",
                action="Pipeline Error",
                details=str(e),
                status="ERROR"
            )
            raise

    def run_stage_two_advisory(
        self,
        human_decision: Optional[HumanDecision] = None
    ) -> AdvisoryReport:
        """
        Stage 2: Advisory Synthesis & Finalization.
        Applies Human-in-the-Loop decisions, retrieves historical memory,
        routes to Advisor Agent, and updates long-term memory.
        """
        if not self.short_term_memory.raw_financial_data or not self.short_term_memory.portfolio_metrics:
            raise RuntimeError("Cannot execute Stage 2: Stage 1 has not been executed or memory is empty.")

        client_id = self.short_term_memory.client_id or "unknown"
        anomalies = self.short_term_memory.detected_anomalies
        human_notes = None

        # Process HITL Decision if provided
        if human_decision:
            anomalies = self.hitl_checkpoint.process_review(anomalies=anomalies, decision=human_decision)
            self.short_term_memory.human_checkpoint_decision = human_decision.model_dump()
            human_notes = human_decision.advisor_notes
            self.short_term_memory.detected_anomalies = anomalies

        # Retrieve Long-Term Historical Context
        historical_context = self.long_term_memory.get_historical_context_prompt(client_id)

        # Route to Advisor Agent
        report = self.advisor.generate_advisory(
            client_data=self.short_term_memory.raw_financial_data,
            crm_profile=self.short_term_memory.crm_data,
            metrics=self.short_term_memory.portfolio_metrics,
            anomalies=anomalies,
            human_notes=human_notes,
            historical_context=historical_context
        )

        self.short_term_memory.final_advisory_report = report.model_dump()

        # Update Long-Term Memory
        self.long_term_memory.save_session_record(
            client_id=client_id,
            summary={
                "executive_summary": report.executive_summary,
                "risk_alignment_score": report.risk_alignment_score,
                "recommendations": [r.model_dump() for r in report.recommendations],
                "anomalies": anomalies,
                "human_decision": human_decision.model_dump() if human_decision else None
            }
        )

        execution_trace.add_event(
            agent="Orchestrator",
            action="Pipeline Execution Finalized Successfully",
            details={"client_id": client_id, "recommendations": len(report.recommendations)},
            status="SUCCESS"
        )
        logger.info(f"=== Completed Orchestration Pipeline for Client: {client_id} ===")
        return report

    def run_full(
        self,
        financial_input: Union[Dict[str, Any], str],
        client_id: str,
        human_decision: Optional[HumanDecision] = None
    ) -> AdvisoryReport:
        """Convenience method to execute full pipeline end-to-end."""
        self.run_stage_one_analysis(financial_input=financial_input, client_id=client_id)
        return self.run_stage_two_advisory(human_decision=human_decision)
