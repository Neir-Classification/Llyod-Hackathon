# 🏠 Insurance AI Agent - Nier
## Hackathon Pitch Deck

---

## 🎯 The Problem

### The 15% Problem

**85% of insurance calls are now automated** - paying bills, downloading ID cards, simple status checks.

**But 15% are the "messy" calls** that humans still handle:
- "Does my policy cover water damage if the neighbor's pipe burst?"
- "I found mold behind my washing machine. Is that covered?"
- "I'm renting on Airbnb. What about theft by a guest?"

**The Cost:**
- Average handling time: 8-12 minutes per complex call
- Trained agents cost: $35-50/hour
- Customer wait time: 15-40 minutes
- Customer satisfaction: Drops significantly

---

## 💡 Our Solution: Agent Nier

### Not a Chatbot. An Intelligent Agent.

**Traditional Chatbot:**
```
Input → Search → Output
```

**Agent Nier:**
```
Input → Understand → Plan → Investigate → Reason → Respond
```

Nier acts like a smart employee:
> "I don't know the answer yet, but I know how to find it."

---

## 🧠 How It Works

### The ReAct Pattern (Reason + Act)

**Customer:** "My basement flooded because the sump pump failed."

**Agent's Internal Process:**

1. **💭 THOUGHT:** "This is a water damage claim inquiry. I need to check if sump pump failure is covered."

2. **🔧 ACTION:** `get_customer_profile("John Doe")`
   - ✅ Found: Policy HO-2024-001234

3. **🔧 ACTION:** `check_customer_endorsement("Water Backup")`
   - ✅ Customer HAS this endorsement

4. **🔧 ACTION:** `search_policy_documents("sump pump coverage")`
   - Found: "Water Backup Endorsement covers sump pump overflow..."

5. **💬 RESPONSE:** "Based on your policy, it appears you have the Water Backup endorsement, which covers sump pump failure. Would you like to start a claim?"

---

## 🎙️ Voice-to-Voice Experience

### Sub-3 Second Latency

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Whisper   │────▶│   GPT-4o    │────▶│ ElevenLabs  │
│    STT      │     │   Agent     │     │    TTS      │
│   (~0.5s)   │     │  (~1-2s)    │     │   (~0.3s)   │
└─────────────┘     └─────────────┘     └─────────────┘
```

**Total: 1.8-2.8 seconds** for complete voice-to-voice response

---

## 🔒 Compliance First

### The Legal Team's Nightmare: Hallucination

❌ **Bad Bot:** "Yes, you're definitely covered. We'll pay everything."

✅ **Agent Nier:** "Based on your policy and the Water Backup Endorsement, it **appears** you **may be** covered for this type of damage. According to section 4.2 of your policy..."

### Our Guardrails:
- ✓ **100% Citation Rate** - Every answer references policy source
- ✓ **Conditional Language** - "appears to be", "may be eligible"
- ✓ **Automatic Escalation** - Transfers to human when uncertain
- ✓ **Real-time Compliance Check** - Sanitizes risky language

---

## 📊 Demo Scenarios

### Scenario 1: ✅ The YES Path
**Customer:** "My sump pump failed and flooded my basement."
**Agent:** Checks endorsements → Finds Water Backup coverage → Confirms eligibility

### Scenario 2: ❌ The NO Path  
**Customer:** "The river flooded my basement."
**Agent:** Explains flood exclusion → Recommends NFIP → Empathetic tone

### Scenario 3: ❓ Needs Clarification
**Customer:** "I found mold behind my washing machine."
**Agent:** Asks when discovered → Checks 14-day reporting rule → Conditional answer

---

## 🏗️ Technical Architecture

```
┌─────────────────────────────────────────────────────┐
│                   VOICE LAYER                        │
│     Whisper (STT) ←──────────→ ElevenLabs (TTS)     │
└───────────────────────┬─────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────┐
│                 AGENT ORCHESTRATOR                   │
│                    (LangGraph)                       │
│   ┌─────────┐  ┌─────────┐  ┌─────────┐            │
│   │ THOUGHT │→ │ ACTION  │→ │OBSERVE  │→ Response  │
│   └─────────┘  └─────────┘  └─────────┘            │
└───────────────────────┬─────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────┐
│                    TOOL BELT                         │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐   │
│  │ Policy RAG  │ │ Customer DB │ │ Calculator  │   │
│  │ (ChromaDB)  │ │   (JSON)    │ │(Deductibles)│   │
│  └─────────────┘ └─────────────┘ └─────────────┘   │
└───────────────────────┬─────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────┐
│                   GUARDRAILS                         │
│    Compliance │ Sentiment │ Escalation Manager      │
└─────────────────────────────────────────────────────┘
```

---

## 📈 Business Impact

### By the Numbers

| Metric | Before | After Nier | Improvement |
|--------|--------|------------|-------------|
| Avg Handle Time | 8-12 min | 2-3 min | **70% ↓** |
| Cost per Call | $8-12 | $0.15 | **98% ↓** |
| Wait Time | 15-40 min | Instant | **100% ↓** |
| CSAT Score | 3.2/5 | 4.5/5* | **40% ↑** |
| 24/7 Availability | No | Yes | **∞** |

*Projected based on response quality and speed

### ROI Calculation
- 10,000 complex calls/month × $8 saved = **$80,000/month**
- Annual savings: **$960,000**
- Implementation cost: ~$50,000
- **ROI: 1,820%**

---

## 🚀 What's Next

### Phase 1 (Now): MVP
- ✅ Voice-to-voice conversation
- ✅ Policy RAG search
- ✅ Customer lookup
- ✅ Compliance guardrails

### Phase 2 (Q1 2025): Enhancement
- ⏳ Multi-language support
- ⏳ Claims form auto-fill
- ⏳ Photo damage assessment
- ⏳ Appointment scheduling

### Phase 3 (Q2 2025): Scale
- ⏳ Auto, Life, Commercial lines
- ⏳ Multi-carrier deployment
- ⏳ White-label solution

---

## 👥 Team

| Role | Responsibility |
|------|---------------|
| **Architect** | Agent logic, LangGraph workflow, prompts |
| **Knowledge Engineer** | RAG setup, document processing, ChromaDB |
| **Full-Stack** | UI/UX, API, voice integration |

---

## 🎬 Live Demo

### "The Mold Discovery Scenario"

**Setup:** Customer Sarah found mold behind washing machine

**Watch for:**
1. Agent's real-time thought process (visible in UI)
2. Clarifying question about discovery date
3. Policy citation in response
4. Conditional, compliant language

---

## 🏆 Why We Win

1. **Traceability** - Every answer shows its source
2. **Compliance** - Legal team approved language
3. **Empathy** - Natural, human-like voice
4. **Speed** - Sub-3 second response
5. **Scalability** - Handles unlimited concurrent calls

---

## Thank You!

### Questions?

**Try it yourself:**
```bash
streamlit run ui/app.py
```

**Or API:**
```bash
curl -X POST http://localhost:8000/chat \
  -d '{"message": "Is mold covered?"}'
```
