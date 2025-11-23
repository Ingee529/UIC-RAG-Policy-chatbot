"""
TF-IDF Weighted Embeddings - Extracted from META notebook
Augments chunk text with TF-IDF weighted keywords for better retrieval
"""

# --- Setup ---
from sentence_transformers import SentenceTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np
import pandas as pd
import json, os, time

# Load embedding model
embed_model = SentenceTransformer('all-MiniLM-L6-v2')
print("✅ Embedding model loaded.")

# Initialize text variants
texts_content = []
texts_tfidf = []
texts_prefix = []

# Extract base text from each chunk
corpus_texts = [chunk["text"] for chunk in all_chunks]

# Compute TF-IDF top keywords across all chunks
vectorizer = TfidfVectorizer(max_features=50, stop_words='english')
X = vectorizer.fit_transform(corpus_texts)
feature_names = vectorizer.get_feature_names_out()

# Prepare all chunks with 3 styles
for i, chunk in enumerate(all_chunks):
    content = chunk["text"]
    texts_content.append(content)

    # TF-IDF weighted keywords
    row = X.getrow(i)
    top_terms = []
    if row.getnnz() > 0:
        nz_indices = row.indices
        nz_weights = row.data
        sorted_idx = np.argsort(nz_weights)[::-1]
        top_terms = [feature_names[nz_indices[idx]] for idx in sorted_idx[:5]]

    weighted_text = content
    if top_terms:
        augmented_terms = []
        for j, term in enumerate(top_terms):
            repeat = 3 if j == 0 else 2 if j == 1 else 1
            augmented_terms.extend([term] * repeat)
        weighted_text = content + "\nKEYWORDS: " + " ".join(augmented_terms)
    texts_tfidf.append(weighted_text)

    # Prefix-fusion: summary + content
    summary = chunk.get("summary", "")
    prefix_text = f"SUMMARY: {summary}\n{content}" if summary else content
    texts_prefix.append(prefix_text)

# --- Embed (choose best strategy: tfidf for retrieval strength) ---
print("🧠 Computing semantic embeddings...")
embeddings = embed_model.encode(texts_tfidf, show_progress_bar=True, convert_to_numpy=True)

# Attach embedding to each chunk
for i, emb in enumerate(embeddings):
    all_chunks[i]["embedding"] = emb.tolist()

print("✅ Embeddings attached.")

# --- Add metadata & citation for GEAR ---
from tqdm import tqdm
tqdm.pandas()

for i, chunk in enumerate(all_chunks):
    chunk["chunk_id"] = i
    chunk["doc_name"] = os.path.basename(chunk.get("doc", "")) or "Unknown document"
    page = chunk.get("page")
    block_idx = chunk.get("block_index")
    chunk["citation"] = f"{chunk['doc_name']} – page {page}, block {block_idx}" if page is not None else chunk["doc_name"]


