from typing import List, Optional, Dict
from pydantic import BaseModel, Field

class Holding(BaseModel):
    symbol: str = Field(..., description="Asset ticker or identifier")
    name: str = Field(..., description="Asset or company name")
    asset_class: str = Field(..., description="Asset class e.g. Equities, Fixed Income, Crypto / Alternative, Real Estate")
    quantity: float = Field(..., ge=0, description="Number of units held")
    current_price: float = Field(..., ge=0, description="Current market price per unit")
    total_value: float = Field(..., ge=0, description="Total market value")

class Liability(BaseModel):
    name: str = Field(..., description="Name or source of liability/debt")
    amount: float = Field(..., ge=0, description="Outstanding balance")
    interest_rate: float = Field(..., ge=0, description="Annual interest rate percentage")

class Transaction(BaseModel):
    id: str = Field(..., description="Unique transaction ID")
    date: str = Field(..., description="Date of transaction in YYYY-MM-DD")
    type: str = Field(..., description="CREDIT or DEBIT")
    category: str = Field(..., description="Category e.g. Salary, Pension, Living Expenses, Options Trading, Unusual Outflow")
    amount: float = Field(..., ge=0, description="Transaction amount")
    description: str = Field(..., description="Transaction memo or details")
    flagged: Optional[bool] = Field(default=False, description="Flagged for manual review or anomaly")

class ClientFinancialData(BaseModel):
    client_id: str = Field(..., description="Unique client identifier")
    name: str = Field(..., description="Client full name")
    age: int = Field(..., ge=0, le=120, description="Client age")
    occupation: str = Field(..., description="Client profession or retirement status")
    annual_income: float = Field(..., ge=0, description="Annual earned/pension income")
    currency: str = Field(default="USD", description="Currency denomination")
    cash_balance: float = Field(..., ge=0, description="Liquid cash or checking account balance")
    holdings: List[Holding] = Field(default_factory=list, description="List of investment holdings")
    liabilities: List[Liability] = Field(default_factory=list, description="List of debts or liabilities")
    recent_transactions: List[Transaction] = Field(default_factory=list, description="Recent ledger transactions")

class CRMProfile(BaseModel):
    client_id: str = Field(..., description="Unique client identifier")
    name: str = Field(..., description="Client full name")
    risk_profile: str = Field(..., description="Conservative, Moderate, or Aggressive Growth")
    primary_goal: str = Field(..., description="Primary financial objective")
    target_horizon_years: int = Field(..., ge=1, description="Investment time horizon in years")
    kyc_status: str = Field(default="Verified", description="KYC compliance status")
    tax_bracket: str = Field(default="25%", description="Federal/marginal tax bracket")
    target_allocation: Dict[str, float] = Field(
        default_factory=lambda: {"Equities": 50.0, "Fixed Income": 40.0, "Cash": 10.0},
        description="Target asset allocation percentages"
    )
    advisor_notes: List[str] = Field(default_factory=list, description="Historical advisor interaction notes")
    last_contact_date: Optional[str] = Field(default=None, description="Date of last advisor consultation")
