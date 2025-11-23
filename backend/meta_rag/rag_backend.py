"""
Enhanced RAG Backend - META Notebook
From META Notebook, components:
- BGE Reranker (Cell 24-25)
- GEAR Beam Search (Cell 51)
- RRF Fusion (Cell 55)
- Gemini Answer Generation 
"""

import os
import sys
import json
import pickle
from pathlib import Path
from typing import List, Dict, Optional, Tuple

import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

# Load backend .env
BACKEND_DIR = Path(__file__).parent.parent
env_path = BACKEND_DIR / ".env"
load_dotenv(env_path)

# Mistral components are NOT needed for retrieval - only for building index
# So we don't import them at all
MISTRAL_AVAILABLE = False
meta_answer_gen = None
meta_mistral_client = None

# Import notebook components (但 Reranker 現在用 subprocess，不直接 import)
# try:
#     from meta_rag.components.reranker import BGEReranker, retrieve_and_rerank
#     RERANKER_AVAILABLE = True
# except Exception as e:
#     print(f"⚠️  BGE Reranker not available: {e}")
#     RERANKER_AVAILABLE = False
RERANKER_AVAILABLE = True  # We use subprocess now

try:
    from meta_rag.components.rrf_fusion import rrf_fuse
    RRF_AVAILABLE = True
except Exception as e:
    print(f"⚠️  RRF Fusion not available: {e}")
    RRF_AVAILABLE = False

try:
    from meta_rag.components.gear_beam_search import diverse_triple_beam_search
    GEAR_AVAILABLE = True
except Exception as e:
    print(f"⚠️  GEAR Beam Search not available: {e}")
    GEAR_AVAILABLE = False

# Import Gemini for answer generation
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    print("⚠️  Google Generative AI not available")


class EnhancedRAGBackendV2:
    """
    Enhanced RAG Backend with full META notebook features:
    - Dense retrieval (FAISS)
    - BGE reranking
    - GEAR graph retrieval (if available)
    - RRF fusion
    - Gemini answer generation
    """

    def __init__(
        self,
        embedding_dir: str = None,
        use_reranker: bool = True,
        use_gear: bool = False,
        gemini_api_key: Optional[str] = None,
        gemini_model: str = "gemini-flash-latest",
        index_choice: str = "prefix"  # New parameter: "content", "tfidf", or "prefix"
    ):
        """
        Initialize the RAG backend.

        Args:
            embedding_dir: Directory containing FAISS index and metadata
            use_reranker: Whether to use BGE reranker
            use_gear: Whether to use GEAR graph retrieval
            gemini_api_key: Gemini API key for answer generation
            gemini_model: Gemini model name
            index_choice: Which index to use ("content", "tfidf", or "prefix")
        """
        if embedding_dir is None:
            # Get backend directory (parent of meta_rag directory)
            backend_dir = Path(__file__).parent.parent
            embedding_dir = backend_dir / "embeddings_output_MISTRAL"

        self.embedding_dir = Path(embedding_dir)
        self.use_reranker = use_reranker and RERANKER_AVAILABLE
        self.use_gear = use_gear and GEAR_AVAILABLE
        self.index_choice = index_choice

        # Load resources
        self._load_indices()  # Load all 3 indices
        self._load_metadata()
        self._load_embedding_model()

        # Initialize reranker (Process Isolation - no direct loading)
        self.reranker = None
        print(f"DEBUG: Initializing EnhancedRAGBackendV2 with use_reranker={self.use_reranker}")
        if self.use_reranker:
            print("✅ Reranker enabled (will use subprocess worker)")

        # Load GEAR triples if available
        self.gear_triples = None
        if self.use_gear:
            self._load_gear_triples()

        # Initialize Gemini LLM
        self.llm = None
        self.gemini_api_key = gemini_api_key
        self.gemini_model = gemini_model
        if gemini_api_key:
            self._init_gemini()

    def _load_indices(self):
        """Load all 3 FAISS indices and select the active one."""
        # Try to load all 3 indices
        index_content_path = self.embedding_dir / "index_content.faiss"
        index_tfidf_path = self.embedding_dir / "index_tfidf.faiss"
        index_prefix_path = self.embedding_dir / "index_prefix.faiss"

        # Check if 3-index format exists
        if index_content_path.exists() and index_tfidf_path.exists() and index_prefix_path.exists():
            # Load all 3 indices
            self.index_content = faiss.read_index(str(index_content_path))
            self.index_tfidf = faiss.read_index(str(index_tfidf_path))
            self.index_prefix = faiss.read_index(str(index_prefix_path))

            # Select the active index based on index_choice
            index_map = {
                "content": self.index_content,
                "tfidf": self.index_tfidf,
                "prefix": self.index_prefix
            }

            if self.index_choice not in index_map:
                print(f"⚠️  Invalid index_choice '{self.index_choice}', defaulting to 'prefix'")
                self.index_choice = "prefix"

            self.index = index_map[self.index_choice]

            print(f"✅ Loaded 3 FAISS indices:")
            print(f"   - index_content: {self.index_content.ntotal} vectors")
            print(f"   - index_tfidf: {self.index_tfidf.ntotal} vectors")
            print(f"   - index_prefix: {self.index_prefix.ntotal} vectors")
            print(f"   - Using: {self.index_choice} ({self.index.ntotal} vectors)")

        else:
            # Fallback to old single index format
            old_index_path = self.embedding_dir / "index.faiss"
            if not old_index_path.exists():
                raise FileNotFoundError(
                    f"No FAISS indices found in {self.embedding_dir}\n"
                    f"Expected either:\n"
                    f"  - 3-index format: index_content.faiss, index_tfidf.faiss, index_prefix.faiss\n"
                    f"  - Single index format: index.faiss"
                )

            self.index = faiss.read_index(str(old_index_path))
            self.index_content = self.index
            self.index_tfidf = self.index
            self.index_prefix = self.index
            print(f"⚠️  Using legacy single index format")
            print(f"✅ Loaded FAISS index with {self.index.ntotal} vectors")

    def _load_metadata(self):
        """Load metadata and ID mappings."""
        # Load metadata
        metadata_path = self.embedding_dir / "metadata.json"
        with open(metadata_path, 'r', encoding='utf-8') as f:
            self.metadata = json.load(f)

        # Load ID mapping
        id_mapping_path = self.embedding_dir / "id_mapping.pkl"
        with open(id_mapping_path, 'rb') as f:
            mapping_data = pickle.load(f)
            self.index_to_id = mapping_data['index_to_id']
            self.id_to_index = mapping_data['id_to_index']

        # Build chunks list
        self.all_chunks = []
        for i in range(len(self.index_to_id)):
            chunk_id = self.index_to_id[i]
            self.all_chunks.append(self.metadata[chunk_id])

        print(f"✅ Loaded metadata for {len(self.metadata)} chunks")

        # Expose chunks & Mistral helpers to answer_gen module (optional - only if Mistral available)
        if MISTRAL_AVAILABLE and meta_answer_gen and meta_mistral_client:
            try:
                meta_answer_gen.all_chunks = self.all_chunks
                meta_answer_gen._call_mistral_chat = meta_mistral_client._call_mistral_chat
                meta_answer_gen._extract_text_from_response = meta_mistral_client._extract_text_from_response
                meta_answer_gen.MODEL_NAME = meta_mistral_client.MODEL_NAME
                print("✅ Connected answer_gen to MetaRAG chunks & Mistral client")
            except Exception as e:
                print(f"⚠️  Could not wire answer_gen to Mistral client: {e}")

    def _load_embedding_model(self):
        """Load embedding model."""
        # Try to get model name from index info
        info_path = self.embedding_dir / "index_info.json"
        if info_path.exists():
            with open(info_path, 'r') as f:
                info = json.load(f)
                model_name = info.get('model_name', 'all-MiniLM-L6-v2')
        else:
            model_name = 'all-MiniLM-L6-v2'

        self.embed_model = SentenceTransformer(model_name)
        print(f"✅ Loaded embedding model: {model_name}")

    def _load_gear_triples(self):
        """Load GEAR triples if available."""
        triples_path = self.embedding_dir / "gear_triples.json"
        if triples_path.exists():
            with open(triples_path, 'r', encoding='utf-8') as f:
                self.gear_triples = json.load(f)
            print(f"✅ Loaded {len(self.gear_triples)} GEAR triples")
        else:
            print("⚠️  No GEAR triples found, disabling GEAR")
            self.use_gear = False

    def _init_gemini(self):
        """Initialize Gemini LLM for answer generation."""
        try:
            genai.configure(api_key=self.gemini_api_key)
            self.llm = genai.GenerativeModel(
                model_name=self.gemini_model,
                generation_config={
                    "temperature": 0.5,
                    "top_p": 0.95,
                    "max_output_tokens": 2048,
                }
            )
            print(f"✅ Gemini LLM initialized: {self.gemini_model}")
        except Exception as e:
            print(f"⚠️  Could not initialize Gemini: {e}")
            self.llm = None

    def retrieve_dense(self, query: str, top_k: int = 10) -> List[int]:
        """
        Dense retrieval using FAISS.

        Returns:
            List of chunk indices
        """
        # Embed query
        q_emb = self.embed_model.encode([query])

        # Normalize for IndexFlatIP
        q_emb = q_emb / np.linalg.norm(q_emb, axis=1, keepdims=True)
        q_emb = np.array(q_emb, dtype=np.float32)

        # Search
        distances, indices = self.index.search(q_emb, top_k)
        return indices[0].tolist()

    def retrieve_with_reranking(self, query: str, top_k: int = 10, rerank_top: int = None) -> Tuple[List[int], List[float]]:
        """
        Retrieve with BGE reranking using subprocess isolation.
        """
        # 1. Dense Retrieval first to get candidates
        # Retrieve more candidates for reranking (e.g. 30)
        candidate_k = max(top_k * 3, 30)
        candidate_indices = self.retrieve_dense(query, candidate_k)
        
        if not self.use_reranker:
            # Fallback if reranker disabled
            return candidate_indices[:top_k], [1.0] * min(len(candidate_indices), top_k)

        # 2. Prepare data for reranker worker
        chunks_data = []
        for idx in candidate_indices:
            chunks_data.append({
                "text": self.all_chunks[idx].get("text", "")
            })
            
        input_data = {
            "query": query,
            "chunks": chunks_data
        }
        
        # 3. Call worker subprocess
        import subprocess
        import json
        
        worker_path = Path(__file__).parent / "rerank_worker.py"
        
        try:
            print("🔄 Calling Reranker Worker (Isolated Process)...")
            # Use the same python interpreter as current process
            process = subprocess.Popen(
                [sys.executable, str(worker_path)],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            stdout, stderr = process.communicate(input=json.dumps(input_data))
            
            # Debug output
            if stderr:
                print(f"[DEBUG] Reranker stderr: {stderr}")
            
            if process.returncode != 0:
                print(f"❌ Reranker worker failed with code {process.returncode}")
                print(f"   stdout: {stdout}")
                print(f"   stderr: {stderr}")
                raise RuntimeError(f"Reranker worker failed with code {process.returncode}")
            
            # Try to parse result
            try:
                result = json.loads(stdout)
            except json.JSONDecodeError as e:
                print(f"❌ Failed to parse reranker output: {e}")
                print(f"   Raw output: {stdout}")
                raise
                
            if "error" in result:
                raise RuntimeError(f"Reranker error: {result['error']}")
                
            scores = result["scores"]
            
            # 4. Sort by reranker scores
            # Combine indices and scores
            combined = list(zip(candidate_indices, scores))
            # Sort desc
            combined.sort(key=lambda x: x[1], reverse=True)
            
            # 5. Take top_k
            top_results = combined[:top_k]
            
            reranked_indices = [x[0] for x in top_results]
            reranked_scores = [x[1] for x in top_results]
            
            print("✅ Reranker worker finished successfully")
            return reranked_indices, reranked_scores
            
        except Exception as e:
            print(f"⚠️ Reranking failed, falling back to dense: {e}")
            return candidate_indices[:top_k], [1.0] * min(len(candidate_indices), top_k)

    def retrieve_with_gear_fusion(
        self,
        query: str,
        top_k: int = 10,
        beam_size: int = 3,
        max_length: int = 3
    ) -> Tuple[List[int], List[float]]:
        """
        Retrieve using both dense retrieval and GEAR, then fuse with RRF.

        Returns:
            Tuple of (fused_indices, scores)
        """
        if not self.use_gear or not self.gear_triples or not RRF_AVAILABLE:
            # Fallback to reranking only
            return self.retrieve_with_reranking(query, top_k)

        # Path A: Dense retrieval with reranking
        dense_indices, dense_scores = self.retrieve_with_reranking(query, top_k)

        # Path B: GEAR graph retrieval
        # Note: This is a simplified version - full GEAR pipeline would require more setup
        # For now, we'll just use dense retrieval
        gear_indices = dense_indices  # Placeholder

        # Fuse with RRF
        fused_indices = rrf_fuse([dense_indices, gear_indices], k=60)
        fused_indices = fused_indices[:top_k]

        # Get scores (use reranker scores if available)
        scores = [dense_scores[dense_indices.index(idx)] if idx in dense_indices else 0.5
                  for idx in fused_indices]

        return fused_indices, scores

    def retrieve(self, query: str, top_k: int = 5, use_fusion: bool = False) -> List[Dict]:
        """
        Main retrieval function.

        Args:
            query: User question
            top_k: Number of results to return
            use_fusion: Whether to use GEAR fusion (requires GEAR triples)

        Returns:
            List of chunk dictionaries with scores
        """
        # Choose retrieval method
        if use_fusion and self.use_gear:
            indices, scores = self.retrieve_with_gear_fusion(query, top_k)
        elif self.use_reranker:
            indices, scores = self.retrieve_with_reranking(query, top_k)
        else:
            indices = self.retrieve_dense(query, top_k)
            scores = [1.0] * len(indices)

        # Build results
        results = []
        for idx, score in zip(indices, scores):
            chunk = self.all_chunks[idx].copy()
            chunk['score'] = float(score)
            chunk['retrieval_index'] = int(idx)
            results.append(chunk)

        return results

    def generate_answer(self, query: str, top_k: int = 10, use_fusion: bool = False) -> Dict:
        """
        Retrieve relevant chunks and generate an answer using **Gemini**.

        - Gemini 只負責產生帶有 [1], [2]... 的答案文字。
        - \"Sources used\" 區塊不再附加在答案文字中，而是交給前端在 View Sources 中呈現。
        """
        # Retrieve relevant chunks
        results = self.retrieve(query, top_k, use_fusion=use_fusion)

        if not results:
            return {
                'answer': "I couldn't find relevant information to answer your question.",
                'sources': []
            }

        # --- 1) 給 Gemini 的編號 context ---
        # Funnel Design: Retrieve top_k (e.g. 10), but only give top 5 to LLM for context
        top_n_context = 5
        context_lines = []
        for i, result in enumerate(results[:top_n_context], start=1):
            text = (result.get("text") or "").strip()
            context_lines.append(f"[{i}] {text}")
        context_str = "\n".join(context_lines)

        system_msg = (
            "You are a helpful policy QA assistant for the UIC Vice Chancellor's Office. "
            "Your task is to answer the user's question based ONLY on the provided numbered snippets.\n"
            "Note: Some snippets might be irrelevant due to retrieval noise. Ignore them."
        )
        user_msg = (
            f"Provided Snippets:\n{context_str}\n\n"
            f"Question: {query}\n\n"
            "Instructions:\n"
            "1. Read the snippets carefully and identify which ones contain the answer.\n"
            "2. Answer the question concisely using ONLY the relevant snippets.\n"
            "3. Cite the snippets you used inline as [i], e.g., 'According to policy [1]...'.\n"
            "4. If multiple snippets support a point, cite them all: [1][2].\n"
            "5. If none of the snippets answer the question, state that you cannot find the information in the provided documents.\n"
            "6. Do NOT generate a 'Sources used' list at the end.\n"
        )

        answer_text = None
        if self.llm:
            try:
                # Combine system and user messages into one prompt
                full_prompt = f"{system_msg}\n\n{user_msg}"
                response = self.llm.generate_content(full_prompt)
                answer_text = (response.text or "").strip()
                print("✅ Generated answer using Gemini with [i] citations")
            except Exception as e:
                print(f"Error generating Gemini citation-style answer: {e}")
                import traceback
                traceback.print_exc()

        # --- 2) 如果 Gemini 掛掉，退回簡單回答 ---
        if not answer_text:
            answer_text = f"""Based on the UIC Vice Chancellor's Office policy documents:

{results[0]['text']}

Summary: {results[0].get('summary', 'No summary available.')}"""

        return {
            'answer': answer_text,
            'sources': results
        }


def get_backend_v2(use_reranker=True, use_gear=False, embedding_dir=None, metadata_source="gemini"):
    """
    Get or create the enhanced RAG backend V2 singleton.

    Args:
        use_reranker: Whether to use BGE reranker
        use_gear: Whether to use GEAR graph retrieval
        embedding_dir: Custom embedding directory path (if None, uses default based on metadata_source)
        metadata_source: "mistral" or "gemini" - determines which index to use (default: "gemini")
    """
    # Load API keys
    load_dotenv()
    gemini_key = os.getenv("GEMINI_API_KEY")
    gemini_model = os.getenv("GEMINI_MODEL", "gemini-flash-latest")

    # Get backend directory (parent of meta_rag directory)
    backend_dir = Path(__file__).parent.parent
    
    # Determine embedding directory
    if embedding_dir is None:
        if metadata_source.lower() == "gemini":
            embedding_dir = backend_dir / "embeddings_output_GEMINI"
        else:  # default to mistral
            embedding_dir = backend_dir / "embeddings_output_MISTRAL"
    
    # Convert to Path if string
    if isinstance(embedding_dir, str):
        embedding_dir = Path(embedding_dir)

    backend = EnhancedRAGBackendV2(
        embedding_dir=str(embedding_dir),
        use_reranker=use_reranker,
        use_gear=use_gear,
        gemini_api_key=gemini_key,
        gemini_model=gemini_model
    )

    return backend


if __name__ == "__main__":
    # Test the backend
    print("Testing Enhanced RAG Backend V2\n")

    backend = get_backend_v2(use_reranker=True, use_gear=False)

    # Test query
    query = "What is the policy on financial conflicts of interest?"
    print(f"Query: {query}\n")

    # Test retrieval
    results = backend.retrieve(query, top_k=3)
    print(f"Retrieved {len(results)} results:")
    for i, result in enumerate(results, 1):
        print(f"{i}. Score: {result['score']:.4f}")
        print(f"   Text: {result['text'][:100]}...")
        print()

    # Test answer generation
    answer_data = backend.generate_answer(query, top_k=3)
    print(f"Answer: {answer_data['answer']}\n")
