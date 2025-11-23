#!/bin/bash
# MetaRAG Project Cleanup Script
# Prepares project for GitHub and Hugging Face deployment

echo "🧹 Starting MetaRAG cleanup..."

cd "$(dirname "$0")"

# Delete legacy code
echo "📦 Removing legacy code..."
rm -rf backend/legacy
rm -rf backend/chunking
rm -rf backend/embedding
rm -rf backend/metadata
rm -rf backend/retrieval
rm -rf backend/utils

# Delete log files
echo "📝 Removing log files..."
find . -name "*.log" -type f -delete

# Delete cache files
echo "💾 Removing cache files..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete
find . -name ".DS_Store" -delete
find . -name ".Rhistory" -delete

# Delete test outputs and legacy output directories
echo "🧪 Removing test outputs and legacy directories..."
rm -rf backend/retrieval_output
rm -rf backend/flare_data_high_quality
rm -rf backend/chunk_output
rm -rf backend/embeddings_output
rm -rf backend/metadata_gen_output
rm -rf backend/evaluation
rm -f backend/metadata_log.txt
rm -f backend/metadata_comparison.json
rm -f backend/minimal_test_results.json
rm -f backend/simple_test_results.json
rm -f backend/metadata_full_log.txt
rm -f backend/metadata_success_log.txt
rm -f backend/embeddings_log.txt
rm -f backend/compare_metadata.py
rm -f backend/test_gemini_metadata.py
rm -f backend/reorganize_backend.py
rm -f backend/rag_backend.py
rm -f backend/config.py
rm -f backend/download_models.py
rm -f backend/run_both_metadata.sh
rm -f frontend/test_backend.py
rm -f frontend/test_reranker.py
rm -f frontend/check_env.py
rm -f frontend/startup.log

# Delete old virtual environments (keep only .venv)
echo "🐍 Removing old virtual environments..."
rm -rf backend/MetaRAG_env
rm -rf frontend/venv

# Delete unnecessary markdown files
echo "📄 Removing unnecessary docs..."
rm -f INTEGRATION_COMPLETE.md

# Keep only necessary files
echo "✨ Cleanup complete!"
echo ""
echo "📊 Project structure cleaned for deployment"
ls -la

