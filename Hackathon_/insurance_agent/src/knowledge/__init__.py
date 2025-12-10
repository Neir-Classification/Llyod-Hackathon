"""Knowledge module initialization."""
from .document_loader import InsuranceDocumentLoader
from .vector_store import InsuranceVectorStore, initialize_vector_store
from .retriever import PolicyRetriever, RetrievalResult, search_policy

# Try to import dataset loader (requires pymupdf and pandas)
try:
    from .dataset_loader import DatasetLoader, get_dataset_loader
    DATASET_LOADER_AVAILABLE = True
except ImportError:
    DATASET_LOADER_AVAILABLE = False
    DatasetLoader = None
    get_dataset_loader = None

__all__ = [
    "InsuranceDocumentLoader",
    "InsuranceVectorStore",
    "initialize_vector_store",
    "PolicyRetriever",
    "RetrievalResult",
    "search_policy",
    "DatasetLoader",
    "get_dataset_loader",
    "DATASET_LOADER_AVAILABLE"
]
