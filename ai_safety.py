"""
AI Safety & Responsible AI Module

This module provides safety guardrails, content moderation, and responsible AI practices
for the insurance RAG chatbot.
"""

import logging
import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import hashlib

logger = logging.getLogger(__name__)


class SafetyFlag(Enum):
    """Safety flags for content moderation."""
    SAFE = "safe"
    PII_DETECTED = "pii_detected"
    FINANCIAL_ADVICE = "financial_advice"
    LEGAL_ADVICE = "legal_advice"
    HARMFUL_CONTENT = "harmful_content"
    SCOPE_VIOLATION = "out_of_scope"
    LOW_CONFIDENCE = "low_confidence"
    HALLUCINATION_RISK = "hallucination_risk"


@dataclass
class SafetyReport:
    """Report of safety checks performed on content."""
    is_safe: bool
    flags: List[SafetyFlag] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    pii_found: List[str] = field(default_factory=list)
    confidence_score: float = 1.0
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    def to_dict(self) -> Dict:
        return {    
            "is_safe": self.is_safe,
            "flags": [f.value for f in self.flags],
            "warnings": self.warnings,
            "recommendations": self.recommendations,
            "pii_redacted_count": len(self.pii_found),
            "confidence_score": self.confidence_score,
            "timestamp": self.timestamp
        }


class PIIDetector:
    """Detects and redacts Personally Identifiable Information."""
    
    # PII Patterns (regex)
    PATTERNS = {
        "email": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        "phone_uk": r'\b(?:0|\+44)[\s.-]?\d{4}[\s.-]?\d{6}\b',
        "phone_us": r'\b(?:\+1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b',
        "national_insurance": r'\b[A-Z]{2}\s?\d{2}\s?\d{2}\s?\d{2}\s?[A-Z]\b',  # UK NI number
        "ssn": r'\b\d{3}[-.\s]?\d{2}[-.\s]?\d{4}\b',  # US SSN
        "credit_card": r'\b(?:\d{4}[-.\s]?){3}\d{4}\b',
        "policy_number": r'\b(?:POL|INS|LIFE)[-]?\d{5,10}\b',
        "date_of_birth": r'\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b',
        "address_postcode": r'\b[A-Z]{1,2}\d{1,2}[A-Z]?\s?\d[A-Z]{2}\b',  # UK postcode
    }
    
    @classmethod
    def detect_pii(cls, text: str) -> List[Tuple[str, str, str]]:
        """
        Detect PII in text.
        Returns: List of (pii_type, matched_text, position) tuples
        """
        findings = []
        for pii_type, pattern in cls.PATTERNS.items():
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                findings.append((pii_type, match.group(), f"{match.start()}-{match.end()}"))
        return findings
    
    @classmethod
    def redact_pii(cls, text: str) -> Tuple[str, List[str]]:
        """
        Redact PII from text.
        Returns: (redacted_text, list_of_redacted_types)
        """
        redacted_types = []
        redacted_text = text
        
        for pii_type, pattern in cls.PATTERNS.items():
            if re.search(pattern, redacted_text, re.IGNORECASE):
                redacted_text = re.sub(
                    pattern, 
                    f"[REDACTED-{pii_type.upper()}]", 
                    redacted_text, 
                    flags=re.IGNORECASE
                )
                redacted_types.append(pii_type)
        
        return redacted_text, redacted_types


class ContentModerator:
    """Moderates content for safety and appropriateness."""
    
    # Topics the system should NOT provide advice on
    OUT_OF_SCOPE_TOPICS = [
        r'\b(?:invest(?:ment)?|stock|crypto|bitcoin|trading)\b',
        r'\b(?:legal\s+advice|sue|lawsuit|court|attorney)\b',
        r'\b(?:medical\s+advice|diagnos|treatment|medication)\b',
        r'\b(?:tax\s+advice|tax\s+return|deduction)\b',
    ]
    
    # Financial advice indicators that need disclaimers
    FINANCIAL_ADVICE_INDICATORS = [
        r'\b(?:you\s+should|recommend|best\s+option|better\s+to)\b',
        r'\b(?:guaranteed|definitely|certainly\s+will)\b',
    ]
    
    # Disclaimers to add when financial topics are discussed
    DISCLAIMERS = {
        "financial": "This information is for educational purposes only and should not be considered financial advice. Please consult a qualified financial advisor.",
        "legal": "This is general information only and does not constitute legal advice. Please consult a qualified legal professional for specific guidance.",
        "medical": "This information is not medical advice. Please consult a healthcare professional for medical questions.",
        "policy_specific": "Please review your specific policy documents or contact your insurance provider for personalized guidance.",
    }
    
    @classmethod
    def check_scope(cls, query: str) -> Tuple[bool, List[str]]:
        """
        Check if query is within the system's scope.
        Returns: (is_in_scope, list_of_violations)
        """
        violations = []
        for pattern in cls.OUT_OF_SCOPE_TOPICS:
            if re.search(pattern, query, re.IGNORECASE):
                violations.append(pattern)
        return len(violations) == 0, violations
    
    @classmethod
    def needs_disclaimer(cls, response: str) -> List[str]:
        """
        Check if response needs disclaimers.
        Returns: List of applicable disclaimer types
        """
        disclaimers_needed = []
        
        for pattern in cls.FINANCIAL_ADVICE_INDICATORS:
            if re.search(pattern, response, re.IGNORECASE):
                disclaimers_needed.append("policy_specific")
                break
        
        return list(set(disclaimers_needed))
    
    @classmethod
    def add_disclaimers(cls, response: str, disclaimer_types: List[str]) -> str:
        """Add appropriate disclaimers to the response."""
        if not disclaimer_types:
            return response
        
        disclaimers = [cls.DISCLAIMERS.get(dt, "") for dt in disclaimer_types if dt in cls.DISCLAIMERS]
        if disclaimers:
            return f"{response}\n\n⚠️ {' '.join(disclaimers)}"
        return response


class ConfidenceEvaluator:
    """Evaluates confidence in RAG responses to detect potential hallucinations."""
    
    @classmethod
    def evaluate_retrieval_confidence(
        cls, 
        query: str, 
        retrieved_chunks: List[Tuple], 
        threshold: float = 0.7
    ) -> Tuple[float, List[str]]:
        """
        Evaluate confidence based on retrieval scores.
        Returns: (confidence_score, warnings)
        """
        warnings = []
        
        if not retrieved_chunks:
            return 0.0, ["No relevant documents found in knowledge base."]
        
        # Get similarity scores (lower is better for FAISS L2 distance)
        scores = [score for _, score in retrieved_chunks]
        
        # Normalize scores (FAISS L2 distance - lower is better)
        # Convert to confidence (0-1 scale, higher is better)
        max_expected_distance = 2.0  # Adjust based on your embedding model
        confidences = [max(0, 1 - (score / max_expected_distance)) for score in scores]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0
        
        if avg_confidence < 0.3:
            warnings.append("Retrieved documents have low relevance to your query.")
        elif avg_confidence < 0.5:
            warnings.append("Response is based on partially relevant documents.")
        
        # Check content overlap
        query_words = set(query.lower().split())
        for doc, score in retrieved_chunks:
            doc_words = set(doc.page_content.lower().split())
            overlap = len(query_words & doc_words) / len(query_words) if query_words else 0
            if overlap < 0.1:
                warnings.append("Query terms not well-represented in retrieved documents.")
                break
        
        return avg_confidence, warnings
    
    @classmethod
    def check_response_grounding(
        cls,
        response: str,
        retrieved_chunks: List[Tuple],
        min_grounding_ratio: float = 0.3
    ) -> Tuple[bool, List[str]]:
        """
        Check if response is grounded in retrieved documents.
        Returns: (is_grounded, warnings)
        """
        warnings = []
        
        if not retrieved_chunks:
            return False, ["Response may not be grounded in policy documents."]
        
        # Combine all retrieved content
        all_context = " ".join([doc.page_content for doc, _ in retrieved_chunks]).lower()
        
        # Extract key terms from response (simple approach)
        response_words = set(response.lower().split())
        context_words = set(all_context.split())
        
        # Check overlap
        overlap = len(response_words & context_words) / len(response_words) if response_words else 0
        
        if overlap < min_grounding_ratio:
            warnings.append("⚠️ Some parts of this response may not be directly from your policy documents.")
        
        return overlap >= min_grounding_ratio, warnings


class AISafetyGuard:
    """Main safety guard combining all safety checks."""
    
    def __init__(self, enable_pii_protection: bool = True):
        self.enable_pii_protection = enable_pii_protection
        self.audit_log = []
    
    def check_input(self, query: str) -> SafetyReport:
        """
        Perform safety checks on user input.
        """
        report = SafetyReport(is_safe=True)
        
        # 1. PII Detection
        if self.enable_pii_protection:
            pii_findings = PIIDetector.detect_pii(query)
            if pii_findings:
                report.flags.append(SafetyFlag.PII_DETECTED)
                report.pii_found = [pii_type for pii_type, _, _ in pii_findings]
                report.warnings.append(
                    f"Personal information detected in your query. "
                    f"For your privacy, please avoid sharing sensitive data."
                )
                report.recommendations.append(
                    "Rephrase your question without personal identifiers."
                )
        
        # 2. Scope Check
        in_scope, violations = ContentModerator.check_scope(query)
        if not in_scope:
            report.flags.append(SafetyFlag.SCOPE_VIOLATION)
            report.warnings.append(
                "Your question may be outside the scope of insurance policy information. "
                "I can help with questions about your insurance coverage, claims, and policy details."
            )
        
        # Update safety status
        report.is_safe = SafetyFlag.HARMFUL_CONTENT not in report.flags
        
        # Log the check
        self._log_audit("input_check", query, report)
        
        return report
    
    def check_output(
        self, 
        response: str, 
        query: str,
        retrieved_chunks: List[Tuple]
    ) -> SafetyReport:
        """
        Perform safety checks on AI output before sending to user.
        """
        report = SafetyReport(is_safe=True)
        
        # 1. Confidence Evaluation
        confidence, conf_warnings = ConfidenceEvaluator.evaluate_retrieval_confidence(
            query, retrieved_chunks
        )
        report.confidence_score = confidence
        
        if confidence < 0.3:
            report.flags.append(SafetyFlag.LOW_CONFIDENCE)
            report.flags.append(SafetyFlag.HALLUCINATION_RISK)
        
        report.warnings.extend(conf_warnings)
        
        # 2. Grounding Check
        is_grounded, grounding_warnings = ConfidenceEvaluator.check_response_grounding(
            response, retrieved_chunks
        )
        if not is_grounded:
            report.flags.append(SafetyFlag.HALLUCINATION_RISK)
        report.warnings.extend(grounding_warnings)
        
        # 3. Disclaimer Check
        disclaimer_types = ContentModerator.needs_disclaimer(response)
        if disclaimer_types:
            report.recommendations.extend(
                [ContentModerator.DISCLAIMERS[dt] for dt in disclaimer_types if dt in ContentModerator.DISCLAIMERS]
            )
        
        # 4. PII in output check
        if self.enable_pii_protection:
            pii_findings = PIIDetector.detect_pii(response)
            if pii_findings:
                report.flags.append(SafetyFlag.PII_DETECTED)
                report.warnings.append("Response contained sensitive information that was redacted.")
        
        report.is_safe = SafetyFlag.HARMFUL_CONTENT not in report.flags
        
        # Log the check
        self._log_audit("output_check", response[:200], report)
        
        return report
    
    def sanitize_input(self, query: str) -> str:
        """Sanitize user input by redacting PII."""
        if self.enable_pii_protection:
            sanitized, _ = PIIDetector.redact_pii(query)
            return sanitized
        return query
    
    def sanitize_output(self, response: str) -> str:
        """Sanitize AI output by redacting any leaked PII."""
        if self.enable_pii_protection:
            sanitized, _ = PIIDetector.redact_pii(response)
            return sanitized
        return response
    
    def _log_audit(self, check_type: str, content_preview: str, report: SafetyReport):
        """Log audit trail for compliance."""
        # Hash the content for privacy in logs
        content_hash = hashlib.sha256(content_preview.encode()).hexdigest()[:16]
        
        log_entry = {
            "timestamp": report.timestamp,
            "check_type": check_type,
            "content_hash": content_hash,
            "flags": [f.value for f in report.flags],
            "is_safe": report.is_safe,
            "confidence": report.confidence_score
        }
        self.audit_log.append(log_entry)
        
        # Also log to application logger
        logger.info(f"[AI_SAFETY] {check_type}: safe={report.is_safe}, flags={[f.value for f in report.flags]}")
    
    def get_audit_log(self) -> List[Dict]:
        """Get audit log for compliance reporting."""
        return self.audit_log.copy()


# Singleton instance
_safety_guard: Optional[AISafetyGuard] = None


def get_safety_guard() -> AISafetyGuard:
    """Get or create the safety guard instance."""
    global _safety_guard
    if _safety_guard is None:
        _safety_guard = AISafetyGuard(enable_pii_protection=True)
    return _safety_guard
