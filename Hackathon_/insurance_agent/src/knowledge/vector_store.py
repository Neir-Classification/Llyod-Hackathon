"""
Vector store management using ChromaDB.
"""
import os
from pathlib import Path
from typing import List, Optional

import chromadb
from chromadb.config import Settings
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain.schema import Document

from src.utils.config import config, CHROMA_DIR


class InsuranceVectorStore:
    """Manage the vector store for insurance policy documents."""
    
    def __init__(
        self,
        persist_directory: Optional[Path] = None,
        collection_name: str = "insurance_policies"
    ):
        self.persist_directory = persist_directory or CHROMA_DIR
        self.collection_name = collection_name
        
        # Initialize embeddings
        self.embeddings = OpenAIEmbeddings(
            model=config.vector_db.embedding_model,
            openai_api_key=config.openai.api_key
        )
        
        # Initialize ChromaDB client
        self.chroma_client = chromadb.PersistentClient(
            path=str(self.persist_directory),
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        self._vectorstore: Optional[Chroma] = None
    
    @property
    def vectorstore(self) -> Chroma:
        """Get or create the vector store."""
        if self._vectorstore is None:
            self._vectorstore = Chroma(
                client=self.chroma_client,
                collection_name=self.collection_name,
                embedding_function=self.embeddings,
                persist_directory=str(self.persist_directory)
            )
        return self._vectorstore
    
    def add_documents(self, documents: List[Document]) -> None:
        """Add documents to the vector store."""
        if not documents:
            print("No documents to add.")
            return
        
        print(f"Adding {len(documents)} documents to vector store...")
        self.vectorstore.add_documents(documents)
        print("Documents added successfully.")
    
    def similarity_search(
        self,
        query: str,
        k: int = 5,
        filter_dict: Optional[dict] = None
    ) -> List[Document]:
        """Search for similar documents."""
        return self.vectorstore.similarity_search(
            query=query,
            k=k,
            filter=filter_dict
        )
    
    def similarity_search_with_score(
        self,
        query: str,
        k: int = 5,
        filter_dict: Optional[dict] = None
    ) -> List[tuple[Document, float]]:
        """Search for similar documents with relevance scores."""
        return self.vectorstore.similarity_search_with_score(
            query=query,
            k=k,
            filter=filter_dict
        )
    
    def hybrid_search(
        self,
        query: str,
        k: int = 5,
        keyword_filter: Optional[str] = None
    ) -> List[Document]:
        """
        Perform hybrid search combining semantic and keyword matching.
        """
        # Get semantic results
        semantic_results = self.similarity_search(query, k=k*2)
        
        # Apply keyword filter if provided
        if keyword_filter:
            keyword_lower = keyword_filter.lower()
            filtered_results = [
                doc for doc in semantic_results
                if keyword_lower in doc.page_content.lower()
            ]
            # If keyword filter removes too many, fallback to semantic
            if len(filtered_results) >= k // 2:
                return filtered_results[:k]
        
        return semantic_results[:k]
    
    def get_collection_stats(self) -> dict:
        """Get statistics about the vector store collection."""
        collection = self.chroma_client.get_collection(self.collection_name)
        return {
            "name": self.collection_name,
            "count": collection.count(),
            "persist_directory": str(self.persist_directory)
        }
    
    def reset_collection(self) -> None:
        """Reset (delete and recreate) the collection."""
        try:
            self.chroma_client.delete_collection(self.collection_name)
            print(f"Collection '{self.collection_name}' deleted.")
        except Exception as e:
            print(f"Collection may not exist: {e}")
        
        self._vectorstore = None
        print(f"Collection '{self.collection_name}' will be recreated on next use.")


def initialize_vector_store(reset: bool = False, include_dataset: bool = True) -> InsuranceVectorStore:
    """
    Initialize the vector store with policy documents.
    
    Args:
        reset: If True, delete existing collection and recreate.
        include_dataset: If True, also load PDFs from the Dataset folder.
    """
    from src.knowledge.document_loader import InsuranceDocumentLoader
    from src.utils.config import POLICIES_DIR, DATASET_DIR, ensure_directories
    
    ensure_directories()
    
    # Create vector store
    vector_store = InsuranceVectorStore()
    
    # Check if we need to initialize
    try:
        stats = vector_store.get_collection_stats()
        if stats["count"] > 0 and not reset:
            print(f"Vector store already initialized with {stats['count']} documents.")
            return vector_store
    except Exception:
        pass  # Collection doesn't exist yet
    
    if reset:
        vector_store.reset_collection()
    
    all_documents = []
    
    # Load markdown documents from data/policies
    loader = InsuranceDocumentLoader(POLICIES_DIR)
    md_documents = loader.load_all_documents()
    if md_documents:
        all_documents.extend(md_documents)
        print(f"Loaded {len(md_documents)} chunks from markdown files")
    
    # Load PDFs from Dataset folder (hackathon data)
    if include_dataset and DATASET_DIR.exists():
        try:
            from src.knowledge.dataset_loader import DatasetLoader
            dataset_loader = DatasetLoader()
            pdf_documents = dataset_loader.load_all_policy_documents()
            if pdf_documents:
                all_documents.extend(pdf_documents)
                print(f"Loaded {len(pdf_documents)} chunks from Dataset PDFs")
        except Exception as e:
            print(f"Warning: Could not load Dataset PDFs: {e}")
    
    if all_documents:
        # Add to vector store
        vector_store.add_documents(all_documents)
        
        # Print stats
        stats = vector_store.get_collection_stats()
        print(f"\nVector store initialized: {stats['count']} documents total")
    else:
        print("No documents found to load.")
    
    return vector_store


if __name__ == "__main__":
    # Initialize with reset to rebuild
    store = initialize_vector_store(reset=True)
    
    # Test search
    print("\n=== Testing Search ===")
    query = "sump pump water backup coverage"
    results = store.similarity_search(query, k=3)
    
    for i, doc in enumerate(results):
        print(f"\n--- Result {i+1} ---")
        print(f"Source: {doc.metadata.get('source')}")
        print(f"Topics: {doc.metadata.get('topics')}")
        print(f"Content: {doc.page_content[:200]}...")
