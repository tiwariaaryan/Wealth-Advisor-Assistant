import json
import pytest
from src.agents.orchestrator import OrchestratorAgent
from src.hitl.checkpoint import HumanDecision
from src.config import config

def test_orchestration_pipeline_end_to_end():
    with open(config.SAMPLE_CLIENTS_PATH, "r") as f:
        sample_data = json.load(f)
    client_data = sample_data["client_001"]

    orchestrator = OrchestratorAgent()

    # Stage 1: Ingestion & Analysis
    stage_one = orchestrator.run_stage_one_analysis(financial_input=client_data, client_id="client_001")
    assert stage_one["client_id"] == "client_001"
    assert stage_one["metrics"]["total_aum"] > 0
    assert len(stage_one["anomalies"]) > 0
    assert stage_one["requires_human_review"] is True

    # Stage 2: Human-in-the-Loop review & advisory synthesis
    decision = HumanDecision(
        action="OVERRIDE",
        approved=True,
        overridden_anomaly_ids=["ANOM-001"],
        advisor_notes="Authorized wire transfer for vacation real estate purchase."
    )
    report = orchestrator.run_stage_two_advisory(human_decision=decision)

    assert report.client_name == client_data["name"]
    assert len(report.recommendations) > 0
    assert report.executive_summary is not None
