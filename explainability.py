"""
Explainability Module for RAG Pipeline

This module provides explainability features including:
- Source attribution and citations
- Confidence scoring
- Decision reasoning
- Transparency in AI responses
"""

import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json

logger = logging.getLogger(__name__)


class ReasoningType(Enum):
    """Types of reasoning used in response generation."""
    DIRECT_RETRIEVAL = "direct_retrieval"  # Answer found directly in documents
    SYNTHESIS = "synthesis"  # Answer synthesized from multiple sources
    INFERENCE = "inference"  # Answer inferred from context
    POLICY_APPLICATION = "policy_application"  # Applying policy rules to situation
    NO_INFORMATION = "no_information"  # No relevant information found


@dataclass
class SourceAttribution:
    """Attribution to a specific source document."""
    policy_name: str
    page_number: int | str
    section: Optional[str] = None
    quote: Optional[str] = None
    relevance_score: float = 0.0
    
    def to_dict(self) -> Dict:
        return {
            "policy_name": self.policy_name,
            "page_number": self.page_number,
            "section": self.section,
            "quote": self.quote,
            "relevance_score": round(self.relevance_score, 3)
        }


@dataclass
class ExplainableResponse:
    """An AI response with full explainability metadata."""
    response_text: str
    query: str
    
    # Source Attribution
    sources: List[SourceAttribution] = field(default_factory=list)
    
    # Confidence & Reasoning
    confidence_score: float = 1.0
    reasoning_type: ReasoningType = ReasoningType.DIRECT_RETRIEVAL
    reasoning_explanation: str = ""
    
    # Transparency
    model_used: str = "gpt-4o-mini"
    retrieval_method: str = "semantic_similarity"
    num_chunks_retrieved: int = 0
    processing_time_ms: Optional[float] = None
    
    # Safety
    safety_flags: List[str] = field(default_factory=list)
    disclaimers: List[str] = field(default_factory=list)
    
    # Limitations
    limitations: List[str] = field(default_factory=list)
    
    # Metadata
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    session_id: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            "response": self.response_text,
            "query": self.query,
            "explainability": {
                "sources": [s.to_dict() for s in self.sources],
                "confidence": {
                    "score": round(self.confidence_score, 3),
                    "level": self._confidence_level(),
                    "explanation": self._confidence_explanation()
                },
                "reasoning": {
                    "type": self.reasoning_type.value,
                    "explanation": self.reasoning_explanation
                },
                "transparency": {
                    "model": self.model_used,
                    "retrieval_method": self.retrieval_method,
                    "chunks_retrieved": self.num_chunks_retrieved,
                    "processing_time_ms": self.processing_time_ms
                },
                "limitations": self.limitations
            },
            "safety": {
                "flags": self.safety_flags,
                "disclaimers": self.disclaimers
            },
            "metadata": {
                "timestamp": self.timestamp,
                "session_id": self.session_id
            }
        }
    
    def _confidence_level(self) -> str:
        """Convert confidence score to human-readable level."""
        if self.confidence_score >= 0.8:
            return "high"
        elif self.confidence_score >= 0.5:
            return "medium"
        else:
            return "low"
    
    def _confidence_explanation(self) -> str:
        """Generate human-readable confidence explanation."""
        level = self._confidence_level()
        if level == "high":
            return "This response is strongly supported by your policy documents."
        elif level == "medium":
            return "This response is partially supported by your policy documents. Please verify with your policy."
        else:
            return "Limited relevant information was found. Please consult your full policy documents or contact support."
    
    def get_summary_for_voice(self) -> str:
        """Get a voice-friendly summary including key explainability info."""
        confidence_note = ""
        if self.confidence_score < 0.5:
            confidence_note = " Please note that I had limited information to answer this question fully."
        
        source_note = ""
        if self.sources:
            primary_source = self.sources[0]
            source_note = f" This information is from {primary_source.policy_name}, page {primary_source.page_number}."
        
        return f"{self.response_text}{source_note}{confidence_note}"


class ExplainabilityEngine:
    """Engine for generating explainable AI responses."""
    
    def __init__(self):
        self.explanation_templates = {
            ReasoningType.DIRECT_RETRIEVAL: "This answer was found directly in your policy documents.",
            ReasoningType.SYNTHESIS: "This answer was compiled from multiple sections of your policy.",
            ReasoningType.INFERENCE: "This answer was inferred based on related policy information.",
            ReasoningType.POLICY_APPLICATION: "This answer applies your policy rules to your specific situation.",
            ReasoningType.NO_INFORMATION: "I couldn't find specific information about this in your policy documents."
        }
    
    def create_source_attributions(
        self, 
        retrieved_chunks: List[Tuple],
        max_sources: int = 3
    ) -> List[SourceAttribution]:
        """Create source attributions from retrieved chunks."""
        sources = []
        
        for doc, score in retrieved_chunks[:max_sources]:
            # Extract section from content if available (look for headers)
            content = doc.page_content
            section = self._extract_section_header(content)
            
            # Get a relevant quote (first 150 chars)
            quote = content[:150].strip() + "..." if len(content) > 150 else content
            
            # Convert FAISS distance to relevance (inverse relationship)
            # FAISS L2 distance: lower is better
            # Ensure we convert to native Python float to avoid JSON serialization issues
            relevance = float(max(0, 1 - (float(score) / 2.0)))  # Normalize assuming max distance ~2
            
            source = SourceAttribution(
                policy_name=doc.metadata.get("policy_name", "Unknown Policy"),
                page_number=doc.metadata.get("page_number", "N/A"),
                section=section,
                quote=quote,
                relevance_score=relevance
            )
            sources.append(source)
        
        return sources
    
    def _extract_section_header(self, content: str) -> Optional[str]:
        """Extract section header from content."""
        lines = content.split('\n')
        for line in lines[:5]:  # Check first 5 lines
            line = line.strip()
            if line.startswith('###') or line.startswith('##'):
                return line.replace('#', '').strip()
            if line.isupper() and len(line) < 100:  # All caps header
                return line.title()
        return None
    
    def determine_reasoning_type(
        self, 
        query: str, 
        retrieved_chunks: List[Tuple],
        response: str
    ) -> Tuple[ReasoningType, str]:
        """Determine what type of reasoning was used to generate the response."""
        
        if not retrieved_chunks:
            return ReasoningType.NO_INFORMATION, self.explanation_templates[ReasoningType.NO_INFORMATION]
        
        # Calculate average relevance - ensure float conversion for numpy compatibility
        avg_relevance = sum(1 - (float(score) / 2.0) for _, score in retrieved_chunks) / len(retrieved_chunks)
        
        # Check if multiple sources were needed
        if len(retrieved_chunks) > 1 and avg_relevance > 0.5:
            reasoning_type = ReasoningType.SYNTHESIS
        elif avg_relevance > 0.7:
            reasoning_type = ReasoningType.DIRECT_RETRIEVAL
        elif avg_relevance > 0.4:
            reasoning_type = ReasoningType.POLICY_APPLICATION
        else:
            reasoning_type = ReasoningType.INFERENCE
        
        explanation = self.explanation_templates[reasoning_type]
        
        # Add source-specific context
        if retrieved_chunks:
            primary_source = retrieved_chunks[0][0].metadata.get("policy_name", "your policy")
            if reasoning_type == ReasoningType.DIRECT_RETRIEVAL:
                explanation = f"This answer was found directly in {primary_source}."
            elif reasoning_type == ReasoningType.SYNTHESIS:
                sources = set(doc.metadata.get("policy_name", "policy") for doc, _ in retrieved_chunks)
                explanation = f"This answer was compiled from {', '.join(sources)}."
        
        return reasoning_type, explanation
    
    def calculate_confidence(
        self, 
        retrieved_chunks: List[Tuple],
        query: str,
        response: str
    ) -> float:
        """Calculate overall confidence score for the response."""
        
        if not retrieved_chunks:
            return 0.1
        
        # Factor 1: Retrieval relevance (40% weight)
        # Convert scores to native Python floats to avoid numpy float32 issues
        scores = [float(score) for _, score in retrieved_chunks]
        avg_distance = sum(scores) / len(scores)
        retrieval_confidence = max(0, 1 - (avg_distance / 2.0))
        
        # Factor 2: Query-document overlap (30% weight)
        query_terms = set(query.lower().split())
        all_content = " ".join([doc.page_content for doc, _ in retrieved_chunks]).lower()
        content_terms = set(all_content.split())
        
        overlap = len(query_terms & content_terms) / max(len(query_terms), 1)
        
        # Factor 3: Number of supporting sources (30% weight)
        source_factor = min(len(retrieved_chunks) / 3, 1.0)  # Normalize to max 3 sources
        
        # Weighted combination
        confidence = (
            retrieval_confidence * 0.6 +
            overlap * 0.2 +
            source_factor * 0.2
        )
        
        return float(min(max(confidence, 0.0), 1.0))
    
    def identify_limitations(
        self,
        query: str,
        retrieved_chunks: List[Tuple],
        confidence: float
    ) -> List[str]:
        """Identify limitations of the response."""
        limitations = []
        
        if confidence < 0.5:
            limitations.append(
                "Limited relevant information found in the knowledge base for this specific query."
            )
        
        if not retrieved_chunks:
            limitations.append(
                "No matching policy documents were retrieved for this question."
            )
        
        # Check if query mentions specific scenarios not well covered
        scenario_keywords = ["specific", "my situation", "in my case", "exactly"]
        if any(kw in query.lower() for kw in scenario_keywords):
            limitations.append(
                "Individual circumstances may vary. Please consult your policy or agent for personalized advice."
            )
        
        # Check for time-sensitive queries
        time_keywords = ["current", "today", "now", "latest", "recent"]
        if any(kw in query.lower() for kw in time_keywords):
            limitations.append(
                "Policy information may have been updated since this knowledge base was created."
            )
        
        return limitations
    
    def generate_explainable_response(
        self,
        response_text: str,
        query: str,
        retrieved_chunks: List[Tuple],
        model_used: str = "gpt-4o-mini",
        processing_time_ms: Optional[float] = None,
        safety_flags: List[str] = None,
        disclaimers: List[str] = None,
        session_id: Optional[str] = None
    ) -> ExplainableResponse:
        """Generate a fully explainable response."""
        
        # Create source attributions
        sources = self.create_source_attributions(retrieved_chunks)
        
        # Determine reasoning type
        reasoning_type, reasoning_explanation = self.determine_reasoning_type(
            query, retrieved_chunks, response_text
        )
        
        # Calculate confidence
        confidence = self.calculate_confidence(retrieved_chunks, query, response_text)
        
        # Identify limitations
        limitations = self.identify_limitations(query, retrieved_chunks, confidence)
        
        return ExplainableResponse(
            response_text=response_text,
            query=query,
            sources=sources,
            confidence_score=confidence,
            reasoning_type=reasoning_type,
            reasoning_explanation=reasoning_explanation,
            model_used=model_used,
            retrieval_method="semantic_similarity",
            num_chunks_retrieved=len(retrieved_chunks),
            processing_time_ms=processing_time_ms,
            safety_flags=safety_flags or [],
            disclaimers=disclaimers or [],
            limitations=limitations,
            session_id=session_id
        )


# Citation formatter for different output formats
class CitationFormatter:
    """Format citations for different output contexts."""
    
    @staticmethod
    def format_for_text(sources: List[SourceAttribution]) -> str:
        """Format citations for text display."""
        if not sources:
            return ""
        
        citations = []
        for i, source in enumerate(sources, 1):
            citation = f"[{i}] {source.policy_name}"
            if source.page_number != "N/A":
                citation += f", Page {source.page_number}"
            if source.section:
                citation += f" - {source.section}"
            citations.append(citation)
        
        return "\n\n📚 Sources:\n" + "\n".join(citations)
    
    @staticmethod
    def format_for_voice(sources: List[SourceAttribution]) -> str:
        """Format citations for voice output (brief)."""
        if not sources:
            return ""
        
        primary = sources[0]
        text = f"This information comes from {primary.policy_name}"
        if primary.page_number != "N/A":
            text += f", page {primary.page_number}"
        
        if len(sources) > 1:
            text += f", and {len(sources) - 1} other source{'s' if len(sources) > 2 else ''}"
        
        return text + "."
    
    @staticmethod
    def format_inline(sources: List[SourceAttribution], response: str) -> str:
        """Add inline citations to response text."""
        if not sources:
            return response
        
        # Add citation marker at end
        citation_refs = ", ".join([f"[{i+1}]" for i in range(len(sources))])
        return f"{response} {citation_refs}"


# Singleton instance
_explainability_engine: Optional[ExplainabilityEngine] = None


def get_explainability_engine() -> ExplainabilityEngine:
    """Get or create the explainability engine instance."""
    global _explainability_engine
    if _explainability_engine is None:
        _explainability_engine = ExplainabilityEngine()
    return _explainability_engine
