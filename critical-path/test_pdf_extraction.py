"""
Test PDF extraction to see what content is being loaded.
Run: python3 test_pdf_extraction.py
"""

import csv
from pathlib import Path
from langchain_community.document_loaders import PyPDFLoader

# Setup
BASE_DIR = Path(__file__).resolve().parent

PRAJAS_NIER_DIR = BASE_DIR / "Prajas-Nier"
DATASET_DIR = PRAJAS_NIER_DIR / "Dataset"
PDF_PATHS = [DATASET_DIR / "policy-booklet.pdf", DATASET_DIR / "policy-limits.pdf"]


def load_pdfs(pdf_paths):
    """Load PDFs and add metadata."""
    docs = []
    for path in pdf_paths:
        if not path.exists():
            print(f"❌ PDF not found: {path}")
            continue
        
        print(f"\n{'='*70}")
        print(f"📄 Loading: {path.name}")
        print(f"{'='*70}")
        
        loader = PyPDFLoader(str(path))
        loaded_docs = loader.load()
        policy_name = path.name
        
        print(f"✅ Loaded {len(loaded_docs)} pages")
        
        for doc in loaded_docs:
            doc.metadata["policy_name"] = policy_name
            if "page" in doc.metadata:
                doc.metadata["page_number"] = doc.metadata["page"]
        
        docs.extend(loaded_docs)
    
    return docs


def main():
    print("🔍 PDF EXTRACTION TEST")
    print("="*70 + "\n")
    
    # Load PDFs
    docs = load_pdfs(PDF_PATHS)
    
    if not docs:
        print("\n❌ No documents loaded!")
        return
    
    print(f"\n{'='*70}")
    print(f"📊 SUMMARY")
    print(f"{'='*70}")
    print(f"Total pages loaded: {len(docs)}")
    
    # Show first page content
    print(f"\n{'='*70}")
    print(f"📖 FIRST PAGE SAMPLE")
    print(f"{'='*70}")
    print(f"Policy: {docs[0].metadata.get('policy_name', 'unknown')}")
    print(f"Page: {docs[0].metadata.get('page_number', 'N/A')}")
    print(f"\nContent preview (first 500 chars):")
    print("-"*70)
    print(docs[0].page_content[:500])
    print("-"*70)
    
    # Show full first page
    print(f"\n{'='*70}")
    print(f"📄 FULL FIRST PAGE")
    print(f"{'='*70}")
    print(docs[0].page_content)
    print(f"\n{'='*70}\n")
    
    # Export to CSV
    csv_filename = BASE_DIR / "pdf_extraction_output.csv"
    print(f"💾 Exporting to CSV: {csv_filename}")
    
    with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['policy_name', 'page_number', 'content', 'char_count']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        for doc in docs:
            writer.writerow({
                'policy_name': doc.metadata.get('policy_name', 'unknown'),
                'page_number': doc.metadata.get('page_number', 'N/A'),
                'content': doc.page_content,
                'char_count': len(doc.page_content)
            })
    
    print(f"✅ Exported {len(docs)} pages to CSV")
    print(f"📂 Location: {csv_filename}")
    
    # Also create a summary CSV
    summary_filename = BASE_DIR / "pdf_extraction_summary.csv"
    print(f"\n💾 Creating summary: {summary_filename}")
    
    from collections import Counter
    policy_pages = Counter([doc.metadata.get('policy_name', 'unknown') for doc in docs])
    
    with open(summary_filename, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['policy_name', 'total_pages', 'total_chars', 'avg_chars_per_page']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        for policy_name in sorted(policy_pages.keys()):
            policy_docs = [d for d in docs if d.metadata.get('policy_name') == policy_name]
            total_chars = sum(len(d.page_content) for d in policy_docs)
            writer.writerow({
                'policy_name': policy_name,
                'total_pages': len(policy_docs),
                'total_chars': total_chars,
                'avg_chars_per_page': total_chars // len(policy_docs) if policy_docs else 0
            })
    
    print(f"✅ Summary created")
    print(f"\n{'='*70}")
    print("📊 FILES CREATED:")
    print(f"  1. pdf_extraction_output.csv - Full content of all pages")
    print(f"  2. pdf_extraction_summary.csv - Statistics summary")
    print("="*70)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Exiting...")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
