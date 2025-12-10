#!/usr/bin/env python3
"""
Integration test for the Dataset integration.
Tests that PDF and Excel data from the Dataset folder is properly loaded and usable.
"""
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_pdf_loading():
    """Test that policy PDFs can be loaded."""
    print("\n=== Testing PDF Loading ===")
    try:
        import fitz
        from src.utils.config import DATASET_DIR
        
        pdf_path = DATASET_DIR / "policy-booklet.pdf"
        if not pdf_path.exists():
            print(f"❌ PDF not found: {pdf_path}")
            return False
        
        doc = fitz.open(pdf_path)
        print(f"✓ Loaded policy-booklet.pdf: {len(doc)} pages")
        doc.close()
        
        limits_path = DATASET_DIR / "policy-limits.pdf"
        if limits_path.exists():
            doc = fitz.open(limits_path)
            print(f"✓ Loaded policy-limits.pdf: {len(doc)} pages")
            doc.close()
        
        return True
    except Exception as e:
        print(f"❌ PDF loading failed: {e}")
        return False


def test_excel_loading():
    """Test that customer Excel data can be loaded."""
    print("\n=== Testing Excel Loading ===")
    try:
        import pandas as pd
        from src.utils.config import DATASET_DIR
        
        excel_path = DATASET_DIR / "3.1 Agentic AI Servicing Agent in Home Insurance_ai_hackathon_data.xlsx"
        if not excel_path.exists():
            print(f"❌ Excel not found: {excel_path}")
            return False
        
        df = pd.read_excel(excel_path, sheet_name="data")
        print(f"✓ Loaded {len(df)} customer records with {len(df.columns)} columns")
        print(f"  Sample: {df.iloc[0]['FORENAME']} {df.iloc[0]['SURNAME']} - {df.iloc[0]['POLICY_ID']}")
        
        return True
    except Exception as e:
        print(f"❌ Excel loading failed: {e}")
        return False


def test_real_customer_db():
    """Test the real customer database."""
    print("\n=== Testing Real Customer Database ===")
    try:
        from src.database.real_customer_db import get_real_customer_db
        
        db = get_real_customer_db()
        customers = db.get_all_customers()
        print(f"✓ Loaded {len(customers)} customers into database")
        
        if customers:
            c = customers[0]
            print(f"  Sample: {c.full_name}")
            print(f"    Policy ID: {c.policy_id}")
            print(f"    Tier: {c.tier}")
            print(f"    Buildings: {c.has_buildings_cover}, Contents: {c.has_contents_cover}")
            print(f"    Home Emergency: {c.has_home_emergency_cover}")
        
        # Test search
        result = db.search("Frankie")
        if result:
            print(f"✓ Search working: Found {result.full_name}")
        
        # Test coverage check
        if customers:
            check = db.check_coverage(customers[0].policy_id, "buildings")
            print(f"✓ Coverage check working: {check.get('has_coverage')}")
        
        return True
    except Exception as e:
        print(f"❌ Real customer DB failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_dataset_loader():
    """Test the dataset loader for PDFs."""
    print("\n=== Testing Dataset Loader ===")
    try:
        # Import directly to avoid chromadb issues
        import sys
        import fitz
        from pathlib import Path
        from langchain_text_splitters import RecursiveCharacterTextSplitter
        
        DATASET_DIR = Path(__file__).parent.parent / "Dataset"
        
        # Test PDF loading directly
        pdf_path = DATASET_DIR / "policy-booklet.pdf"
        if not pdf_path.exists():
            print(f"❌ PDF not found: {pdf_path}")
            return False
        
        doc = fitz.open(pdf_path)
        pages_content = []
        for page in doc:
            text = page.get_text()
            if text.strip():
                pages_content.append(text)
        doc.close()
        
        print(f"✓ Extracted text from {len(pages_content)} pages")
        
        # Test text splitting
        splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)
        all_chunks = []
        for content in pages_content:
            chunks = splitter.split_text(content)
            all_chunks.extend(chunks)
        
        print(f"✓ Created {len(all_chunks)} chunks for RAG")
        
        return True
    except Exception as e:
        print(f"❌ Dataset loader failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_evaluation_data():
    """Test loading the evaluation queries."""
    print("\n=== Testing Evaluation Data ===")
    try:
        import pandas as pd
        from pathlib import Path
        
        DATASET_DIR = Path(__file__).parent.parent / "Dataset"
        eval_path = DATASET_DIR / "3.1 Agentic AI Servicing Agent in Home Insurance_Copy of TW Home Insurance Evaluate Results - Sample 1.xlsx"
        
        if not eval_path.exists():
            print(f"⚠ Evaluation file not found: {eval_path}")
            return True  # Not a failure if file is optional
        
        eval_data = pd.read_excel(eval_path, sheet_name=None)
        
        if eval_data:
            print(f"✓ Loaded evaluation data with sheets: {list(eval_data.keys())}")
            
            # Show sample query
            for sheet_name, df in eval_data.items():
                if 'query' in df.columns and len(df) > 0:
                    print(f"\n  Sample from '{sheet_name}':")
                    print(f"    Query: {str(df.iloc[0]['query'])[:100]}...")
                    if 'response' in df.columns:
                        print(f"    Response: {str(df.iloc[0]['response'])[:100]}...")
                    break
        else:
            print("⚠ No evaluation data loaded")
        
        return True
    except Exception as e:
        print(f"❌ Evaluation data loading failed: {e}")
        return False


def main():
    """Run all integration tests."""
    print("=" * 60)
    print("  Dataset Integration Test Suite")
    print("=" * 60)
    
    results = {
        "PDF Loading": test_pdf_loading(),
        "Excel Loading": test_excel_loading(),
        "Real Customer DB": test_real_customer_db(),
        "Dataset Loader": test_dataset_loader(),
        "Evaluation Data": test_evaluation_data(),
    }
    
    print("\n" + "=" * 60)
    print("  Test Results Summary")
    print("=" * 60)
    
    all_passed = True
    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "❌ FAIL"
        print(f"  {status}: {test_name}")
        if not passed:
            all_passed = False
    
    print("=" * 60)
    
    if all_passed:
        print("  All tests passed! Dataset integration is working.")
    else:
        print("  Some tests failed. Check the output above.")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
