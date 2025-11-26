"""
UIC Policy Assistant - Streamlit Cloud Entry Point (Force Sync Version)
功能：
1. 下載 Dataset
2. 自動修復巢狀資料夾
3. 【關鍵修改】強制同步 input_files (解決 GitHub 空資料夾佔位問題)
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

# 目標路徑
TARGET_INDEX_DIR = BACKEND_DIR / "embeddings_output_GEMINI"
TARGET_DOCS_DIR = BACKEND_DIR / "input_files"

# Dataset 來源
DATASET_REPO = "Ingee529/uic-policy-rag-data"

# ========= 2. 自動下載資料 =========
try:
    from huggingface_hub import snapshot_download
    print(f"📥 [System] Connecting to HF Dataset: {DATASET_REPO}")
    
    # 下載到 Cache
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

    # ========= 3. 智慧搬運 & 強制同步 =========
    
    # --- A. Index 搬運 (保持不變) ---
    source_index_dir = DOWNLOAD_CACHE_DIR
    nested_index_dir = DOWNLOAD_CACHE_DIR / "embeddings_output_GEMINI"
    
    if nested_index_dir.exists():
        source_index_dir = nested_index_dir
        
    if not TARGET_INDEX_DIR.exists() or not any(TARGET_INDEX_DIR.iterdir()):
        print(f"📦 [System] Moving Index files to {TARGET_INDEX_DIR}...")
        # 確保父目錄存在
        TARGET_INDEX_DIR.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source_index_dir, TARGET_INDEX_DIR, dirs_exist_ok=True)
    else:
        print(f"ℹ️ [System] Index dir exists. (Checking contents...)")
        # 雙重保險：如果裡面是空的，還是要搬
        if not any(TARGET_INDEX_DIR.glob("*.faiss")):
             print(f"⚠️ [System] Index dir is empty! Force copying...")
             shutil.copytree(source_index_dir, TARGET_INDEX_DIR, dirs_exist_ok=True)

    # --- B. Input Files 搬運 (🔥 關鍵修改區) ---
    source_docs_dir = DOWNLOAD_CACHE_DIR / "input_files"
    
    if source_docs_dir.exists():
        # 不管目標存不存在，都強制執行「合併/覆蓋」
        # 這樣可以把 Dataset 裡的 PDF 補進去，而不會因為資料夾已存在就跳過
        print(f"📦 [System] Force syncing input_files to {TARGET_DOCS_DIR}...")
        TARGET_DOCS_DIR.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source_docs_dir, TARGET_DOCS_DIR, dirs_exist_ok=True)
        print(f"✅ [System] Documents synced successfully!")
    else:
        print("⚠️ [Warning] input_files folder not found in dataset.")

    # 清理 Cache (建議保留這行註解，除錯時比較方便)
    # shutil.rmtree(DOWNLOAD_CACHE_DIR) 

except Exception as e:
    print(f"⚠️ [System] Setup failed: {e}")
    import traceback
    traceback.print_exc()

# ========= 4. 設定環境並啟動 =========
if str(FRONTEND_DIR) not in sys.path:
    sys.path.insert(0, str(FRONTEND_DIR))
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.chdir(FRONTEND_DIR)
print(f"🚀 [System] Launching App...")

with open("app.py", encoding="utf-8") as f:
    exec(f.read())