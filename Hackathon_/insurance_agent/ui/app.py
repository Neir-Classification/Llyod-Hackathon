"""
Streamlit UI for the Insurance AI Agent.
Displays conversation with real-time agent thoughts visualization.
"""
import streamlit as st
import time
from datetime import datetime
import json
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agent.orchestrator import InsuranceAgent
from src.knowledge.vector_store import initialize_vector_store
from src.database.customer_db import get_customer_db, CustomerProfile
from src.utils.logger import agent_logger


# ============================================================================
# Page Configuration
# ============================================================================

st.set_page_config(
    page_title="Insurance AI Agent - Nier",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ============================================================================
# Custom CSS
# ============================================================================

st.markdown("""
<style>
    /* Main styling */
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1e40af;
        margin-bottom: 0.5rem;
    }
    
    .sub-header {
        font-size: 1.1rem;
        color: #6b7280;
        margin-bottom: 2rem;
    }
    
    /* Chat messages */
    .user-message {
        background: #eff6ff;
        border-left: 4px solid #3b82f6;
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 0 8px 8px 0;
    }
    
    .agent-message {
        background: #f0fdf4;
        border-left: 4px solid #22c55e;
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 0 8px 8px 0;
    }
    
    /* Thought log */
    .thought-box {
        background: #fefce8;
        border: 1px solid #fcd34d;
        padding: 0.75rem;
        margin: 0.25rem 0;
        border-radius: 6px;
        font-size: 0.9rem;
    }
    
    .action-box {
        background: #fff7ed;
        border: 1px solid #fb923c;
        padding: 0.75rem;
        margin: 0.25rem 0;
        border-radius: 6px;
        font-size: 0.9rem;
    }
    
    .observation-box {
        background: #f0f9ff;
        border: 1px solid #38bdf8;
        padding: 0.75rem;
        margin: 0.25rem 0;
        border-radius: 6px;
        font-size: 0.9rem;
    }
    
    /* Customer card */
    .customer-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 12px;
        margin-bottom: 1rem;
    }
    
    .customer-card h3 {
        margin: 0 0 0.5rem 0;
        font-size: 1.3rem;
    }
    
    .customer-card p {
        margin: 0.25rem 0;
        font-size: 0.9rem;
        opacity: 0.9;
    }
    
    /* Endorsement badges */
    .endorsement-badge {
        display: inline-block;
        background: rgba(255,255,255,0.2);
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.8rem;
        margin: 0.25rem 0.25rem 0.25rem 0;
    }
    
    /* Status indicator */
    .status-indicator {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        font-size: 0.9rem;
    }
    
    .status-ready {
        background: #dcfce7;
        color: #166534;
    }
    
    .status-thinking {
        background: #fef3c7;
        color: #92400e;
    }
    
    .status-error {
        background: #fee2e2;
        color: #991b1b;
    }
</style>
""", unsafe_allow_html=True)


# ============================================================================
# Session State Initialization
# ============================================================================

def init_session_state():
    """Initialize session state variables."""
    if "agent" not in st.session_state:
        with st.spinner("Initializing AI Agent..."):
            initialize_vector_store(reset=False)
            st.session_state.agent = InsuranceAgent()
    
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    if "thought_history" not in st.session_state:
        st.session_state.thought_history = []
    
    if "selected_customer" not in st.session_state:
        st.session_state.selected_customer = None
    
    if "status" not in st.session_state:
        st.session_state.status = "ready"


# ============================================================================
# Helper Functions
# ============================================================================

def get_customer_options():
    """Get list of customers for dropdown."""
    db = get_customer_db()
    customers = db.get_all_customers()
    options = {"None (New Customer)": None}
    for c in customers:
        options[f"{c.full_name} ({c.policy_number})"] = c.policy_number
    return options


def display_customer_card(customer: CustomerProfile):
    """Display customer info card."""
    st.markdown(f"""
    <div class="customer-card">
        <h3>👤 {customer.full_name}</h3>
        <p><strong>Policy:</strong> {customer.policy_number}</p>
        <p><strong>Type:</strong> {customer.policy_type}</p>
        <p><strong>Coverage:</strong> Dwelling ${customer.coverage.get('dwelling', 0):,} | 
           Personal Property ${customer.coverage.get('personal_property', 0):,}</p>
        <p><strong>Deductible:</strong> ${customer.deductible:,}</p>
        <div style="margin-top: 0.75rem;">
            <strong>Endorsements:</strong><br>
            {"".join([f'<span class="endorsement-badge">✓ {e}</span>' for e in customer.endorsements]) if customer.endorsements else '<span class="endorsement-badge">None</span>'}
        </div>
    </div>
    """, unsafe_allow_html=True)


def display_thought_log(thoughts):
    """Display the agent's thought process."""
    for thought in thoughts:
        thought_type = thought.get("type", "thought")
        content = thought.get("content", "")
        
        if thought_type == "thought":
            st.markdown(f"""
            <div class="thought-box">
                💭 <strong>Thought:</strong> {content}
            </div>
            """, unsafe_allow_html=True)
        
        elif thought_type == "action":
            tool = thought.get("tool", "unknown")
            params = thought.get("params", {})
            st.markdown(f"""
            <div class="action-box">
                🔧 <strong>Action:</strong> {tool}<br>
                <small>{json.dumps(params, indent=2)}</small>
            </div>
            """, unsafe_allow_html=True)
        
        elif thought_type == "observation":
            display_content = content[:300] + "..." if len(str(content)) > 300 else content
            st.markdown(f"""
            <div class="observation-box">
                👁️ <strong>Observation:</strong><br>
                <small>{display_content}</small>
            </div>
            """, unsafe_allow_html=True)
        
        elif thought_type == "response":
            st.success(f"💬 **Final Response Generated**")
        
        elif thought_type == "escalation":
            st.warning(f"⚠️ **Escalation:** {content}")
        
        elif thought_type == "error":
            st.error(f"❌ **Error:** {content}")


def process_user_input(user_input: str):
    """Process user input and get agent response."""
    # Add user message to history
    st.session_state.messages.append({
        "role": "user",
        "content": user_input,
        "timestamp": datetime.now().isoformat()
    })
    
    # Update status
    st.session_state.status = "thinking"
    
    # Build customer context
    customer_context = None
    if st.session_state.selected_customer:
        db = get_customer_db()
        customer = db.search(st.session_state.selected_customer)
        if customer:
            customer_context = customer.to_dict()
    
    # Clear previous thought log
    agent_logger.clear_history()
    
    # Get agent response
    result = st.session_state.agent.process_message(
        user_input,
        customer_context=customer_context
    )
    
    # Add agent response to history
    st.session_state.messages.append({
        "role": "assistant",
        "content": result["response"],
        "timestamp": datetime.now().isoformat(),
        "escalated": result.get("escalated", False)
    })
    
    # Store thought history
    st.session_state.thought_history = result.get("thought_log", [])
    
    # Update status
    st.session_state.status = "ready"


# ============================================================================
# Main UI
# ============================================================================

def main():
    """Main Streamlit app."""
    init_session_state()
    
    # Header
    st.markdown('<p class="main-header">🏠 Insurance AI Agent - Nier</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Intelligent voice-enabled assistant for complex insurance inquiries</p>', unsafe_allow_html=True)
    
    # Layout: Main chat area and sidebar
    col_chat, col_thoughts = st.columns([2, 1])
    
    # Sidebar: Customer Selection
    with st.sidebar:
        st.header("📋 Customer Context")
        
        customer_options = get_customer_options()
        selected = st.selectbox(
            "Select Customer",
            options=list(customer_options.keys()),
            index=0
        )
        
        st.session_state.selected_customer = customer_options[selected]
        
        # Display selected customer info
        if st.session_state.selected_customer:
            db = get_customer_db()
            customer = db.search(st.session_state.selected_customer)
            if customer:
                display_customer_card(customer)
        else:
            st.info("No customer selected. The agent will ask for identification if needed.")
        
        st.divider()
        
        # Demo scenarios
        st.header("🎬 Demo Scenarios")
        
        if st.button("💧 Sump Pump Coverage", use_container_width=True):
            st.session_state.selected_customer = "HO-2024-001234"
            process_user_input("My basement flooded because the sump pump failed. Am I covered?")
            st.rerun()
        
        if st.button("🌊 River Flood (Excluded)", use_container_width=True):
            st.session_state.selected_customer = "HO-2024-009012"
            process_user_input("The river near my house overflowed and damaged my basement. Is this covered?")
            st.rerun()
        
        if st.button("🍄 Mold Behind Washer", use_container_width=True):
            st.session_state.selected_customer = "HO-2024-005678"
            process_user_input("I just found mold behind my washing machine. Is that covered?")
            st.rerun()
        
        if st.button("💍 Engagement Ring", use_container_width=True):
            st.session_state.selected_customer = "HO-2024-005678"
            process_user_input("I just bought a $10,000 engagement ring. Is it covered under my contents limit?")
            st.rerun()
        
        if st.button("🏠 Airbnb Theft", use_container_width=True):
            st.session_state.selected_customer = "HO-2024-009012"
            process_user_input("I'm renting my house on Airbnb this weekend. Does my insurance cover theft by a guest?")
            st.rerun()
        
        if st.button("🌳 Tree on Fence", use_container_width=True):
            st.session_state.selected_customer = "HO-2024-001234"
            process_user_input("A tree fell on my fence, but the tree belongs to the city. Who pays?")
            st.rerun()
        
        st.divider()
        
        if st.button("🔄 Reset Conversation", use_container_width=True):
            st.session_state.messages = []
            st.session_state.thought_history = []
            st.session_state.agent.reset_conversation()
            agent_logger.clear_history()
            st.rerun()
    
    # Main chat area
    with col_chat:
        st.subheader("💬 Conversation")
        
        # Status indicator
        status = st.session_state.status
        if status == "ready":
            st.markdown('<div class="status-indicator status-ready">🟢 Ready</div>', unsafe_allow_html=True)
        elif status == "thinking":
            st.markdown('<div class="status-indicator status-thinking">🟡 Thinking...</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="status-indicator status-error">🔴 Error</div>', unsafe_allow_html=True)
        
        # Chat messages
        chat_container = st.container()
        with chat_container:
            for msg in st.session_state.messages:
                if msg["role"] == "user":
                    st.markdown(f"""
                    <div class="user-message">
                        <strong>👤 You:</strong><br>{msg['content']}
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    escalated = msg.get("escalated", False)
                    prefix = "⚠️" if escalated else "🤖"
                    st.markdown(f"""
                    <div class="agent-message">
                        <strong>{prefix} Nier:</strong><br>{msg['content']}
                    </div>
                    """, unsafe_allow_html=True)
        
        # Chat input
        st.divider()
        user_input = st.chat_input("Ask about your insurance coverage...")
        
        if user_input:
            process_user_input(user_input)
            st.rerun()
    
    # Thought log panel
    with col_thoughts:
        st.subheader("🧠 Agent's Thoughts")
        st.caption("Real-time view of the agent's reasoning process")
        
        thought_container = st.container()
        with thought_container:
            if st.session_state.thought_history:
                display_thought_log(st.session_state.thought_history)
            else:
                st.info("The agent's thought process will appear here during conversations.")


if __name__ == "__main__":
    main()
