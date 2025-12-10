"""
═══════════════════════════════════════════════════════════════════════
            VERTEX AI RAG SETUP GUIDE - STEP BY STEP
═══════════════════════════════════════════════════════════════════════

Complete guide to set up and use Vertex AI with your FAISS index.
"""

SETUP_GUIDE = """
╔══════════════════════════════════════════════════════════════════════╗
║                     VERTEX AI SETUP - 3 STEPS                        ║
╚══════════════════════════════════════════════════════════════════════╝


STEP 1: GET GCP PROJECT & ENABLE VERTEX AI
═══════════════════════════════════════════════════════════════════════

1a. Create GCP Account (if needed):
   → https://console.cloud.google.com
   → Sign up with Google account
   → Get $300 free credits!

1b. Create a Project:
   → Go to: https://console.cloud.google.com/projectcreate
   → Project name: "insurance-hackathon" (or your choice)
   → Note your PROJECT ID (e.g., "insurance-hackathon-12345")

1c. Enable Vertex AI API:
   → Go to: https://console.cloud.google.com/apis/library/aiplatform.googleapis.com
   → Click "ENABLE"
   → Wait 1-2 minutes for activation


STEP 2: SET UP AUTHENTICATION
═══════════════════════════════════════════════════════════════════════

Choose ONE method:

METHOD A: gcloud CLI (Easiest for local dev)
────────────────────────────────────────────

1. Install gcloud CLI:
   Mac:    brew install google-cloud-sdk
   Windows: https://cloud.google.com/sdk/docs/install
   Linux:   curl https://sdk.cloud.google.com | bash

2. Authenticate:
   gcloud auth application-default login
   
3. Set project:
   gcloud config set project YOUR-PROJECT-ID


METHOD B: Service Account (Best for production)
────────────────────────────────────────────────

1. Create Service Account:
   → Go to: https://console.cloud.google.com/iam-admin/serviceaccounts
   → Click "CREATE SERVICE ACCOUNT"
   → Name: "vertex-ai-rag"
   → Click "CREATE AND CONTINUE"

2. Grant Roles:
   → Add role: "Vertex AI User"
   → Add role: "Storage Object Viewer" (if using GCS)
   → Click "CONTINUE" → "DONE"

3. Create Key:
   → Click on your service account
   → Go to "KEYS" tab
   → "ADD KEY" → "Create new key"
   → Choose JSON format
   → Download file (e.g., credentials.json)

4. Save to your project:
   mv ~/Downloads/credentials.json /Users/akshat/Documents/GitHub/Lyyod-Hackathon/gcp-credentials.json


STEP 3: SET ENVIRONMENT VARIABLES
═══════════════════════════════════════════════════════════════════════

For METHOD A (gcloud):
──────────────────────
export GCP_PROJECT_ID='your-project-id'

For METHOD B (Service Account):
────────────────────────────────
export GCP_PROJECT_ID='your-project-id'
export GOOGLE_APPLICATION_CREDENTIALS='/Users/akshat/Documents/GitHub/Lyyod-Hackathon/gcp-credentials.json'


Make it permanent (add to ~/.zshrc):
─────────────────────────────────────
echo "export GCP_PROJECT_ID='your-project-id'" >> ~/.zshrc
echo "export GOOGLE_APPLICATION_CREDENTIALS='$(pwd)/gcp-credentials.json'" >> ~/.zshrc
source ~/.zshrc


╔══════════════════════════════════════════════════════════════════════╗
║                          USAGE                                       ║
╚══════════════════════════════════════════════════════════════════════╝

OPTION 1: Run the demo script
──────────────────────────────
python Akshat/vertex_ai_rag.py


OPTION 2: Use in your code
───────────────────────────
from Akshat.vertex_ai_rag import VertexAIRAG
from Akshat.hybrid_faiss_bm25_search import HybridSearch

# Initialize
rag = VertexAIRAG(
    project_id='your-project-id',
    location='us-central1',
    model_name='gemini-1.5-flash'
)

# Load FAISS index
search_engine = HybridSearch()
rag.load_search_index(search_engine, 'faiss_index_hybrid')

# Ask questions
result = rag.ask("What is covered for water damage?")
print(result['answer'])

# Or start interactive chat
rag.chat()


╔══════════════════════════════════════════════════════════════════════╗
║                   MODEL OPTIONS & PRICING                            ║
╚══════════════════════════════════════════════════════════════════════╝

Gemini 1.5 Flash (RECOMMENDED for hackathons):
───────────────────────────────────────────────
- Speed: Very fast
- Cost: $0.000125 per 1K characters
- Context: Up to 1M tokens
- Best for: Real-time chat, cost-sensitive apps
- Per query: ~$0.0005

Gemini 1.5 Pro (Best quality):
───────────────────────────────
- Speed: Fast
- Cost: $0.00125 per 1K characters (10x more)
- Context: Up to 2M tokens
- Best for: Complex reasoning, important queries
- Per query: ~$0.005

Change model in code:
─────────────────────
rag = VertexAIRAG(
    project_id='your-project-id',
    model_name='gemini-1.5-pro'  # or 'gemini-1.5-flash'
)


╔══════════════════════════════════════════════════════════════════════╗
║                     TROUBLESHOOTING                                  ║
╚══════════════════════════════════════════════════════════════════════╝

ERROR: "Project not found"
──────────────────────────
→ Check GCP_PROJECT_ID is correct
→ Make sure project exists in GCP Console

ERROR: "Permission denied"
──────────────────────────
→ Enable Vertex AI API (Step 1c)
→ Check service account has "Vertex AI User" role
→ Re-run: gcloud auth application-default login

ERROR: "Quota exceeded"
───────────────────────
→ Free tier has limits
→ Upgrade to paid account (you have $300 credits)

ERROR: "Invalid credentials"
────────────────────────────
→ Check GOOGLE_APPLICATION_CREDENTIALS path
→ Make sure JSON file exists
→ Re-download credentials if needed


╔══════════════════════════════════════════════════════════════════════╗
║                     QUICK COMPARISON                                 ║
╚══════════════════════════════════════════════════════════════════════╝

                OpenAI          Vertex AI (Gemini)
────────────────────────────────────────────────────────────────────
Setup Time      2 minutes       15-30 minutes
Quality         Excellent       Excellent
Speed           Fast            Fast
Cost/query      $0.001          $0.0005 (cheaper!)
Context window  128K tokens     1M tokens (8x larger!)
Free credits    $5 trial        $300 (amazing!)
Best for        Quick start     Production, GCP users


╔══════════════════════════════════════════════════════════════════════╗
║                        NEXT STEPS                                    ║
╚══════════════════════════════════════════════════════════════════════╝

1. ✅ Complete STEP 1-3 above
2. ✅ Run: python Akshat/vertex_ai_rag.py
3. ✅ Test with demo queries
4. ✅ Start interactive chat
5. ✅ Integrate into your app


═══════════════════════════════════════════════════════════════════════
                  YOU NOW HAVE 2 RAG OPTIONS!
═══════════════════════════════════════════════════════════════════════

Files Created:
├── openai_faiss_search.py    (OpenAI embeddings only)
├── vertex_ai_rag.py           (Complete RAG with Gemini)
└── VERTEX_AI_SETUP_GUIDE.py  (This guide)

Choose based on your needs:
• Quick hackathon demo → OpenAI
• Production with GCP → Vertex AI
• Maximum context (1M tokens) → Vertex AI
• Cheapest option → Vertex AI ($300 free credits!)

═══════════════════════════════════════════════════════════════════════
"""

if __name__ == "__main__":
    print(SETUP_GUIDE)
