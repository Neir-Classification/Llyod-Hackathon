"""
Insurance AI Agent - Nier
=========================

An intelligent voice-enabled AI agent for handling complex insurance inquiries.
Built with LangGraph, ChromaDB, and real-time voice processing.

Usage:
    # Start the Streamlit UI
    streamlit run ui/app.py
    
    # Start the FastAPI backend
    uvicorn src.api:app --reload
    
    # Run the demo script
    python demo/run_demo.py
    
    # Interactive CLI chat
    python -m src.agent.orchestrator
"""

__version__ = "1.0.0"
__author__ = "Insurance AI Team"
__description__ = "Intelligent voice-enabled insurance assistant"

from src.utils.config import config, ensure_directories

# Ensure data directories exist on import
ensure_directories()
