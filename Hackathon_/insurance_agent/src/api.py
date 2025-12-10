"""
FastAPI backend for the Insurance AI Agent.
Provides REST and WebSocket endpoints.
"""
import asyncio
import json
from typing import Optional, Dict, Any, List
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agent.orchestrator import get_agent, InsuranceAgent
from src.knowledge.vector_store import initialize_vector_store
from src.database.customer_db import get_customer_db
from src.utils.logger import agent_logger


# ============================================================================
# Lifespan and App Setup
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize resources on startup."""
    print("Initializing Insurance AI Agent...")
    
    # Initialize vector store
    try:
        initialize_vector_store(reset=False)
        print("✓ Vector store initialized")
    except Exception as e:
        print(f"⚠ Vector store initialization failed: {e}")
    
    # Initialize customer database
    get_customer_db()
    print("✓ Customer database loaded")
    
    # Initialize agent
    get_agent()
    print("✓ Agent initialized")
    
    print("\nInsurance AI Agent ready!")
    yield
    
    print("Shutting down...")


app = FastAPI(
    title="Insurance AI Agent API",
    description="Intelligent voice-enabled insurance assistant",
    version="1.0.0",
    lifespan=lifespan
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# Request/Response Models
# ============================================================================

class ChatRequest(BaseModel):
    """Chat request model."""
    message: str
    customer_id: Optional[str] = None
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    """Chat response model."""
    success: bool
    response: str
    thought_log: List[Dict[str, Any]]
    escalated: bool
    session_id: str
    timestamp: str


class CustomerRequest(BaseModel):
    """Customer lookup request."""
    identifier: str


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    timestamp: str
    version: str


# ============================================================================
# REST Endpoints
# ============================================================================

@app.get("/", response_class=HTMLResponse)
async def root():
    """Root endpoint with API info."""
    return """
    <html>
        <head>
            <title>Insurance AI Agent API</title>
            <style>
                body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif; 
                       max-width: 800px; margin: 50px auto; padding: 20px; }
                h1 { color: #2563eb; }
                .endpoint { background: #f3f4f6; padding: 10px; margin: 10px 0; border-radius: 5px; }
                code { background: #e5e7eb; padding: 2px 6px; border-radius: 3px; }
            </style>
        </head>
        <body>
            <h1>🏠 Insurance AI Agent API</h1>
            <p>Intelligent voice-enabled insurance assistant powered by GPT-4 and LangGraph.</p>
            
            <h2>Endpoints</h2>
            <div class="endpoint">
                <strong>POST /chat</strong> - Send a message to the agent<br>
                Body: <code>{"message": "your question", "customer_id": "optional"}</code>
            </div>
            <div class="endpoint">
                <strong>GET /customer/{identifier}</strong> - Look up customer by ID/policy/name
            </div>
            <div class="endpoint">
                <strong>WS /ws/chat</strong> - WebSocket for real-time chat
            </div>
            <div class="endpoint">
                <strong>GET /health</strong> - Health check
            </div>
            
            <h2>Interactive Docs</h2>
            <p>Visit <a href="/docs">/docs</a> for Swagger UI or <a href="/redoc">/redoc</a> for ReDoc.</p>
        </body>
    </html>
    """


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now().isoformat(),
        version="1.0.0"
    )


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Send a message to the insurance agent.
    """
    agent = get_agent()
    
    # Build customer context if ID provided
    customer_context = None
    if request.customer_id:
        db = get_customer_db()
        customer = db.search(request.customer_id)
        if customer:
            customer_context = customer.to_dict()
    
    # Process message
    result = agent.process_message(
        request.message,
        customer_context=customer_context
    )
    
    return ChatResponse(
        success=result["success"],
        response=result["response"],
        thought_log=result.get("thought_log", []),
        escalated=result.get("escalated", False),
        session_id=agent.context.conversation_id,
        timestamp=datetime.now().isoformat()
    )


@app.get("/customer/{identifier}")
async def get_customer(identifier: str):
    """
    Look up customer by ID, policy number, phone, or name.
    """
    db = get_customer_db()
    customer = db.search(identifier)
    
    if not customer:
        raise HTTPException(status_code=404, detail=f"Customer not found: {identifier}")
    
    return customer.to_dict()


@app.get("/customers")
async def list_customers():
    """List all customers (for demo purposes)."""
    db = get_customer_db()
    customers = db.get_all_customers()
    return [
        {
            "id": c.id,
            "name": c.full_name,
            "policy_number": c.policy_number,
            "policy_type": c.policy_type
        }
        for c in customers
    ]


@app.post("/reset")
async def reset_conversation():
    """Reset the current conversation."""
    agent = get_agent()
    agent.reset_conversation()
    return {"success": True, "message": "Conversation reset"}


@app.get("/thoughts")
async def get_thought_log():
    """Get the current thought log for display."""
    return agent_logger.get_history()


# ============================================================================
# WebSocket Endpoints
# ============================================================================

class ConnectionManager:
    """Manage WebSocket connections."""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        self.active_connections[session_id] = websocket
    
    def disconnect(self, session_id: str):
        if session_id in self.active_connections:
            del self.active_connections[session_id]
    
    async def send_json(self, session_id: str, data: dict):
        if session_id in self.active_connections:
            await self.active_connections[session_id].send_json(data)
    
    async def broadcast(self, data: dict):
        for connection in self.active_connections.values():
            await connection.send_json(data)


manager = ConnectionManager()


@app.websocket("/ws/chat/{session_id}")
async def websocket_chat(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for real-time chat.
    """
    await manager.connect(websocket, session_id)
    agent = get_agent()
    
    try:
        while True:
            # Receive message
            data = await websocket.receive_json()
            message = data.get("message", "")
            customer_id = data.get("customer_id")
            
            # Send "thinking" status
            await manager.send_json(session_id, {
                "type": "status",
                "status": "thinking"
            })
            
            # Build customer context
            customer_context = None
            if customer_id:
                db = get_customer_db()
                customer = db.search(customer_id)
                if customer:
                    customer_context = customer.to_dict()
            
            # Process message
            result = agent.process_message(message, customer_context)
            
            # Send response
            await manager.send_json(session_id, {
                "type": "response",
                "success": result["success"],
                "response": result["response"],
                "thought_log": result.get("thought_log", []),
                "escalated": result.get("escalated", False),
                "timestamp": datetime.now().isoformat()
            })
    
    except WebSocketDisconnect:
        manager.disconnect(session_id)


# ============================================================================
# Run Server
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
