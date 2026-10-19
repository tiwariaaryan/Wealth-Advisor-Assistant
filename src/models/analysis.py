from typing import List, Dict, Optional
from pydantic import BaseModel, Field

class AssetAllocation(BaseModel):
    asset_class: str = Field(..., description="Asset class name")
    amount: float = Field(..., ge=0, description="Dollar value in this asset class")
    percentage: float = Field(..., ge=0, le=100, description="Percentage of total portfolio")

class ConcentrationRisk(BaseModel):
    symbol: str = Field(..., description="Ticker symbol")
    name: str = Field(..., description="Asset name")
    percentage: float = Field(..., ge=0, le=100, description="Percentage of total portfolio")
    is_violation: bool = Field(..., description="True if exceeds concentration threshold")

class AnomalyItem(BaseModel):
    id: str = Field(..., description="Unique anomaly ID e.g. ANOM-001")
    anomaly_type: str = Field(..., description="E.g. SPENDING_SPIKE, RISK_MISMATCH, UNUSUAL_COUNTERPARTY, CASH_DRAG")
    severity: str = Field(..., description="LOW, MEDIUM, HIGH, or CRITICAL")
    description: str = Field(..., description="Detailed description of what is anomalous")
    transaction_id: Optional[str] = Field(default=None, description="Associated transaction ID if applicable")
    suggested_action: str = Field(..., description="Actionable suggestion for the advisor")
    overridden_by_human: bool = Field(default=False, description="Whether overridden during human checkpoint")
    human_notes: Optional[str] = Field(default=None, description="Notes added by advisor during review")

class PortfolioMetrics(BaseModel):
    total_holdings_value: float = Field(..., ge=0, description="Total market value of non-cash holdings")
    cash_balance: float = Field(..., ge=0, description="Total cash balance")
    total_aum: float = Field(..., ge=0, description="Total assets under management (Holdings + Cash)")
    total_liabilities: float = Field(..., ge=0, description="Total outstanding debt")
    net_worth: float = Field(..., description="Total AUM minus Total Liabilities")
    cash_drag_percent: float = Field(..., ge=0, le=100, description="Cash as percentage of total portfolio")
    debt_to_asset_ratio: float = Field(..., ge=0, description="Total liabilities divided by Total AUM")
    allocations: List[AssetAllocation] = Field(default_factory=list, description="Asset class breakdown")
    concentration_risks: List[ConcentrationRisk] = Field(default_factory=list, description="Holdings exceeding threshold")

class AnalysisResult(BaseModel):
    client_id: str
    client_name: str
    metrics: PortfolioMetrics
    anomalies: List[AnomalyItem]
    requires_human_review: bool = Field(default=False, description="True if any HIGH or CRITICAL anomalies detected")
