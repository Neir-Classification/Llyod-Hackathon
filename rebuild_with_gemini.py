"""
Rebuild FAISS embeddings using Gemini 2.0 Flash for structured extraction.
Run: python3 rebuild_with_gemini.py
"""

import os
import shutil
from pathlib import Path
from dotenv import load_dotenv

# Setup
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

PRAJAS_NIER_DIR = BASE_DIR / "Prajas-Nier"
FAISS_DIR = PRAJAS_NIER_DIR / "artifacts" / "faiss_index"


def main():
    print("🔄 REBUILDING FAISS EMBEDDINGS WITH GEMINI")
    print("="*70 + "\n")
    
    # Check for API key
    openai_key = os.environ.get("OPENAI_API_KEY")
    
    if not openai_key:
        print("❌ OPENAI_API_KEY not found in .env file")
        return
    
    print("✅ OpenAI API key found")
    
    # Delete existing index
    if FAISS_DIR.exists():
        print(f"\n🗑️  Deleting existing FAISS index: {FAISS_DIR}")
        try:
            shutil.rmtree(FAISS_DIR)
            print("✅ Old index deleted")
        except Exception as e:
            print(f"❌ Failed to delete index: {e}")
            return
    else:
        print("\n📁 No existing index found")
    
    # Import and rebuild
    print("\n🏗️  Building new index with ChatGPT processing...")
    print("This will:")
    print("  1. Load each PDF page")
    print("  2. Process through GPT-4o for structured extraction")
    print("  3. Create semantic chunks")
    print("  4. Generate embeddings with OpenAI text-embedding-3-large")
    print("  5. Build FAISS index (CPU version with L2 distance)")
    print("\n⏳ This may take several minutes...\n")
    
    try:
        # Import here to ensure environment is loaded
        from main import build_vector_store
        
        vector_store = build_vector_store()
        
        print("\n" + "="*70)
        print("✅ SUCCESS!")
        print("="*70)
        print(f"Index saved to: {FAISS_DIR}")
        print(f"Total vectors: {vector_store.index.ntotal}")
        print("\n💡 Restart your backend server to use the new index:")
        print("   uvicorn main:app --host 0.0.0.0 --port 8000 --reload")
        
    except Exception as e:
        print(f"\n❌ Failed to build index: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
