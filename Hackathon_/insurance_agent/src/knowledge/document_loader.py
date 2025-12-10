"""
Document loader for insurance policy documents.
Handles chunking and metadata extraction.
"""
import os
import re
from pathlib import Path
from typing import List, Dict, Any
from dataclasses import dataclass

from langchain_text_splitters import RecursiveCharacterTextSplitter, MarkdownHeaderTextSplitter
from langchain_core.documents import Document


@dataclass
class PolicyChunk:
    """Represents a chunk of policy document with metadata."""
    content: str
    metadata: Dict[str, Any]


class InsuranceDocumentLoader:
    """Load and process insurance policy documents."""
    
    def __init__(self, policies_dir: Path):
        self.policies_dir = policies_dir
        
        # Markdown header splitter for structure-aware chunking
        self.header_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=[
                ("#", "section"),
                ("##", "subsection"),
                ("###", "topic"),
            ]
        )
        
        # Secondary splitter for large sections
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
    
    def load_markdown_file(self, file_path: Path) -> List[Document]:
        """Load and chunk a markdown file."""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # First pass: split by headers
        header_docs = self.header_splitter.split_text(content)
        
        documents = []
        for doc in header_docs:
            # Extract metadata from headers
            metadata = {
                "source": file_path.name,
                "file_path": str(file_path),
                **doc.metadata
            }
            
            # Add topic classification
            metadata["topics"] = self._classify_content(doc.page_content)
            
            # If chunk is too large, split further
            if len(doc.page_content) > 600:
                sub_chunks = self.text_splitter.split_text(doc.page_content)
                for i, chunk in enumerate(sub_chunks):
                    chunk_metadata = {**metadata, "chunk_index": i}
                    documents.append(Document(
                        page_content=chunk,
                        metadata=chunk_metadata
                    ))
            else:
                documents.append(Document(
                    page_content=doc.page_content,
                    metadata=metadata
                ))
        
        return documents
    
    def _classify_content(self, content: str) -> List[str]:
        """Classify content by topic for better retrieval."""
        content_lower = content.lower()
        topics = []
        
        topic_keywords = {
            "water": ["water", "flood", "sump", "pipe", "plumbing", "sewage", "backup", "overflow", "drainage"],
            "mold": ["mold", "fungus", "mildew", "rot"],
            "theft": ["theft", "stolen", "burglary", "robbery"],
            "fire": ["fire", "lightning", "smoke", "burn"],
            "wind": ["wind", "hail", "storm", "hurricane", "tornado"],
            "liability": ["liability", "lawsuit", "injury", "damage to others", "medical payments"],
            "jewelry": ["jewelry", "watch", "ring", "precious", "valuable", "scheduled", "floater", "rider"],
            "rental": ["rental", "airbnb", "vrbo", "tenant", "landlord", "short-term"],
            "tree": ["tree", "fallen", "branch", "shrub", "landscaping"],
            "coverage": ["coverage", "covered", "cover", "limit", "deductible"],
            "exclusion": ["exclusion", "excluded", "not covered", "does not cover", "void"],
            "claim": ["claim", "report", "loss", "damage", "file"],
            "endorsement": ["endorsement", "rider", "add-on", "additional coverage"],
            "dwelling": ["dwelling", "home", "house", "residence", "structure"],
            "personal_property": ["personal property", "contents", "belongings", "possessions"],
            "business": ["business", "commercial", "professional", "home office"]
        }
        
        for topic, keywords in topic_keywords.items():
            if any(kw in content_lower for kw in keywords):
                topics.append(topic)
        
        return topics if topics else ["general"]
    
    def load_all_documents(self) -> List[Document]:
        """Load all policy documents from the policies directory."""
        all_documents = []
        
        for file_path in self.policies_dir.glob("*.md"):
            print(f"Loading: {file_path.name}")
            docs = self.load_markdown_file(file_path)
            all_documents.extend(docs)
            print(f"  - Created {len(docs)} chunks")
        
        print(f"\nTotal documents loaded: {len(all_documents)}")
        return all_documents
    
    def get_document_stats(self, documents: List[Document]) -> Dict[str, Any]:
        """Get statistics about loaded documents."""
        topics_count = {}
        sources = set()
        
        for doc in documents:
            sources.add(doc.metadata.get("source", "unknown"))
            for topic in doc.metadata.get("topics", []):
                topics_count[topic] = topics_count.get(topic, 0) + 1
        
        return {
            "total_chunks": len(documents),
            "sources": list(sources),
            "topics_distribution": topics_count,
            "avg_chunk_length": sum(len(d.page_content) for d in documents) / len(documents) if documents else 0
        }


if __name__ == "__main__":
    from src.utils.config import POLICIES_DIR, ensure_directories
    
    ensure_directories()
    
    loader = InsuranceDocumentLoader(POLICIES_DIR)
    documents = loader.load_all_documents()
    
    stats = loader.get_document_stats(documents)
    print("\n=== Document Statistics ===")
    print(f"Total chunks: {stats['total_chunks']}")
    print(f"Sources: {stats['sources']}")
    print(f"Average chunk length: {stats['avg_chunk_length']:.0f} chars")
    print(f"Topics distribution: {stats['topics_distribution']}")
