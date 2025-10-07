# UIC Policy Assistant

AI-powered assistant for University of Illinois Chicago Vice Chancellor's Office policies using Meta Retrieval-Augmented Generation (MetaRAG).

## Overview

This system provides an intelligent Q&A interface for UIC policy documents, combining:
- **Semantic Search**: FAISS vector similarity search across 757 document chunks
- **RAG Pipeline**: Retrieval-Augmented Generation for accurate answers
- **LLM Integration**: Google Gemini for natural language generation
- **Web Interface**: Interactive Streamlit application

## Quick Start

```bash
# Clone or download the repository
cd METARAG

# Run the automated setup and launch
python run_app.py
```

The application will be available at: **http://localhost:8501**

## Features

- ✅ **Retrieval-Augmented Generation (RAG)**: Combines document retrieval with LLM generation
- ✅ **Semantic Search**: Find relevant policies based on meaning, not just keywords
- ✅ **Source Citation**: Every answer shows the source documents with relevance scores
- ✅ **High Accuracy**: Average retrieval score of 0.88/1.0 on test queries
- ✅ **Interactive UI**: Clean, user-friendly Streamlit interface

## System Architecture

```
User Query
    ↓
[Streamlit Frontend]
    ↓
[Embedding Model] → Query Vector
    ↓
[FAISS Index] → Top-K Similar Documents (757 chunks)
    ↓
[Retrieved Context] + [User Query]
    ↓
[Gemini LLM] → Generated Answer
    ↓
[Display Answer + Sources]
```

## Requirements

- Python 3.10+
- 8GB+ RAM
- Internet connection (for downloading models and LLM API)

## Installation

For detailed setup instructions, see [SETUP.md](SETUP.md)

**Quick Install:**
```bash
pip install -r requirements.txt
```

**Configure API Key:**
1. Get Gemini API key from https://makersuite.google.com/app/apikey
2. Copy `backend/.env.example` to `backend/.env`
3. Add your API key to `.env`

## Usage

### Start the Application

```bash
python run_app.py
```

### Ask Questions

Example queries:
- "What are custodial funds?"
- "How should custodial funds be managed?"
- "What are the financial reporting requirements?"
- "What is the policy for deficit reporting?"

### View Sources

Click "View Sources" to see:
- Relevance scores (0-1 scale)
- Document categories
- Content type
- Full text and summaries

## Testing

Test the RAG backend:

```bash
cd backend
source MetaRAG_env/bin/activate
python minimal_test.py
```

Expected results:
- 100% success rate on sample queries
- Average relevance score: 0.88+
- Top result scores: 0.93+

## Project Structure

```
METARAG/
├── backend/                    # RAG processing pipeline
│   ├── MetaRAG_env/           # Python virtual environment
│   ├── embeddings_output/     # FAISS index (757 vectors, 384 dims)
│   │   └── naive/naive_embedding/
│   │       ├── index.faiss    # Vector index
│   │       ├── metadata.json  # Document metadata
│   │       └── id_mapping.pkl # ID mappings
│   ├── input_files/           # Source policy documents
│   ├── .env                   # API configuration
│   ├── minimal_test.py        # Test script
│   └── requirements.txt       # Backend dependencies
│
├── frontend/                   # Streamlit web app
│   ├── venv/                  # Python virtual environment
│   ├── app.py                 # Main application
│   ├── rag_backend.py         # RAG interface
│   └── requirements.txt       # Frontend dependencies
│
├── run_app.py                 # Automated launcher
├── requirements.txt           # Combined dependencies
├── README.md                  # This file
└── SETUP.md                   # Detailed setup guide
```

## Technology Stack

**Backend:**
- `sentence-transformers` - Text embeddings (Snowflake/arctic-embed-s)
- `faiss-cpu` - Vector similarity search
- `google-generativeai` - Gemini LLM
- `python-dotenv` - Configuration management

**Frontend:**
- `streamlit` - Web application framework

**Processing:**
- `numpy`, `pandas` - Data handling
- `scikit-learn` - Machine learning utilities
- `pypdf`, `pdfplumber` - Document processing

## Performance

**Retrieval Quality:**
- Average relevance score: **0.8645**
- Top result average: **0.8837**
- Best score achieved: **0.9711** (custodial funds query)
- Success rate: **100%** on test queries

**Response Time:**
- First query: 30-60 seconds (model loading)
- Subsequent queries: 2-5 seconds

## Course Information

**Course:** IDS 560 - Analytics Strategy and Practice
**Institution:** University of Illinois Chicago
**Purpose:** AI virtual assistant for the UIC Vice Chancellor's Office

## Troubleshooting

See [SETUP.md](SETUP.md) for detailed troubleshooting steps.

**Common issues:**
- Port 8501 in use: `pkill -f streamlit`
- Missing dependencies: `pip install -r requirements.txt`
- API errors: Check `.env` file configuration

## License

See [LICENSE](LICENSE) file for details.

## Support

For issues:
1. Review [SETUP.md](SETUP.md)
2. Check error messages
3. Verify virtual environments are activated
4. Ensure all dependencies are installed

---

**Powered by MetaRAG** | Built with ❤️ for UIC
