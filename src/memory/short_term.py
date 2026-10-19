from typing import Dict, Any, List, Optional
from datetime import datetime

class ShortTermMemory:
    """
    Session-level in-memory scratchpad.
    Tracks state transitions, intermediate agent findings, and current context during pipeline execution.
    """
    def __init__(self, session_id: Optional[str] = None):
        self.session_id: str = session_id or f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.client_id: Optional[str] = None
        self.raw_financial_data: Optional[Dict[str, Any]] = None
        self.crm_data: Optional[Dict[str, Any]] = None
        self.portfolio_metrics: Optional[Dict[str, Any]] = None
        self.detected_anomalies: List[Dict[str, Any]] = []
        self.human_checkpoint_decision: Optional[Dict[str, Any]] = None
        self.final_advisory_report: Optional[Dict[str, Any]] = None
        self.agent_thought_log: List[Dict[str, Any]] = []

    def log_agent_thought(self, agent_name: str, thought: str, payload: Optional[Any] = None):
        self.agent_thought_log.append({
            "timestamp": datetime.now().isoformat(),
            "agent": agent_name,
            "thought": thought,
            "payload": payload
        })

    def get_state_summary(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "client_id": self.client_id,
            "has_financial_data": self.raw_financial_data is not None,
            "has_crm_data": self.crm_data is not None,
            "has_metrics": self.portfolio_metrics is not None,
            "anomaly_count": len(self.detected_anomalies),
            "hitl_reviewed": self.human_checkpoint_decision is not None,
            "has_final_report": self.final_advisory_report is not None
        }
