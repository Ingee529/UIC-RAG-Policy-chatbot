"""
RAG Backend Interface
Connects to the Enhanced MetaRAG retrieval system (MetaRAG V2)
STRICTLY NO LEGACY BACKEND
"""
import sys
import os
from pathlib import Path

# Add the backend directory to Python path
BACKEND_DIR = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))

import streamlit as st

# Import the MetaRAG backend (V2)
try:
    from meta_rag.rag_backend import get_backend_v2
    METARAG_AVAILABLE = True
    print("✅ MetaRAG backend imported successfully")
except ImportError as e:
    METARAG_AVAILABLE = False
    print(f"❌ MetaRAG backend not available: {e}")
    raise ImportError(f"Could not import MetaRAG backend: {e}")


@st.cache_resource(show_spinner="Loading RAG Backend...")
def get_backend(use_reranker=True, use_gear=False, metadata_source="gemini"):
    """
    Get the MetaRAG backend singleton using Streamlit's cache_resource.
    This ensures the model is loaded only once and persists across reruns.
    
    Args:
        use_reranker: Whether to use BGE reranker
        use_gear: Whether to use GEAR graph retrieval
        metadata_source: "mistral" or "gemini" - determines which index to use (default: "gemini")
    """
    print(f"🚀 Loading MetaRAG Backend (Cached, metadata_source={metadata_source})...")
    try:
        # Initialize backend with selected metadata source
        backend = get_backend_v2(
            use_reranker=use_reranker, 
            use_gear=use_gear,
            metadata_source=metadata_source
        )
        print(f"✅ MetaRAG loaded successfully (reranker={use_reranker}, gear={use_gear}, metadata={metadata_source})")
        return backend
    except Exception as e:
        print(f"❌ Failed to load MetaRAG: {e}")
        raise e
