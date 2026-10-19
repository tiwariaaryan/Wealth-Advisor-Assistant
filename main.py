import argparse
import json
import sys
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm
from src.agents.orchestrator import OrchestratorAgent
from src.hitl.checkpoint import HumanDecision
from src.config import config

console = Console()

def display_metrics_table(metrics: dict):
    table = Table(title="📊 Portfolio Key Metrics", show_header=True, header_style="bold cyan")
    table.add_column("Metric", style="bold white")
    table.add_column("Value", justify="right", style="green")

    table.add_row("Total AUM", f"${metrics.get('total_aum', 0):,.2f}")
    table.add_row("Cash Balance", f"${metrics.get('cash_balance', 0):,.2f}")
    table.add_row("Cash Drag", f"{metrics.get('cash_drag_percent', 0):.1f}%")
    table.add_row("Total Liabilities", f"${metrics.get('total_liabilities', 0):,.2f}")
    table.add_row("Net Worth", f"${metrics.get('net_worth', 0):,.2f}")
    table.add_row("Debt-to-Asset Ratio", f"{metrics.get('debt_to_asset_ratio', 0):.2f}")
    console.print(table)

    alloc_table = Table(title="📈 Asset Class Allocation", show_header=True, header_style="bold magenta")
    alloc_table.add_column("Asset Class")
    alloc_table.add_column("Amount", justify="right")
    alloc_table.add_column("Percentage", justify="right")

    for a in metrics.get("allocations", []):
        alloc_table.add_row(a["asset_class"], f"${a['amount']:,.2f}", f"{a['percentage']:.1f}%")
    console.print(alloc_table)

def display_anomalies(anomalies: list):
    if not anomalies:
        console.print("[bold green]✅ No high-risk anomalies or rule violations detected.[/bold green]")
        return

    table = Table(title="⚠️ Flagged Anomalies & Risk Signals", show_header=True, header_style="bold red")
    table.add_column("ID", style="dim")
    table.add_column("Severity")
    table.add_column("Type")
    table.add_column("Description")

    for a in anomalies:
        sev = a.get("severity")
        color = "red bold" if sev == "CRITICAL" else ("yellow bold" if sev == "HIGH" else "cyan")
        table.add_row(a.get("id"), f"[{color}]{sev}[/{color}]", a.get("anomaly_type"), a.get("description"))
    console.print(table)

def run_cli():
    parser = argparse.ArgumentParser(description="Wealth Advisor Assistant - Multi-Agent System")
    parser.add_argument("--client", type=str, default="client_001", help="Client ID from sample database (e.g. client_001, client_002, client_003)")
    parser.add_argument("--file", type=str, default=None, help="Path to custom client financial JSON file")
    parser.add_argument("--auto", action="store_true", help="Auto-approve HITL checkpoint without interactive prompt")
    args = parser.parse_args()

    console.print(Panel.fit(
        "[bold cyan]🏛️ Wealth Advisor Assistant[/bold cyan]\n"
        "[dim]Autonomous Multi-Agent System with Gemini LLM & Human-in-the-Loop[/dim]",
        border_style="cyan"
    ))

    # Load client financial data
    if args.file:
        file_path = Path(args.file)
        if not file_path.exists():
            console.print(f"[bold red]File not found: {file_path}[/bold red]")
            sys.exit(1)
        with open(file_path, "r") as f:
            financial_data = json.load(f)
        client_id = financial_data.get("client_id", "custom_client")
    else:
        sample_path = config.SAMPLE_CLIENTS_PATH
        with open(sample_path, "r") as f:
            all_samples = json.load(f)
        if args.client not in all_samples:
            console.print(f"[bold red]Client ID '{args.client}' not found in sample clients. Available: {list(all_samples.keys())}[/bold red]")
            sys.exit(1)
        financial_data = all_samples[args.client]
        client_id = args.client

    orchestrator = OrchestratorAgent()

    # Stage 1: Ingestion & Analysis
    with console.status("[bold blue]Executing Stage 1: Data Ingestion & Financial Analysis...[/bold blue]"):
        stage_one_res = orchestrator.run_stage_one_analysis(financial_input=financial_data, client_id=client_id)

    console.print(f"\n[bold green]Client Profile Loaded:[/bold green] {stage_one_res['financial_data']['name']} (Risk Profile: {stage_one_res['crm_profile']['risk_profile']})")
    display_metrics_table(stage_one_res["metrics"])
    display_anomalies(stage_one_res["anomalies"])

    # Stage 2: Human-in-the-Loop Checkpoint
    decision = None
    if stage_one_res["requires_human_review"] and not args.auto:
        console.print("\n[bold yellow]🛑 Human-in-the-Loop Review Required[/bold yellow]")
        console.print("[dim]Critical anomalies or risk mismatches were flagged above.[/dim]")
        
        choice = Prompt.ask(
            "Select action",
            choices=["approve", "override", "reject"],
            default="approve"
        )
        
        if choice == "override":
            overridden_ids = Prompt.ask("Enter Anomaly IDs to override/authorize (comma-separated, e.g. ANOM-001)")
            override_list = [x.strip() for x in overridden_ids.split(",") if x.strip()]
            notes = Prompt.ask("Enter Advisor Directive / Justification Note")
            decision = HumanDecision(
                action="OVERRIDE",
                approved=True,
                overridden_anomaly_ids=override_list,
                advisor_notes=notes
            )
        elif choice == "approve":
            notes = Prompt.ask("Enter optional advisor steering notes (or press enter)", default="")
            decision = HumanDecision(action="APPROVE", approved=True, advisor_notes=notes or None)
        else:
            console.print("[bold red]Execution halted by Human Advisor.[/bold red]")
            sys.exit(0)
    else:
        decision = HumanDecision(action="APPROVE", approved=True, advisor_notes="Auto-approved execution.")

    # Stage 3: Advisory Synthesis via Gemini
    with console.status("[bold magenta]Executing Stage 2: Synthesizing Advisory Strategy with Gemini...[/bold magenta]"):
        report = orchestrator.run_stage_two_advisory(human_decision=decision)

    # Display Final Report
    console.print(Panel(
        f"[bold white]{report.executive_summary}[/bold white]\n\n"
        f"[bold cyan]Risk Alignment:[/bold cyan] {report.risk_alignment_score}\n"
        f"[bold cyan]Generated At:[/bold cyan] {report.generated_at}",
        title=f"📋 Advisory Report for {report.client_name}",
        border_style="green"
    ))

    # Recommendations Table
    rec_table = Table(title="💡 Strategic Recommendations", show_header=True, header_style="bold yellow")
    rec_table.add_column("Priority", style="bold")
    rec_table.add_column("Category")
    rec_table.add_column("Action Title")
    rec_table.add_column("Detailed Guidance")

    for r in report.recommendations:
        p_color = "red" if r.priority == "URGENT" else ("yellow" if r.priority == "HIGH" else "green")
        rec_table.add_row(f"[{p_color}]{r.priority}[/{p_color}]", r.category, r.action_title, r.detailed_guidance)
    console.print(rec_table)

    # Rebalance Table
    if report.rebalance_plan:
        reb_table = Table(title="⚖️ Recommended Portfolio Rebalancing", show_header=True, header_style="bold blue")
        reb_table.add_column("Asset Class")
        reb_table.add_column("Current %", justify="right")
        reb_table.add_column("Target %", justify="right")
        reb_table.add_column("Action", justify="center")
        reb_table.add_column("Est. Dollar Shift", justify="right")

        for reb in report.rebalance_plan:
            act_color = "green" if reb.adjustment_action == "INCREASE" else ("red" if reb.adjustment_action == "DECREASE" else "white")
            reb_table.add_row(
                reb.asset_class,
                f"{reb.current_percent:.1f}%",
                f"{reb.target_percent:.1f}%",
                f"[{act_color}]{reb.adjustment_action}[/{act_color}]",
                f"${reb.suggested_dollar_shift:,.2f}"
            )
        console.print(reb_table)

    console.print(f"\n[dim italic]{report.compliance_disclaimer}[/dim italic]\n")

if __name__ == "__main__":
    run_cli()
