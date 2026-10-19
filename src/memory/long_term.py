import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
from src.config import config
from src.utils.logger import logger

class LongTermMemory:
    """
    Long-term persistent store for historical client consultations,
    prior anomalies, and human advisor overrides.
    """
    def __init__(self, storage_path: Optional[Path] = None):
        self.storage_path = storage_path or config.LONG_TERM_MEMORY_PATH
        self._initialize_store()

    def _initialize_store(self):
        if not self.storage_path.exists():
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.storage_path, "w") as f:
                json.dump({}, f, indent=2)

    def _read_data(self) -> Dict[str, Any]:
        try:
            with open(self.storage_path, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error reading long term memory: {e}")
            return {}

    def _write_data(self, data: Dict[str, Any]):
        try:
            with open(self.storage_path, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error writing to long term memory: {e}")

    def save_session_record(self, client_id: str, summary: Dict[str, Any]):
        """Appends a completed consultation record to the client's historical timeline."""
        data = self._read_data()
        if client_id not in data:
            data[client_id] = {
                "client_id": client_id,
                "consultations": [],
                "past_anomalies": [],
                "advisor_overrides": []
            }

        consultation_entry = {
            "timestamp": datetime.now().isoformat(),
            "executive_summary": summary.get("executive_summary", ""),
            "risk_alignment": summary.get("risk_alignment_score", ""),
            "recommendation_count": len(summary.get("recommendations", [])),
            "anomalies_detected": [a.get("description") for a in summary.get("anomalies", [])]
        }
        data[client_id]["consultations"].append(consultation_entry)

        # Save overrides if any
        if summary.get("human_decision"):
            data[client_id]["advisor_overrides"].append({
                "timestamp": datetime.now().isoformat(),
                "decision": summary.get("human_decision")
            })

        self._write_data(data)
        logger.info(f"Long-term memory updated for client '{client_id}'.")

    def get_client_history(self, client_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves past historical interactions and insights for a client."""
        data = self._read_data()
        return data.get(client_id, None)

    def get_historical_context_prompt(self, client_id: str) -> str:
        """Formats historical interactions into a concise context string for LLM prompts."""
        history = self.get_client_history(client_id)
        if not history or not history.get("consultations"):
            return "No previous consultation history found for this client (first consultation)."

        lines = [f"Historical Consultations on Record ({len(history['consultations'])}):"]
        for c in history["consultations"][-3:]:  # Last 3 consultations
            lines.append(f"- Date: {c['timestamp'][:10]} | Summary: {c['executive_summary'][:120]}... | Risk: {c['risk_alignment']}")
        
        if history.get("advisor_overrides"):
            lines.append(f"Past Advisor Overrides: {len(history['advisor_overrides'])} on file.")
        
        return "\n".join(lines)
