"""
Comprehensive script to check and validate FAISS index embeddings.
Run: python check_embeddings.py
"""

import os
import numpy as np
from pathlib import Path
from dotenv import load_dotenv
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings

# Fix OpenMP error on macOS
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'

# Setup
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

PRAJAS_NIER_DIR = BASE_DIR / "Prajas-Nier"
FAISS_DIR = PRAJAS_NIER_DIR / "artifacts" / "faiss_index"


def check_embeddings():
    """Check FAISS embeddings health and quality."""
    
    print("🔍 FAISS EMBEDDINGS HEALTH CHECK")
    print("="*70 + "\n")
    
    # Check if index exists
    if not FAISS_DIR.exists():
        print(f"❌ FAISS index not found at: {FAISS_DIR}")
        print(f"💡 Run: python rebuild_embeddings.py")
        return
    
    print(f"✅ Index directory found: {FAISS_DIR}\n")
    
    # Check files
    print("📁 FILES IN INDEX:")
    print("-" * 70)
    index_file = FAISS_DIR / "index.faiss"
    pkl_file = FAISS_DIR / "index.pkl"
    
    for file in [index_file, pkl_file]:
        if file.exists():
            size_mb = file.stat().st_size / (1024 * 1024)
            print(f"✅ {file.name}: {size_mb:.2f} MB")
        else:
            print(f"❌ {file.name}: MISSING")
    
    if not index_file.exists() or not pkl_file.exists():
        print("\n❌ Required files missing. Rebuild the index.")
        return
    
    print("\n" + "="*70)
    
    # Load index
    try:
        print("\n📊 LOADING INDEX...")
        embeddings = OpenAIEmbeddings(model="text-embedding-3-large")
        vector_store = FAISS.load_local(
            str(FAISS_DIR), 
            embeddings, 
            allow_dangerous_deserialization=True
        )
        print("✅ Index loaded successfully\n")
        
    except Exception as e:
        print(f"❌ Failed to load index: {e}")
        return
    
    # Get index info
    index = vector_store.index
    docstore = vector_store.docstore
    index_to_docstore_id = vector_store.index_to_docstore_id
    
    print("="*70)
    print("📐 INDEX STATISTICS")
    print("="*70)
    print(f"Total vectors: {index.ntotal}")
    print(f"Vector dimension: {index.d}")
    print(f"Total documents: {len(index_to_docstore_id)}")
    print(f"Index trained: {index.is_trained}")
    
    # Check document distribution
    print("\n" + "="*70)
    print("📚 DOCUMENT DISTRIBUTION")
    print("="*70)
    
    sources = {}
    pages = {}
    chunk_sizes = []
    
    for idx, doc_id in index_to_docstore_id.items():
        doc = docstore.search(doc_id)
        source = doc.metadata.get('policy_name', 'unknown')
        page = doc.metadata.get('page_number', 'N/A')
        
        sources[source] = sources.get(source, 0) + 1
        
        if source not in pages:
            pages[source] = set()
        pages[source].add(page)
        
        chunk_sizes.append(len(doc.page_content))
    
    for source, count in sorted(sources.items()):
        page_count = len(pages.get(source, []))
        print(f"\n{source}:")
        print(f"  Chunks: {count}")
        print(f"  Pages: {page_count}")
        print(f"  Avg chunks/page: {count/page_count if page_count > 0 else 0:.1f}")
    
    # Chunk size statistics
    print("\n" + "="*70)
    print("📏 CHUNK SIZE STATISTICS")
    print("="*70)
    print(f"Min chunk size: {min(chunk_sizes)} chars")
    print(f"Max chunk size: {max(chunk_sizes)} chars")
    print(f"Average chunk size: {np.mean(chunk_sizes):.1f} chars")
    print(f"Median chunk size: {np.median(chunk_sizes):.1f} chars")
    
    # Check for empty or very small chunks
    small_chunks = [s for s in chunk_sizes if s < 50]
    if small_chunks:
        print(f"\n⚠️  Warning: {len(small_chunks)} chunks smaller than 50 chars")
    
    # Sample embeddings quality
    print("\n" + "="*70)
    print("🧪 EMBEDDING QUALITY CHECK")
    print("="*70)
    
    # Get a few random vectors
    sample_size = min(5, index.ntotal)
    sample_indices = np.random.choice(index.ntotal, sample_size, replace=False)
    
    print(f"\nChecking {sample_size} random embeddings:")
    for i, idx in enumerate(sample_indices, 1):
        vector = index.reconstruct(int(idx))
        
        # Check for issues
        has_nan = np.isnan(vector).any()
        has_inf = np.isinf(vector).any()
        norm = np.linalg.norm(vector)
        
        status = "✅" if not (has_nan or has_inf) else "❌"
        print(f"{status} Embedding {i}: norm={norm:.4f}, has_nan={has_nan}, has_inf={has_inf}")
    
    # Test search functionality
    print("\n" + "="*70)
    print("🔎 INTERACTIVE SEARCH")
    print("="*70)
    print("\n💡 Type your questions to search the embeddings.")
    print("   Commands: 'quit' or 'exit' to stop, 'skip' to skip to next section\n")
    
    while True:
        try:
            query = input("❓ Your question (or 'skip' to continue): ").strip()
            
            if query.lower() in ['quit', 'exit', 'q']:
                print("\n👋 Exiting...")
                return
            
            if query.lower() == 'skip' or not query:
                break
            
            print(f"\n🔍 Searching for: '{query}'")
            results = vector_store.similarity_search_with_score(query, k=3)
            
            print(f"\n📋 Found {len(results)} results:\n")
            for i, (doc, score) in enumerate(results, 1):
                source = doc.metadata.get('policy_name', 'unknown')
                page = doc.metadata.get('page_number', 'N/A')
                
                print(f"{'='*70}")
                print(f"Result {i}: Score={score:.4f}")
                print(f"Source: {source} | Page: {page}")
                print(f"\n📄 FULL CONTENT:")
                print(f"{'-'*70}")
                print(doc.page_content)
                print(f"{'-'*70}\n")
            
        except KeyboardInterrupt:
            print("\n\n👋 Interrupted by user")
            return
        except EOFError:
            break
        except Exception as e:
            print(f"❌ Search failed: {e}")
            break
    
    # Vector similarity check
    print("\n" + "="*70)
    print("📊 VECTOR SIMILARITY ANALYSIS")
    print("="*70)
    
    # Check if embeddings are too similar (potential issue)
    sample_size = min(100, index.ntotal)
    sample_indices = np.random.choice(index.ntotal, sample_size, replace=False)
    sample_vectors = np.array([index.reconstruct(int(i)) for i in sample_indices])
    
    # Compute pairwise similarities
    from sklearn.metrics.pairwise import cosine_similarity
    similarities = cosine_similarity(sample_vectors)
    
    # Remove diagonal (self-similarity)
    np.fill_diagonal(similarities, 0)
    
    avg_similarity = similarities.mean()
    max_similarity = similarities.max()
    min_similarity = similarities.min()
    
    print(f"Average inter-chunk similarity: {avg_similarity:.4f}")
    print(f"Max similarity (most similar pair): {max_similarity:.4f}")
    print(f"Min similarity (least similar pair): {min_similarity:.4f}")
    
    if avg_similarity > 0.95:
        print("\n⚠️  Warning: Very high average similarity. Chunks might be too similar.")
    elif avg_similarity < 0.3:
        print("\n⚠️  Warning: Very low average similarity. Check if documents are diverse enough.")
    else:
        print("\n✅ Similarity distribution looks healthy.")
    
    # Final summary
    print("\n" + "="*70)
    print("📋 SUMMARY")
    print("="*70)
    
    issues = []
    
    if small_chunks:
        issues.append(f"{len(small_chunks)} very small chunks detected")
    
    if avg_similarity > 0.95:
        issues.append("Chunks might be too similar")
    
    if len(sources) < 2:
        issues.append("Only one source document found")
    
    if issues:
        print("\n⚠️  ISSUES FOUND:")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("\n✅ No major issues detected!")
    
    print("\n💡 Recommendations:")
    print("  - Use rebuild_embeddings.py if you see issues")
    print("  - Use inspect_faiss.py for interactive exploration")
    print("  - Use view_faiss_stats.py for quick stats")
    print("\n" + "="*70)


if __name__ == "__main__":
    try:
        check_embeddings()
    except KeyboardInterrupt:
        print("\n\n👋 Exiting...")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
