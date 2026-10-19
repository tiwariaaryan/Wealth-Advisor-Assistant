from typing import Dict, Any, List
from collections import defaultdict
from pydantic import BaseModel, Field
from src.tools.base import BaseTool
from src.config import config
from src.models.analysis import PortfolioMetrics, AssetAllocation, ConcentrationRisk

class PortfolioMetricsInput(BaseModel):
    cash_balance: float = Field(..., ge=0, description="Liquid cash or checking account balance")
    holdings: List[Dict[str, Any]] = Field(default_factory=list, description="List of holding dictionaries")
    liabilities: List[Dict[str, Any]] = Field(default_factory=list, description="List of liability dictionaries")

class PortfolioMetricsTool(BaseTool):
    """Tool to calculate deterministic financial ratios, allocations, and concentration risks."""
    name = "portfolio_metrics_calculator"
    description = "Calculates total AUM, net worth, asset class allocations, cash drag %, and concentration risk."
    args_schema = PortfolioMetricsInput

    def execute(self, cash_balance: float, holdings: List[Dict[str, Any]], liabilities: List[Dict[str, Any]]) -> Dict[str, Any]:
        # Calculate holdings value
        total_holdings_val = sum(h.get("total_value", 0.0) for h in holdings)
        total_aum = total_holdings_val + cash_balance
        
        # Calculate liabilities
        total_liabilities = sum(l.get("amount", 0.0) for l in liabilities)
        net_worth = total_aum - total_liabilities

        # Cash drag percentage
        cash_drag_pct = (cash_balance / total_aum * 100.0) if total_aum > 0 else 0.0

        # Debt to asset ratio
        debt_to_asset = (total_liabilities / total_aum) if total_aum > 0 else 0.0

        # Allocation breakdown by asset class
        class_totals = defaultdict(float)
        class_totals["Cash"] = cash_balance

        for h in holdings:
            aclass = h.get("asset_class", "Other")
            val = h.get("total_value", 0.0)
            class_totals[aclass] += val

        allocations: List[AssetAllocation] = []
        for aclass, amt in sorted(class_totals.items(), key=lambda x: x[1], reverse=True):
            pct = (amt / total_aum * 100.0) if total_aum > 0 else 0.0
            allocations.append(AssetAllocation(
                asset_class=aclass,
                amount=round(amt, 2),
                percentage=round(pct, 2)
            ))

        # Concentration risk analysis
        concentration_risks: List[ConcentrationRisk] = []
        for h in holdings:
            val = h.get("total_value", 0.0)
            pct = (val / total_aum * 100.0) if total_aum > 0 else 0.0
            is_violation = pct >= config.CONCENTRATION_RISK_THRESHOLD
            if is_violation:
                concentration_risks.append(ConcentrationRisk(
                    symbol=h.get("symbol", "UNKNOWN"),
                    name=h.get("name", "Unknown Holding"),
                    percentage=round(pct, 2),
                    is_violation=True
                ))

        metrics = PortfolioMetrics(
            total_holdings_value=round(total_holdings_val, 2),
            cash_balance=round(cash_balance, 2),
            total_aum=round(total_aum, 2),
            total_liabilities=round(total_liabilities, 2),
            net_worth=round(net_worth, 2),
            cash_drag_percent=round(cash_drag_pct, 2),
            debt_to_asset_ratio=round(debt_to_asset, 4),
            allocations=allocations,
            concentration_risks=concentration_risks
        )

        return metrics.model_dump()
