"""
UIC Policy Assistant - Streamlit Cloud Entry Point
This file redirects to the main app in frontend/app.py
"""
import sys
import os
from pathlib import Path

# Get absolute path to frontend directory
frontend_dir = Path(__file__).parent.resolve() / "frontend"
app_file = frontend_dir / "app.py"

# Add frontend directory to Python path
sys.path.insert(0, str(frontend_dir))

# Read the app file before changing directory
with open(app_file, encoding="utf-8") as f:
    app_code = f.read()

# Change to frontend directory for relative file access (uic.png, etc.)
os.chdir(frontend_dir)

# Execute the main app
exec(app_code)
