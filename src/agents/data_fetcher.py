import json
from typing import Dict, Any, Union
from pydantic import BaseModel
from src.agents.base_agent import BaseAgent
from src.tools.crm_tool import CRMTool
from src.models.client import ClientFinancialData, CRMProfile
from src.utils.logger import logger, execution_trace

class DataFetcherAgent(BaseAgent):
    """
    Data Fetcher Agent:
    Retrieves and prepares client financial data, queries CRM records via the Tool Layer,
    and normalizes all raw inputs into validated schemas.
    """
    def __init__(self):
        super().__init__(name="DataFetcherAgent", role="Financial Data Ingestion & Context Enrichment")
        self.crm_tool = CRMTool()

    def process(self, financial_input: Union[Dict[str, Any], str], client_id: str) -> Dict[str, Any]:
        """
        Ingests financial data, validates it, and fetches CRM context.
        """
        logger.info(f"[{self.name}] Ingesting data for client '{client_id}'...")
        execution_trace.add_event(
            agent=self.name,
            action="Ingesting and Validating Financial Data",
            details={"client_id": client_id}
        )

        # 1. Parse / Validate Financial Input
        if isinstance(financial_input, str):
            try:
                financial_dict = json.loads(financial_input)
            except Exception as e:
                raise ValueError(f"Failed to parse JSON string: {e}")
        else:
            financial_dict = financial_input

        try:
            validated_client = ClientFinancialData(**financial_dict)
        except Exception as ve:
            logger.error(f"[{self.name}] Financial data validation failed: {ve}")
            execution_trace.add_event(
                agent=self.name,
                action="Data Validation Error",
                details=str(ve),
                status="ERROR"
            )
            raise ValueError(f"Invalid client financial data schema: {ve}")

        # 2. Fetch CRM Context via Tool Abstraction
        execution_trace.add_event(
            agent=self.name,
            action="Invoking CRM Tool",
            details={"tool": self.crm_tool.name}
        )
        tool_res = self.crm_tool.run(client_id=client_id)
        if not tool_res.success:
            logger.warning(f"[{self.name}] CRM fetch warning: {tool_res.error}. Utilizing fallback profile.")
            crm_data = self.crm_tool._fallback_profile(client_id).model_dump()
        else:
            crm_data = tool_res.data

        crm_profile = CRMProfile(**crm_data)

        logger.info(f"[{self.name}] Successfully fetched and enriched profile for '{validated_client.name}'.")
        execution_trace.add_event(
            agent=self.name,
            action="Data Preparation Complete",
            details={
                "client_name": validated_client.name,
                "holdings_count": len(validated_client.holdings),
                "transactions_count": len(validated_client.recent_transactions),
                "risk_profile": crm_profile.risk_profile
            },
            status="SUCCESS"
        )

        return {
            "financial_data": validated_client.model_dump(),
            "crm_profile": crm_profile.model_dump()
        }

    def _generate_fallback(self, prompt: str, schema: BaseModel):
        pass
