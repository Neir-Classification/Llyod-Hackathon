# Insurance AI Agent - System Architecture

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              USER INTERFACE                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│   ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐         │
│   │   Voice Input   │    │   Streamlit UI  │    │   FastAPI REST  │         │
│   │   (Microphone)  │    │   (Dashboard)   │    │   (WebSocket)   │         │
│   └────────┬────────┘    └────────┬────────┘    └────────┬────────┘         │
│            │                      │                      │                    │
│            ▼                      ▼                      ▼                    │
│   ┌─────────────────┐                                                        │
│   │  Whisper STT    │◄──────────────────────────────────────────────────────┤
│   │  (OpenAI)       │                                                        │
│   └────────┬────────┘                                                        │
│            │                                                                  │
└────────────┼──────────────────────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           AGENT ORCHESTRATOR                                  │
│                              (LangGraph)                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                         ReAct Loop                                    │   │
│   │                                                                       │   │
│   │   ┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐   │   │
│   │   │ THOUGHT  │────▶│  ACTION  │────▶│OBSERVATION│────▶│ RESPONSE │   │   │
│   │   │(Reasoning)│    │(Tool Call)│    │(Tool Result)│   │(Final)   │   │   │
│   │   └──────────┘     └──────────┘     └──────────┘     └──────────┘   │   │
│   │        ▲                                                  │          │   │
│   │        └──────────────────────────────────────────────────┘          │   │
│   │                    (Loop until answer found)                          │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                          │
│                                    ▼                                          │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                     GPT-4o LLM Core                                   │   │
│   │                (System Prompt + Persona)                              │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                                                               │
└────────────────────────────────────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              TOOL BELT                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│   ┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐           │
│   │  Policy RAG     │   │  Customer CRM   │   │  Calculator     │           │
│   │  (ChromaDB)     │   │  (JSON DB)      │   │  (Deductibles)  │           │
│   ├─────────────────┤   ├─────────────────┤   ├─────────────────┤           │
│   │ • Semantic      │   │ • Profile       │   │ • Coverage      │           │
│   │   Search        │   │   Lookup        │   │   Limits        │           │
│   │ • Hybrid        │   │ • Endorsement   │   │ • Depreciation  │           │
│   │   Retrieval     │   │   Check         │   │ • Deductible    │           │
│   │ • Citation      │   │ • Claims        │   │   Application   │           │
│   │   Extraction    │   │   History       │   │                 │           │
│   └─────────────────┘   └─────────────────┘   └─────────────────┘           │
│                                                                               │
└────────────────────────────────────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            GUARDRAILS                                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│   ┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐           │
│   │  Compliance     │   │  Sentiment      │   │  Escalation     │           │
│   │  Checker        │   │  Analyzer       │   │  Manager        │           │
│   ├─────────────────┤   ├─────────────────┤   ├─────────────────┤           │
│   │ • No Guarantees │   │ • Frustration   │   │ • Search        │           │
│   │ • Conditional   │   │   Detection     │   │   Threshold     │           │
│   │   Language      │   │ • Urgency       │   │ • Human         │           │
│   │ • Citation      │   │   Detection     │   │   Handoff       │           │
│   │   Required      │   │ • Tone          │   │ • Conversation  │           │
│   │ • Sanitization  │   │   Adjustment    │   │   Summary       │           │
│   └─────────────────┘   └─────────────────┘   └─────────────────┘           │
│                                                                               │
└────────────────────────────────────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           VOICE OUTPUT                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│   ┌─────────────────┐                      ┌─────────────────┐              │
│   │  ElevenLabs TTS │  ─────────────────▶  │  Audio Player   │              │
│   │  (Turbo v2)     │                      │  (Web/Speaker)  │              │
│   └─────────────────┘                      └─────────────────┘              │
│                                                                               │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Data Flow Diagram

```
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│  User    │     │  STT     │     │  Agent   │     │  TTS     │     │  User    │
│  Speaks  │────▶│ (Whisper)│────▶│ Process  │────▶│(Eleven)  │────▶│  Hears   │
└──────────┘     └──────────┘     └──────────┘     └──────────┘     └──────────┘
                                       │
                    ┌──────────────────┼──────────────────┐
                    ▼                  ▼                  ▼
              ┌──────────┐       ┌──────────┐       ┌──────────┐
              │  Search  │       │  Lookup  │       │Calculate │
              │  Policy  │       │ Customer │       │ Coverage │
              └──────────┘       └──────────┘       └──────────┘
                    │                  │                  │
                    ▼                  ▼                  ▼
              ┌──────────┐       ┌──────────┐       ┌──────────┐
              │ ChromaDB │       │   JSON   │       │  Python  │
              │ Vectors  │       │    DB    │       │   Math   │
              └──────────┘       └──────────┘       └──────────┘
```

## Component Descriptions

### 1. Voice Interface Layer
- **Whisper STT**: OpenAI's speech-to-text for transcription
- **ElevenLabs TTS**: Low-latency text-to-speech synthesis
- **Audio Handler**: Manages microphone input and speaker output

### 2. Agent Orchestrator
- **LangGraph**: Manages the ReAct loop workflow
- **GPT-4o**: Core reasoning and language understanding
- **System Prompt**: Defines agent persona and behavior

### 3. Tool Belt
- **Policy RAG**: Vector search over policy documents (ChromaDB)
- **Customer CRM**: Customer profile and endorsement lookup
- **Calculator**: Coverage and deductible calculations

### 4. Guardrails
- **Compliance**: Ensures legal/regulatory compliance
- **Sentiment**: Detects customer frustration
- **Escalation**: Manages human handoff

### 5. Knowledge Base
- **Policy Documents**: HO-3 homeowners policy
- **FAQ Documents**: Common questions and answers
- **Customer Database**: Mock CRM with policy info

## Tech Stack Summary

| Component | Technology |
|-----------|------------|
| LLM | OpenAI GPT-4o |
| Agent Framework | LangGraph |
| Vector Database | ChromaDB |
| Embeddings | OpenAI text-embedding-3-small |
| Speech-to-Text | OpenAI Whisper |
| Text-to-Speech | ElevenLabs Turbo v2 |
| Backend | FastAPI |
| Frontend | Streamlit |
| Language | Python 3.11+ |
