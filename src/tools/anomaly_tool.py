import math
from typing import Dict, Any, List
from pydantic import BaseModel, Field
from src.tools.base import BaseTool
from src.config import config
from src.models.analysis import AnomalyItem

class AnomalyDetectionInput(BaseModel):
    portfolio_metrics: Dict[str, Any] = Field(..., description="Computed portfolio metrics")
    transactions: List[Dict[str, Any]] = Field(default_factory=list, description="Recent transactions")
    crm_profile: Dict[str, Any] = Field(..., description="Client CRM profile and risk mandate")

class AnomalyDetectionTool(BaseTool):
    """Tool to detect transaction outliers, allocation drift, and profile risk mismatches."""
    name = "anomaly_detector"
    description = "Detects statistical spending spikes, high-risk outflows, cash drag, and CRM risk mismatches."
    args_schema = AnomalyDetectionInput

    def execute(self, portfolio_metrics: Dict[str, Any], transactions: List[Dict[str, Any]], crm_profile: Dict[str, Any]) -> List[Dict[str, Any]]:
        anomalies: List[AnomalyItem] = []
        counter = 1

        # 1. Transaction Anomaly Detection (Statistical Z-Score & Large Outflow)
        debit_amounts = [t.get("amount", 0.0) for t in transactions if t.get("type") == "DEBIT"]
        if len(debit_amounts) >= 3:
            mean_debit = sum(debit_amounts) / len(debit_amounts)
            variance = sum((x - mean_debit) ** 2 for x in debit_amounts) / len(debit_amounts)
            std_dev = math.sqrt(variance) if variance > 0 else 0.0
        else:
            mean_debit = 0.0
            std_dev = 0.0

        for tx in transactions:
            amt = tx.get("amount", 0.0)
            tx_type = tx.get("type", "")
            desc = tx.get("description", "")
            cat = tx.get("category", "")
            is_flagged = tx.get("flagged", False)

            # Check if flagged by ledger or large absolute amount
            if (amt >= config.LARGE_TX_THRESHOLD_USD and tx_type == "DEBIT") or is_flagged:
                anomalies.append(AnomalyItem(
                    id=f"ANOM-{counter:03d}",
                    anomaly_type="UNUSUAL_OUTFLOW",
                    severity="CRITICAL",
                    description=f"High-value debit of ${amt:,.2f} on {tx.get('date')}: '{desc}' (Category: {cat}).",
                    transaction_id=tx.get("id"),
                    suggested_action="Verify transaction authorization directly with client to rule out unauthorized access or account takeover."
                ))
                counter += 1
            # Check statistical z-score outlier
            elif std_dev > 0 and (amt - mean_debit) / std_dev >= config.ANOMALY_ZSCORE_THRESHOLD and tx_type == "DEBIT":
                z_score = (amt - mean_debit) / std_dev
                anomalies.append(AnomalyItem(
                    id=f"ANOM-{counter:03d}",
                    anomaly_type="SPENDING_SPIKE",
                    severity="HIGH",
                    description=f"Transaction of ${amt:,.2f} is a statistical anomaly (Z-score: {z_score:.2f} > {config.ANOMALY_ZSCORE_THRESHOLD}). Description: '{desc}'.",
                    transaction_id=tx.get("id"),
                    suggested_action="Review if this represents a one-off expenditure or a recurring shift in spending lifestyle."
                ))
                counter += 1

        # 2. Cash Drag Anomaly
        cash_drag = portfolio_metrics.get("cash_drag_percent", 0.0)
        cash_balance = portfolio_metrics.get("cash_balance", 0.0)
        if cash_drag >= config.CASH_DRAG_THRESHOLD_PERCENT:
            anomalies.append(AnomalyItem(
                id=f"ANOM-{counter:03d}",
                anomaly_type="CASH_DRAG",
                severity="MEDIUM",
                description=f"Substantial cash drag: ${cash_balance:,.2f} ({cash_drag:.1f}% of total AUM) sits uninvested in cash, suffering purchasing power loss from inflation.",
                suggested_action=f"Formulate a dollar-cost-averaging (DCA) or short-term yield deployment plan to bring cash closer to target (target: ~5-10%)."
            ))
            counter += 1

        # 3. Single Asset Concentration Risk
        conc_risks = portfolio_metrics.get("concentration_risks", [])
        for c in conc_risks:
            anomalies.append(AnomalyItem(
                id=f"ANOM-{counter:03d}",
                anomaly_type="CONCENTRATION_RISK",
                severity="HIGH",
                description=f"Concentration Risk: {c.get('symbol')} ({c.get('name')}) comprises {c.get('percentage'):.1f}% of entire portfolio, exceeding safety threshold of {config.CONCENTRATION_RISK_THRESHOLD}%.",
                suggested_action="Develop a systematic tax-efficient divestment or collar hedging strategy to diversify into broader index funds."
            ))
            counter += 1

        # 4. CRM Risk Mandate Mismatch
        risk_profile = crm_profile.get("risk_profile", "Moderate")
        allocations = {a["asset_class"]: a["percentage"] for a in portfolio_metrics.get("allocations", [])}
        
        # If conservative client holds speculative assets (Crypto, Options)
        crypto_pct = allocations.get("Crypto / Alternative", 0.0)
        if risk_profile.lower() == "conservative" and crypto_pct > 2.0:
            anomalies.append(AnomalyItem(
                id=f"ANOM-{counter:03d}",
                anomaly_type="RISK_PROFILE_MISMATCH",
                severity="CRITICAL",
                description=f"Client risk profile is 'Conservative' (Preservation Goal), but holds {crypto_pct:.1f}% in speculative alternative/crypto assets.",
                suggested_action="Consult with client to determine if speculative holdings should be liquidated into fixed income or capital preservation vehicles."
            ))
            counter += 1

        # Check debt to asset ratio
        debt_ratio = portfolio_metrics.get("debt_to_asset_ratio", 0.0)
        if debt_ratio >= 0.50:
            anomalies.append(AnomalyItem(
                id=f"ANOM-{counter:03d}",
                anomaly_type="HIGH_LEVERAGE",
                severity="HIGH",
                description=f"High portfolio leverage: Debt-to-Asset ratio is {debt_ratio:.2f} (exceeds 0.50 safe threshold).",
                suggested_action="Evaluate high-interest debt service and consider paying down floating-rate loans using surplus liquidity."
            ))
            counter += 1

        return [a.model_dump() for a in anomalies]
