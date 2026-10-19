import logging
import sys
from datetime import datetime
from typing import List, Dict, Any
from rich.console import Console
from rich.logging import RichHandler

console = Console()

class AgentExecutionTrace:
    """Stores in-memory execution logs and state transitions for UI and debugging."""
    def __init__(self):
        self.events: List[Dict[str, Any]] = []

    def add_event(self, agent: str, action: str, details: Any = None, status: str = "INFO"):
        event = {
            "timestamp": datetime.now().strftime("%H:%M:%S.%f")[:-3],
            "agent": agent,
            "action": action,
            "details": details,
            "status": status,
        }
        self.events.append(event)

    def get_events(self) -> List[Dict[str, Any]]:
        return self.events

    def clear(self):
        self.events = []

# Global trace instance
execution_trace = AgentExecutionTrace()

def setup_logger(name: str = "WealthAdvisor") -> logging.Logger:
    """Configures a Rich-formatted logger."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        rich_handler = RichHandler(
            console=console,
            rich_tracebacks=True,
            show_time=True,
            show_path=False
        )
        formatter = logging.Formatter("%(message)s")
        rich_handler.setFormatter(formatter)
        logger.addHandler(rich_handler)
    return logger

logger = setup_logger()
