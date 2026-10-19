import pytest
from src.tools.crm_tool import CRMTool
from src.tools.portfolio_tool import PortfolioMetricsTool
from src.tools.anomaly_tool import AnomalyDetectionTool

def test_crm_tool_success():
    tool = CRMTool()
    res = tool.run(client_id="client_001")
    assert res.success is True
    assert res.data["client_id"] == "client_001"
    assert res.data["risk_profile"] == "Conservative"

def test_crm_tool_fallback_on_missing():
    tool = CRMTool()
    res = tool.run(client_id="non_existent_client")
    assert res.success is True
    assert "Pending Verification" in res.data["kyc_status"]

def test_crm_tool_simulated_failure():
    tool = CRMTool()
    res = tool.run(client_id="client_001", simulate_failure=True)
    assert res.success is False
    assert "timed out" in res.error

def test_portfolio_tool_metrics():
    tool = PortfolioMetricsTool()
    holdings = [
        {"symbol": "VTI", "name": "Vanguard Total Stock", "asset_class": "Equities", "quantity": 10, "current_price": 200.0, "total_value": 2000.0},
        {"symbol": "BND", "name": "Total Bond", "asset_class": "Fixed Income", "quantity": 10, "current_price": 100.0, "total_value": 1000.0}
    ]
    liabilities = [{"name": "Loan", "amount": 500.0, "interest_rate": 5.0}]
    
    res = tool.run(cash_balance=1000.0, holdings=holdings, liabilities=liabilities)
    assert res.success is True
    metrics = res.data
    assert metrics["total_holdings_value"] == 3000.0
    assert metrics["cash_balance"] == 1000.0
    assert metrics["total_aum"] == 4000.0
    assert metrics["net_worth"] == 3500.0
    assert metrics["cash_drag_percent"] == 25.0

def test_anomaly_tool_detection():
    portfolio_metrics = {
        "cash_drag_percent": 32.0,
        "cash_balance": 395000.0,
        "debt_to_asset_ratio": 0.04,
        "concentration_risks": [],
        "allocations": [
            {"asset_class": "Cash", "percentage": 32.0},
            {"asset_class": "Crypto / Alternative", "percentage": 5.0}
        ]
    }
    transactions = [
        {"id": "tx_1", "date": "2026-10-01", "type": "DEBIT", "category": "Living Expenses", "amount": 200.0, "description": "Coffee"},
        {"id": "tx_2", "date": "2026-10-02", "type": "DEBIT", "category": "Living Expenses", "amount": 300.0, "description": "Utilities"},
        {"id": "tx_3", "date": "2026-10-03", "type": "DEBIT", "category": "Living Expenses", "amount": 250.0, "description": "Market"},
        {"id": "tx_4", "date": "2026-10-14", "type": "DEBIT", "category": "Unusual Outflow", "amount": 50000.0, "description": "Offshore wire", "flagged": True}
    ]
    crm_profile = {"risk_profile": "Conservative"}

    tool = AnomalyDetectionTool()
    res = tool.run(portfolio_metrics=portfolio_metrics, transactions=transactions, crm_profile=crm_profile)
    assert res.success is True
    anomalies = res.data
    types = [a["anomaly_type"] for a in anomalies]
    assert "UNUSUAL_OUTFLOW" in types
    assert "CASH_DRAG" in types
    assert "RISK_PROFILE_MISMATCH" in types
