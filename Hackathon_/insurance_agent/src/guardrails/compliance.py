"""
Compliance guardrails for the Insurance AI Agent.
Ensures responses are safe, accurate, and legally compliant.
"""
import re
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class RiskLevel(Enum):
    """Risk level for compliance violations."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ComplianceViolation:
    """Represents a compliance violation."""
    rule: str
    description: str
    risk_level: RiskLevel
    original_text: str
    suggested_fix: Optional[str] = None


class ComplianceGuardrails:
    """
    Compliance checking and response sanitization.
    Prevents the agent from making promises or statements
    that could create legal liability.
    """
    
    # Phrases that guarantee coverage (FORBIDDEN)
    GUARANTEE_PATTERNS = [
        r"\bwe will pay\b",
        r"\bwe will cover\b",
        r"\byou are covered\b",
        r"\byou're covered\b",
        r"\bI promise\b",
        r"\bI guarantee\b",
        r"\babsolutely covered\b",
        r"\bdefinitely covered\b",
        r"\b100% covered\b",
        r"\bfully covered\b",
        r"\bno question.*covered\b",
        r"\bwithout a doubt.*covered\b",
    ]
    
    # Phrases that definitively deny coverage (also risky)
    DENIAL_PATTERNS = [
        r"\bwe will not pay\b",
        r"\byou are not covered\b",
        r"\babsolutely not covered\b",
        r"\bno way.*covered\b",
    ]
    
    # Conditional/safe phrases (PREFERRED)
    SAFE_ALTERNATIVES = {
        "you are covered": "based on your policy, it appears you may be covered",
        "we will pay": "your policy may provide coverage for",
        "you're covered": "your coverage appears to include",
        "I promise": "based on the policy documentation",
        "absolutely covered": "appears to be covered under your policy",
        "definitely covered": "based on your policy terms, this situation appears to be covered",
        "you are not covered": "based on the policy exclusions, this type of loss does not appear to be covered",
        "we will not pay": "this situation appears to fall under policy exclusions",
    }
    
    # Topics that require special care
    SENSITIVE_TOPICS = [
        "lawsuit", "litigation", "sue", "legal action",
        "fraud", "fraudulent",
        "bad faith",
        "discrimination",
        "cancel policy", "non-renewal",
    ]
    
    # Required citation patterns
    CITATION_INDICATORS = [
        r"according to",
        r"based on",
        r"per your policy",
        r"the policy states",
        r"section.*states",
        r"as stated in",
        r"\[citation",
        r"\[source",
    ]
    
    def __init__(self, strict_mode: bool = True):
        """
        Initialize guardrails.
        
        Args:
            strict_mode: If True, block responses with violations.
                        If False, just warn and suggest fixes.
        """
        self.strict_mode = strict_mode
        self.violation_log: List[ComplianceViolation] = []
    
    def check_response(self, response: str) -> Tuple[bool, List[ComplianceViolation]]:
        """
        Check a response for compliance violations.
        
        Args:
            response: The agent's response text
        
        Returns:
            Tuple of (is_compliant, list_of_violations)
        """
        violations = []
        response_lower = response.lower()
        
        # Check for guarantee patterns
        for pattern in self.GUARANTEE_PATTERNS:
            if re.search(pattern, response_lower):
                match = re.search(pattern, response_lower)
                violations.append(ComplianceViolation(
                    rule="NO_GUARANTEE",
                    description="Response contains language that guarantees coverage",
                    risk_level=RiskLevel.HIGH,
                    original_text=match.group() if match else pattern,
                    suggested_fix=self._suggest_fix(match.group() if match else pattern)
                ))
        
        # Check for absolute denial patterns
        for pattern in self.DENIAL_PATTERNS:
            if re.search(pattern, response_lower):
                match = re.search(pattern, response_lower)
                violations.append(ComplianceViolation(
                    rule="ABSOLUTE_DENIAL",
                    description="Response contains absolute denial language",
                    risk_level=RiskLevel.MEDIUM,
                    original_text=match.group() if match else pattern,
                    suggested_fix=self._suggest_fix(match.group() if match else pattern)
                ))
        
        # Check for sensitive topics without proper hedging
        for topic in self.SENSITIVE_TOPICS:
            if topic in response_lower:
                violations.append(ComplianceViolation(
                    rule="SENSITIVE_TOPIC",
                    description=f"Response discusses sensitive topic: {topic}",
                    risk_level=RiskLevel.MEDIUM,
                    original_text=topic
                ))
        
        # Check for citation (required for coverage statements)
        has_coverage_statement = any(
            term in response_lower 
            for term in ["covered", "coverage", "pays", "reimburse"]
        )
        has_citation = any(
            re.search(pattern, response_lower) 
            for pattern in self.CITATION_INDICATORS
        )
        
        if has_coverage_statement and not has_citation:
            violations.append(ComplianceViolation(
                rule="MISSING_CITATION",
                description="Coverage statement made without citing policy source",
                risk_level=RiskLevel.LOW,
                original_text="[coverage statement without citation]"
            ))
        
        # Log violations
        self.violation_log.extend(violations)
        
        # Determine compliance
        high_risk = any(v.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL] for v in violations)
        is_compliant = not (self.strict_mode and high_risk)
        
        return is_compliant, violations
    
    def _suggest_fix(self, original: str) -> str:
        """Suggest a compliant alternative for problematic text."""
        original_lower = original.lower().strip()
        for bad, good in self.SAFE_ALTERNATIVES.items():
            if bad in original_lower:
                return good
        return f"Consider rephrasing: '{original}'"
    
    def sanitize_response(self, response: str) -> str:
        """
        Sanitize a response by replacing problematic phrases.
        
        Args:
            response: Original response text
        
        Returns:
            Sanitized response
        """
        sanitized = response
        
        # Replace guarantee patterns
        for bad_phrase, good_phrase in self.SAFE_ALTERNATIVES.items():
            # Case-insensitive replacement
            pattern = re.compile(re.escape(bad_phrase), re.IGNORECASE)
            sanitized = pattern.sub(good_phrase, sanitized)
        
        return sanitized
    
    def add_compliance_disclaimer(self, response: str) -> str:
        """
        Add a compliance disclaimer to the response.
        
        Args:
            response: Original response
        
        Returns:
            Response with disclaimer
        """
        disclaimer = (
            "\n\n*This information is provided based on your policy documents. "
            "Final coverage determinations are made during the claims process. "
            "Please refer to your policy for complete terms and conditions.*"
        )
        
        return response + disclaimer
    
    def validate_for_output(self, response: str) -> Dict[str, Any]:
        """
        Full validation pipeline for agent output.
        
        Args:
            response: The agent's response
        
        Returns:
            Dictionary with validated response and metadata
        """
        # Check compliance
        is_compliant, violations = self.check_response(response)
        
        # Sanitize if needed
        if violations:
            sanitized = self.sanitize_response(response)
        else:
            sanitized = response
        
        # Log violations
        if violations:
            for v in violations:
                logger.warning(f"Compliance violation [{v.rule}]: {v.description}")
        
        return {
            "original_response": response,
            "sanitized_response": sanitized,
            "is_compliant": is_compliant,
            "violations": [
                {
                    "rule": v.rule,
                    "description": v.description,
                    "risk_level": v.risk_level.value,
                    "suggested_fix": v.suggested_fix
                }
                for v in violations
            ],
            "was_modified": response != sanitized
        }
    
    def get_violation_summary(self) -> Dict[str, int]:
        """Get summary of all violations logged."""
        summary = {}
        for v in self.violation_log:
            key = f"{v.rule}:{v.risk_level.value}"
            summary[key] = summary.get(key, 0) + 1
        return summary
    
    def clear_log(self):
        """Clear the violation log."""
        self.violation_log = []


class SentimentAnalyzer:
    """
    Simple sentiment analysis for detecting customer frustration.
    Used to trigger tone adjustments or escalation.
    """
    
    FRUSTRATION_INDICATORS = [
        "frustrated", "angry", "upset", "ridiculous",
        "unacceptable", "terrible", "awful", "worst",
        "hate", "stupid", "incompetent", "waste of time",
        "speak to manager", "speak to supervisor",
        "file a complaint", "report you",
        "cancel my policy", "switching companies",
    ]
    
    URGENCY_INDICATORS = [
        "emergency", "urgent", "asap", "immediately",
        "right now", "can't wait", "critical",
        "flooding", "fire", "break-in",
    ]
    
    POSITIVE_INDICATORS = [
        "thank you", "thanks", "appreciate",
        "helpful", "great", "wonderful",
        "excellent", "perfect",
    ]
    
    def analyze(self, text: str) -> Dict[str, Any]:
        """
        Analyze text for sentiment indicators.
        
        Args:
            text: User message text
        
        Returns:
            Sentiment analysis results
        """
        text_lower = text.lower()
        
        frustration_score = sum(
            1 for indicator in self.FRUSTRATION_INDICATORS
            if indicator in text_lower
        )
        
        urgency_score = sum(
            1 for indicator in self.URGENCY_INDICATORS
            if indicator in text_lower
        )
        
        positive_score = sum(
            1 for indicator in self.POSITIVE_INDICATORS
            if indicator in text_lower
        )
        
        # Determine overall sentiment
        if frustration_score >= 2:
            sentiment = "negative"
            should_escalate = True
        elif frustration_score == 1:
            sentiment = "slightly_negative"
            should_escalate = False
        elif positive_score > 0:
            sentiment = "positive"
            should_escalate = False
        else:
            sentiment = "neutral"
            should_escalate = False
        
        # Check for urgent situations
        is_urgent = urgency_score > 0
        
        return {
            "sentiment": sentiment,
            "frustration_score": frustration_score,
            "urgency_score": urgency_score,
            "positive_score": positive_score,
            "should_escalate": should_escalate,
            "is_urgent": is_urgent,
            "suggested_tone": self._suggest_tone(sentiment, is_urgent)
        }
    
    def _suggest_tone(self, sentiment: str, is_urgent: bool) -> str:
        """Suggest appropriate tone based on sentiment."""
        if sentiment == "negative":
            return "apologetic_and_empathetic"
        elif sentiment == "slightly_negative":
            return "understanding_and_helpful"
        elif is_urgent:
            return "direct_and_efficient"
        elif sentiment == "positive":
            return "warm_and_friendly"
        else:
            return "professional_and_helpful"


class EscalationManager:
    """
    Manage escalation logic and handoff to human agents.
    """
    
    def __init__(self, search_threshold: int = 2):
        self.search_threshold = search_threshold
        self.search_attempts = 0
        self.escalation_reasons: List[str] = []
    
    def record_search_attempt(self, found_answer: bool):
        """Record a knowledge base search attempt."""
        if not found_answer:
            self.search_attempts += 1
    
    def should_escalate(
        self,
        sentiment_result: Optional[Dict[str, Any]] = None,
        user_requested: bool = False,
        violations: Optional[List[ComplianceViolation]] = None
    ) -> Tuple[bool, List[str]]:
        """
        Determine if conversation should be escalated.
        
        Returns:
            Tuple of (should_escalate, list_of_reasons)
        """
        reasons = []
        
        # Too many failed searches
        if self.search_attempts >= self.search_threshold:
            reasons.append(f"Unable to find definitive answer after {self.search_attempts} searches")
        
        # Customer frustration
        if sentiment_result and sentiment_result.get("should_escalate"):
            reasons.append("Customer showing signs of frustration")
        
        # User explicitly requested
        if user_requested:
            reasons.append("Customer requested human agent")
        
        # Critical compliance violations
        if violations:
            critical = [v for v in violations if v.risk_level == RiskLevel.CRITICAL]
            if critical:
                reasons.append("Critical compliance issue detected")
        
        self.escalation_reasons.extend(reasons)
        return len(reasons) > 0, reasons
    
    def get_escalation_message(self, reasons: List[str]) -> str:
        """Generate escalation message for customer."""
        return (
            "I want to make sure you receive the most accurate and thorough assistance. "
            "This situation requires a specialist's review, so I'd like to transfer you "
            "to a senior agent who can help you further. They will have access to our "
            "conversation summary and can continue from where we left off. "
            "Would you like me to connect you now?"
        )
    
    def reset(self):
        """Reset escalation tracking."""
        self.search_attempts = 0
        self.escalation_reasons = []


# Global instances
_guardrails: Optional[ComplianceGuardrails] = None
_sentiment: Optional[SentimentAnalyzer] = None
_escalation: Optional[EscalationManager] = None


def get_guardrails() -> ComplianceGuardrails:
    """Get global guardrails instance."""
    global _guardrails
    if _guardrails is None:
        _guardrails = ComplianceGuardrails()
    return _guardrails


def get_sentiment_analyzer() -> SentimentAnalyzer:
    """Get global sentiment analyzer."""
    global _sentiment
    if _sentiment is None:
        _sentiment = SentimentAnalyzer()
    return _sentiment


def get_escalation_manager() -> EscalationManager:
    """Get global escalation manager."""
    global _escalation
    if _escalation is None:
        _escalation = EscalationManager()
    return _escalation


if __name__ == "__main__":
    # Test guardrails
    print("=== Testing Compliance Guardrails ===\n")
    
    guardrails = ComplianceGuardrails()
    
    # Test responses
    test_responses = [
        "You are covered for this damage. We will pay the full amount.",
        "Based on your policy, it appears you may be covered for water backup damage.",
        "I promise we will reimburse you for the damages.",
        "According to the policy exclusions section, flood damage from rivers is not covered.",
    ]
    
    for response in test_responses:
        print(f"Testing: {response[:60]}...")
        result = guardrails.validate_for_output(response)
        print(f"  Compliant: {result['is_compliant']}")
        print(f"  Violations: {len(result['violations'])}")
        if result['was_modified']:
            print(f"  Sanitized: {result['sanitized_response'][:60]}...")
        print()
    
    # Test sentiment analysis
    print("\n=== Testing Sentiment Analysis ===\n")
    
    sentiment = SentimentAnalyzer()
    
    test_messages = [
        "This is ridiculous! I've been a customer for 10 years!",
        "Thank you so much for your help!",
        "Can you explain what my deductible is?",
        "I need help immediately, my basement is flooding!",
    ]
    
    for message in test_messages:
        print(f"Message: {message}")
        result = sentiment.analyze(message)
        print(f"  Sentiment: {result['sentiment']}")
        print(f"  Suggested tone: {result['suggested_tone']}")
        print(f"  Should escalate: {result['should_escalate']}")
        print()
