"""
Script to rebuild FAISS embeddings from scratch.
Run: python rebuild_embeddings.py
"""

import shutil
from pathlib import Path
from dotenv import load_dotenv
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings

# Setup
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

PRAJAS_NIER_DIR = BASE_DIR / "Prajas-Nier"
DATASET_DIR = PRAJAS_NIER_DIR / "Dataset"
PDF_PATHS = [DATASET_DIR / "policy-booklet.pdf", DATASET_DIR / "policy-limits.pdf"]
FAISS_DIR = PRAJAS_NIER_DIR / "artifacts" / "faiss_index"


def load_pdfs(pdf_paths):
    """Load PDFs and add metadata."""
    docs = []
    for path in pdf_paths:
        if not path.exists():
            print(f"⚠️  PDF not found: {path}")
            continue
        print(f"📄 Loading: {path.name}")
        loader = PyPDFLoader(str(path))
        loaded_docs = loader.load()
        policy_name = path.name
        for doc in loaded_docs:
            doc.metadata["policy_name"] = policy_name
            if "page" in doc.metadata:
                doc.metadata["page_number"] = doc.metadata["page"]
        docs.extend(loaded_docs)
        print(f"   ✅ Loaded {len(loaded_docs)} pages")
    return docs


def chunk_docs(docs, chunk_size=500, chunk_overlap=100):
    """Split documents into chunks."""
    print(f"\n✂️  Chunking documents (size={chunk_size}, overlap={chunk_overlap})")
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""]
    )
    chunks = splitter.split_documents(docs)
    for chunk in chunks:
        if "policy_name" not in chunk.metadata:
            chunk.metadata["policy_name"] = chunk.metadata.get("source", "unknown")
        if "page_number" not in chunk.metadata and "page" in chunk.metadata:
            chunk.metadata["page_number"] = chunk.metadata["page"]
    print(f"   ✅ Created {len(chunks)} chunks")
    return chunks


def rebuild_index():
    """Rebuild FAISS index from scratch."""
    print("🔄 REBUILDING FAISS EMBEDDINGS\n")
    print("="*60)
    
    # Step 1: Delete old index
    if FAISS_DIR.exists():
        print(f"🗑️  Deleting old index: {FAISS_DIR}")
        shutil.rmtree(FAISS_DIR)
        print("   ✅ Old index deleted")
    else:
        print("ℹ️  No existing index found")
    
    # Step 2: Load PDFs
    print(f"\n📚 Loading PDFs from: {DATASET_DIR}")
    docs = load_pdfs(PDF_PATHS)
    if not docs:
        print("❌ No PDFs found!")
        return
    print(f"   ✅ Total pages loaded: {len(docs)}")
    
    # Step 3: Chunk documents
    chunks = chunk_docs(docs)
    
    # Step 4: Create embeddings
    print(f"\n🧠 Creating embeddings (model: text-embedding-3-large)")
    print("   ⏳ This may take a minute...")
    embeddings = OpenAIEmbeddings(model="text-embedding-3-large")
    
    # Step 5: Build FAISS index
    print(f"\n💾 Building FAISS index...")
    vector_store = FAISS.from_documents(chunks, embeddings)
    
    # Step 6: Save to disk
    FAISS_DIR.mkdir(parents=True, exist_ok=True)
    vector_store.save_local(str(FAISS_DIR))
    print(f"   ✅ Index saved to: {FAISS_DIR}")
    
    # Summary
    print("\n" + "="*60)
    print("✅ REBUILD COMPLETE!")
    print("="*60)
    print(f"📊 Statistics:")
    print(f"   - Total documents: {len(chunks)}")
    print(f"   - Vector dimension: {vector_store.index.d}")
    print(f"   - Index size: {vector_store.index.ntotal} vectors")
    print(f"\n💡 Your server will now use the new embeddings!")


if __name__ == "__main__":
    try:
        rebuild_index()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
