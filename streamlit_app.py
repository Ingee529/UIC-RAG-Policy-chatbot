"""
UIC Policy Assistant - Streamlit Cloud Entry Point (Smart Bridge)
功能：
1. 下載 Dataset
2. 自動修復「資料夾包資料夾」的巢狀問題 (Nesting Fix)
3. 搬運 input_files
4. 啟動 App
"""

import sys
import os
import shutil
from pathlib import Path

# ========= 1. 設定路徑 =========
ROOT_DIR = Path(__file__).parent.resolve()
BACKEND_DIR = ROOT_DIR / "backend"
FRONTEND_DIR = ROOT_DIR / "frontend"

# 資料下載目標 (這是 rag_backend 預設會去讀的地方)
TARGET_INDEX_DIR = BACKEND_DIR / "embeddings_output_GEMINI"
TARGET_DOCS_DIR = BACKEND_DIR / "input_files"

# Dataset 來源
DATASET_REPO = "Ingee529/uic-policy-rag-data"

# ========= 2. 自動下載資料 =========
try:
    from huggingface_hub import snapshot_download
    print(f"📥 [System] Connecting to HF Dataset: {DATASET_REPO}")
    
    # 為了避免混亂，我們先下載到一個臨時的 Cache 資料夾
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

    # ========= 3. 智慧搬運 (Smart Move) =========
    
    # --- A. 處理 Index (FAISS) ---
    # 情況 1: 檔案在 Cache 根目錄 (正確結構)
    # 情況 2: 檔案在 Cache/embeddings_output_GEMINI 裡面 (巢狀結構)
    
    source_index_dir = DOWNLOAD_CACHE_DIR
    nested_index_dir = DOWNLOAD_CACHE_DIR / "embeddings_output_GEMINI"
    
    if nested_index_dir.exists():
        print("⚠️ [System] Detected nested index folder. Adjusting path...")
        source_index_dir = nested_index_dir
        
    # 把 Index 搬到正確位置 (TARGET_INDEX_DIR)
    if not TARGET_INDEX_DIR.exists():
        # 檢查來源有沒有關鍵檔案 (index_content.faiss 或 index.faiss)
        has_index = any(source_index_dir.glob("*.faiss"))
        if has_index:
            print(f"📦 [System] Moving Index files to {TARGET_INDEX_DIR}...")
            shutil.copytree(source_index_dir, TARGET_INDEX_DIR, dirs_exist_ok=True)
        else:
            print(f"❌ [Error] No .faiss files found in {source_index_dir}!")
    else:
        print(f"ℹ️ [System] Index dir already exists at {TARGET_INDEX_DIR}")

    # --- B. 處理 Input Files (PDF) ---
    source_docs_dir = DOWNLOAD_CACHE_DIR / "input_files"
    
    if source_docs_dir.exists():
        if not TARGET_DOCS_DIR.exists():
            print(f"📦 [System] Moving input_files to {TARGET_DOCS_DIR}...")
            shutil.copytree(source_docs_dir, TARGET_DOCS_DIR)
        else:
            print(f"ℹ️ [System] Docs dir already exists at {TARGET_DOCS_DIR}")
    else:
        print("⚠️ [Warning] input_files folder not found in dataset.")

    # 清理 Cache (可選)
    # shutil.rmtree(DOWNLOAD_CACHE_DIR) 

except Exception as e:
    print(f"⚠️ [System] Setup failed: {e}")
    # 繼續嘗試執行，也許本地已經有檔案了

# ========= 4. 設定環境並啟動 =========
if str(FRONTEND_DIR) not in sys.path:
    sys.path.insert(0, str(FRONTEND_DIR))
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.chdir(FRONTEND_DIR)
print(f"🚀 [System] Launching App...")

with open("app.py", encoding="utf-8") as f:
    exec(f.read())