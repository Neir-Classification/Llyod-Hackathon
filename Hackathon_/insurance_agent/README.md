# Insurance AI Agent - Nier

An intelligent voice-enabled AI agent for handling complex insurance inquiries. Built with LangGraph, ChromaDB, and real-time voice processing.

## 🎯 Project Overview

This project addresses the "15% problem" in insurance - the complex, ambiguous cases that traditional chatbots can't handle. Unlike simple FAQ bots, this agent:

- **Reasons** through multi-step problems
- **Investigates** policy documents dynamically
- **Cites sources** for every answer
- **Empathizes** with customer situations
- **Escalates** when appropriate

## 🏗️ Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Voice Input   │────▶│   Orchestrator  │────▶│  Voice Output   │
│  (Whisper STT)  │     │   (LangGraph)   │     │  (ElevenLabs)   │
└─────────────────┘     └────────┬────────┘     └─────────────────┘
                                 │
                    ┌────────────┼────────────┐
                    ▼            ▼            ▼
            ┌───────────┐ ┌───────────┐ ┌───────────┐
            │  Policy   │ │  Customer │ │ Calculator│
            │   RAG     │ │    CRM    │ │   Tool    │
            │  (Chroma) │ │   (JSON)  │ │           │
            └───────────┘ └───────────┘ └───────────┘
```

## 📁 Project Structure

```
insurance_agent/
├── src/
│   ├── agent/           # Core agent logic (ReAct pattern)
│   │   ├── orchestrator.py
│   │   ├── tools.py
│   │   └── prompts.py
│   ├── knowledge/       # RAG & Vector DB
│   │   ├── document_loader.py
│   │   ├── vector_store.py
│   │   └── retriever.py
│   ├── voice/           # STT & TTS
│   │   ├── speech_to_text.py
│   │   ├── text_to_speech.py
│   │   └── audio_handler.py
│   ├── database/        # Mock CRM
│   │   └── customer_db.py
│   ├── guardrails/      # Compliance & Safety
│   │   └── compliance.py
│   └── utils/           # Helpers
│       ├── config.py
│       └── logger.py
├── data/
│   ├── policies/        # PDF policy documents
│   ├── customers/       # Mock customer data
│   └── chroma_db/       # Vector database
├── ui/
│   ├── app.py           # Streamlit dashboard
│   └── components/      # UI components
├── tests/
│   └── scenarios/       # Golden path tests
├── requirements.txt
├── .env.example
└── README.md
```

## 🚀 Quick Start

### 1. Installation

```bash
cd insurance_agent
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configuration

```bash
cp .env.example .env
# Edit .env with your API keys
```

### 3. Initialize the Knowledge Base

```bash
python -m src.knowledge.document_loader
```

### 4. Run the Application

```bash
# Start the Streamlit UI
streamlit run ui/app.py

# Or run the FastAPI backend only
uvicorn src.api:app --reload
```

## 🎮 Demo Scenarios

### Scenario 1: The "Yes" Path - Sump Pump Coverage

**Customer**: "My basement flooded because the sump pump failed."

**Agent Response**: Identifies user, checks Water Backup endorsement, confirms coverage.

### Scenario 2: The "No" Path - Flood Exclusion

**Customer**: "The river near my house overflowed and flooded my basement."

**Agent Response**: Empathetically explains that river flooding requires separate flood insurance (NFIP).

### Scenario 3: Clarification Needed - Mold Damage

**Customer**: "I found mold behind my washing machine."

**Agent Response**: Asks clarifying questions about discovery date, then cites Hidden Water Damage clause.

## 📊 Key Features

- **Sub-3 second latency**: Real-time voice conversations
- **100% Citation Rate**: Every answer references specific policy sections
- **ReAct Pattern**: Transparent reasoning visible in UI
- **Guardrails**: Compliance-safe language ("appears to be covered" vs "is covered")
- **Escalation**: Automatic handoff for ambiguous cases

## 🛠️ Tech Stack

- **LLM**: OpenAI GPT-4o
- **Agent Framework**: LangGraph
- **Vector DB**: ChromaDB
- **STT**: OpenAI Whisper
- **TTS**: ElevenLabs
- **UI**: Streamlit
- **Backend**: FastAPI

## 📝 License

MIT License - Built for Insurance AI Hackathon 2024
