"""
BGE Reranker - EXACT implementation from META notebook
Uses BAAI/bge-reranker-base cross-encoder for reranking retrieved chunks
"""

import numpy as np
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from typing import List, Tuple


class BGEReranker:
    """BGE cross-encoder reranker for improving retrieval quality"""

    def __init__(self, model_name: str = "BAAI/bge-reranker-base"):
        """
        Initialize BGE reranker model.

        Args:
            model_name: HuggingFace model name (default: BAAI/bge-reranker-base)
        """
        print(f"🔄 Loading BGE reranker: {model_name}")
        self.model_name = model_name
        
        # Use GPU if available (MPS for M3 Pro)
        if torch.backends.mps.is_available():
            self.device = torch.device("mps")
            print("📱 Using Apple Silicon GPU (MPS)")
        elif torch.cuda.is_available():
            self.device = torch.device("cuda")
            print("🎮 Using NVIDIA GPU (CUDA)")
        else:
            self.device = torch.device("cpu")
            print("💻 Using CPU")
        
        # Load model with memory optimization
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForSequenceClassification.from_pretrained(
            model_name,
            torch_dtype=torch.float16 if self.device.type != "cpu" else torch.float32
        )
        self.model.eval()
        self.model.to(self.device)
        
        print(f"✅ BGE reranker loaded on {self.device}")

    def rerank(self, query: str, chunks: List[dict], top_k: int = None, batch_size: int = 8) -> Tuple[List[int], List[float]]:
        """
        Rerank retrieved chunks using BGE cross-encoder.
        Uses batch processing to avoid memory issues.

        Args:
            query: User question
            chunks: List of chunk dictionaries (must have 'text' field)
            top_k: Number of results to return (None = return all)
            batch_size: Number of pairs to process at once (default 8 for memory efficiency)

        Returns:
            Tuple of (reranked_indices, reranked_scores)
        """
        # Prepare query-document pairs for reranker
        pairs = []
        for chunk in chunks:
            doc_text = chunk["text"]
            pairs.append([query, doc_text])

        # Process in batches to avoid OOM
        all_scores = []
        for i in range(0, len(pairs), batch_size):
            batch_pairs = pairs[i:i+batch_size]
            
            # Tokenize pairs for reranker
            inputs = self.tokenizer(
                batch_pairs,
                padding=True,
                truncation=True,
                return_tensors='pt',
                max_length=512
            )
            inputs = {key: val.to(self.device) for key, val in inputs.items()}

            # Get relevance scores from reranker
            with torch.no_grad():
                logits = self.model(**inputs).logits  # shape (batch, 1) or (batch, 2)

            # If model has 2 outputs (e.g., for binary classification), use the second (relevance) logit
            if logits.size(-1) == 2:
                # Assuming logits[:,1] corresponds to "relevant" class
                batch_scores = logits[:, 1]
            else:
                # If single output
                batch_scores = logits.view(-1)

            all_scores.extend(batch_scores.cpu().numpy().tolist())
        
        scores = np.array(all_scores)

        # Sort the indices by score desc
        sorted_idx = np.argsort(-scores)

        # Apply top_k if specified
        if top_k is not None:
            sorted_idx = sorted_idx[:top_k]

        reranked_indices = [int(i) for i in sorted_idx]
        reranked_scores = [float(scores[i]) for i in sorted_idx]

        return reranked_indices, reranked_scores


def retrieve_and_rerank(
    query: str,
    index,
    all_chunks: List[dict],
    embed_model,
    reranker: BGEReranker,
    top_k: int = 10
) -> Tuple[List[int], List[float]]:
    """
    Retrieve top_k chunks for the query from the FAISS index and rerank them with BGE.
    EXACT implementation from META notebook.

    Args:
        query: User question
        index: FAISS index
        all_chunks: List of all chunk dictionaries
        embed_model: SentenceTransformer embedding model
        reranker: BGEReranker instance
        top_k: Number of initial candidates to retrieve

    Returns:
        Tuple of (reranked_chunk_indices, reranked_scores)
    """
    # Embed the query
    q_emb = embed_model.encode([query])

    # Normalize for IndexFlatIP (converts to cosine similarity)
    q_emb = q_emb / np.linalg.norm(q_emb, axis=1, keepdims=True)
    q_emb = np.array(q_emb, dtype=np.float32)

    # Search the FAISS index
    distances, indices = index.search(q_emb, top_k)
    top_indices = indices[0]  # indices of top_k retrieved chunks

    # Get the corresponding chunks
    retrieved_chunks = [all_chunks[idx] for idx in top_indices]

    # Rerank using BGE cross-encoder
    reranked_local_indices, reranked_scores = reranker.rerank(query, retrieved_chunks, top_k=None)

    # Map back to global indices
    reranked_global_indices = [int(top_indices[i]) for i in reranked_local_indices]

    return reranked_global_indices, reranked_scores


if __name__ == "__main__":
    # Test BGE reranker
    print("Testing BGE Reranker\n")

    reranker = BGEReranker()

    # Sample data
    query = "What is the policy on financial conflicts of interest?"
    chunks = [
        {"text": "The university has strict policies on financial conflicts of interest."},
        {"text": "Budget planning requires annual submissions."},
        {"text": "Conflicts of interest must be disclosed annually."},
    ]

    indices, scores = reranker.rerank(query, chunks)

    print(f"\nQuery: {query}\n")
    print("Reranked results:")
    for rank, (idx, score) in enumerate(zip(indices, scores), 1):
        print(f"{rank}. Score: {score:.4f}")
        print(f"   {chunks[idx]['text']}\n")
