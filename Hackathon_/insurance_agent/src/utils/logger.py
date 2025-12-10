"""
Logging utilities for the Insurance AI Agent.
"""
import logging
import sys
from datetime import datetime
from typing import Optional
from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel
from rich.text import Text

console = Console()


def setup_logger(name: str, level: str = "INFO") -> logging.Logger:
    """Set up a logger with rich formatting."""
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))
    
    if not logger.handlers:
        handler = RichHandler(
            console=console,
            show_time=True,
            show_path=False,
            rich_tracebacks=True
        )
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(handler)
    
    return logger


class AgentLogger:
    """Specialized logger for agent thoughts and actions."""
    
    def __init__(self, name: str = "Agent"):
        self.name = name
        self.console = Console()
        self.thought_history: list[dict] = []
    
    def thought(self, message: str):
        """Log an agent thought."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "type": "thought",
            "content": message
        }
        self.thought_history.append(entry)
        self.console.print(Panel(
            Text(message, style="italic cyan"),
            title="💭 Thought",
            border_style="cyan"
        ))
    
    def action(self, tool_name: str, params: dict):
        """Log a tool action."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "type": "action",
            "tool": tool_name,
            "params": params
        }
        self.thought_history.append(entry)
        self.console.print(Panel(
            f"[bold yellow]{tool_name}[/bold yellow]\n{params}",
            title="🔧 Action",
            border_style="yellow"
        ))
    
    def observation(self, result: str):
        """Log a tool observation/result."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "type": "observation",
            "content": result[:500]  # Truncate for logging
        }
        self.thought_history.append(entry)
        display_result = result[:300] + "..." if len(result) > 300 else result
        self.console.print(Panel(
            display_result,
            title="👁️ Observation",
            border_style="green"
        ))
    
    def response(self, message: str):
        """Log the final agent response."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "type": "response",
            "content": message
        }
        self.thought_history.append(entry)
        self.console.print(Panel(
            Text(message, style="bold white"),
            title="🎙️ Response",
            border_style="blue"
        ))
    
    def error(self, message: str):
        """Log an error."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "type": "error",
            "content": message
        }
        self.thought_history.append(entry)
        self.console.print(Panel(
            Text(message, style="bold red"),
            title="❌ Error",
            border_style="red"
        ))
    
    def escalation(self, reason: str):
        """Log an escalation event."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "type": "escalation",
            "content": reason
        }
        self.thought_history.append(entry)
        self.console.print(Panel(
            Text(reason, style="bold magenta"),
            title="⚠️ Escalation",
            border_style="magenta"
        ))
    
    def get_history(self) -> list[dict]:
        """Get the full thought history."""
        return self.thought_history
    
    def clear_history(self):
        """Clear the thought history."""
        self.thought_history = []


# Global agent logger instance
agent_logger = AgentLogger()
