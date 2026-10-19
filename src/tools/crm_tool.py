import json
import time
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from src.tools.base import BaseTool
from src.config import config
from src.models.client import CRMProfile
from src.utils.logger import logger

class CRMToolInput(BaseModel):
    client_id: str = Field(..., description="The unique ID of the client whose CRM profile to fetch")
    simulate_failure: bool = Field(default=False, description="Whether to simulate an external CRM API timeout/error")

class CRMTool(BaseTool):
    """Tool to fetch client CRM details, investment goals, risk mandates, and notes."""
    name = "crm_fetcher"
    description = "Queries the enterprise CRM API to retrieve client risk profile, target horizons, and advisor notes."
    args_schema = CRMToolInput

    def execute(self, client_id: str, simulate_failure: bool = False) -> Dict[str, Any]:
        if simulate_failure:
            raise ConnectionError(f"CRM API Endpoint timed out while querying client_id: {client_id}")

        # Simulate realistic API network latency
        time.sleep(0.05)

        crm_path = config.MOCK_CRM_PATH
        if not crm_path.exists():
            logger.warning(f"CRM database file not found at {crm_path}. Using fallback default profile.")
            return self._fallback_profile(client_id).model_dump()

        try:
            with open(crm_path, "r") as f:
                crm_db = json.load(f)
            
            if client_id in crm_db:
                record = crm_db[client_id]
                profile = CRMProfile(**record)
                return profile.model_dump()
            else:
                logger.warning(f"Client '{client_id}' not found in CRM. Synthesizing conservative fallback profile.")
                return self._fallback_profile(client_id).model_dump()
        except Exception as e:
            logger.error(f"Error parsing CRM database: {e}. Falling back to default profile.")
            return self._fallback_profile(client_id).model_dump()

    def _fallback_profile(self, client_id: str) -> CRMProfile:
        """Fallback behavior when CRM fails or client is missing."""
        return CRMProfile(
            client_id=client_id,
            name=f"Client ({client_id})",
            risk_profile="Moderate",
            primary_goal="Capital Preservation & Moderate Growth (Default Fallback)",
            target_horizon_years=10,
            kyc_status="Pending Verification",
            tax_bracket="24%",
            target_allocation={"Equities": 50.0, "Fixed Income": 40.0, "Cash": 10.0},
            advisor_notes=["Note: Profile was generated via fallback mechanism due to CRM unavailability."]
        )
