"""
Main orchestrator for the Insurance AI Agent.
Implements the ReAct pattern using LangGraph.
"""
import json
from typing import Dict, Any, List, Optional, Annotated, TypedDict, Sequence
from datetime import datetime
from dataclasses import dataclass, field

from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langgraph.graph.message import add_messages

from src.agent.tools import get_all_tools
from src.agent.prompts import SYSTEM_PROMPT, get_safe_phrase
from src.utils.config import config
from src.utils.logger import agent_logger


# ============================================================================
# State Definition
# ============================================================================

class AgentState(TypedDict):
    """State object for the agent graph."""
    messages: Annotated[Sequence[BaseMessage], add_messages]
    customer_context: Optional[Dict[str, Any]]
    search_attempts: int
    should_escalate: bool
    thought_log: List[Dict[str, Any]]


@dataclass
class ConversationContext:
    """Track conversation context and history."""
    customer_id: Optional[str] = None
    customer_name: Optional[str] = None
    policy_number: Optional[str] = None
    conversation_id: str = field(default_factory=lambda: datetime.now().strftime("%Y%m%d%H%M%S"))
    messages: List[Dict[str, str]] = field(default_factory=list)
    thought_log: List[Dict[str, Any]] = field(default_factory=list)
    
    def add_message(self, role: str, content: str):
        self.messages.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
    
    def add_thought(self, thought_type: str, content: Any):
        self.thought_log.append({
            "type": thought_type,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
    
    def get_history_text(self) -> str:
        return "\n".join([
            f"{m['role'].upper()}: {m['content']}"
            for m in self.messages[-10:]  # Last 10 messages
        ])


# ============================================================================
# Agent Orchestrator
# ============================================================================

class InsuranceAgent:
    """
    Main orchestrator for the Insurance AI Agent.
    Uses LangGraph to implement the ReAct pattern.
    """
    
    def __init__(self):
        # Initialize LLM
        self.llm = ChatOpenAI(
            model=config.openai.model,
            temperature=config.openai.temperature,
            api_key=config.openai.api_key
        )
        
        # Get tools
        self.tools = get_all_tools()
        
        # Bind tools to LLM
        self.llm_with_tools = self.llm.bind_tools(self.tools)
        
        # Build the agent graph
        self.graph = self._build_graph()
        
        # Conversation context
        self.context = ConversationContext()
        
        # Escalation tracking
        self.search_attempts = 0
        self.max_search_attempts = config.agent.escalation_threshold
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow."""
        
        # Define the graph
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("agent", self._agent_node)
        workflow.add_node("tools", ToolNode(self.tools))
        workflow.add_node("check_escalation", self._check_escalation_node)
        
        # Set entry point
        workflow.set_entry_point("agent")
        
        # Add conditional edges
        workflow.add_conditional_edges(
            "agent",
            self._should_continue,
            {
                "continue": "tools",
                "escalate": "check_escalation",
                "end": END
            }
        )
        
        # Tools always go back to agent
        workflow.add_edge("tools", "agent")
        
        # Escalation goes to end
        workflow.add_edge("check_escalation", END)
        
        return workflow.compile()
    
    def _agent_node(self, state: AgentState) -> Dict[str, Any]:
        """Main agent reasoning node."""
        messages = state["messages"]
        
        # Create system message with context
        system_content = SYSTEM_PROMPT
        if state.get("customer_context"):
            system_content += f"\n\nCurrent Customer: {state['customer_context']}"
        
        # Build message list
        full_messages = [SystemMessage(content=system_content)] + list(messages)
        
        # Log thought
        agent_logger.thought(f"Processing message with {len(messages)} in history")
        
        # Get LLM response
        response = self.llm_with_tools.invoke(full_messages)
        
        # Log the response
        if response.tool_calls:
            for tool_call in response.tool_calls:
                agent_logger.action(tool_call["name"], tool_call["args"])
        
        return {"messages": [response]}
    
    def _should_continue(self, state: AgentState) -> str:
        """Determine if we should continue, escalate, or end."""
        messages = state["messages"]
        last_message = messages[-1]
        
        # Check for escalation flag
        if state.get("should_escalate"):
            return "escalate"
        
        # Check if the last message has tool calls
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            # Track search attempts for escalation
            for tool_call in last_message.tool_calls:
                if "search" in tool_call["name"].lower():
                    current_attempts = state.get("search_attempts", 0)
                    if current_attempts >= self.max_search_attempts:
                        return "escalate"
            return "continue"
        
        return "end"
    
    def _check_escalation_node(self, state: AgentState) -> Dict[str, Any]:
        """Handle escalation to human agent."""
        agent_logger.escalation("Escalating to human agent")
        
        escalation_message = get_safe_phrase("escalation", 0)
        escalation_message += " Let me transfer you to a senior agent who can review your case in detail."
        
        return {
            "messages": [AIMessage(content=escalation_message)]
        }
    
    def process_message(
        self,
        user_message: str,
        customer_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process a user message and return the agent's response.
        
        Args:
            user_message: The customer's message
            customer_context: Optional customer identification context
        
        Returns:
            Dictionary with response and metadata
        """
        # Log user message
        self.context.add_message("user", user_message)
        
        # Build initial state
        initial_state: AgentState = {
            "messages": [HumanMessage(content=user_message)],
            "customer_context": customer_context or self.context.__dict__,
            "search_attempts": 0,
            "should_escalate": False,
            "thought_log": []
        }
        
        # Run the graph
        try:
            result = self.graph.invoke(initial_state)
            
            # Extract the final response
            final_message = result["messages"][-1]
            response_text = final_message.content if hasattr(final_message, "content") else str(final_message)
            
            # Log response
            agent_logger.response(response_text)
            self.context.add_message("assistant", response_text)
            
            return {
                "success": True,
                "response": response_text,
                "thought_log": agent_logger.get_history(),
                "escalated": result.get("should_escalate", False)
            }
            
        except Exception as e:
            agent_logger.error(f"Error processing message: {str(e)}")
            return {
                "success": False,
                "response": "I apologize, but I encountered an issue processing your request. Let me connect you with a human agent.",
                "error": str(e),
                "escalated": True
            }
    
    def reset_conversation(self):
        """Reset the conversation context."""
        self.context = ConversationContext()
        self.search_attempts = 0
        agent_logger.clear_history()
    
    def get_conversation_summary(self) -> Dict[str, Any]:
        """Get a summary of the current conversation."""
        return {
            "conversation_id": self.context.conversation_id,
            "customer_id": self.context.customer_id,
            "customer_name": self.context.customer_name,
            "policy_number": self.context.policy_number,
            "message_count": len(self.context.messages),
            "messages": self.context.messages,
            "thought_log": self.context.thought_log
        }


# ============================================================================
# Convenience Functions
# ============================================================================

_agent_instance: Optional[InsuranceAgent] = None


def get_agent() -> InsuranceAgent:
    """Get or create the global agent instance."""
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = InsuranceAgent()
    return _agent_instance


def chat(message: str) -> str:
    """Quick chat function for testing."""
    agent = get_agent()
    result = agent.process_message(message)
    return result["response"]


if __name__ == "__main__":
    # Interactive test
    print("=" * 60)
    print("Insurance AI Agent - Interactive Test")
    print("=" * 60)
    print("\nType 'quit' to exit, 'reset' to start new conversation\n")
    
    agent = get_agent()
    
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
