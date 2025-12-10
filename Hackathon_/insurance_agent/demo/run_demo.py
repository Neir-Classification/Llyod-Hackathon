#!/usr/bin/env python3
"""
Demo Script for Insurance AI Agent.
Runs through the key demo scenarios for presentation.
"""
import sys
import time
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.table import Table
from rich.prompt import Prompt, Confirm

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agent.orchestrator import InsuranceAgent
from src.knowledge.vector_store import initialize_vector_store
from src.database.customer_db import get_customer_db
from src.utils.logger import agent_logger


console = Console()


# ============================================================================
# Demo Scenarios
# ============================================================================

DEMO_SCENARIOS = {
    "1": {
        "name": "💧 Sump Pump Coverage (YES Path)",
        "customer": "HO-2024-001234",
        "description": "Customer John Doe's sump pump failed. He HAS Water Backup endorsement.",
        "message": "My basement flooded because the sump pump failed. Am I covered?",
        "expected": "Agent confirms coverage exists (Water Backup endorsement)"
    },
    "2": {
        "name": "🌊 River Flood (NO Path)",
        "customer": "HO-2024-009012",
        "description": "River flooded Michael Chen's basement. Standard policy excludes flood.",
        "message": "The river near my house overflowed and flooded my basement. Is this covered?",
        "expected": "Agent explains flood exclusion, suggests NFIP"
    },
    "3": {
        "name": "🍄 Mold Discovery (Clarification)",
        "customer": "HO-2024-005678",
        "description": "Sarah found mold behind washer. Coverage depends on conditions.",
        "message": "I just found mold behind my washing machine. Is that covered?",
        "expected": "Agent explains conditions for mold coverage (hidden, sudden, 14 days)"
    },
    "4": {
        "name": "💍 Engagement Ring (Sub-Limits)",
        "customer": "HO-2024-005678",
        "description": "Question about $10,000 ring. Standard limit is $1,500.",
        "message": "I just bought a $10,000 engagement ring. Is it covered under my contents limit?",
        "expected": "Agent explains jewelry sub-limit and scheduling option"
    },
    "5": {
        "name": "🏠 Airbnb Rental (Exclusion)",
        "customer": "HO-2024-009012",
        "description": "Customer wants to rent home on Airbnb. Commercial use exclusion.",
        "message": "I'm renting my house on Airbnb this weekend. Does my insurance cover theft by a guest?",
        "expected": "Agent explains commercial/rental use exclusion"
    },
    "6": {
        "name": "🌳 City Tree on Fence (Liability)",
        "customer": "HO-2024-001234",
        "description": "City's tree fell on customer's fence. Who is liable?",
        "message": "A tree fell on my fence, but the tree belongs to the city. Who pays?",
        "expected": "Agent explains filing on own policy, city liability rules"
    }
}


# ============================================================================
# Demo Functions
# ============================================================================

def print_header():
    """Print demo header."""
    console.print(Panel.fit(
        "[bold blue]🏠 Insurance AI Agent - Nier[/bold blue]\n"
        "[dim]Intelligent Voice-Enabled Insurance Assistant[/dim]\n\n"
        "[yellow]Demo Script for Hackathon Presentation[/yellow]",
        border_style="blue"
    ))


def print_scenario_menu():
    """Print scenario selection menu."""
    table = Table(title="Demo Scenarios", show_header=True, header_style="bold cyan")
    table.add_column("#", style="dim", width=3)
    table.add_column("Scenario", style="bold")
    table.add_column("Customer", style="green")
    table.add_column("Expected Outcome", style="yellow")
    
    for key, scenario in DEMO_SCENARIOS.items():
        table.add_row(
            key,
            scenario["name"],
            scenario["customer"],
            scenario["expected"][:50] + "..."
        )
    
    console.print(table)


def run_scenario(agent: InsuranceAgent, scenario: dict):
    """Run a demo scenario."""
    console.print()
    console.print(Panel(
        f"[bold]{scenario['name']}[/bold]\n\n"
        f"[dim]Customer:[/dim] {scenario['customer']}\n"
        f"[dim]Situation:[/dim] {scenario['description']}\n"
        f"[dim]Expected:[/dim] {scenario['expected']}",
        title="📋 Scenario Setup",
        border_style="cyan"
    ))
    
    # Get customer context
    db = get_customer_db()
    customer = db.get_by_policy_number(scenario["customer"])
    
    if customer:
        console.print(f"\n[green]✓ Customer loaded:[/green] {customer.full_name}")
        console.print(f"[dim]  Policy: {customer.policy_number}[/dim]")
        console.print(f"[dim]  Endorsements: {', '.join(customer.endorsements) if customer.endorsements else 'None'}[/dim]")
    
    # Display user message
    console.print()
    console.print(Panel(
        scenario["message"],
        title="👤 Customer Says",
        border_style="blue"
    ))
    
    # Process with agent
    console.print("\n[yellow]🔄 Agent processing...[/yellow]\n")
    
    # Clear previous thoughts
    agent_logger.clear_history()
    
    start_time = time.time()
    result = agent.process_message(
        scenario["message"],
        customer_context=customer.to_dict() if customer else None
    )
    elapsed = time.time() - start_time
    
    # Display response
    console.print(Panel(
        result["response"],
        title="🤖 Agent Response",
        border_style="green"
    ))
    
    console.print(f"\n[dim]Response time: {elapsed:.2f}s[/dim]")
    
    # Display thoughts if available
    if result.get("thought_log"):
        if Confirm.ask("\n[dim]Show agent's thought process?[/dim]", default=False):
            console.print("\n[bold cyan]🧠 Agent's Thoughts:[/bold cyan]")
            for thought in result["thought_log"]:
                thought_type = thought.get("type", "thought")
                content = thought.get("content", "")
                
                if thought_type == "thought":
                    console.print(f"  [cyan]💭 {content}[/cyan]")
                elif thought_type == "action":
                    tool = thought.get("tool", "")
                    console.print(f"  [yellow]🔧 Tool: {tool}[/yellow]")
                elif thought_type == "observation":
                    preview = str(content)[:100] + "..." if len(str(content)) > 100 else content
                    console.print(f"  [green]👁️ {preview}[/green]")
    
    if result.get("escalated"):
        console.print("\n[red]⚠️ This conversation was escalated to a human agent.[/red]")


def interactive_mode(agent: InsuranceAgent):
    """Run in interactive chat mode."""
    console.print("\n[bold green]Interactive Mode[/bold green]")
    console.print("[dim]Type your questions, 'menu' for scenarios, 'reset' to clear, 'quit' to exit[/dim]\n")
    
    current_customer = None
    
    while True:
        try:
            user_input = Prompt.ask("[blue]You[/blue]")
            
            if user_input.lower() == 'quit':
                break
            elif user_input.lower() == 'menu':
                print_scenario_menu()
                continue
            elif user_input.lower() == 'reset':
                agent.reset_conversation()
                current_customer = None
                console.print("[yellow]Conversation reset.[/yellow]")
                continue
            elif user_input.lower().startswith('customer '):
                # Set customer context
                customer_id = user_input.split(' ', 1)[1]
                db = get_customer_db()
                customer = db.search(customer_id)
                if customer:
                    current_customer = customer.to_dict()
                    console.print(f"[green]Customer set: {customer.full_name}[/green]")
                else:
                    console.print(f"[red]Customer not found: {customer_id}[/red]")
                continue
            
            # Process message
            result = agent.process_message(user_input, customer_context=current_customer)
            console.print(f"\n[green]Agent:[/green] {result['response']}\n")
            
        except KeyboardInterrupt:
            break
    
    console.print("\n[dim]Goodbye![/dim]")


def main():
    """Main demo function."""
    print_header()
    
    # Initialize
    console.print("\n[yellow]Initializing AI Agent...[/yellow]")
    
    with console.status("[bold green]Loading knowledge base..."):
        initialize_vector_store(reset=False)
    console.print("[green]✓ Knowledge base ready[/green]")
    
    agent = InsuranceAgent()
    console.print("[green]✓ Agent initialized[/green]")
    
    while True:
        console.print()
        print_scenario_menu()
        console.print("\n[dim]Enter scenario number (1-6), 'i' for interactive mode, or 'q' to quit[/dim]")
        
        choice = Prompt.ask("Select", default="1")
        
        if choice.lower() == 'q':
            break
        elif choice.lower() == 'i':
            interactive_mode(agent)
        elif choice in DEMO_SCENARIOS:
            run_scenario(agent, DEMO_SCENARIOS[choice])
            agent.reset_conversation()
        else:
            console.print("[red]Invalid selection[/red]")
        
        if choice in DEMO_SCENARIOS:
            if not Confirm.ask("\n[dim]Run another scenario?[/dim]", default=True):
                break
    
    console.print("\n[bold blue]Thank you for watching the demo![/bold blue]")


if __name__ == "__main__":
    main()
