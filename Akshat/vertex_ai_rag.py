"""
Vertex AI RAG System with Gemini
- Uses Google's Gemini models via Vertex AI
- Integrates with your existing FAISS index
- Production-ready with error handling
"""

import os
import sys
from typing import List, Dict, Optional
import vertexai
from vertexai.generative_models import GenerativeModel, Part, Content
from google.oauth2 import service_account

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class VertexAIRAG:
    """
    RAG system using Vertex AI Gemini models.
    Combines FAISS retrieval with Gemini answer generation.
    """
    
    def __init__(
        self,
        project_id: str,
        location: str = "us-central1",
        model_name: str = "gemini-2.5-flash",
        credentials_path: Optional[str] = None
    ):
        """
        Initialize Vertex AI RAG system.
        
        Args:
            project_id: Your GCP project ID
            location: GCP region (us-central1, europe-west1, etc.)
            model_name: Gemini model to use
                - gemini-2.5-flash: Latest stable, fast (RECOMMENDED)
                - gemini-1.5-flash-002: Older stable
                - gemini-1.5-pro-002: Best quality
            credentials_path: Path to service account JSON (optional)
        """
        self.project_id = project_id
        self.location = location
        self.model_name = model_name
        
        # Initialize Vertex AI
        if credentials_path and os.path.exists(credentials_path):
            credentials = service_account.Credentials.from_service_account_file(
                credentials_path
            )
            vertexai.init(
                project=project_id,
                location=location,
                credentials=credentials
            )
            print(f"✓ Vertex AI initialized with service account")
        else:
            # Use default credentials (gcloud auth)
            vertexai.init(project=project_id, location=location)
            print(f"✓ Vertex AI initialized with default credentials")
        
        # Initialize Gemini model
        self.model = GenerativeModel(model_name)
        print(f"✓ Model loaded: {model_name}")
        
        # Load FAISS search engine
        self.search_engine = None
        
    def load_search_index(self, search_engine, index_path: str = "faiss_index_hybrid"):
        """
        Load existing FAISS index.
        
        Args:
            search_engine: Instance of your search class (HybridSearch, BasicFAISSSearch, etc.)
            index_path: Path to saved FAISS index
        """
        self.search_engine = search_engine
        self.search_engine.load_index(index_path)
        print(f"✓ Search index loaded from {index_path}")
    
    def retrieve_context(self, query: str, top_k: int = 5) -> tuple[List[Dict], str]:
        """
        Retrieve relevant context using FAISS.
        
        Args:
            query: User question
            top_k: Number of chunks to retrieve
            
        Returns:
            Tuple of (chunks, formatted_context)
        """
        if not self.search_engine:
            raise ValueError("Search engine not loaded. Call load_search_index() first.")
        
        # Retrieve relevant chunks
        chunks = self.search_engine.search(query, top_k=top_k)
        
        # Format context for LLM
        context_parts = []
        for i, chunk in enumerate(chunks, 1):
            context_parts.append(
                f"[Source {i} - Page {chunk['page']}]\n{chunk['text']}"
            )
        
        formatted_context = "\n\n".join(context_parts)
        return chunks, formatted_context
    
    def generate_answer(
        self,
        query: str,
        context: str,
        temperature: float = 0.3,
        max_output_tokens: int = 10000
    ) -> str:
        """
        Generate answer using Gemini optimized for voice output.
        
        Args:
            query: User question
            context: Retrieved context from FAISS
            temperature: Creativity (0.0-1.0, lower = more focused)
            max_output_tokens: Maximum length of response (short for voice)
            
        Returns:
            Generated answer optimized for voice
        """
        # Build prompt optimized for voice output
        prompt = f"""You are a helpful insurance assistant providing answers for voice output. Answer based ONLY on the policy documents provided.

Policy Context:
{context}

User Question: {query}

CRITICAL INSTRUCTIONS FOR VOICE OUTPUT:
- Give a BRIEF, direct answer (4-5 sentences maximum)
- Use natural, conversational language suitable for speaking
- Avoid technical jargon, use simple words
- NO bullet points, lists, or special formatting
- If multiple items, say "and" between them naturally
- If information is missing, say "I don't have that information available at the moment."
- iF possible give examples to illustrate points
- Be warm and helpful, as if speaking to a customer on the phone

Provide ONLY the answer, nothing else:"""
        
        try:
            # Generate response
            response = self.model.generate_content(
                prompt,
                generation_config={
                    "temperature": temperature,
                    "max_output_tokens": max_output_tokens,
                }
            )
            
            answer = response.text.strip()
            
            # Clean up for voice output
            answer = answer.replace('*', '').replace('#', '').replace('`', '')
            answer = answer.replace('\n\n', '. ').replace('\n', ' ')
            
            # Handle edge cases
            if not answer or len(answer) < 10:
                return "I apologize, I couldn't find a clear answer to your question in the policy documents."
            
            # Limit length for voice (roughly 30 seconds at normal speaking pace)
            if len(answer) > 500:
                sentences = answer.split('. ')
                answer = '. '.join(sentences[:3]) + '.'
            
            return answer
            
        except Exception as e:
            # Handle API errors gracefully for voice
            return f"I'm sorry, I encountered an issue accessing the information. Please try asking your question again."
    
    def ask(
        self,
        query: str,
        top_k: int = 3,
        temperature: float = 0.3,
        include_sources: bool = False
    ) -> Dict:
        """
        Complete RAG pipeline optimized for voice output.
        
        Args:
            query: User question
            top_k: Number of chunks to retrieve (fewer for voice)
            temperature: LLM creativity
            include_sources: Whether to include source chunks in response
            
        Returns:
            Dictionary with voice-optimized answer and metadata
        """
        try:
            # Handle empty or invalid queries
            if not query or len(query.strip()) < 3:
                return {
                    "query": query,
                    "answer": "I didn't catch that. Could you please repeat your question?",
                    "num_sources": 0,
                    "error": None
                }
            
            # 1. Retrieve context
            try:
                chunks, context = self.retrieve_context(query, top_k=top_k)
            except Exception as e:
                return {
                    "query": query,
                    "answer": "I'm having trouble accessing the policy information right now. Please try again in a moment.",
                    "num_sources": 0,
                    "error": str(e)
                }
            
            # 2. Check if we got relevant results
            if not chunks or len(chunks) == 0:
                return {
                    "query": query,
                    "answer": "I couldn't find relevant information about that in your policy. Could you rephrase your question?",
                    "num_sources": 0,
                    "error": None
                }
            
            # 3. Generate answer
            try:
                answer = self.generate_answer(query, context, temperature=temperature)
            except Exception as e:
                return {
                    "query": query,
                    "answer": "I apologize, I'm having difficulty generating a response right now. Please try asking again.",
                    "num_sources": len(chunks),
                    "error": str(e)
                }
            
            # 4. Format response for voice
            result = {
                "query": query,
                "answer": answer,
                "num_sources": len(chunks),
                "error": None
            }
            
            # Only include sources if explicitly requested (not for voice typically)
            if include_sources:
                result["sources"] = [
                    {
                        "page": chunk["page"],
                        "score": chunk["score"]
                    }
                    for chunk in chunks
                ]
            
            return result
            
        except Exception as e:
            # Catch-all for any unexpected errors
            return {
                "query": query if query else "",
                "answer": "I apologize, something went wrong. Please try asking your question again.",
                "num_sources": 0,
                "error": str(e)
            }
    
    def chat(self, max_turns: int = 10):
        """
        Interactive chat interface.
        
        Args:
            max_turns: Maximum number of conversation turns
        """
        print("\n" + "="*70)
        print("VERTEX AI RAG CHATBOT - Insurance Policy Assistant")
        print("="*70)
        print("Ask questions about your insurance policy.")
        print("Type 'quit' or 'exit' to end the conversation.\n")
        
        for turn in range(max_turns):
            try:
                query = input("You: ").strip()
                
                if query.lower() in ['quit', 'exit', 'q']:
                    print("\nGoodbye! 👋")
                    break
                
                if not query:
                    continue
                
                print("\n🤔 Thinking...")
                result = self.ask(query)
                
                print(f"\n🤖 Assistant:\n{result['answer']}")
                print(f"\n📄 Sources: {result['num_sources']} relevant sections found")
                
                if result.get('sources'):
                    print("\n📚 References:")
                    for i, source in enumerate(result['sources'], 1):
                        print(f"  {i}. Page {source['page']} (relevance: {source['score']:.2f})")
                
                print("\n" + "-"*70 + "\n")
                
            except KeyboardInterrupt:
                print("\n\nGoodbye! 👋")
                break
            except Exception as e:
                print(f"\n❌ Error: {e}\n")


def main():
    """Demo: RAG system with Vertex AI."""
    
    print("""
╔══════════════════════════════════════════════════════════════════════╗
║              VERTEX AI RAG SYSTEM SETUP                              ║
╚══════════════════════════════════════════════════════════════════════╝
    """)
    
    # Check for required environment variables
    project_id = os.getenv('GCP_PROJECT_ID')
    credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    
    if not project_id:
        print("❌ GCP_PROJECT_ID not set!")
        print("\nSet it with:")
        print("  export GCP_PROJECT_ID='your-project-id'")
        print("\nOr pass it directly in code:")
        print("  rag = VertexAIRAG(project_id='your-project-id')")
        return
    
    print(f"✓ Project ID: {project_id}")
    if credentials_path:
        print(f"✓ Credentials: {credentials_path}")
    else:
        print("ℹ️  Using default credentials (gcloud auth)")
    
    # Initialize RAG system
    try:
        rag = VertexAIRAG(
            project_id=project_id,
            location="us-central1",
            model_name="gemini-2.5-flash",  # Latest stable model
            credentials_path=credentials_path
        )
    except Exception as e:
        print(f"\n❌ Failed to initialize Vertex AI: {e}")
        print("\nMake sure you have:")
        print("1. GCP project with Vertex AI enabled")
        print("2. Valid credentials (gcloud auth or service account)")
        return
    
    # Load FAISS index
    print("\nLoading search index...")
    try:
        from hybrid_faiss_bm25_search import HybridSearch
        
        search_engine = HybridSearch()
        rag.load_search_index(search_engine, "faiss_index_hybrid")
    except Exception as e:
        print(f"❌ Failed to load search index: {e}")
        print("Make sure you have run hybrid_faiss_bm25_search.py first")
        return
    
    print("\n" + "="*70)
    print("DEMO QUERIES")
    print("="*70)
    
    # Demo queries
    queries = [
        "What is covered for water damage?",
        "Am I covered for theft outside my home?",
        "How do I make a claim?"
    ]
    
    for query in queries:
        print(f"\n{'─'*70}")
        print(f"Q: {query}")
        print('─'*70)
        
        try:
            result = rag.ask(query, top_k=3)
            print(f"\n🤖 Answer:\n{result['answer']}")
            print(f"\n📄 Based on {result['num_sources']} sources")
        except Exception as e:
            print(f"❌ Error: {e}")
    
    # Start interactive chat
    print("\n" + "="*70)
    print("Starting interactive mode...")
    print("="*70)
    
    try:
        rag.chat()
    except Exception as e:
        print(f"❌ Chat error: {e}")


if __name__ == "__main__":
    main()
