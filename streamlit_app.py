"""
UIC Policy Assistant - Streamlit Cloud Entry Point (Force Sync Version)
Features:
1. Download the dataset
2. Automatically fix nested folders
3. [Key change] Force-sync input_files (workaround for empty folder placeholder issue on GitHub)
4. Launch the app
"""

import sys
import os
import subprocess
def force_install(package_name, import_name):
    try:
        __import__(import_name)
        print(f"✅ {package_name} (module: {import_name}) is already installed.")
    except ImportError:
        print(f"⚠️ {package_name} not found! Force installing...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package_name])
            print(f"✅ {package_name} installed successfully!")
        except Exception as e:
            print(f"❌ Failed to install {package_name}: {e}")


force_install("faiss-cpu", "faiss")
force_install("sentence-transformers", "sentence_transformers")

import shutil
from pathlib import Path


# ========= 1. Path configuration =========
ROOT_DIR = Path(__file__).parent.resolve()
BACKEND_DIR = ROOT_DIR / "backend"
FRONTEND_DIR = ROOT_DIR / "frontend"

# Target paths
TARGET_INDEX_DIR = BACKEND_DIR / "embeddings_output_GEMINI"
TARGET_DOCS_DIR = BACKEND_DIR / "input_files"

# Dataset source
DATASET_REPO = "Ingee529/uic-policy-rag-data"

# ========= 2. Automatically download data =========
try:
    from huggingface_hub import snapshot_download
    print(f"📥 [System] Connecting to HF Dataset: {DATASET_REPO}")
    
    # Download to cache
    DOWNLOAD_CACHE_DIR = BACKEND_DIR / "download_cache"
    DOWNLOAD_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    
    snapshot_download(
        repo_id=DATASET_REPO,
        repo_type="dataset",
        local_dir=str(DOWNLOAD_CACHE_DIR),
        local_dir_use_symlinks=False,
        token=os.getenv("HF_TOKEN"),
    )
    print(f"✅ [System] Raw dataset downloaded to cache.")

    # ========= 3. Smart copying & force sync =========
    
    # --- A. Move index files (same as before) ---
    source_index_dir = DOWNLOAD_CACHE_DIR
    nested_index_dir = DOWNLOAD_CACHE_DIR / "embeddings_output_GEMINI"
    
    if nested_index_dir.exists():
        source_index_dir = nested_index_dir
        
    if not TARGET_INDEX_DIR.exists() or not any(TARGET_INDEX_DIR.iterdir()):
        print(f"📦 [System] Moving Index files to {TARGET_INDEX_DIR}...")
        # Make sure the parent directory exists
        TARGET_INDEX_DIR.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source_index_dir, TARGET_INDEX_DIR, dirs_exist_ok=True)
    else:
        print(f"ℹ️ [System] Index dir exists. (Checking contents...)")
        # Double-check: if the directory is empty, still copy
        if not any(TARGET_INDEX_DIR.glob("*.faiss")):
             print(f"⚠️ [System] Index dir is empty! Force copying...")
             shutil.copytree(source_index_dir, TARGET_INDEX_DIR, dirs_exist_ok=True)

    # --- B. Move input files ---
    source_docs_dir = DOWNLOAD_CACHE_DIR / "input_files"
    
    if source_docs_dir.exists():
        # Always merge/overwrite the target directory
        # This ensures PDFs from the dataset are synced even if the folder already exists
        print(f"📦 [System] Force syncing input_files to {TARGET_DOCS_DIR}...")
        TARGET_DOCS_DIR.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source_docs_dir, TARGET_DOCS_DIR, dirs_exist_ok=True)
        print(f"✅ [System] Documents synced successfully!")
    else:
        print("⚠️ [Warning] input_files folder not found in dataset.")

    # Clean up cache
    # shutil.rmtree(DOWNLOAD_CACHE_DIR) 

except Exception as e:
    print(f"⚠️ [System] Setup failed: {e}")
    import traceback
    traceback.print_exc()

# ========= 4. Set up environment and launch =========
if str(FRONTEND_DIR) not in sys.path:
    sys.path.insert(0, str(FRONTEND_DIR))
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.chdir(FRONTEND_DIR)
print(f"🚀 [System] Launching App...")

with open("app.py", encoding="utf-8") as f:
    exec(f.read())