# UIC Policy Assistant - Setup Guide

Complete installation and setup instructions for the MetaRAG system.

## Prerequisites

- Python 3.10 or higher
- pip package manager
- 8GB+ RAM recommended
- Internet connection for downloading models

## Quick Start

### Option 1: One-Command Setup (Recommended)

Run the automated setup script:

```bash
python run_app.py
```

This will:
1. Check Python version
2. Verify/create virtual environment
3. Install all dependencies
4. Start the Streamlit application

The app will be available at: http://localhost:8501

### Option 2: Manual Setup

If you prefer manual installation, follow these steps:

## Step 1: Backend Setup

```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python -m venv MetaRAG_env

# Activate virtual environment
# On macOS/Linux:
source MetaRAG_env/bin/activate
# On Windows:
# MetaRAG_env\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Step 2: Configure Environment Variables

Create a `.env` file in the `backend/` directory:

```bash
cd backend
cp .env.example .env  # If example exists, otherwise create new file
```

Add your API keys to `backend/.env`:

```env
# LLM Provider (azure or gemini)
LLM_PROVIDER=gemini

# Gemini API Configuration
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-flash-latest

# Common LLM parameters
TEMPERATURE=0.5
```

**Get Gemini API Key:**
1. Go to https://makersuite.google.com/app/apikey
2. Create a new API key
3. Copy and paste into `.env` file

## Step 3: Frontend Setup

```bash
# Navigate to frontend directory
cd ../frontend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Step 4: Run the Application

### Method 1: Using run_app.py (Simplest)

From the METARAG root directory:

```bash
python run_app.py
```

### Method 2: Direct Streamlit Launch

```bash
# From frontend directory with activated venv
cd frontend
source venv/bin/activate
streamlit run app.py --server.port 8501 --server.address localhost
```

## Step 5: Access the Application

Open your browser and go to:
```
http://localhost:8501
```

## Testing the RAG Backend

To verify the RAG backend is working correctly:

```bash
# From backend directory with activated venv
cd backend
source MetaRAG_env/bin/activate
python minimal_test.py
```

This will run a test with 5 sample queries and show retrieval quality metrics.

## Project Structure

```
METARAG/
├── backend/                 # RAG pipeline and processing
│   ├── MetaRAG_env/        # Backend virtual environment
│   ├── embeddings_output/  # FAISS index and embeddings
│   ├── input_files/        # Source policy documents
│   ├── metadata/           # Generated metadata
│   ├── .env               # API keys and configuration
│   ├── requirements.txt    # Backend dependencies
│   └── minimal_test.py     # Test script
│
├── frontend/               # Streamlit web application
│   ├── venv/              # Frontend virtual environment
│   ├── app.py             # Main Streamlit app
│   ├── rag_backend.py     # RAG backend interface
│   └── requirements.txt    # Frontend dependencies
│
├── requirements.txt        # Combined dependencies
├── run_app.py             # Automated launcher
└── SETUP.md               # This file

```

## Troubleshooting

### Issue: "Module not found" errors

**Solution:** Make sure you're using the correct virtual environment:
```bash
# For backend
cd backend
source MetaRAG_env/bin/activate
pip install -r requirements.txt

# For frontend
cd frontend
source venv/bin/activate
pip install -r requirements.txt
```

### Issue: FAISS index not found

**Solution:** The embeddings should already be in `backend/embeddings_output/naive/naive_embedding/`. If missing, you'll need to regenerate them (contact the project maintainer).

### Issue: Gemini API errors

**Solution:**
1. Verify your API key in `backend/.env`
2. Check internet connection
3. Verify API quota at https://console.cloud.google.com

### Issue: Port 8501 already in use

**Solution:**
```bash
# Kill existing Streamlit processes
pkill -f streamlit

# Or use a different port
streamlit run app.py --server.port 8502
```

### Issue: Slow loading times

**Solution:**
- First launch takes 30-60 seconds to load the embedding model
- Subsequent queries are faster
- Ensure you have at least 8GB RAM available

## System Requirements

**Minimum:**
- Python 3.10+
- 8GB RAM
- 2GB free disk space

**Recommended:**
- Python 3.11+
- 16GB RAM
- SSD storage

## Features

- ✅ Retrieval-Augmented Generation (RAG)
- ✅ Semantic search across policy documents
- ✅ FAISS vector similarity search
- ✅ Gemini LLM integration
- ✅ Source citation and transparency
- ✅ Interactive web interface

## Support

For issues or questions:
1. Check this SETUP.md file
2. Review error messages carefully
3. Verify all dependencies are installed
4. Check that virtual environments are activated

## Development Notes

**Testing Backend:**
```bash
cd backend
source MetaRAG_env/bin/activate
python minimal_test.py  # Test retrieval quality
```

**Stopping the Application:**
- Press `Ctrl+C` in the terminal
- Or: `pkill -f streamlit`

**Resetting the Application:**
```bash
# Clear Streamlit cache
streamlit cache clear

# Or restart fresh
pkill -f streamlit
python run_app.py
```
