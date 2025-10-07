#!/usr/bin/env python3
"""
UIC Policy Assistant Launcher
Run this file to start the application
"""

import os
import sys
import subprocess
from pathlib import Path

def main():
    print("=" * 60)
    print("🚀 UIC Policy Assistant - MetaRAG System")
    print("=" * 60)

    # Check Python version
    if sys.version_info < (3, 10):
        print("❌ Error: Python 3.10 or higher required")
        print(f"   Current version: {sys.version}")
        return

    print(f"✅ Python version: {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")

    # Get paths
    project_root = Path(__file__).parent
    frontend_dir = project_root / "frontend"
    venv_path = frontend_dir / "venv"
    venv_python = venv_path / "bin" / "python"

    # Check if frontend venv exists
    if not venv_python.exists():
        print("\n⚠️  Frontend virtual environment not found")
        print("📦 Creating virtual environment...")

        try:
            subprocess.run([
                sys.executable, "-m", "venv", str(venv_path)
            ], check=True)
            print("✅ Virtual environment created")
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to create virtual environment: {e}")
            return

    # Install/upgrade dependencies
    print("\n📦 Checking dependencies...")
    requirements_file = frontend_dir / "requirements.txt"

    if requirements_file.exists():
        try:
            print("   Installing frontend dependencies...")
            subprocess.run([
                str(venv_python), "-m", "pip", "install", "--upgrade", "pip", "-q"
            ], check=True)

            subprocess.run([
                str(venv_python), "-m", "pip", "install", "-r", str(requirements_file), "-q"
            ], check=True)
            print("✅ Dependencies installed")
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to install dependencies: {e}")
            return

    # Check backend .env file
    backend_env = project_root / "backend" / ".env"
    if not backend_env.exists():
        print("\n⚠️  Warning: backend/.env file not found")
        print("   Please create it from .env.example and add your Gemini API key")
        print("   The app will run in demo mode without real RAG backend")

    # Change to frontend directory
    os.chdir(frontend_dir)

    # Launch Streamlit
    print("\n" + "=" * 60)
    print("🌐 Starting Streamlit application...")
    print("📍 URL: http://localhost:8501")
    print("🛑 Press Ctrl+C to stop")
    print("=" * 60 + "\n")

    try:
        subprocess.run([
            str(venv_python), "-m", "streamlit", "run", "app.py",
            "--server.port", "8501",
            "--server.address", "localhost"
        ])
    except KeyboardInterrupt:
        print("\n\n🛑 Application stopped")
    except Exception as e:
        print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    main()
