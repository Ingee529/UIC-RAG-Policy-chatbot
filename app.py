"""
UIC Policy Assistant - Streamlit Cloud Entry Point
This file redirects to the main app in frontend/app.py
"""
import sys
import os
from pathlib import Path

# Add frontend directory to Python path
frontend_dir = Path(__file__).parent / "frontend"
sys.path.insert(0, str(frontend_dir))

# Change to frontend directory for relative file access (uic.png, etc.)
os.chdir(frontend_dir)

# Execute the main app from frontend directory
with open(frontend_dir / "app.py", encoding="utf-8") as f:
    exec(f.read())
