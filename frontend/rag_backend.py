"""
RAG Backend Interface
Connects to the MetaRAG retrieval system
"""
import sys
import os
from pathlib import Path

# Add the backend directory to Python path
BACKEND_DIR = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from sentence_transformers import SentenceTransformer
import faiss
import pickle
import json
import numpy as np

# Import Gemini for answer generation
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True

    # Try to get API key from Streamlit secrets first (for Streamlit Cloud)
    try:
        import streamlit as st
        GEMINI_API_KEY = st.secrets.get("Gemini_API_KEY")
        GEMINI_MODEL = st.secrets.get("GEMINI_MODEL", "gemini-flash-latest")
        TEMPERATURE = float(st.secrets.get("TEMPERATURE", "0.5"))
        if GEMINI_API_KEY:
            print("✅ Using Gemini API key from Streamlit secrets")
    except (ImportError, FileNotFoundError, KeyError):
        # Fallback to .env file (for local development)
        from dotenv import load_dotenv
        env_path = BACKEND_DIR / ".env"
        load_dotenv(env_path)
        GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
        GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-flash-latest")
        TEMPERATURE = float(os.getenv("TEMPERATURE", "0.5"))
        if GEMINI_API_KEY:
            print("✅ Using Gemini API key from .env file")

except ImportError:
    GEMINI_AVAILABLE = False
    GEMINI_API_KEY = None
    GEMINI_MODEL = None


class RAGBackend:
    """Interface to the MetaRAG retrieval system"""
    
    def __init__(self, embedding_dir=None):
        """Initialize the RAG backend"""
        if embedding_dir is None:
            embedding_dir = BACKEND_DIR / "embeddings_output" / "naive" / "naive_embedding"

        self.embedding_dir = Path(embedding_dir)
        self.model = None
        self.index = None
        self.id_mapping = None
        self.metadata = None
        self.llm = None

        self._load_resources()
        self._init_llm()
    
    def _load_resources(self):
        """Load the FAISS index, model, and metadata"""
        # Load FAISS index
        index_path = self.embedding_dir / "index.faiss"
        if not index_path.exists():
            raise FileNotFoundError(f"FAISS index not found: {index_path}")
        
        self.index = faiss.read_index(str(index_path))
        
        # Load ID mapping
        id_mapping_path = self.embedding_dir / "id_mapping.pkl"
        with open(id_mapping_path, 'rb') as f:
            mapping_data = pickle.load(f)
            self.id_mapping = mapping_data['index_to_id']
        
        # Load metadata
        metadata_path = self.embedding_dir / "metadata.json"
        with open(metadata_path, 'r') as f:
            self.metadata = json.load(f)
        
        # Load embedding model
        model_name = self.metadata.get('model_name', 'Snowflake/arctic-embed-s')
        self.model = SentenceTransformer(model_name)

        print(f"✅ Loaded RAG backend with {self.index.ntotal} vectors")

    def _init_llm(self):
        """Initialize Gemini LLM for answer generation"""
        if GEMINI_AVAILABLE and GEMINI_API_KEY:
            try:
                genai.configure(api_key=GEMINI_API_KEY)
                self.llm = genai.GenerativeModel(
                    model_name=GEMINI_MODEL,
                    generation_config={
                        "temperature": TEMPERATURE,
                        "top_p": 0.95,
                        "max_output_tokens": 2048,
                    }
                )
                print(f"✅ Gemini LLM initialized: {GEMINI_MODEL}")
            except Exception as e:
                print(f"⚠️ Could not initialize Gemini: {e}")
                self.llm = None
        else:
            print("⚠️ Gemini not available, using simple retrieval")
    
    def retrieve(self, query, top_k=5):
        """
        Retrieve top_k most relevant chunks for the query
        
        Args:
            query: User question
            top_k: Number of results to return
            
        Returns:
            List of dicts with chunk text, metadata, and scores
        """
        # Generate query embedding
        query_embedding = self.model.encode([query], convert_to_numpy=True)
        
        # Search FAISS index
        scores, indices = self.index.search(query_embedding, top_k)
        
        # Collect results
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1:
                continue
            
            # Convert numpy int64 to regular int
            idx = int(idx)
            
            # Check if index is valid
            if idx not in self.id_mapping:
                print(f"Warning: Index {idx} not found in mapping, skipping...")
                continue
                
            chunk_id = self.id_mapping[idx]
            chunk_data = self.metadata[chunk_id]
            
            results.append({
                'text': chunk_data.get('text', ''),
                'score': float(score),
                'document_id': chunk_data.get('document_id', ''),
                'content_type': chunk_data.get('content_type', ''),
                'summary': chunk_data.get('summary', ''),
                'primary_category': chunk_data.get('primary_category', ''),
                'chunk_id': chunk_id
            })
        
        return results
    
    def generate_answer(self, query, top_k=5):
        """
        Retrieve relevant chunks and generate an answer

        Args:
            query: User question
            top_k: Number of chunks to retrieve

        Returns:
            Dict with answer and sources
        """
        # Retrieve relevant chunks
        results = self.retrieve(query, top_k)

        if not results:
            return {
                'answer': "I couldn't find relevant information to answer your question.",
                'sources': []
            }

        # Compile context from top results
        context_parts = []
        for i, result in enumerate(results[:3], 1):
            text = result['text']
            summary = result.get('summary', '')
            context_parts.append(f"Source {i}:\nContent: {text}\nSummary: {summary}")

        context = "\n\n".join(context_parts)

        # Generate answer with LLM if available
        if self.llm:
            try:
                prompt = f"""You are a helpful assistant for the UIC Vice Chancellor's Office. Answer the user's question based on the provided policy documents.

Question: {query}

Relevant Policy Information:
{context}

Instructions:
- Synthesize the information from the sources to provide a helpful answer
- Use the document titles, content, and summaries to construct your response
- If the sources discuss policies, procedures, or responsibilities related to the topic, explain them
- Focus on what the documents DO say rather than what they don't say
- If information is partial or incomplete, explain what IS covered based on the sources
- Use professional language appropriate for university policies
- Be specific and reference the information provided in the sources

Answer:"""

                response = self.llm.generate_content(prompt)
                answer = response.text

            except Exception as e:
                print(f"Error generating LLM answer: {e}")
                # Fallback to simple answer
                answer = f"""Based on the UIC Vice Chancellor's Office policy documents:

{results[0]['text']}

Summary: {results[0].get('summary', 'No summary available.')}"""
        else:
            # Simple answer without LLM
            answer = f"""Based on the UIC Vice Chancellor's Office policy documents:

{results[0]['text']}

Summary: {results[0].get('summary', 'No summary available.')}"""

        return {
            'answer': answer,
            'sources': results
        }


# Singleton instance
_backend = None

def get_backend():
    """Get or create the RAG backend singleton"""
    global _backend
    if _backend is None:
        _backend = RAGBackend()
    return _backend
