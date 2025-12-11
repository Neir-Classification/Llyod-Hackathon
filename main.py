import logging
import os
import json
import time
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile, Depends, status
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
from pydantic import BaseModel
from jose import JWTError, jwt
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

# Database imports
from database import get_db, User, Policy, Ticket, CallSummary

# RAG imports
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_core.documents import Document

# Safety & Explainability imports
from ai_safety import get_safety_guard, SafetyFlag, ContentModerator
from explainability import (
    get_explainability_engine, 
    CitationFormatter,
    ExplainableResponse
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


app = FastAPI(title="Speech-Text Bridge", version="0.1.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Load environment variables from a local .env file if present (for local dev convenience).
load_dotenv(BASE_DIR / ".env")

# RAG Configuration
PRAJAS_NIER_DIR = BASE_DIR / "Prajas-Nier"
DATASET_DIR = PRAJAS_NIER_DIR / "Dataset"
PDF_PATHS = [DATASET_DIR / "policy-booklet.pdf", DATASET_DIR / "policy-limits.pdf"]
FAISS_DIR = PRAJAS_NIER_DIR / "artifacts" / "faiss_index"

TONE_PROMPTS = {
    "angry": """You are a DEEPLY EMPATHETIC insurance assistant dealing with a FRUSTRATED customer. 
    
CRITICAL INSTRUCTIONS FOR ANGRY/FRUSTRATED USERS:
- START your response by explicitly acknowledging their frustration: "I completely understand your frustration" or "I hear how upset you are, and that's absolutely valid"
- Use calming, validating language throughout: "That must be really difficult," "You have every right to feel this way," "I'm genuinely sorry this happened"
- Speak in a slower, more measured tone - avoid rushing
- Express GENUINE EMPATHY before any policy information: "Let me help make this right" or "I'm here to support you through this"
- Be apologetic and take ownership where appropriate: "I apologize for this situation"
- Use phrases like "Let's work together to fix this" to show partnership
- NEVER sound defensive or dismissive - stay calm, patient, and understanding
- End with reassurance: "I'm going to help you resolve this" or "We'll get through this together"
    
Your goal: DE-ESCALATE by showing you TRULY care about their situation.""",
    
    "confused": """You are an EXCEPTIONALLY PATIENT insurance assistant helping someone who is CONFUSED.
    
CRITICAL INSTRUCTIONS FOR CONFUSED USERS:
- START with reassurance: "That's a great question - insurance can be confusing, so let me break this down simply"
- Use the SIMPLEST possible language - imagine explaining to a friend who knows nothing about insurance
- Break information into SMALL, DIGESTIBLE STEPS: "First... then... finally..."
- Use real-world analogies and examples: "Think of it like..." or "For example..."
- Avoid all jargon - if you must use a term, immediately explain it in plain English
- Speak slowly and deliberately - give them time to process
- Repeat key points in different ways to ensure understanding
- Ask if clarification is needed: "Does that make sense?" or "Would you like me to explain any part differently?"
- Be encouraging: "You're asking all the right questions" or "It's smart that you're checking this"
    
Your goal: Make complex insurance concepts CRYSTAL CLEAR and build their confidence.""",
    
    "neutral": """You are a PROFESSIONAL yet APPROACHABLE insurance assistant.
    
INSTRUCTIONS FOR NEUTRAL TONE:
- Maintain a balanced, conversational tone - friendly but not overly casual
- Provide clear, factual information with warmth
- Be thorough but concise - respect their time
- Use complete sentences with a natural flow
- Be helpful without being pushy or overly enthusiastic
- Show competence and reliability through clear communication
- Maintain professionalism while staying personable
    
Your goal: Deliver helpful information in a trustworthy, competent manner.""",
    
    "happy": """You are a WARM, ENTHUSIASTIC insurance assistant matching a HAPPY customer's positive energy!
    
CRITICAL INSTRUCTIONS FOR HAPPY USERS:
- MATCH their enthusiasm! Start with upbeat acknowledgment: "I'm so glad you reached out!" or "That's wonderful!"
- Use positive, encouraging language throughout: "Excellent question!" "You're absolutely right!" "Great news!"
- Add exclamation points naturally to show energy (but don't overdo it)
- Celebrate their proactive approach: "It's fantastic that you're thinking ahead" or "You're being really smart about this"
- Be conversational and warm - like talking to a friend
- Use phrases like "Here's the good news..." or "You'll be happy to know..."
- Keep the positive momentum going with uplifting language
- End on an encouraging note: "You're all set!" or "Feel confident about your coverage!"
    
Your goal: Keep their positive energy HIGH and make them feel GREAT about their decisions.""",
    
    "anxious": """You are a DEEPLY COMPASSIONATE and REASSURING insurance assistant helping someone who is WORRIED.
    
CRITICAL INSTRUCTIONS FOR ANXIOUS USERS:
- IMMEDIATELY provide comfort: "Don't worry, I'm here to help put your mind at ease" or "Let me help calm your concerns"
- Use soothing, reassuring language: "You're going to be okay," "Everything is going to be fine," "You're covered for this"
- Speak in a gentle, calming tone - avoid anything that could increase anxiety
- Emphasize SAFETY and PROTECTION: "Your policy protects you," "You're well-covered," "We've got you protected"
- Remove uncertainty with clear, definitive statements: "You ARE covered" not "You should be covered"
- Address worries directly and compassionately: "I understand this is stressful, but here's what will happen..."
- Use phrases like "Rest assured," "You can feel confident," "There's nothing to worry about"
- Provide specific, concrete information to reduce uncertainty
- End with strong reassurance: "You're in good hands" or "Everything is taken care of"
    
Your goal: CALM their anxiety and make them feel SECURE and PROTECTED.""",
    
    "distressed": """You are an EXTREMELY EMPATHETIC and SUPPORTIVE insurance assistant helping someone in DISTRESS or facing a DIFFICULT SITUATION.
    
CRITICAL INSTRUCTIONS FOR DISTRESSED USERS:
- Lead with DEEP COMPASSION: "I'm so sorry you're going through this" or "I can only imagine how difficult this must be for you"
- Use the most caring, gentle language possible: "I'm here for you," "You're not alone in this," "We're going to help you through this"
- Prioritize EMOTIONAL SUPPORT over information - they need to feel heard and supported first
- Speak very gently and slowly - give them space and time
- Validate their feelings extensively: "Anyone would feel overwhelmed," "It's completely understandable to feel this way"
- Express genuine care: "Please know that I truly care about helping you," "Your well-being matters"
- Focus on how the policy can HELP and SUPPORT them during this difficult time
- Use phrases like "I'm here to support you every step of the way" or "Let me help lighten this burden"
- Be patient if they're emotional or having trouble explaining
- Offer hope and support: "We're going to get through this together" or "Help is available"
- End with compassionate reassurance: "You're going to be okay" or "I'm here whenever you need support"
    
Your goal: Provide MAXIMUM EMOTIONAL SUPPORT and show DEEP HUMAN COMPASSION.""",
    
    "urgent": """You are a RESPONSIVE and EFFICIENT insurance assistant handling an URGENT situation.
    
CRITICAL INSTRUCTIONS FOR URGENT SITUATIONS:
- Acknowledge the urgency IMMEDIATELY: "I understand this is urgent - let me help you right away" or "I've got you, let's handle this quickly"
- Be DIRECT and ACTION-ORIENTED - cut out unnecessary words
- Prioritize the MOST IMPORTANT information first - what they need to know NOW
- Use clear, decisive language: "Here's what you need to do immediately..."
- Break down next steps in order of priority: "First, do this. Then, this. Finally, this."
- Maintain calm efficiency - show you're taking this seriously but not panicking
- Give specific timeframes: "This will be resolved within 24 hours" or "You'll hear back in 2 hours"
- Provide immediate action items: "Right now, you should..." or "Your next step is..."
- Include emergency contacts or resources if relevant
- Show you care while being efficient: "I understand time is critical here"
- End with clear next steps and timeline: "You're all set - expect [X] by [time]"
    
Your goal: Provide FAST, CLEAR, ACTIONABLE information while showing you take their urgency seriously."""
}

# Global vector store (cached)
_vector_store = None

# JWT Configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

security = HTTPBearer()


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token."""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Get current user from JWT token."""
    token = credentials.credentials
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id_str: str = payload.get("sub")
        if user_id_str is None:
            logger.error("JWT payload missing 'sub' field")
            raise credentials_exception
        user_id = int(user_id_str)
    except JWTError as e:
        logger.error(f"JWT decode error: {e}")
        raise credentials_exception
    except Exception as e:
        logger.error(f"Unexpected error in get_current_user: {e}")
        raise credentials_exception
    
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        logger.error(f"User not found for id: {user_id}")
        raise credentials_exception
    if not user.is_active:
        logger.error(f"User {user_id} is not active")
        raise credentials_exception
    return user


def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """Get current user if authenticated, otherwise None."""
    if credentials is None:
        return None
    try:
        return get_current_user(credentials, db)
    except HTTPException:
        return None


def detect_empathy_and_tone(user_query: str, conversation_history: list = None) -> str:
    """Detect the emotional tone and empathy needs from user's query using LLM."""
    try:
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3)
        
        history_context = ""
        if conversation_history:
            history_context = "\n\nConversation context:\n"
            for msg in conversation_history[-3:]:  # Last 3 messages for context
                role = "User" if msg.get("role") == "user" else "Assistant"
                history_context += f"{role}: {msg.get('content', '')}\n"
        
        prompt = f"""Analyze the emotional tone and empathy needs of this user's message. Consider both the content and any conversation history.

User message: "{user_query}"{history_context}

Classify into ONE of these categories:
- "distressed": User is going through a difficult situation (accident, loss, emergency, personal crisis, grief)
- "anxious": User is worried, stressed, or uncertain about coverage or situations
- "angry": User is frustrated, upset, or expressing dissatisfaction
- "confused": User is unclear, asking for clarification, or finding things complicated
- "urgent": User needs immediate help or has time-sensitive concerns
- "happy": User is satisfied, positive, or expressing gratitude
- "neutral": Standard informational question, no strong emotional content

IMPORTANT: Be sensitive to context. Even simple questions might hide deeper concerns if they relate to accidents, health issues, losses, or stressful life events.

Respond with ONLY ONE WORD - the category name."""
        
        response = llm.invoke([{"role": "user", "content": prompt}])
        detected_tone = response.content.strip().lower()
        
        # Validate tone is in our supported list
        valid_tones = ["distressed", "anxious", "angry", "confused", "urgent", "happy", "neutral"]
        if detected_tone not in valid_tones:
            logger.warning(f"Detected tone '{detected_tone}' not in valid list, defaulting to neutral")
            detected_tone = "neutral"
        
        logger.info(f"[EMPATHY] Detected tone: {detected_tone} for query: '{user_query[:50]}...'")
        return detected_tone
        
    except Exception as e:
        logger.error(f"[EMPATHY] Failed to detect tone: {e}")
        return "neutral"


def detect_ticket_intent(user_query: str, conversation_history: list = None) -> dict:
    """Detect if the user query requires creating a ticket (e.g., filing a claim, requesting service).
    Returns dict with: {'requires_ticket': bool, 'category': str, 'title': str, 'priority': str}"""
    try:
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.2)
        
        history_context = ""
        if conversation_history:
            history_context = "\n\nConversation context:\n"
            for msg in conversation_history[-3:]:
                role = "User" if msg.get("role") == "user" else "Assistant"
                history_context += f"{role}: {msg.get('content', '')}\n"
        
        prompt = f"""Analyze if this user query requires creating a support ticket in an insurance system.

User query: "{user_query}"{history_context}

A ticket should be created for:
- Filing or applying for a claim (accident, damage, loss, injury, etc.)
- Requesting policy changes or updates
- Reporting billing issues or payment problems
- Filing a formal complaint
- Requesting a service (inspection, appraisal, document request, etc.)

A ticket should NOT be created for:
- General information questions
- Questions about coverage or policy details
- Clarifications or explanations
- Status checks on existing tickets

If a ticket IS needed, respond in this EXACT JSON format:
{{"requires_ticket": true, "category": "claim|billing|policy_change|complaint|service_request", "title": "Brief descriptive title (max 50 chars)", "priority": "low|medium|high|urgent"}}

If NO ticket is needed, respond:
{{"requires_ticket": false}}

Respond with ONLY the JSON, no other text."""
        
        response = llm.invoke([{"role": "user", "content": prompt}])
        result = json.loads(response.content.strip())
        
        logger.info(f"[TICKET DETECTION] Query: '{user_query[:50]}...' -> Requires ticket: {result.get('requires_ticket', False)}")
        return result
        
    except Exception as e:
        logger.error(f"[TICKET DETECTION] Failed to detect ticket intent: {e}")
        return {"requires_ticket": False}


def create_ticket_for_user(
    user: User, 
    category: str, 
    title: str, 
    description: str, 
    priority: str,
    db: Session
) -> Ticket:
    """Create a new ticket for a user."""
    import random
    import string
    
    # Generate unique ticket number
    timestamp = datetime.utcnow().strftime("%Y%m%d")
    random_suffix = ''.join(random.choices(string.digits, k=4))
    ticket_number = f"TKT-{timestamp}-{random_suffix}"
    
    # Check if user has any policies to associate
    policy = db.query(Policy).filter(Policy.user_id == user.id).first()
    
    new_ticket = Ticket(
        user_id=user.id,
        policy_id=policy.id if policy else None,
        ticket_number=ticket_number,
        title=title[:255],  # Ensure it fits in the field
        description=description,
        category=category,
        priority=priority,
        status="open",
        created_at=datetime.utcnow()
    )
    
    db.add(new_ticket)
    db.commit()
    db.refresh(new_ticket)
    
    logger.info(f"[TICKET CREATED] {ticket_number} for user {user.email} - {title}")
    return new_ticket


def get_vector_store():
    """Get or initialize the FAISS vector store."""
    global _vector_store
    if _vector_store is not None:
        return _vector_store
    
    if FAISS_DIR.exists():
        try:
            embeddings = OpenAIEmbeddings(model="text-embedding-3-large")
            _vector_store = FAISS.load_local(str(FAISS_DIR), embeddings, allow_dangerous_deserialization=True)
            return _vector_store
        except Exception as e:
            logger.warning(f"Failed to load existing FAISS index: {e}. Rebuilding...")
    
    # Build new index if not found
    return build_vector_store()


def extract_structured_content_with_chatgpt(page_content: str, page_num: int, policy_name: str) -> str:
    """Use ChatGPT to extract and structure content from a PDF page."""
    try:
        llm = ChatOpenAI(model="gpt-4o", temperature=0.1)
        
        prompt = f"""You are an expert at extracting and structuring insurance policy information.

Analyze the following insurance policy page and extract ALL information into a well-structured, searchable format.

IMPORTANT INSTRUCTIONS:
1. Extract ALL data points including: coverage details, limits, conditions, exclusions, definitions, procedures, contact info, etc.
2. Organize information hierarchically with clear sections and subsections
3. Convert tables into structured text format with clear labels
4. Preserve all numerical values, percentages, and monetary amounts
5. Keep policy-specific terminology intact
6. Create clear relationships between related items
7. Make the output optimized for semantic search and retrieval

Format your response as structured text with:
- Clear section headers (use ### for sections, #### for subsections)
- Bullet points for lists
- Key-value pairs for specific data (e.g., "Maximum Limit: $500,000")
- Complete sentences for explanations and conditions

Policy: {policy_name}
Page: {page_num}

---PAGE CONTENT---
{page_content}
---END PAGE CONTENT---

Structured Output:"""
        
        messages = [{"role": "user", "content": prompt}]
        response = llm.invoke(messages)
        structured_text = response.content
        
        logger.info(f"[ChatGPT] Processed {policy_name} page {page_num}: {len(structured_text)} chars")
        return structured_text
        
    except Exception as e:
        logger.error(f"[ChatGPT] Failed to process page {page_num}: {e}")
        # Fallback to original content if ChatGPT fails
        return page_content


def load_pdfs_with_chatgpt(pdf_paths):
    """Load PDFs and process each page through ChatGPT for structured extraction."""
    docs = []
    for path in pdf_paths:
        if not path.exists():
            logger.warning(f"PDF not found: {path}")
            continue
        
        logger.info(f"[ChatGPT] Processing PDF: {path.name}")
        loader = PyPDFLoader(str(path))
        loaded_docs = loader.load()
        policy_name = path.name
        
        for doc in loaded_docs:
            page_num = doc.metadata.get("page", "unknown")
            
            # Process through ChatGPT for structured extraction
            structured_content = extract_structured_content_with_chatgpt(
                doc.page_content, 
                page_num, 
                policy_name
            )
            
            # Create new document with structured content
            structured_doc = Document(
                page_content=structured_content,
                metadata={
                    "policy_name": policy_name,
                    "page_number": page_num,
                    "source": str(path),
                    "processed_by": "gpt-4o"
                }
            )
            docs.append(structured_doc)
        
        logger.info(f"[ChatGPT] Completed processing {path.name}: {len([d for d in docs if d.metadata['policy_name'] == policy_name])} pages")
    
    return docs


def chunk_docs(docs, chunk_size=2000, chunk_overlap=200):
    """Split ChatGPT-structured documents into semantic chunks."""
    # Use section-aware splitting for ChatGPT-structured content
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n### ", "\n#### ", "\n\n", "\n", ". ", " ", ""]
    )
    chunks = splitter.split_documents(docs)
    for chunk in chunks:
        if "policy_name" not in chunk.metadata:
            chunk.metadata["policy_name"] = chunk.metadata.get("source", "unknown")
        if "page_number" not in chunk.metadata and "page" in chunk.metadata:
            chunk.metadata["page_number"] = chunk.metadata["page"]
    return chunks


def build_vector_store():
    """Build a new FAISS vector store from PDFs using ChatGPT processing."""
    global _vector_store
    logger.info("Building FAISS index from PDFs with ChatGPT processing...")
    
    # Use ChatGPT-based processing
    docs = load_pdfs_with_chatgpt(PDF_PATHS)
    if not docs:
        raise RuntimeError("No PDFs found to index")
    
    logger.info(f"Loaded {len(docs)} pages from PDFs")
    
    # Chunk the structured content
    chunks = chunk_docs(docs)
    logger.info(f"Created {len(chunks)} chunks from {len(docs)} pages")
    
    # Create embeddings and build FAISS index
    embeddings = OpenAIEmbeddings(model="text-embedding-3-large")
    _vector_store = FAISS.from_documents(chunks, embeddings)
    FAISS_DIR.mkdir(parents=True, exist_ok=True)
    _vector_store.save_local(str(FAISS_DIR))
    logger.info(f"FAISS index built and saved to {FAISS_DIR}")
    return _vector_store


def retrieve(query: str, vector_db: FAISS, k: int = 3):
    """Retrieve relevant chunks from the vector store (ChatGPT-structured) with scores."""
    # Use similarity search with scores for citations
    results = vector_db.similarity_search_with_score(query, k=k)
    
    # Don't truncate ChatGPT-structured content as aggressively
    for doc, score in results:
        doc.page_content = doc.page_content[:1000]
    
    return results


def get_user_context(user: User, db: Session) -> str:
    """Build a context string from the user's policies, tickets, and call history."""
    try:
        # Fetch user's policies
        policies = db.query(Policy).filter(Policy.user_id == user.id).all()
        
        # Fetch user's open tickets
        tickets = db.query(Ticket).filter(
            Ticket.user_id == user.id,
            Ticket.status.in_(['open', 'in_progress'])
        ).all()
        
        # Build context string
        context = f"\n\n=== USER CONTEXT ===\n"
        context += f"User: {user.full_name} ({user.email})\n"
        
        if policies:
            context += f"\nActive Policies ({len(policies)}):\n"
            for p in policies:
                context += f"- {p.policy_type.upper()} Insurance (Policy #{p.policy_number})\n"
                context += f"  Status: {p.status}\n"
                context += f"  Coverage: ${p.coverage_amount:,.0f}\n"
                context += f"  Deductible: ${p.deductible:,.0f}\n"
                context += f"  Premium: ${p.premium_amount:.2f}/month\n"
                context += f"  Period: {p.start_date.strftime('%Y-%m-%d')} to {p.end_date.strftime('%Y-%m-%d')}\n"
                if p.policy_details:
                    context += f"  Details: {p.policy_details}\n"
        else:
            context += "\nNo active policies found.\n"
        
        if tickets:
            context += f"\nOpen Support Tickets ({len(tickets)}):\n"
            for t in tickets:
                context += f"- Ticket #{t.ticket_number}: {t.title}\n"
                context += f"  Priority: {t.priority} | Status: {t.status}\n"
                context += f"  Description: {t.description}\n"
        else:
            context += "\nNo open support tickets.\n"
        
        context += "===================\n\n"
        context += "IMPORTANT: When the user asks about 'my policy', 'my coverage', 'my claim', or similar personal questions, use the specific information from their USER CONTEXT above. Provide personalized responses based on their actual policy details.\n\n"
        
        return context
    except Exception as e:
        logger.error(f"Error building user context: {e}")
        return ""


def adjust_tone_with_llm(retrieved_chunks, user_question: str, tone: str = "neutral", conversation_history: list = None, auto_detect_tone: bool = False, user_context: str = "") -> tuple[str, str]:
    """Use LLM to generate a tone-appropriate response from retrieved chunks with conversation context.
    Returns tuple of (response_text, detected_tone)"""
    # Auto-detect empathetic tone if requested
    detected_tone = tone
    if auto_detect_tone:
        detected_tone = detect_empathy_and_tone(user_question, conversation_history)
        logger.info(f"[EMPATHY] Using auto-detected tone: {detected_tone} (override: {tone} -> {detected_tone})")
        tone = detected_tone
    
    if tone not in TONE_PROMPTS:
        tone = "neutral"
        detected_tone = "neutral"
    
    if conversation_history is None:
        conversation_history = []
    
    # Combine retrieved chunks into context
    context = "\n\n".join([doc.page_content for doc, _ in retrieved_chunks])
    
    # Add user context if available (for personalized responses)
    if user_context:
        context = user_context + context
    
    # Build conversation history context
    history_context = ""
    if conversation_history:
        history_context = "\n\nPrevious Conversation:\n"
        for msg in conversation_history:  # Use complete conversation history
            role = "User" if msg.get("role") == "user" else "Assistant"
            history_context += f"{role}: {msg.get('content', '')}\n"
    
    system_prompt = f"""{TONE_PROMPTS[tone]}

EMPATHY & EMOTIONAL INTELLIGENCE:
- ALWAYS acknowledge the user's emotional state when appropriate
- Show genuine compassion for difficult situations (accidents, losses, health issues, financial stress)
- Use validating phrases naturally: "That sounds stressful," "I understand your concern," "I'm here to help"
- If the user is going through something difficult, express care BEFORE diving into policy details
- Balance empathy with practical help - people need both emotional support AND useful information
- Adapt your language: warm and conversational for emotional topics, clear and structured for technical questions
- Act like a caring human, not a robotic assistant

Based on the policy information below, answer the user's question in 3-4 sentences suitable for voice (20-30 seconds of speech).

**Core Instructions:**

1.  **Prioritize Knowledge Base Search:** Always attempt to answer the user's question by first searching the provided knowledge base.

2.  **Identify Key Information Needs & Keywords:** Understand what specific information the user is asking for. Extract the most relevant
    keywords and entities from their query (e.g., name, policy number, type of information).

3.  **Execute Knowledge Base Search:** Use the identified keywords to search the knowledge base. Be mindful of potential synonyms or related 
    terms if the initial search is unsuccessful.

4.  **Analyze Search Results:** Carefully review the entries returned by the search. Identify the entry that directly addresses the user's question.

5.  **Extract and Formulate Answer:** Locate the specific data point needed to answer the user's query within the relevant knowledge base entry. 
    Formulate a clear, concise, and grammatically correct answer using this information. Avoid directly copying the entire knowledge base entry.

6.  **Handle "No Match" Scenarios:** If your search yields no relevant results, inform the user politely that the information is not currently 
    available in the knowledge base. For example: "I'm sorry, but I couldn't find that information in our current knowledge base."

7.  **Seek Clarification for Ambiguity:** If the user's question is unclear or ambiguous, ask for specific details before attempting to search the 
    knowledge base. For example: "Could you please specify which \[policy type/customer name/etc.] you are referring to?"

8.  **Maintain Professional Tone:** Always maintain a helpful and professional tone while providing information to the user.

9.  **Report Knowledge Base Issues:** If you identify any outdated, incorrect, or missing information in the knowledge base, flag it for review by
     the administrator.

10. **Enhanced Data Analysis:** For questions that require calculations (e.g., total, average, sum), perform the necessary calculations using the 
    data extracted from the knowledge base. Show your work or the formulas used if appropriate for clarity.

11. **Temporal Reasoning:** When a question involves dates, extract all relevant dates from the knowledge base. Perform any necessary date 
    calculations (e.g., differences, comparisons). Be precise with date formats in your answers (e.g., YYYY-MM-DD).

12. **Table Generation:** If the question asks for a table or a summary of multiple items, organize your answer in a table format. Include 
    clear column headers, and align the data appropriately. Sort the table as requested. If no sort order is specified, use a logical order 
    (e.g., alphabetical, numerical).

13. **Multi-Step Reasoning:** Break down complex questions into smaller, manageable steps. Extract the information needed for each step from 
    the knowledge base. Use the results of one step to inform the next. Maintain context throughout the process.

14. **Context Maintenance:** Pay attention to the context of the conversation. If a user refers to a previous query, try to use the information 
    you already provided. Avoid repeating information unless necessary for clarity.

**Example Workflow:**

\* **User Question:** "What is John Smith's life insurance policy number?"

\* **Identify Keywords:** "John Smith", "life insurance", "policy number"

\* **Search Knowledge Base:** Search for entries containing these keywords.

\* **Relevant Entry Found:** (The John Smith entry we discussed earlier)

\* **Extract Answer:** Locate the value for the "policy\_number" field ("LIFE-001").

\* **Formulate Response:** "John Smith's life insurance policy number is LIFE-001."

**Remember:** Your goal is to efficiently and accurately retrieve information from the knowledge base to answer user inquiries, 
perform calculations, handle dates, generate tables, and maintain context when necessary.

Policy Context:
{context}{history_context}"""

    user_prompt = f"User question: {user_question}"
    
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3)
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    
    response = llm.invoke(messages)
    return response.content, detected_tone


def get_openai_client() -> OpenAI:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("Set the OPENAI_API_KEY environment variable.")
    return OpenAI(api_key=api_key)


class SpeechRequest(BaseModel):
    text: str
    voice: Optional[str] = "alloy"
    audio_format: Optional[str] = "mp3"


class ChatMessage(BaseModel):
    role: str  # 'user' or 'assistant'
    content: str


class RAGQueryRequest(BaseModel):
    query: str
    tone: Optional[str] = "neutral"
    k: Optional[int] = 2
    conversation_history: Optional[list[ChatMessage]] = []
    auto_detect_empathy: Optional[bool] = True  # Auto-detect emotional tone by default
    include_explainability: Optional[bool] = True  # New: Include explainability metadata
    enable_safety_checks: Optional[bool] = True    # New: Enable safety guardrails


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.get("/ai/model-card")
async def get_model_card() -> JSONResponse:
    """
    Returns the AI Model Card with transparency information about the system.
    This endpoint provides information about the AI system's capabilities,
    limitations, intended use, and ethical considerations.
    """
    model_card = {
        "model_name": "Insurance Policy RAG Assistant",
        "version": "1.0.0",
        "description": "An AI-powered assistant for answering questions about insurance policies using Retrieval-Augmented Generation (RAG).",
        
        "intended_use": {
            "primary_use_cases": [
                "Answering questions about insurance policy coverage",
                "Explaining policy terms and conditions",
                "Providing information about claims procedures",
                "Clarifying policy limits and exclusions"
            ],
            "intended_users": [
                "Insurance policyholders",
                "Customer service representatives",
                "Insurance agents"
            ],
            "out_of_scope_uses": [
                "Providing financial investment advice",
                "Giving legal counsel",
                "Making medical recommendations",
                "Processing actual insurance claims"
            ]
        },
        
        "technical_specifications": {
            "base_models": {
                "language_model": "GPT-4o-mini",
                "embedding_model": "text-embedding-3-large",
                "speech_to_text": "Whisper-1",
                "text_to_speech": "GPT-4o-mini-TTS"
            },
            "retrieval_system": {
                "type": "FAISS Vector Store",
                "similarity_metric": "L2 Distance",
                "chunk_size": 2000,
                "chunk_overlap": 200
            }
        },
        
        "performance_characteristics": {
            "response_latency": "Typically 2-5 seconds",
            "context_window": "Supports conversation history",
            "retrieval_accuracy": "Dependent on query specificity and knowledge base coverage"
        },
        
        "limitations": [
            "Responses are limited to information contained in the indexed policy documents",
            "May not have the most recent policy updates if index is not refreshed",
            "Cannot access external systems or real-time policy data",
            "Complex queries may receive generalized responses",
            "Tone detection may not be 100% accurate for all emotional states"
        ],
        
        "ethical_considerations": {
            "bias_mitigation": "Responses are grounded in policy documents to minimize bias",
            "transparency": "All responses include source citations and confidence scores",
            "privacy": "PII detection and redaction is enabled by default",
            "accountability": "All AI interactions are logged for audit purposes"
        },
        
        "safety_measures": [
            "Input sanitization and PII redaction",
            "Output validation and grounding checks",
            "Confidence scoring to flag uncertain responses",
            "Automatic disclaimer insertion for sensitive topics",
            "Scope validation to prevent off-topic responses"
        ],
        
        "data_sources": {
            "knowledge_base": "Insurance policy documents (PDF)",
            "update_frequency": "On-demand index rebuild",
            "data_retention": "Session-based, no long-term storage of queries"
        },
        
        "contact": {
            "maintainer": "Insurance AI Team",
            "feedback_channel": "Contact support for feedback or concerns"
        }
    }
    
    return JSONResponse(model_card)


@app.get("/ai/safety-audit")
async def get_safety_audit() -> JSONResponse:
    """
    Returns the safety audit log for compliance and monitoring.
    This endpoint provides a log of all safety checks performed.
    """
    safety_guard = get_safety_guard()
    audit_log = safety_guard.get_audit_log()
    
    return JSONResponse({
        "audit_log": audit_log[-100],  # Last 100 entries
        "total_entries": len(audit_log),
        "safety_summary": {
            "total_checks": len(audit_log),
            "pii_detections": sum(1 for entry in audit_log if "pii_detected" in entry.get("flags", [])),
            "low_confidence_responses": sum(1 for entry in audit_log if "low_confidence" in entry.get("flags", [])),
            "scope_violations": sum(1 for entry in audit_log if "out_of_scope" in entry.get("flags", []))
        }
    })


@app.post("/speech-to-text")
async def speech_to_text(audio_file: UploadFile = File(...), language: Optional[str] = None) -> JSONResponse:
    client = get_openai_client()

    audio_bytes = await audio_file.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Empty audio payload")

    try:
        transcript = client.audio.transcriptions.create(
            model="whisper-1",
            file=(audio_file.filename or "audio.wav", audio_bytes, audio_file.content_type or "audio/wav"),
            language=language,
        )
        logger.info(f"[SPEECH-TO-TEXT] Transcribed: '{transcript.text}'")
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Transcription failed: {exc}") from exc

    return JSONResponse({"text": transcript.text})


@app.post("/speech-to-text-chunk")
async def speech_to_text_chunk(
    audio_chunk: UploadFile = File(...),
    language: Optional[str] = None,
    mime_type: Optional[str] = Form(None),
) -> JSONResponse:
    client = get_openai_client()

    chunk_bytes = await audio_chunk.read()
    if not chunk_bytes:
        raise HTTPException(status_code=400, detail="Empty audio payload")

    supported = {
        "audio/webm": "webm",
        "audio/ogg": "ogg",
        "audio/mp3": "mp3",
        "audio/mpeg": "mp3",
        "audio/wav": "wav",
        "audio/x-wav": "wav",
        "audio/mp4": "mp4",
        "audio/m4a": "m4a",
        "video/webm": "webm",
    }

    def pick_mime() -> str:
        for candidate in [mime_type, audio_chunk.content_type, "audio/webm"]:
            if not candidate:
                continue
            base = candidate.split(";")[0].strip().lower()
            if base in supported:
                return base
        return "audio/webm"

    mime = pick_mime()
    ext = supported[mime]

    filename = audio_chunk.filename or f"chunk.{ext}"
    content_type = mime

    logger.info(f"[chunk] filename={filename}, content_type={content_type}, size={len(chunk_bytes)}, provided_mime_type={mime_type}, upload_content_type={audio_chunk.content_type}")

    try:
        transcript = client.audio.transcriptions.create(
            model="whisper-1",
            file=(filename, chunk_bytes, content_type),
            language=language,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Transcription failed")
        raise HTTPException(status_code=502, detail=f"Transcription failed: {exc}") from exc

    return JSONResponse({"text": transcript.text})


@app.post("/text-to-speech")
async def text_to_speech(body: SpeechRequest) -> StreamingResponse:
    client = get_openai_client()

    if not body.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")

    response_format = body.audio_format or "mp3"

    try:
        stream = client.audio.speech.with_streaming_response.create(
            model="gpt-4o-mini-tts",
            voice=body.voice or "alloy",
            input=body.text,
            response_format=response_format,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"TTS failed: {exc}") from exc

    def iter_audio():
        # Stream audio bytes so large responses do not exhaust memory.
        with stream as response:
            for chunk in response.iter_bytes():
                yield chunk

    media_type = "audio/mpeg" if response_format == "mp3" else f"audio/{response_format}"
    headers = {"Content-Disposition": "inline; filename=tts-output." + response_format}
    return StreamingResponse(iter_audio(), media_type=media_type, headers=headers)


@app.get("/")
async def root():
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path)

    return {
        "message": "Speech/Text service ready",
        "routes": ["GET /health", "POST /speech-to-text", "POST /text-to-speech"],
    }


@app.post("/rag-query")
async def rag_query(
    body: RAGQueryRequest, 
    current_user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db)
) -> JSONResponse:
    """Query the RAG pipeline and return a tone-adjusted response with conversation history."""
    start_time = time.time()
    
    try:
        if not body.query.strip():
            raise HTTPException(status_code=400, detail="Query cannot be empty")
        
        logger.info(f"[RAG QUERY INPUT] Query: '{body.query}' | Tone: '{body.tone}' | K: {body.k} | History: {len(body.conversation_history or [])} | User: {current_user.email if current_user else 'Guest'}")
        
        # Initialize safety and explainability components
        safety_guard = get_safety_guard()
        explainability_engine = get_explainability_engine()
        
        # ===== SAFETY: Input Validation =====
        safety_warnings = []
        safety_flags = []
        
        if body.enable_safety_checks:
            input_safety = safety_guard.check_input(body.query)
            if input_safety.warnings:
                safety_warnings.extend(input_safety.warnings)
            if input_safety.flags:
                safety_flags.extend([f.value for f in input_safety.flags])
            
            # Sanitize input (redact PII)
            sanitized_query = safety_guard.sanitize_input(body.query)
        else:
            sanitized_query = body.query
        
        # Get or build the vector store
        vector_db = get_vector_store()
        
        # Retrieve relevant chunks
        results = retrieve(sanitized_query, vector_db, k=body.k)
        
        # Convert conversation history to dict format
        history = [{"role": msg.role, "content": msg.content} for msg in (body.conversation_history or [])]
        
        # Build user context if user is authenticated
        user_context = ""
        if current_user:
            user_context = get_user_context(current_user, db)
            logger.info(f"[USER CONTEXT] Built context for {current_user.email}")
        
        # Generate tone-adjusted response with conversation context and empathy detection
        response_text, detected_emotion = adjust_tone_with_llm(
            results, 
            sanitized_query, 
            body.tone, 
            history, 
            auto_detect_tone=body.auto_detect_empathy,
            user_context=user_context
        )
        
        # ===== TICKET DETECTION & CREATION =====
        ticket_created = None
        if current_user:  # Only create tickets for authenticated users
            ticket_intent = detect_ticket_intent(body.query, history)
            if ticket_intent.get("requires_ticket", False):
                try:
                    new_ticket = create_ticket_for_user(
                        user=current_user,
                        category=ticket_intent.get("category", "service_request"),
                        title=ticket_intent.get("title", body.query[:50]),
                        description=f"User query: {body.query}\n\nDetected intent: {ticket_intent.get('category')}\n\nContext: Auto-generated from conversation.",
                        priority=ticket_intent.get("priority", "medium"),
                        db=db
                    )
                    ticket_created = {
                        "ticket_number": new_ticket.ticket_number,
                        "title": new_ticket.title,
                        "category": new_ticket.category,
                        "priority": new_ticket.priority,
                        "status": new_ticket.status
                    }
                    
                    # Add ticket info to response
                    ticket_message = f"\n\n✓ I've created ticket {new_ticket.ticket_number} to handle your {new_ticket.category} request. Our team will process this and get back to you soon."
                    response_text += ticket_message
                    
                    logger.info(f"[TICKET AUTO-CREATED] {new_ticket.ticket_number} for user {current_user.email}")
                except Exception as e:
                    logger.error(f"[TICKET CREATION ERROR] Failed to create ticket: {e}")
        
        # ===== SAFETY: Output Validation =====
        disclaimers = []
        if body.enable_safety_checks:
            output_safety = safety_guard.check_output(response_text, sanitized_query, results)
            if output_safety.warnings:
                safety_warnings.extend(output_safety.warnings)
            if output_safety.flags:
                safety_flags.extend([f.value for f in output_safety.flags])
            if output_safety.recommendations:
                disclaimers.extend(output_safety.recommendations)
            
            # Sanitize output
            response_text = safety_guard.sanitize_output(response_text)
            
            # Add disclaimers if needed
            disclaimer_types = ContentModerator.needs_disclaimer(response_text)
            if disclaimer_types:
                response_text = ContentModerator.add_disclaimers(response_text, disclaimer_types)
        
        # Calculate processing time
        processing_time_ms = (time.time() - start_time) * 1000
        
        # ===== EXPLAINABILITY: Generate Explainable Response =====
        if body.include_explainability:
            explainable_response = explainability_engine.generate_explainable_response(
                response_text=response_text,
                query=body.query,
                retrieved_chunks=results,
                model_used="gpt-4o-mini",
                processing_time_ms=processing_time_ms,
                safety_flags=safety_flags,
                disclaimers=disclaimers
            )
            
            # Format citations - ensure all floats are native Python floats for JSON serialization
            citations = []
            for source in explainable_response.sources:
                citations.append({
                    "policy_name": source.policy_name,
                    "page_number": int(source.page_number) if isinstance(source.page_number, (int, float)) else source.page_number,
                    "section": source.section,
                    "content": source.quote,
                    "relevance_score": float(source.relevance_score)
                })
            
            response_data = {
                "response": response_text,
                "tone": body.tone,
                "query": body.query,
                "citations": citations,
                "detected_emotion": detected_emotion,
                "ticket_created": ticket_created,
                "explainability": {
                    "confidence": {
                        "score": float(round(explainable_response.confidence_score, 3)),
                        "level": explainable_response._confidence_level(),
                        "explanation": explainable_response._confidence_explanation()
                    },
                    "reasoning": {
                        "type": explainable_response.reasoning_type.value,
                        "explanation": explainable_response.reasoning_explanation
                    },
                    "sources_count": len(citations),
                    "limitations": explainable_response.limitations,
                    "processing_time_ms": float(round(processing_time_ms, 2))
                },
                "safety": {
                    "flags": list(set(safety_flags)),
                    "warnings": safety_warnings,
                    "disclaimers": disclaimers,
                    "input_sanitized": sanitized_query != body.query
                }
            }
        else:
            # Legacy format without explainability
            citations = []
            for doc, score in results:
                citations.append({
                    "policy_name": doc.metadata.get("policy_name", "unknown"),
                    "page_number": doc.metadata.get("page_number", "N/A"),
                    "content": doc.page_content[:300],
                    "score": float(score)
                })
            
            response_data = {
                "response": response_text,
                "tone": body.tone,
                "query": body.query,
                "citations": citations,
                "detected_emotion": detected_emotion,
                "ticket_created": ticket_created
            }
        
        logger.info(f"[RAG QUERY OUTPUT] Response length: {len(response_text)} | Citations: {len(citations)} | Emotion: {detected_emotion} | Ticket: {ticket_created['ticket_number'] if ticket_created else 'None'} | Confidence: {explainable_response.confidence_score if body.include_explainability else 'N/A'}")
        
        return JSONResponse(response_data)
    except Exception as exc:
        logger.exception("RAG query failed")
        raise HTTPException(status_code=502, detail=f"RAG query failed: {exc}") from exc


@app.post("/rag-audio-query")
async def rag_audio_query(
    audio_file: UploadFile = File(...),
    tone: Optional[str] = Form("neutral"),
    k: Optional[int] = Form(2),
    voice: Optional[str] = Form("alloy"),
    language: Optional[str] = Form(None),
    current_user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db)
) -> StreamingResponse:
    """
    Complete audio-to-audio RAG pipeline:
    1. Speech-to-text: Convert audio input to text
    2. RAG: Query the knowledge base
    3. Text-to-speech: Convert response back to audio
    """
    client = get_openai_client()
    
    # Step 1: Speech-to-Text
    audio_bytes = await audio_file.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Empty audio payload")
    
    try:
        transcript = client.audio.transcriptions.create(
            model="whisper-1",
            file=(audio_file.filename or "audio.wav", audio_bytes, audio_file.content_type or "audio/wav"),
            language=language,
        )
        user_query = transcript.text
        logger.info(f"[RAG-AUDIO] Transcribed query: '{user_query}' | User: {current_user.email if current_user else 'Guest'}")
    except Exception as exc:
        logger.exception("Transcription failed in RAG audio query")
        raise HTTPException(status_code=502, detail=f"Transcription failed: {exc}") from exc
    
    # Step 2: RAG Query
    try:
        if not user_query.strip():
            raise HTTPException(status_code=400, detail="Transcribed query is empty")
        
        vector_db = get_vector_store()
        results = retrieve(user_query, vector_db, k=k)
        
        # Build user context if user is authenticated
        user_context = ""
        if current_user:
            user_context = get_user_context(current_user, db)
            logger.info(f"[USER CONTEXT] Built context for {current_user.email} in audio query")
        
        # Use empathy detection for audio queries
        response_text, detected_emotion = adjust_tone_with_llm(results, user_query, tone, auto_detect_tone=True, user_context=user_context)
        
        logger.info(f"[RAG-AUDIO] Generated response: '{response_text}' | Emotion: {detected_emotion}")
    except Exception as exc:
        logger.exception("RAG query failed in audio pipeline")
        raise HTTPException(status_code=502, detail=f"RAG query failed: {exc}") from exc
    
    # Step 3: Text-to-Speech
    try:
        stream = client.audio.speech.with_streaming_response.create(
            model="gpt-4o-mini-tts",
            voice=voice or "alloy",
            input=response_text,
            response_format="mp3",
        )
    except Exception as exc:
        logger.exception("TTS failed in RAG audio query")
        raise HTTPException(status_code=502, detail=f"TTS failed: {exc}") from exc
    
    def iter_audio():
        with stream as response:
            for chunk in response.iter_bytes():
                yield chunk
    
    headers = {
        "Content-Disposition": "inline; filename=rag-response.mp3",
        "X-Transcribed-Query": user_query,
        "X-Response-Text": response_text[:200]  # Truncated for header size limits
    }
    return StreamingResponse(iter_audio(), media_type="audio/mpeg", headers=headers)


@app.post("/rag-audio-query-chunk")
async def rag_audio_query_chunk(
    audio_chunk: UploadFile = File(...),
    tone: Optional[str] = Form("neutral"),
    k: Optional[int] = Form(2),
    voice: Optional[str] = Form("alloy"),
    language: Optional[str] = Form(None),
    mime_type: Optional[str] = Form(None),
    current_user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db)
) -> StreamingResponse:
    """
    Audio chunk-based RAG pipeline (for streaming/real-time scenarios):
    1. Speech-to-text: Convert audio chunk to text
    2. RAG: Query the knowledge base
    3. Text-to-speech: Convert response back to audio
    """
    client = get_openai_client()
    
    # Step 1: Speech-to-Text (Chunk)
    chunk_bytes = await audio_chunk.read()
    if not chunk_bytes:
        raise HTTPException(status_code=400, detail="Empty audio payload")
    
    supported = {
        "audio/webm": "webm",
        "audio/ogg": "ogg",
        "audio/mp3": "mp3",
        "audio/mpeg": "mp3",
        "audio/wav": "wav",
        "audio/x-wav": "wav",
        "audio/mp4": "mp4",
        "audio/m4a": "m4a",
        "video/webm": "webm",
    }
    
    def pick_mime() -> str:
        for candidate in [mime_type, audio_chunk.content_type, "audio/webm"]:
            if not candidate:
                continue
            base = candidate.split(";")[0].strip().lower()
            if base in supported:
                return base
        return "audio/webm"
    
    mime = pick_mime()
    ext = supported[mime]
    filename = audio_chunk.filename or f"chunk.{ext}"
    content_type = mime
    
    logger.info(f"[RAG-AUDIO-CHUNK] Processing: filename={filename}, size={len(chunk_bytes)}")
    
    try:
        transcript = client.audio.transcriptions.create(
            model="whisper-1",
            file=(filename, chunk_bytes, content_type),
            language=language,
        )
        user_query = transcript.text
        logger.info(f"[RAG-AUDIO-CHUNK] Transcribed query: '{user_query}' | User: {current_user.email if current_user else 'Guest'}")
    except Exception as exc:
        logger.exception("Transcription failed in RAG audio chunk query")
        raise HTTPException(status_code=502, detail=f"Transcription failed: {exc}") from exc
    
    # Step 2: RAG Query
    try:
        if not user_query.strip():
            raise HTTPException(status_code=400, detail="Transcribed query is empty")
        
        vector_db = get_vector_store()
        results = retrieve(user_query, vector_db, k=k)
        
        # Build user context if user is authenticated
        user_context = ""
        if current_user:
            user_context = get_user_context(current_user, db)
            logger.info(f"[USER CONTEXT] Built context for {current_user.email} in audio chunk query")
        
        # Use empathy detection for audio queries
        response_text, detected_emotion = adjust_tone_with_llm(results, user_query, tone, auto_detect_tone=True, user_context=user_context)
        
        logger.info(f"[RAG-AUDIO-CHUNK] Generated response: '{response_text}' | Emotion: {detected_emotion}")
    except Exception as exc:
        logger.exception("RAG query failed in audio chunk pipeline")
        raise HTTPException(status_code=502, detail=f"RAG query failed: {exc}") from exc
    
    # Step 3: Text-to-Speech
    try:
        stream = client.audio.speech.with_streaming_response.create(
            model="gpt-4o-mini-tts",
            voice=voice or "alloy",
            input=response_text,
            response_format="mp3",
        )
    except Exception as exc:
        logger.exception("TTS failed in RAG audio chunk query")
        raise HTTPException(status_code=502, detail=f"TTS failed: {exc}") from exc
    
    def iter_audio():
        with stream as response:
            for chunk in response.iter_bytes():
                yield chunk
    
    headers = {
        "Content-Disposition": "inline; filename=rag-response.mp3",
        "X-Transcribed-Query": user_query,
        "X-Response-Text": response_text[:200]  # Truncated for header size limits
    }
    return StreamingResponse(iter_audio(), media_type="audio/mpeg", headers=headers)


# ============================================================================
# Authentication Endpoints
# ============================================================================

class UserRegister(BaseModel):
    email: str
    username: str
    password: str
    full_name: str
    phone: Optional[str] = None


class UserLogin(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: dict


class UserResponse(BaseModel):
    id: int
    email: str
    username: str
    full_name: str
    phone: Optional[str]
    is_admin: bool
    is_active: bool
    
    class Config:
        from_attributes = True


@app.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register_user(user_data: UserRegister, db: Session = Depends(get_db)):
    """Register a new user."""
    # Check if user already exists
    existing_user = db.query(User).filter(
        (User.email == user_data.email) | (User.username == user_data.username)
    ).first()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email or username already exists"
        )
    
    # Create new user
    new_user = User(
        email=user_data.email,
        username=user_data.username,
        hashed_password=User.hash_password(user_data.password),
        full_name=user_data.full_name,
        phone=user_data.phone,
        is_active=True,
        is_admin=False
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Create access token
    access_token = create_access_token(data={"sub": str(new_user.id)})
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user={
            "id": new_user.id,
            "email": new_user.email,
            "username": new_user.username,
            "full_name": new_user.full_name,
            "is_admin": new_user.is_admin
        }
    )


@app.post("/login", response_model=TokenResponse)
def login_user(credentials: UserLogin, db: Session = Depends(get_db)):
    """Login user and return JWT token."""
    user = db.query(User).filter(User.email == credentials.email).first()
    
    if not user or not user.verify_password(credentials.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    # Create access token
    access_token = create_access_token(data={"sub": str(user.id)})
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user={
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "full_name": user.full_name,
            "is_admin": user.is_admin
        }
    )


@app.get("/me", response_model=UserResponse)
def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current authenticated user info."""
    return current_user


@app.get("/me/policies")
def get_user_policies(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get all policies for current user."""
    policies = db.query(Policy).filter(Policy.user_id == current_user.id).all()
    return {"policies": [
        {
            "id": p.id,
            "policy_number": p.policy_number,
            "policy_type": p.policy_type,
            "status": p.status,
            "premium_amount": p.premium_amount,
            "coverage_amount": p.coverage_amount,
            "deductible": p.deductible,
            "start_date": p.start_date.isoformat() if p.start_date else None,
            "end_date": p.end_date.isoformat() if p.end_date else None,
            "policy_details": p.policy_details
        }
        for p in policies
    ]}


@app.get("/me/tickets")
def get_user_tickets(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get all tickets for current user."""
    tickets = db.query(Ticket).filter(Ticket.user_id == current_user.id).order_by(Ticket.created_at.desc()).all()
    return {"tickets": [
        {
            "id": t.id,
            "ticket_number": t.ticket_number,
            "title": t.title,
            "description": t.description,
            "category": t.category,
            "priority": t.priority,
            "status": t.status,
            "resolution": t.resolution,
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "resolved_at": t.resolved_at.isoformat() if t.resolved_at else None
        }
        for t in tickets
    ]}


@app.get("/me/call-history")
def get_user_call_history(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get call history for current user."""
    calls = db.query(CallSummary).filter(CallSummary.user_id == current_user.id).order_by(CallSummary.call_date.desc()).all()
    return {"call_history": [
        {
            "id": c.id,
            "call_date": c.call_date.isoformat() if c.call_date else None,
            "duration_seconds": c.duration_seconds,
            "topic": c.topic,
            "summary": c.summary,
            "sentiment": c.sentiment,
            "key_points": c.key_points,
            "action_items": c.action_items,
            "requires_followup": c.requires_followup
        }
        for c in calls
    ]}


# ============================================================================
# Admin Endpoints
# ============================================================================

def get_current_admin(current_user: User = Depends(get_current_user)) -> User:
    """Verify user is admin."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


@app.get("/admin/users")
def get_all_users(current_admin: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    """Get all users (admin only)."""
    from database import User as UserModel
    users = db.query(UserModel).all()
    return [
        {
            "id": u.id,
            "email": u.email,
            "username": u.username,
            "full_name": u.full_name,
            "phone": u.phone,
            "is_admin": u.is_admin,
            "is_active": u.is_active,
            "created_at": u.created_at.isoformat() if u.created_at else None
        }
        for u in users
    ]


@app.get("/admin/policies")
def get_all_policies(current_admin: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    """Get all policies (admin only)."""
    policies = db.query(Policy).all()
    return [
        {
            "id": p.id,
            "user_id": p.user_id,
            "policy_number": p.policy_number,
            "policy_type": p.policy_type,
            "status": p.status,
            "premium_amount": p.premium_amount,
            "coverage_amount": p.coverage_amount,
            "deductible": p.deductible,
            "start_date": p.start_date.isoformat() if p.start_date else None,
            "end_date": p.end_date.isoformat() if p.end_date else None
        }
        for p in policies
    ]


@app.get("/admin/tickets")
def get_all_tickets(current_admin: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    """Get all tickets (admin only)."""
    tickets = db.query(Ticket).all()
    return [
        {
            "id": t.id,
            "user_id": t.user_id,
            "ticket_number": t.ticket_number,
            "title": t.title,
            "description": t.description,
            "category": t.category,
            "priority": t.priority,
            "status": t.status,
            "resolution": t.resolution,
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "resolved_at": t.resolved_at.isoformat() if t.resolved_at else None
        }
        for t in tickets
    ]


@app.get("/admin/interventions")
def get_all_interventions(current_admin: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    """Get all admin interventions (admin only)."""
    from database import AdminIntervention
    interventions = db.query(AdminIntervention).all()
    return [
        {
            "id": i.id,
            "user_id": i.user_id,
            "admin_id": i.admin_id,
            "trigger_reason": i.trigger_reason,
            "ai_confidence_score": i.ai_confidence_score,
            "status": i.status,
            "admin_notes": i.admin_notes,
            "created_at": i.created_at.isoformat() if i.created_at else None,
            "resolved_at": i.resolved_at.isoformat() if i.resolved_at else None
        }
        for i in interventions
    ]


# cd 'c:\Users\praja\Desktop\neir-classification'; python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000