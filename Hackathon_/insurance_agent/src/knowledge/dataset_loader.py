"""
Dataset loader for the hackathon dataset.
Handles PDF policy documents and Excel customer/evaluation data.
"""
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

import pandas as pd
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

try:
    import fitz  # pymupdf
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False
    print("Warning: pymupdf not installed. PDF loading disabled.")

from src.utils.config import DATASET_DIR


@dataclass  
class PDFPage:
    """Represents a page from a PDF document."""
    page_number: int
    content: str
    metadata: Dict[str, Any]


class DatasetLoader:
    """
    Load and process the hackathon dataset including:
    - policy-booklet.pdf: Full policy documentation (40 pages)
    - policy-limits.pdf: Coverage limits by tier (3 pages)
    - ai_hackathon_data.xlsx: Customer policy data (125 customers, 106 columns)
    - Evaluate Results.xlsx: Test queries and expected responses
    """
    
    def __init__(self, dataset_dir: Optional[Path] = None):
        self.dataset_dir = dataset_dir or DATASET_DIR
        
        # File paths
        self.policy_booklet_path = self.dataset_dir / "policy-booklet.pdf"
        self.policy_limits_path = self.dataset_dir / "policy-limits.pdf"
        self.customer_data_path = self.dataset_dir / "3.1 Agentic AI Servicing Agent in Home Insurance_ai_hackathon_data.xlsx"
        self.eval_data_path = self.dataset_dir / "3.1 Agentic AI Servicing Agent in Home Insurance_Copy of TW Home Insurance Evaluate Results - Sample 1.xlsx"
        
        # Text splitter for chunking
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=800,
            chunk_overlap=100,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        
        # Topic keywords for classification
        self.topic_keywords = {
            "buildings": ["buildings", "building", "structure", "roof", "walls", "windows", "ceilings", "fixtures", "rebuild"],
            "contents": ["contents", "belongings", "possessions", "furniture", "clothing", "electronic", "carpets"],
            "water": ["water", "flood", "leak", "leaking", "plumbing", "metered", "drain", "blocked"],
            "fire": ["fire", "smoke", "lightning", "burn"],
            "theft": ["theft", "stolen", "burglary", "robbery"],
            "accidental_damage": ["accidental damage", "accidentally", "damage cover"],
            "legal": ["legal", "expenses", "disputes", "personal injury", "negligence", "legal responsibility"],
            "home_emergency": ["emergency", "repairs", "heating", "plumbing", "electrics", "roofing", "locks", "helpline"],
            "away_from_home": ["away from home", "temporarily", "student", "university", "rings", "watches", "bikes", "laptops"],
            "specified_items": ["specified items", "jewellery", "jewelry", "valuable", "£2,000", "£2000"],
            "excess": ["excess", "deductible"],
            "limits": ["limit", "limits", "cover limit", "maximum"],
            "claim": ["claim", "claims", "claiming", "report"],
            "subsidence": ["subsidence"],
            "liability": ["liability", "legal responsibility", "employer", "tenants"],
            "contact": ["contact", "helpline", "phone", "call", "0345", "0987"],
            "coverage_tiers": ["bronze", "silver", "gold", "landlord"]
        }
    
    def _classify_content(self, content: str) -> List[str]:
        """Classify content by topic for better retrieval."""
        content_lower = content.lower()
        topics = []
        
        for topic, keywords in self.topic_keywords.items():
            if any(kw in content_lower for kw in keywords):
                topics.append(topic)
        
        return topics if topics else ["general"]
    
    def load_pdf(self, pdf_path: Path, source_name: str) -> List[PDFPage]:
        """Load a PDF file and extract text from each page."""
        if not PYMUPDF_AVAILABLE:
            print(f"Cannot load PDF {pdf_path}: pymupdf not installed")
            return []
        
        if not pdf_path.exists():
            print(f"PDF not found: {pdf_path}")
            return []
        
        pages = []
        doc = fitz.open(pdf_path)
        
        for page_num, page in enumerate(doc):
            text = page.get_text()
            # Clean up the text
            text = self._clean_pdf_text(text)
            
            if text.strip():  # Only add non-empty pages
                pages.append(PDFPage(
                    page_number=page_num + 1,
                    content=text,
                    metadata={
                        "source": source_name,
                        "file_path": str(pdf_path),
                        "page": page_num + 1,
                        "total_pages": len(doc)
                    }
                ))
        
        doc.close()
        print(f"Loaded {len(pages)} pages from {source_name}")
        return pages
    
    def _clean_pdf_text(self, text: str) -> str:
        """Clean up extracted PDF text."""
        # Remove classification markers
        text = text.replace("Classification: Public", "")
        # Normalize whitespace
        lines = text.split('\n')
        cleaned_lines = []
        for line in lines:
            line = line.strip()
            if line:
                cleaned_lines.append(line)
        return '\n'.join(cleaned_lines)
    
    def load_policy_booklet(self) -> List[Document]:
        """Load the main policy booklet PDF and chunk it for RAG."""
        pages = self.load_pdf(self.policy_booklet_path, "policy_booklet")
        
        documents = []
        for page in pages:
            # Split page content into chunks
            chunks = self.text_splitter.split_text(page.content)
            
            for chunk_idx, chunk in enumerate(chunks):
                topics = self._classify_content(chunk)
                doc = Document(
                    page_content=chunk,
                    metadata={
                        **page.metadata,
                        "chunk_index": chunk_idx,
                        "topics": topics,
                        "document_type": "policy_booklet"
                    }
                )
                documents.append(doc)
        
        print(f"Created {len(documents)} chunks from policy booklet")
        return documents
    
    def load_policy_limits(self) -> List[Document]:
        """Load the policy limits PDF."""
        pages = self.load_pdf(self.policy_limits_path, "policy_limits")
        
        documents = []
        for page in pages:
            # For limits document, keep chunks larger to preserve table context
            chunks = self.text_splitter.split_text(page.content)
            
            for chunk_idx, chunk in enumerate(chunks):
                topics = self._classify_content(chunk)
                topics.append("limits")  # Always add limits topic
                doc = Document(
                    page_content=chunk,
                    metadata={
                        **page.metadata,
                        "chunk_index": chunk_idx,
                        "topics": list(set(topics)),
                        "document_type": "policy_limits"
                    }
                )
                documents.append(doc)
        
        print(f"Created {len(documents)} chunks from policy limits")
        return documents
    
    def load_all_policy_documents(self) -> List[Document]:
        """Load all policy documents (PDFs) for the vector store."""
        all_docs = []
        
        # Load PDFs from Dataset folder
        all_docs.extend(self.load_policy_booklet())
        all_docs.extend(self.load_policy_limits())
        
        print(f"\nTotal policy document chunks: {len(all_docs)}")
        return all_docs
    
    def load_customer_data(self) -> pd.DataFrame:
        """Load the customer/policy data from Excel."""
        if not self.customer_data_path.exists():
            print(f"Customer data not found: {self.customer_data_path}")
            return pd.DataFrame()
        
        df = pd.read_excel(self.customer_data_path, sheet_name="data")
        print(f"Loaded {len(df)} customer records with {len(df.columns)} columns")
        return df
    
    def load_data_dictionary(self) -> pd.DataFrame:
        """Load the data dictionary explaining column meanings."""
        if not self.customer_data_path.exists():
            return pd.DataFrame()
        
        df = pd.read_excel(self.customer_data_path, sheet_name="data_dictionary")
        return df
    
    def load_evaluation_queries(self) -> Dict[str, pd.DataFrame]:
        """Load the evaluation queries and expected responses."""
        if not self.eval_data_path.exists():
            print(f"Evaluation data not found: {self.eval_data_path}")
            return {}
        
        sheets = pd.read_excel(self.eval_data_path, sheet_name=None)
        print(f"Loaded evaluation data with sheets: {list(sheets.keys())}")
        return sheets
    
    def get_customer_by_policy_id(self, policy_id: str, df: pd.DataFrame = None) -> Optional[Dict[str, Any]]:
        """Get a customer record by policy ID."""
        if df is None:
            df = self.load_customer_data()
        
        if df.empty:
            return None
        
        matches = df[df['POLICY_ID'] == policy_id]
        if matches.empty:
            return None
        
        return matches.iloc[0].to_dict()
    
    def get_customer_by_name(self, first_name: str = None, surname: str = None, df: pd.DataFrame = None) -> List[Dict[str, Any]]:
        """Search for customers by name."""
        if df is None:
            df = self.load_customer_data()
        
        if df.empty:
            return []
        
        mask = pd.Series([True] * len(df))
        
        if first_name:
            mask &= df['FORENAME'].str.lower().str.contains(first_name.lower(), na=False)
        if surname:
            mask &= df['SURNAME'].str.lower().str.contains(surname.lower(), na=False)
        
        matches = df[mask]
        return matches.to_dict('records')


def get_dataset_loader() -> DatasetLoader:
    """Get a dataset loader instance."""
    return DatasetLoader()


if __name__ == "__main__":
    loader = DatasetLoader()
    
    # Test loading documents
    print("\n=== Loading Policy Documents ===")
    docs = loader.load_all_policy_documents()
    
    # Test loading customer data
    print("\n=== Loading Customer Data ===")
    customers = loader.load_customer_data()
    if not customers.empty:
        print(f"Sample customer: {customers.iloc[0]['FORENAME']} {customers.iloc[0]['SURNAME']}")
        print(f"Policy: {customers.iloc[0]['POLICY_ID']}")
