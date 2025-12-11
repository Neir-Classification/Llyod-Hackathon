"""Simple RAG pipeline for the policy PDFs in ~.

Steps
- Load and chunk both PDFs
- Build or load a FAISS vector store with OpenAI embeddings
- Retrieve top-k chunks for a user question

Requirements
- Set OPENAI_API_KEY in your environment
- Install deps from requirements.txt
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Iterable, List, Sequence

from dotenv import load_dotenv
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document

# Load environment variables from .env file
load_dotenv()

BASE_DIR = Path(__file__).parent
DATASET_DIR = BASE_DIR / "Dataset"
PDF_PATHS = [DATASET_DIR / "policy-booklet.pdf", DATASET_DIR / "policy-limits.pdf"]
FAISS_DIR = BASE_DIR / "artifacts" / "faiss_index"

TONE_PROMPTS = {
    "angry": "You are a calm, empathetic customer service agent. Acknowledge the user's frustration briefly and provide clear information. Avoid defensive or technical language. Keep it short and reassuring.",
    "confused": "You are a patient and reassuring assistant. Explain the policy information simply and clearly. Avoid jargon. Use everyday language.",
    "neutral": "You are a professional insurance assistant. Provide clear, factual information about the policy. Be direct and concise.",
    "happy": "You are a warm and friendly insurance assistant. Provide the policy information in a positive, helpful manner. Keep it professional but personable.",
    "anxious": "You are a reassuring and supportive assistant. Provide clear information and emphasize what's covered and next steps. Be comforting and specific."
}


def adjust_tone_with_llm(retrieved_chunks: List[tuple], user_question: str, tone: str = "neutral") -> str:
    """Use LLM to generate a tone-appropriate response from retrieved chunks."""
    from langchain_openai import ChatOpenAI
    
    if tone not in TONE_PROMPTS:
        tone = "neutral"
    
    # Combine retrieved chunks into context
    context = "\n\n".join([doc.page_content for doc, _ in retrieved_chunks])
    
    system_prompt = f"""{TONE_PROMPTS[tone]}

Based on the policy information below, answer the user's question in 3-4 short sentences suitable for voice (20-30 seconds of speech).

Policy Context:
{context}"""

    user_prompt = f"User question: {user_question}"
    
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3)
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    
    response = llm.invoke(messages)
    return response.content


def ensure_api_key() -> None:
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY not set; export it before running.")


def load_pdfs(pdf_paths: Iterable[Path]) -> List:
    docs = []
    for path in pdf_paths:
        if not path.exists():
            raise FileNotFoundError(f"PDF not found: {path}")
        loader = PyPDFLoader(str(path))
        loaded_docs = loader.load()
        policy_name = path.name
        for doc in loaded_docs:
            doc.metadata["policy_name"] = policy_name
            if "page" in doc.metadata:
                doc.metadata["page_number"] = doc.metadata["page"]
        docs.extend(loaded_docs)
    return docs


def chunk_docs(docs: Sequence, chunk_size: int = 500, chunk_overlap: int = 100) -> List:
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
    return chunks


def build_vector_store(chunks: Sequence, persist_dir: Path = FAISS_DIR) -> FAISS:
    embeddings = OpenAIEmbeddings(model="text-embedding-3-large")
    vector_db = FAISS.from_documents(chunks, embeddings)
    persist_dir.mkdir(parents=True, exist_ok=True)
    vector_db.save_local(str(persist_dir))
    return vector_db


def load_vector_store(persist_dir: Path = FAISS_DIR) -> FAISS:
    if not persist_dir.exists():
        raise FileNotFoundError("No saved FAISS index; run with --rebuild first.")
    embeddings = OpenAIEmbeddings(model="text-embedding-3-large")
    return FAISS.load_local(str(persist_dir), embeddings, allow_dangerous_deserialization=True)


def retrieve(query: str, vector_db: FAISS, k: int = 2):
    # Add intent hinting to nudge retrieval toward coverage/decision text
    enhanced_query = f"policy coverage clause: {query}"
    docs = vector_db.max_marginal_relevance_search(enhanced_query, k=k, fetch_k=20)
    
    # Limit chunk length for voice output
    for doc in docs:
        doc.page_content = doc.page_content[:600]
    
    return [(doc, 0.0) for doc in docs]


def rebuild_index() -> FAISS:
    docs = load_pdfs(PDF_PATHS)
    chunks = chunk_docs(docs)
    return build_vector_store(chunks)


def main():
    parser = argparse.ArgumentParser(description="RAG over policy PDFs")
    parser.add_argument("question", type=str, help="Question to ask about the policy")
    parser.add_argument("--k", type=int, default=2, help="How many chunks to return")
    parser.add_argument("--tone", type=str, default="neutral", 
                       choices=["angry", "confused", "neutral", "happy", "anxious"],
                       help="User's emotional tone for response adjustment")
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Force rebuild the FAISS index from the PDFs",
    )
    args = parser.parse_args()

    ensure_api_key()

    if args.rebuild:
        vector_db = rebuild_index()
    else:
        try:
            vector_db = load_vector_store()
        except FileNotFoundError:
            vector_db = rebuild_index()

    results = retrieve(args.question, vector_db, k=args.k)
    
    # Generate tone-adjusted response
    response = adjust_tone_with_llm(results, args.question, args.tone)
    print(f"\n{'='*60}")
    print(f"Tone: {args.tone.upper()}")
    print(f"{'='*60}\n")
    print(response)
    print(f"\n{'='*60}")
    print("Source chunks:")
    print(f"{'='*60}")
    for idx, (doc, score) in enumerate(results, start=1):
        policy_name = doc.metadata.get("policy_name", "unknown")
        page_number = doc.metadata.get("page_number", "unknown")
        # Clean source path for display (show filename only)
        source_path = doc.metadata.get("source", "unknown")
        source_file = Path(source_path).name if source_path != "unknown" else "unknown"
        print(f"\nResult {idx} | policy={policy_name} | page={page_number}")
        print(doc.page_content.strip())


if __name__ == "__main__":
    main()


# python -m venv .venv; .\.venv\Scripts\activate; pip install -r requirements.txt
# setx OPENAI_API_KEY "your-key" (restart shell)
# python rag_pipeline.py "Does my policy cover water damage?" --rebuild