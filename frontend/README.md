# UIC Policy Assistant - Frontend

Interactive Streamlit web interface for the MetaRAG system, providing an AI-powered policy question-answering experience for the UIC Vice Chancellor's Office.

## Features

- 💬 **Conversational Interface** - Natural language chat with the policy assistant
- 📄 **Source Citations** - View relevant policy document excerpts with metadata
- 🔍 **Advanced Search** - Hybrid retrieval combining semantic search, TF-IDF, and metadata filtering
- 🎯 **Smart Reranking** - BGE reranker for improved answer relevance
- ⚙️ **Configurable Backend** - Switch between Gemini and Mistral metadata sources
- 🎨 **Clean UI** - Professional interface designed for UIC branding

## Quick Start

### 1. Prerequisites

Ensure you have built the index in the backend:

```bash
cd ../backend
python -m meta_rag.build_index_gemini --max-size 3000 --overlap 200
```

### 2. Install Dependencies

```bash
pip install -r ../requirements.txt
```

### 3. Configure API Keys

Create a `.streamlit/secrets.toml` file (or use `backend/.env`):

```toml
GEMINI_API_KEY = "your_gemini_api_key_here"
MISTRAL_API_KEY = "your_mistral_api_key_here"  # Optional
OPENAI_API_KEY = "your_openai_api_key_here"    # Optional for GEAR
```

### 4. Run the Application

```bash
streamlit run app.py
```

The app will open at `http://localhost:8501`

## Architecture

The frontend connects to the backend through `rag_backend.py`, which:

1. **Imports Backend**: Adds `backend/` to Python path and imports MetaRAG
2. **Caches Models**: Uses `@st.cache_resource` to load models once per session
3. **Provides Interface**: Exposes `get_backend()` function for the UI

```
┌──────────────┐
│  app.py      │  (Streamlit UI)
└──────┬───────┘
       │
       ▼
┌─────────────────┐
│ rag_backend.py  │  (Interface layer)
└──────┬──────────┘
       │
       ▼
┌──────────────────────────────┐
│ backend/meta_rag/rag_backend │  (Core RAG engine)
└──────────────────────────────┘
```

## Configuration

### Metadata Source

Edit `rag_backend.py` line 28 to switch metadata sources:

```python
def get_backend(use_reranker=True, use_gear=False, metadata_source="gemini"):
    # metadata_source="gemini"  - Use Gemini-extracted metadata (default)
    # metadata_source="mistral" - Use Mistral-extracted metadata
```

### UI Customization

Modify `app.py` to customize:
- Page title and icon (line ~10)
- Sidebar settings (line ~200)
- Example questions (line ~190)
- Answer formatting (line ~600)

## Project Structure

```
frontend/
├── app.py                    # Main Streamlit application
├── rag_backend.py            # Backend interface wrapper
├── documents/                # Auto-populated document cache
├── .streamlit/
│   └── secrets.toml          # API keys (not tracked in git)
└── README.md                 # This file
```

## Features Detail

### 1. Chat Interface
- Persistent conversation history
- Streaming responses (if enabled)
- Source document citations
- Metadata display (keywords, entities, dates)

### 2. Search & Retrieval
- **Hybrid Search**: Combines FAISS semantic search + TF-IDF
- **Metadata Filtering**: Filter by category, year, fund codes, etc.
- **BGE Reranking**: Reorders results by relevance
- **GEAR Enhancement**: Optional graph-based triple extraction

### 3. Document Display
- Shows top-k most relevant chunks
- Displays extracted metadata fields
- Provides document source information
- Highlights key entities and keywords

## Deployment

### Local Development

```bash
cd frontend
streamlit run app.py
```

### Streamlit Cloud

1. Push code to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect repository
4. Set main file to `streamlit_app.py` (root wrapper)
5. Add secrets in Settings > Secrets
6. Deploy!

**Note**: The root `streamlit_app.py` is specifically for Streamlit Cloud deployment. For local development, always use `frontend/app.py`.

### Hugging Face Spaces

1. Create new Space with Streamlit SDK
2. Upload repository
3. Add secrets in Space settings
4. App deploys automatically

**Important**: Pre-build indices and include in repository, or build on first run with `--no-metadata` for faster startup.

## Troubleshooting

### Backend Import Error

If you see `"Could not import MetaRAG backend"`:

```python
# Check Python path in rag_backend.py
BACKEND_DIR = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))
```

### Index Not Found

```bash
cd ../backend
python -m meta_rag.build_index_gemini
```

### API Key Issues

Ensure secrets are set:
- Local: `backend/.env` or `.streamlit/secrets.toml`
- Cloud: Streamlit/Hugging Face secrets settings

### Cache Issues

Clear Streamlit cache:
```bash
streamlit cache clear
```

Or restart with:
```bash
streamlit run app.py --server.runOnSave false
```

## Development

### Adding New Features

1. **New UI Components**: Edit `app.py` sidebar/main sections
2. **New Retrieval Methods**: Modify `backend/meta_rag/rag_backend.py`
3. **New Metadata Fields**: Update `backend/meta_rag/core/metadata_*.py`

### Testing

```bash
# Test backend connection
python -c "from rag_backend import get_backend; backend = get_backend(); print('✅ Backend loaded')"
```

## Related

- **Main Project**: `../` (MetaRAG root)
- **Backend Code**: `../backend/meta_rag/`
- **Documentation**: `../README.md`
- **Tests**: `../backend/tests/`

## License

This project is developed for the UIC Vice Chancellor's Office.

## Contact

For questions or support, please contact the UIC Vice Chancellor's Office IT team.
