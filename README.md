---
title: UIC RAG Policy Chatbot
emoji: 🚀
colorFrom: red
colorTo: red
sdk: streamlit
sdk_version: 1.40.1
app_file: streamlit_app.py
pinned: false
license: mit
short_description: AI-powered assistant for UIC policies (MetaRAG)
---

# UIC Policy Assistant prototype

AI-powered assistant for University of Illinois Chicago Vice Chancellor's Office policies using Meta Retrieval-Augmented Generation (MetaRAG).

## Features

- **Multi-format Document Support**: Parse PDF, DOCX, and TXT files with intelligent heading detection
- **Advanced Retrieval**: Hybrid search combining semantic embeddings, TF-IDF, and metadata filtering
- **Metadata Extraction**: Automatic extraction of 12 structured metadata fields using Gemini or Mistral
- **Smart Reranking**: BGE reranker for improved relevance
- **GEAR Enhancement**: Optional GPT-4o-mini triple extraction for complex queries
- **Interactive Web UI**: Streamlit-based interface with real-time search and filtering

## Architecture

```
┌─────────────────┐
│  User Query     │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────────┐
│  MetaRAG Pipeline                           │
├─────────────────────────────────────────────┤
│  1. Document Parser (PDF/DOCX/TXT)         │
│  2. Metadata Extraction (Gemini/Mistral)   │
│  3. Hybrid Retrieval                       │
│     • Semantic Search (FAISS)              │
│     • TF-IDF Matching                      │
│     • Prefix Fusion                        │
│  4. BGE Reranking                          │
│  5. Answer Generation (Gemini)             │
└─────────────────────────────────────────────┘
```

## Quick Start

### Prerequisites

- Python 3.8+
- pip or conda
- API Keys:
  - `GEMINI_API_KEY` (required for metadata & answer generation)
  - `MISTRAL_API_KEY` (optional, alternative metadata extractor)
  - `OPENAI_API_KEY` (optional, for GEAR enhancement)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/MetaRAG.git
cd MetaRAG
```

2. Create a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
# Create backend/.env file
cd backend
cat > .env << EOF
GEMINI_API_KEY=your_gemini_api_key_here
MISTRAL_API_KEY=your_mistral_api_key_here  # Optional
OPENAI_API_KEY=your_openai_api_key_here    # Optional for GEAR
EOF
```

### Usage

#### 1. Prepare Your Documents

Place your PDF, DOCX, or TXT files in:
```bash
backend/input_files/
```

#### 2. Build the Index

```bash
cd backend

# Build with Gemini metadata (recommended)
python -m meta_rag.build_index_gemini --max-size 3000 --overlap 200

# Or build with Mistral metadata
python -m meta_rag.build_index_mistral --max-size 3000 --overlap 200

# Quick build without metadata (for testing)
python -m meta_rag.build_index_mistral --no-metadata
```

**Build Options:**
- `--max-size`: Maximum chunk size in characters (default: 3000)
- `--overlap`: Overlap between chunks (default: 200)
- `--no-metadata`: Skip metadata extraction for faster testing
- `--enable-gear`: Enable GEAR triple extraction (requires OpenAI API key)
- `--metadata-delay`: Delay between metadata API calls (default: 0.5s for Gemini)

#### 3. Run the Application

```bash
# From project root, go to frontend directory
cd frontend
streamlit run app.py
```

The application will be available at **http://localhost:8501**

**Note**: The root directory contains `streamlit_app.py` which is only used for Streamlit Cloud deployment. For local development, always use `frontend/app.py`.

## Project Structure

```
MetaRAG/
├── backend/
│   ├── meta_rag/
│   │   ├── core/
│   │   │   ├── parser.py              # Document parsing (PDF/DOCX/TXT)
│   │   │   ├── chunker.py             # Text chunking with overlap
│   │   │   ├── metadata_gemini.py     # Gemini metadata extraction
│   │   │   └── metadata_mistral.py    # Mistral metadata extraction
│   │   ├── components/
│   │   │   ├── embedder.py            # Sentence transformer embeddings
│   │   │   ├── faiss_index.py         # FAISS vector indexing
│   │   │   ├── tfidf_index.py         # TF-IDF indexing
│   │   │   ├── reranker.py            # BGE reranker
│   │   │   └── gear.py                # GPT-4o-mini triple extraction
│   │   ├── build_index_gemini.py      # Gemini index builder
│   │   ├── build_index_mistral.py     # Mistral index builder
│   │   └── rag_backend.py             # Main RAG backend
│   ├── tests/                         # Test and evaluation scripts
│   ├── input_files/                   # Place documents here
│   ├── embeddings_output_GEMINI/      # Gemini-based indices (generated)
│   ├── embeddings_output_MISTRAL/     # Mistral-based indices (generated)
│   └── .env                           # API keys (not tracked)
│
├── frontend/
│   ├── app.py                         # Main Streamlit application
│   ├── rag_backend.py                 # Backend interface wrapper
│   ├── documents/                     # Document cache (auto-populated)
│   └── .streamlit/
│       └── secrets.toml               # Streamlit secrets (not tracked)
│
├── streamlit_app.py                   # Streamlit Cloud deployment wrapper
├── requirements.txt                   # Complete dependency list
├── cleanup.sh                         # Project cleanup script
├── .gitignore                         # Git ignore rules
└── README.md                          # This file
```

## Technical Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Document Parsing** | PyMuPDF, python-docx | Extract text from PDFs and Word docs |
| **Text Chunking** | Custom hybrid chunker | Split documents with overlap |
| **Embeddings** | all-MiniLM-L6-v2 | Generate 384-dim semantic embeddings |
| **Vector Search** | FAISS (IndexFlatIP) | Fast similarity search |
| **TF-IDF** | scikit-learn | Keyword-based retrieval |
| **Reranking** | BGE reranker-base | Improve retrieval relevance |
| **Metadata** | Gemini Flash / Mistral 7B | Extract 12 structured fields |
| **Answer Gen** | Gemini Flash | Generate natural language answers |
| **GEAR** | GPT-4o-mini | Triple extraction (optional) |
| **Web UI** | Streamlit | Interactive interface |

## Metadata Fields

The system automatically extracts 12 metadata fields from each document chunk:

1. **summary**: Brief chunk summary
2. **keywords**: Important keywords/phrases
3. **entities**: Named entities (people, organizations)
4. **effective_date**: Policy effective date
5. **fund_codes**: Financial account codes
6. **ilcs_citations**: Illinois statute citations
7. **title**: Document/section title
8. **category**: Main category (Financial, HR, Academic)
9. **sub_category**: Specific sub-category
10. **topic**: Main subject
11. **year**: Associated year
12. **content_type**: Document type (policy, guideline, procedure)

## Configuration

### Frontend Configuration

Edit `frontend/rag_backend.py` line 28 to change metadata source:

```python
def get_backend(use_reranker=True, use_gear=False, metadata_source="gemini"):
```

- `metadata_source="gemini"`: Use Gemini-extracted metadata (default)
- `metadata_source="mistral"`: Use Mistral-extracted metadata

### Backend Configuration

Edit `backend/meta_rag/rag_backend.py` for advanced settings:

- Retrieval parameters (k, weights)
- Reranker settings
- GEAR configuration

## Deployment

### GitHub

1. Ensure `.gitignore` is properly configured
2. Run cleanup script:
```bash
./cleanup.sh
```
3. Commit and push:
```bash
git add .
git commit -m "Initial commit"
git push origin main
```

### Hugging Face Spaces

1. Create a new Space on Hugging Face
2. Choose "Streamlit" as the SDK
3. Upload your repository
4. Add secrets in Space settings:
   - `GEMINI_API_KEY`
   - `MISTRAL_API_KEY` (if using)
   - `OPENAI_API_KEY` (if using GEAR)
5. The app will automatically deploy

**Note**: For Hugging Face deployment, you'll need to pre-build the index and include it in the repository, or build it on first run.

## Performance

- **Indexing**: ~2000 chunks from 10 PDF files in ~15 minutes (with metadata)
- **Query**: <2 seconds for retrieval + reranking
- **Accuracy**: Significant improvement over baseline RAG with metadata filtering

## Troubleshooting

### Index Not Found
```bash
# Rebuild the Gemini index
cd backend
python -m meta_rag.build_index_gemini

# Or rebuild the Mistral index
python -m meta_rag.build_index_mistral
```

### Streamlit Config Error
Ensure `st.set_page_config()` is the first Streamlit command in `frontend/app.py`

### Cache Issues
```bash
# Clear Python cache
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
```

### Missing Dependencies
```bash
# Reinstall all dependencies
pip install -r requirements.txt --force-reinstall
```

## Development

### Running Tests
```bash
cd backend
python meta_rag/rag_backend.py  # Test backend directly
```

### Cleanup Project
```bash
./cleanup.sh  # Removes logs, cache, old indices, temp files
```

## License

This project is developed for the UIC Vice Chancellor's Office.

## Acknowledgments

- Based on the META (Metadata-Enhanced Text Analysis) notebook methodology
- Uses Hugging Face transformers and sentence-transformers
- Powered by Google Gemini, Mistral AI, and OpenAI APIs

## Contact

This project was developed by the student team in IDS 560 (MS in Business Analytics) as part of a collaborative academic project for the UIC Vice Chancellor’s Office.

For questions or support, please contact: 
Hsin-jui Yang — Repository Owner & Project Maintainer
hyang723@uic.edu

Contributors

This project was collaboratively developed by the IDS 560 student team:
	•	Hsin-jui Yang — Frontend development, system integration, and deployment 
	•	Vamshi Krishna Aileni — Primary backend development
	•	Honglin Liu — Documentation, data cleaning, and QA support
  •	Haswatha Sriranga — Baseline RAG pipeline for comparison 


This repository reflects student work and is not an official UIC product.
