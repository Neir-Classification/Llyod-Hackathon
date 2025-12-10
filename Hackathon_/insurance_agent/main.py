#!/usr/bin/env python3
"""
Main entry point for the Insurance AI Agent.
"""
import argparse
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))


def main():
    parser = argparse.ArgumentParser(
        description="Insurance AI Agent - Nier",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py chat              # Interactive CLI chat
  python main.py ui                # Start Streamlit UI
  python main.py api               # Start FastAPI server
  python main.py demo              # Run demo scenarios
  python main.py init              # Initialize knowledge base
        """
    )
    
    parser.add_argument(
        "command",
        choices=["chat", "ui", "api", "demo", "init"],
        help="Command to run"
    )
    
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Reset/rebuild the knowledge base (for 'init' command)"
    )
    
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port for API server (default: 8000)"
    )
    
    args = parser.parse_args()
    
    if args.command == "chat":
        run_chat()
    elif args.command == "ui":
        run_ui()
    elif args.command == "api":
        run_api(args.port)
    elif args.command == "demo":
        run_demo()
    elif args.command == "init":
        init_knowledge_base(args.reset)


def run_chat():
    """Run interactive CLI chat."""
    print("Starting interactive chat mode...")
    from src.agent.orchestrator import InsuranceAgent, get_agent
    from src.knowledge.vector_store import initialize_vector_store
    
    # Initialize
    initialize_vector_store(reset=False)
    agent = get_agent()
    
    print("\n" + "=" * 60)
    print("Insurance AI Agent - Interactive Chat")
    print("=" * 60)
    print("\nType 'quit' to exit, 'reset' to start new conversation\n")
    
    while True:
        try:
            user_input = input("\nYou: ").strip()
            
            if user_input.lower() == 'quit':
                break
            elif user_input.lower() == 'reset':
                agent.reset_conversation()
                print("Conversation reset.")
                continue
            elif not user_input:
                continue
            
            result = agent.process_message(user_input)
            print(f"\nAgent: {result['response']}")
            
        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break


def run_ui():
    """Run Streamlit UI."""
    import subprocess
    ui_path = Path(__file__).parent / "ui" / "app.py"
    subprocess.run(["streamlit", "run", str(ui_path)])


def run_api(port: int):
    """Run FastAPI server."""
    import uvicorn
    uvicorn.run(
        "src.api:app",
        host="0.0.0.0",
        port=port,
        reload=True
    )


def run_demo():
    """Run demo script."""
    from demo.run_demo import main as demo_main
    demo_main()


def init_knowledge_base(reset: bool):
    """Initialize the knowledge base."""
    from src.knowledge.vector_store import initialize_vector_store
    from src.utils.config import ensure_directories
    
    print("Initializing knowledge base...")
    ensure_directories()
    
    store = initialize_vector_store(reset=reset)
    stats = store.get_collection_stats()
    
    print(f"\nKnowledge base ready:")
    print(f"  Collection: {stats['name']}")
    print(f"  Documents: {stats['count']}")
    print(f"  Location: {stats['persist_directory']}")


if __name__ == "__main__":
    main()
