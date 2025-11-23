"""
Build Enhanced FAISS Index - V2 
From META Notebook, components:
- Hybrid chunking
- TF-IDF weighted embeddings
- GEAR triple extraction
- Metadata extraction with Mistral
"""

import os
import sys
import json
import pickle
import argparse
from pathlib import Path
from typing import Dict, List, Optional
from collections import defaultdict

import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from dotenv import load_dotenv
from tqdm import tqdm

# Import modules from notebook (using relative imports)
from .core.parser import parse_directory
from .components.chunking import chunk_blocks  # Cell 8 - Hybrid chunking
from .core.metadata_mistral import MistralMetadataExtractor  # Mistral metadata extraction
from .components.gear_triples import extract_triples_from_text  # Cell 59 - GPT-4o-mini


class IndexBuilderV2:
    """Build FAISS index with all META notebook features"""

    def __init__(
        self,
        input_dir: str,
        output_dir: str,
        embedding_model_name: str = "all-MiniLM-L6-v2",
        mistral_api_key: Optional[str] = None,
        openai_api_key: Optional[str] = None,
        use_metadata_extraction: bool = True,
        use_tfidf_augmentation: bool = True,
        use_gear: bool = False  # Requires OpenAI key
    ):
        """
        Initialize the index builder.

        Args:
            input_dir: Directory containing input documents
            output_dir: Directory to save index and metadata
            embedding_model_name: Name of SentenceTransformer model (default: all-MiniLM-L6-v2)
            mistral_api_key: Mistral API key for metadata extraction
            openai_api_key: OpenAI API key for GEAR triple extraction
            use_metadata_extraction: Whether to extract metadata with Mistral
            use_tfidf_augmentation: Whether to augment embeddings with TF-IDF keywords
            use_gear: Whether to extract triples for GEAR (requires OpenAI key)
        """
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.embedding_model_name = embedding_model_name
        self.use_metadata_extraction = use_metadata_extraction
        self.use_tfidf_augmentation = use_tfidf_augmentation
        self.use_gear = use_gear

        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Load embedding model
        print(f"📦 Loading embedding model: {embedding_model_name}")
        self.embedding_model = SentenceTransformer(embedding_model_name)

        # Initialize metadata extractor if requested
        self.metadata_extractor = None
        if use_metadata_extraction:
            if mistral_api_key:
                print("🔑 Initializing Mistral metadata extractor")
                self.metadata_extractor = MetadataExtractor(api_key=mistral_api_key)
            else:
                print("⚠️  No Mistral API key provided, skipping metadata extraction")

        # Set OpenAI key for GEAR
        if use_gear and openai_api_key:
            os.environ["OPENAI_API_KEY"] = openai_api_key
            print("🔑 OpenAI API key set for GEAR")
        elif use_gear:
            print("⚠️  GEAR requested but no OpenAI key provided, skipping GEAR")
            self.use_gear = False

    def parse_documents(self, extensions: Optional[List[str]] = None) -> Dict[str, List[Dict]]:
        """Parse all documents in input directory."""
        print(f"\n📄 Parsing documents from: {self.input_dir}")
        documents_blocks = parse_directory(str(self.input_dir), extensions=extensions)
        print(f"✅ Parsed {len(documents_blocks)} documents")
        return documents_blocks

    def chunk_documents_hybrid(
        self,
        documents_blocks: Dict[str, List[Dict]],
        max_size: int = 3000,
        overlap: int = 200
    ) -> List[Dict]:
        """
        Chunk documents using notebook's hybrid strategy (Cell 8).

        Args:
            documents_blocks: Dictionary mapping doc names to lists of blocks
            max_size: Maximum chunk size in characters (default: 3000)
            overlap: Character overlap between chunks (default: 200)

        Returns:
            List of chunks with metadata
        """
        print(f"\n✂️  Chunking documents using Hybrid strategy (max_size={max_size}, overlap={overlap})")
        all_chunks = []

        for doc_name, blocks in tqdm(documents_blocks.items(), desc="Chunking documents"):
            chunks = chunk_blocks(doc_name, blocks, max_size=max_size, overlap=overlap)
            all_chunks.extend(chunks)

        print(f"✅ Generated {len(all_chunks)} chunks from {len(documents_blocks)} documents")
        return all_chunks

    def enrich_with_metadata(self, chunks: List[Dict], delay: float = 1.0) -> List[Dict]:
        """Enrich chunks with Mistral metadata extraction."""
        if not self.metadata_extractor:
            print("⚠️  Skipping metadata extraction (no API key)")
            return chunks

        print(f"\n🔍 Extracting metadata for {len(chunks)} chunks using Mistral")
        print("⏱️  This may take a while...")
        enriched_chunks = self.metadata_extractor.enrich_chunks(
            chunks,
            delay=delay,
            batch_size=10,
            verbose=True
        )
        return enriched_chunks

    def prepare_three_text_variants(self, chunks: List[Dict]) -> tuple:
        """
        Prepare 3 text variants for 3-index strategy (notebook Cell 20):
        1. texts_content: Plain chunk text
        2. texts_tfidf: Text + TF-IDF weighted keywords
        3. texts_prefix: Summary prefix + text

        Returns:
            Tuple of (texts_content, texts_tfidf, texts_prefix)
        """
        # Handle empty chunks case
        if len(chunks) == 0:
            print("⚠️  No chunks to process")
            return [], [], []

        print(f"\n🔤 Preparing 3 text variants for {len(chunks)} chunks")

        # Extract base text from each chunk
        corpus_texts = [chunk["text"] for chunk in chunks]

        # Initialize text variants
        texts_content = []
        texts_tfidf = []
        texts_prefix = []

        # Compute TF-IDF top keywords across all chunks
        vectorizer = TfidfVectorizer(max_features=50, stop_words='english')
        X = vectorizer.fit_transform(corpus_texts)
        feature_names = vectorizer.get_feature_names_out()

        # Prepare all 3 variants
        for i, chunk in enumerate(tqdm(chunks, desc="Preparing text variants")):
            content = chunk["text"]

            # 1. Content-only (baseline)
            texts_content.append(content)

            # 2. TF-IDF weighted keywords
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

            # 3. Prefix-fusion: summary + content
            summary = chunk.get("summary", "")
            prefix_text = f"SUMMARY: {summary}\n{content}" if summary else content
            texts_prefix.append(prefix_text)

        print(f"✅ Prepared 3 text variants:")
        print(f"   - texts_content: {len(texts_content)} items")
        print(f"   - texts_tfidf: {len(texts_tfidf)} items")
        print(f"   - texts_prefix: {len(texts_prefix)} items")

        return texts_content, texts_tfidf, texts_prefix

    def extract_gear_triples(self, chunks: List[Dict]) -> List[Dict]:
        """
        Extract knowledge graph triples using GPT-4o-mini (Cell 59).

        Returns:
            List of triples with chunk_id: [(subject, predicate, object, chunk_id), ...]
        """
        if not self.use_gear:
            print("⚠️  Skipping GEAR triple extraction")
            return []

        print(f"\n🕸️  Extracting knowledge graph triples with GPT-4o-mini")
        all_triples = []

        for i, chunk in enumerate(tqdm(chunks, desc="GEAR triple extraction")):
            text = chunk["text"]
            triples_list = extract_triples_from_text(text, query=None, model="gpt-4o-mini")

            # Convert to tuple format with chunk_id
            for triple_dict in triples_list:
                triple = (
                    triple_dict["subject"],
                    triple_dict["predicate"],
                    triple_dict["object"],
                    i  # chunk_id
                )
                all_triples.append(triple)

        print(f"✅ Extracted {len(all_triples)} triples from {len(chunks)} chunks")
        return all_triples

    def build_three_faiss_indices(
        self,
        texts_content: List[str],
        texts_tfidf: List[str],
        texts_prefix: List[str]
    ) -> tuple:
        """
        Build 3 FAISS IndexFlatIP indices (notebook Cell 20):
        1. index_content: Content-only embeddings
        2. index_tfidf: TF-IDF augmented embeddings
        3. index_prefix: Summary-prefixed embeddings

        Args:
            texts_content: Plain text chunks
            texts_tfidf: TF-IDF augmented chunks
            texts_prefix: Summary-prefixed chunks

        Returns:
            Tuple of (index_content, index_tfidf, index_prefix,
                     embeddings_content, embeddings_tfidf, embeddings_prefix)
        """
        print(f"\n🧠 Building 3 FAISS indices")

        # 1. Embed content-only texts
        print("\n1️⃣  Computing content-only embeddings...")
        embeddings_content = self.embedding_model.encode(
            texts_content,
            batch_size=64,
            show_progress_bar=True,
            convert_to_numpy=True
        )
        embeddings_content = embeddings_content.astype(np.float32)
        faiss.normalize_L2(embeddings_content)

        # 2. Embed TF-IDF augmented texts
        print("\n2️⃣  Computing TF-IDF augmented embeddings...")
        embeddings_tfidf = self.embedding_model.encode(
            texts_tfidf,
            batch_size=64,
            show_progress_bar=True,
            convert_to_numpy=True
        )
        embeddings_tfidf = embeddings_tfidf.astype(np.float32)
        faiss.normalize_L2(embeddings_tfidf)

        # 3. Embed prefix-fusion texts
        print("\n3️⃣  Computing prefix-fusion embeddings...")
        embeddings_prefix = self.embedding_model.encode(
            texts_prefix,
            batch_size=64,
            show_progress_bar=True,
            convert_to_numpy=True
        )
        embeddings_prefix = embeddings_prefix.astype(np.float32)
        faiss.normalize_L2(embeddings_prefix)

        # Build FAISS indices
        dimension = embeddings_content.shape[1]
        print(f"\n📊 Building FAISS IndexFlatIP (dimension={dimension})")

        index_content = faiss.IndexFlatIP(dimension)
        index_tfidf = faiss.IndexFlatIP(dimension)
        index_prefix = faiss.IndexFlatIP(dimension)

        index_content.add(embeddings_content)
        index_tfidf.add(embeddings_tfidf)
        index_prefix.add(embeddings_prefix)

        print(f"✅ Built 3 FAISS indices:")
        print(f"   - index_content: {index_content.ntotal} vectors")
        print(f"   - index_tfidf: {index_tfidf.ntotal} vectors")
        print(f"   - index_prefix: {index_prefix.ntotal} vectors")

        return (
            index_content, index_tfidf, index_prefix,
            embeddings_content, embeddings_tfidf, embeddings_prefix
        )

    def save_three_indices(
        self,
        index_content: faiss.Index,
        index_tfidf: faiss.Index,
        index_prefix: faiss.Index,
        chunks: List[Dict],
        embeddings_content: np.ndarray,
        embeddings_tfidf: np.ndarray,
        embeddings_prefix: np.ndarray,
        triples: List = None
    ):
        """Save 3 FAISS indices and metadata to disk."""
        print(f"\n💾 Saving 3 indices to: {self.output_dir}")

        # Save 3 FAISS indices
        index_content_path = self.output_dir / "index_content.faiss"
        index_tfidf_path = self.output_dir / "index_tfidf.faiss"
        index_prefix_path = self.output_dir / "index_prefix.faiss"

        faiss.write_index(index_content, str(index_content_path))
        faiss.write_index(index_tfidf, str(index_tfidf_path))
        faiss.write_index(index_prefix, str(index_prefix_path))

        print(f"✅ Saved index_content: {index_content_path}")
        print(f"✅ Saved index_tfidf: {index_tfidf_path}")
        print(f"✅ Saved index_prefix: {index_prefix_path}")

        # Build metadata dictionary
        metadata = {}
        id_to_index = {}
        index_to_id = {}

        for i, chunk in enumerate(chunks):
            chunk_id = f"chunk_{i}"
            chunk["chunk_id"] = i

            # Store all 3 embeddings
            chunk["embedding_content"] = embeddings_content[i].tolist()
            chunk["embedding_tfidf"] = embeddings_tfidf[i].tolist()
            chunk["embedding_prefix"] = embeddings_prefix[i].tolist()

            # Add citation info
            doc_name = os.path.basename(chunk.get("doc", ""))
            page = chunk.get("page")
            block_idx = chunk.get("block_index")
            chunk["doc_name"] = doc_name
            chunk["citation"] = f"{doc_name} – page {page}, block {block_idx}" if page is not None else doc_name

            metadata[chunk_id] = chunk
            id_to_index[chunk_id] = i
            index_to_id[i] = chunk_id

        # Save metadata
        metadata_path = self.output_dir / "metadata.json"
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        print(f"✅ Saved metadata: {metadata_path}")

        # Save ID mapping
        id_mapping_path = self.output_dir / "id_mapping.pkl"
        with open(id_mapping_path, 'wb') as f:
            pickle.dump({
                'id_to_index': id_to_index,
                'index_to_id': index_to_id
            }, f)
        print(f"✅ Saved ID mapping: {id_mapping_path}")

        # Save triples if GEAR was used
        if triples and len(triples) > 0:
            triples_path = self.output_dir / "gear_triples.json"
            with open(triples_path, 'w', encoding='utf-8') as f:
                json.dump(triples, f, indent=2, ensure_ascii=False)
            print(f"✅ Saved GEAR triples: {triples_path}")

        # Save index info
        info = {
            "model_name": self.embedding_model_name,
            "num_chunks": len(chunks),
            "dimension": embeddings_content.shape[1],
            "has_metadata_extraction": self.metadata_extractor is not None,
            "has_three_indices": True,
            "has_gear": self.use_gear and triples and len(triples) > 0,
            "num_triples": len(triples) if triples else 0
        }
        info_path = self.output_dir / "index_info.json"
        with open(info_path, 'w') as f:
            json.dump(info, f, indent=2)
        print(f"✅ Saved index info: {info_path}")

    def build(
        self,
        max_size: int = 3000,
        overlap: int = 200,
        extract_metadata: bool = True,
        metadata_delay: float = 1.0,
        extensions: Optional[List[str]] = None
    ):
        """
        Run the complete build pipeline.

        Args:
            max_size: Maximum chunk size in characters (default: 3000)
            overlap: Character overlap between chunks (default: 200)
            extract_metadata: Whether to extract metadata
            metadata_delay: Delay between metadata API calls (default: 1.0s)
            extensions: List of file extensions to parse (default: None = all)
        """
        print("=" * 60)
        print("🚀 Building Enhanced FAISS Index (META Notebook V2)")
        print("=" * 60)

        # Step 1: Parse documents
        documents_blocks = self.parse_documents(extensions=extensions)

        # Step 2: Chunk documents with hybrid strategy
        chunks = self.chunk_documents_hybrid(
            documents_blocks,
            max_size=max_size,
            overlap=overlap
        )

        # Step 3: Enrich with metadata (Mistral)
        if extract_metadata:
            chunks = self.enrich_with_metadata(chunks, delay=metadata_delay)

        # Step 4: Prepare 3 text variants (content, tfidf, prefix)
        texts_content, texts_tfidf, texts_prefix = self.prepare_three_text_variants(chunks)

        # Step 5: Extract GEAR triples (GPT-4o-mini)
        triples = self.extract_gear_triples(chunks)

        # Step 6: Build 3 FAISS indices
        (index_content, index_tfidf, index_prefix,
         embeddings_content, embeddings_tfidf, embeddings_prefix) = self.build_three_faiss_indices(
            texts_content, texts_tfidf, texts_prefix
        )

        # Step 7: Save everything
        self.save_three_indices(
            index_content, index_tfidf, index_prefix,
            chunks,
            embeddings_content, embeddings_tfidf, embeddings_prefix,
            triples
        )

        print("\n" + "=" * 60)
        print("✅ Index building complete!")
        print("=" * 60)
        print(f"📊 Summary:")
        print(f"   - Total chunks: {len(chunks)}")
        print(f"   - Embedding dimension: {embeddings_content.shape[1]}")
        print(f"   - Metadata extracted: {self.metadata_extractor is not None}")
        print(f"   - 3 indices built: content, tfidf, prefix")
        print(f"   - GEAR triples: {len(triples) if triples else 0}")
        print(f"   - Output directory: {self.output_dir}")


def main():
    parser = argparse.ArgumentParser(description="Build enhanced FAISS index (META notebook V2)")
    parser.add_argument("--input-dir", default="input_files", help="Input directory")
    parser.add_argument("--output-dir", default="new_embeddings_output", help="Output directory")
    parser.add_argument("--max-size", type=int, default=3000, help="Max chunk size (chars)")
    parser.add_argument("--overlap", type=int, default=200, help="Chunk overlap (chars)")
    parser.add_argument("--no-metadata", action="store_true", help="Skip metadata extraction")
    parser.add_argument("--no-tfidf", action="store_true", help="Skip TF-IDF augmentation")
    parser.add_argument("--enable-gear", action="store_true", help="Enable GEAR triple extraction")
    parser.add_argument("--metadata-delay", type=float, default=1.0, help="Delay between API calls")
    args = parser.parse_args()

    # Load environment variables
    load_dotenv()
    mistral_key = os.getenv("MISTRAL_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")

    # Build index
    builder = IndexBuilderV2(
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        embedding_model_name="all-MiniLM-L6-v2",
        mistral_api_key=mistral_key,
        openai_api_key=openai_key,
        use_metadata_extraction=not args.no_metadata,
        use_tfidf_augmentation=not args.no_tfidf,
        use_gear=args.enable_gear
    )

    builder.build(
        max_size=args.max_size,
        overlap=args.overlap,
        extract_metadata=not args.no_metadata,
        metadata_delay=args.metadata_delay
    )


if __name__ == "__main__":
    main()
