from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from src.utils.logger import logger, execution_trace

class HumanDecision(BaseModel):
    action: str = Field(..., description="APPROVE, OVERRIDE, or REJECT")
    approved: bool = Field(default=True, description="Whether the analysis is approved to proceed")
    overridden_anomaly_ids: List[str] = Field(default_factory=list, description="IDs of anomalies marked false positive/authorized")
    advisor_notes: Optional[str] = Field(default=None, description="Direct steering notes from human wealth advisor")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())

class HumanInTheLoopCheckpoint:
    """
    Supervises the Human-In-The-Loop review phase.
    Allows manual validation, false-positive override, and directive injection
    before advisory recommendations are formulated.
    """
    def __init__(self):
        pass

    def requires_checkpoint(self, anomalies: List[Dict[str, Any]]) -> bool:
        """Determines if any CRITICAL or HIGH severity anomalies demand human sign-off."""
        for a in anomalies:
            severity = a.get("severity", "LOW")
            if severity in ("CRITICAL", "HIGH"):
                return True
        return False

    def process_review(
        self,
        anomalies: List[Dict[str, Any]],
        decision: HumanDecision
    ) -> List[Dict[str, Any]]:
        """Applies human review decisions to the anomaly list."""
        logger.info(f"Human-in-the-Loop decision received: Action={decision.action}, Overrides={decision.overridden_anomaly_ids}")
        execution_trace.add_event(
            agent="HITL_Checkpoint",
            action=f"Human Advisor Review: {decision.action}",
            details={"overrides": decision.overridden_anomaly_ids, "notes": decision.advisor_notes},
            status="SUCCESS" if decision.approved else "WARNING"
        )

        updated_anomalies = []
        for a in anomalies:
            a_copy = dict(a)
            if a_copy.get("id") in decision.overridden_anomaly_ids:
                a_copy["overridden_by_human"] = True
                a_copy["human_notes"] = f"Marked as authorized/overridden by advisor: {decision.advisor_notes or 'No specific note'}"
            updated_anomalies.append(a_copy)

        return updated_anomalies
