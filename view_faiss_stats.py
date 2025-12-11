"""
Quick visualization of FAISS index statistics.
Run: python view_faiss_stats.py
"""

import os
import json
from pathlib import Path
from dotenv import load_dotenv
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

PRAJAS_NIER_DIR = BASE_DIR / "Prajas-Nier"
FAISS_DIR = PRAJAS_NIER_DIR / "artifacts" / "faiss_index"


def main():
    print("📊 FAISS Index Statistics\n")
    
    if not FAISS_DIR.exists():
        print(f"❌ No FAISS index found at: {FAISS_DIR}")
        return
    
    try:
        embeddings = OpenAIEmbeddings(model="text-embedding-3-large")
        vector_store = FAISS.load_local(str(FAISS_DIR), embeddings, allow_dangerous_deserialization=True)
        
        docstore = vector_store.docstore
        index_to_docstore_id = vector_store.index_to_docstore_id
        
        # Basic stats
        total_docs = len(index_to_docstore_id)
        total_vectors = vector_store.index.ntotal
        
        print(f"Total Documents: {total_docs}")
        print(f"Total Vectors: {total_vectors}")
        print(f"Vector Dimension: {vector_store.index.d}")
        
        # Analyze content
        sources = {}
        total_length = 0
        
        for doc_id in index_to_docstore_id.values():
            doc = docstore.search(doc_id)
            source = doc.metadata.get('policy_name', 'unknown')
            page = doc.metadata.get('page_number', 'N/A')
            
            if source not in sources:
                sources[source] = {'count': 0, 'pages': set(), 'total_chars': 0}
            
            sources[source]['count'] += 1
            sources[source]['pages'].add(page)
            sources[source]['total_chars'] += len(doc.page_content)
            total_length += len(doc.page_content)
        
        print("\n📚 Documents by Source:")
        for source, data in sorted(sources.items()):
            pages = len(data['pages'])
            chunks = data['count']
            avg_chunk_size = data['total_chars'] / chunks if chunks > 0 else 0
            print(f"\n  {source}:")
            print(f"    - Pages: {pages}")
            print(f"    - Chunks: {chunks}")
            print(f"    - Avg chunk size: {avg_chunk_size:.0f} chars")
        
        avg_doc_length = total_length / total_docs if total_docs > 0 else 0
        print(f"\n📏 Average Document Length: {avg_doc_length:.0f} characters")
        
        # File sizes
        print("\n💾 File Sizes:")
        for file in FAISS_DIR.iterdir():
            size_mb = file.stat().st_size / (1024 * 1024)
            print(f"  {file.name}: {size_mb:.2f} MB")
        
        # Sample document
        print("\n📄 Sample Document:")
        first_doc_id = list(index_to_docstore_id.values())[0]
        sample_doc = docstore.search(first_doc_id)
        print(f"  Source: {sample_doc.metadata.get('policy_name', 'unknown')}")
        print(f"  Page: {sample_doc.metadata.get('page_number', 'N/A')}")
        print(f"  Content: {sample_doc.page_content[:150]}...")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
