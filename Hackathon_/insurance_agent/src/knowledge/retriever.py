"""
Retriever module for policy document search.
Combines multiple retrieval strategies for optimal results.
"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from langchain.schema import Document

from src.knowledge.vector_store import InsuranceVectorStore


@dataclass
class RetrievalResult:
    """Structured retrieval result with citations."""
    content: str
    source: str
    section: Optional[str]
    subsection: Optional[str]
    topics: List[str]
    relevance_score: float
    citation: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "content": self.content,
            "source": self.source,
            "section": self.section,
            "subsection": self.subsection,
            "topics": self.topics,
            "relevance_score": self.relevance_score,
            "citation": self.citation
        }


class PolicyRetriever:
    """
    Advanced retriever for insurance policy documents.
    Provides structured results with citations.
    """
    
    def __init__(self, vector_store: Optional[InsuranceVectorStore] = None):
        self.vector_store = vector_store or InsuranceVectorStore()
    
    def _format_citation(self, doc: Document) -> str:
        """Format a citation string from document metadata."""
        source = doc.metadata.get("source", "Unknown")
        section = doc.metadata.get("section", "")
        subsection = doc.metadata.get("subsection", "")
        topic = doc.metadata.get("topic", "")
        
        parts = [source.replace(".md", "").replace("_", " ").title()]
        if section:
            parts.append(f"Section: {section}")
        if subsection:
            parts.append(f"- {subsection}")
        if topic:
            parts.append(f"({topic})")
        
        return " > ".join(parts) if len(parts) > 1 else parts[0]
    
    def _doc_to_result(
        self,
        doc: Document,
        score: float = 0.0
    ) -> RetrievalResult:
        """Convert a Document to a RetrievalResult."""
        return RetrievalResult(
            content=doc.page_content,
            source=doc.metadata.get("source", "unknown"),
            section=doc.metadata.get("section"),
            subsection=doc.metadata.get("subsection"),
            topics=doc.metadata.get("topics", []),
            relevance_score=score,
            citation=self._format_citation(doc)
        )
    
    def search(
        self,
        query: str,
        k: int = 5,
        topic_filter: Optional[str] = None
    ) -> List[RetrievalResult]:
        """
        Search for relevant policy information.
        
        Args:
            query: The search query
            k: Number of results to return
            topic_filter: Optional topic to filter by
        
        Returns:
            List of RetrievalResult objects with citations
        """
        # Get results with scores
        results_with_scores = self.vector_store.similarity_search_with_score(
            query=query,
            k=k * 2  # Get more for potential filtering
        )
        
        # Convert to RetrievalResults
        results = []
        for doc, score in results_with_scores:
            # Apply topic filter if specified
            if topic_filter:
                doc_topics = doc.metadata.get("topics", [])
                if topic_filter.lower() not in [t.lower() for t in doc_topics]:
                    continue
            
            # Convert distance to similarity score (ChromaDB returns L2 distance)
            # Lower distance = higher similarity
            similarity = 1.0 / (1.0 + score)
            
            results.append(self._doc_to_result(doc, similarity))
        
        # Sort by relevance and limit
        results.sort(key=lambda x: x.relevance_score, reverse=True)
        return results[:k]
    
    def search_by_topic(
        self,
        topic: str,
        query: Optional[str] = None,
        k: int = 5
    ) -> List[RetrievalResult]:
        """
        Search within a specific topic area.
        
        Args:
            topic: Topic to search within (e.g., "water", "mold", "theft")
            query: Optional additional query for refinement
            k: Number of results
        """
        search_query = f"{topic} {query}" if query else topic
        return self.search(search_query, k=k, topic_filter=topic)
    
    def get_coverage_info(
        self,
        coverage_type: str,
        k: int = 3
    ) -> List[RetrievalResult]:
        """
        Get information about a specific type of coverage.
        
        Args:
            coverage_type: Type of coverage (e.g., "water backup", "jewelry", "liability")
            k: Number of results
        """
        query = f"{coverage_type} coverage policy"
        return self.search(query, k=k)
    
    def get_exclusion_info(
        self,
        exclusion_type: str,
        k: int = 3
    ) -> List[RetrievalResult]:
        """
        Get information about policy exclusions.
        
        Args:
            exclusion_type: Type of exclusion to check
            k: Number of results
        """
        query = f"{exclusion_type} exclusion not covered"
        results = self.search(query, k=k)
        
        # Prioritize results that mention exclusions
        exclusion_keywords = ["exclusion", "excluded", "not covered", "does not cover", "void"]
        
        def has_exclusion_keyword(result: RetrievalResult) -> bool:
            content_lower = result.content.lower()
            return any(kw in content_lower for kw in exclusion_keywords)
        
        # Sort: exclusion-related first, then by relevance
        results.sort(
            key=lambda x: (not has_exclusion_keyword(x), -x.relevance_score)
        )
        
        return results
    
    def format_results_for_llm(
        self,
        results: List[RetrievalResult]
    ) -> str:
        """
        Format retrieval results for LLM consumption.
        Includes citations for compliance.
        """
        if not results:
            return "No relevant policy information found."
        
        formatted_parts = []
        for i, result in enumerate(results, 1):
            formatted_parts.append(
                f"[Source {i}] {result.citation}\n"
                f"Content: {result.content}\n"
                f"Topics: {', '.join(result.topics)}\n"
            )
        
        return "\n---\n".join(formatted_parts)


# Convenience function for quick searches
def search_policy(query: str, k: int = 5) -> List[RetrievalResult]:
    """Quick search function for policy documents."""
    retriever = PolicyRetriever()
    return retriever.search(query, k=k)


if __name__ == "__main__":
    # Test the retriever
    retriever = PolicyRetriever()
    
    print("=== Testing Policy Retriever ===\n")
    
    # Test 1: General search
    print("Test 1: Sump pump coverage")
    results = retriever.search("sump pump water backup", k=3)
    for r in results:
        print(f"\n{r.citation}")
        print(f"Score: {r.relevance_score:.3f}")
        print(f"Content: {r.content[:150]}...")
    
    # Test 2: Topic-specific search
    print("\n\nTest 2: Mold coverage")
    results = retriever.search_by_topic("mold", "hidden water damage", k=2)
    for r in results:
        print(f"\n{r.citation}")
        print(f"Content: {r.content[:150]}...")
    
    # Test 3: Exclusion search
    print("\n\nTest 3: Flood exclusion")
    results = retriever.get_exclusion_info("flood river overflow", k=2)
    for r in results:
        print(f"\n{r.citation}")
        print(f"Content: {r.content[:150]}...")
    
    # Test 4: LLM formatted output
    print("\n\nTest 4: LLM Formatted Output")
    results = retriever.search("Airbnb rental coverage theft", k=2)
    print(retriever.format_results_for_llm(results))
