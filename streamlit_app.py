"""
UIC Policy Assistant - Streamlit Cloud Entry Point (The Bridge)
這支檔案負責：
1. 從 HF Dataset 下載資料 (Index + PDF)
2. 【關鍵】將下載的 PDF 搬運到 app.py 預期的 backend/input_files 位置
3. 啟動前端
"""

import sys
import os
import shutil
from pathlib import Path

# ========= 1. 設定路徑 =========
ROOT_DIR = Path(__file__).parent.resolve()
BACKEND_DIR = ROOT_DIR / "backend"
FRONTEND_DIR = ROOT_DIR / "frontend"

# 這是 app.py 預期找到 PDF 的地方 (本地有，但 GitHub/HF 上可能是空的)
TARGET_DOCS_DIR = BACKEND_DIR / "input_files"

# 這是 Dataset 下載下來的暫存位置
DATASET_REPO = "Ingee529/uic-policy-rag-data"
LOCAL_DATA_DIR = BACKEND_DIR / "embeddings_output_GEMINI"

# ========= 2. 自動下載資料 =========
try:
    from huggingface_hub import snapshot_download
    print(f"📥 [System] Checking/Downloading dataset: {DATASET_REPO}")
    
    # 下載 Dataset 到 LOCAL_DATA_DIR
    snapshot_download(
        repo_id=DATASET_REPO,
        repo_type="dataset",
        local_dir=str(LOCAL_DATA_DIR),
        local_dir_use_symlinks=False,
        token=os.getenv("HF_TOKEN"), 
    )
    print(f"✅ [System] Dataset ready at: {LOCAL_DATA_DIR}")

    # ========= 【關鍵修復】資料搬運工 (The Bridge) =========
    # 檢查下載下來的資料裡，有沒有 input_files 資料夾
    DOWNLOADED_DOCS_SOURCE = LOCAL_DATA_DIR / "input_files"
    
    if DOWNLOADED_DOCS_SOURCE.exists():
        # 如果目標目錄 (backend/input_files) 不存在，就從下載的資料複製過去
        if not TARGET_DOCS_DIR.exists():
            print(f"📦 [System] Moving input_files from Dataset to {TARGET_DOCS_DIR}...")
            shutil.copytree(DOWNLOADED_DOCS_SOURCE, TARGET_DOCS_DIR)
            print("✅ [System] Documents are ready for the app!")
        else:
            # 如果目標已經存在 (例如本地開發，或者 GitHub 有推部分檔案)，我們就不覆蓋，以免打架
            print(f"ℹ️ [System] Target docs dir {TARGET_DOCS_DIR} already exists. Skipping copy.")
    else:
        print(f"⚠️ [Warning] 'input_files' folder not found in dataset! Download buttons might fail.")

except Exception as e:
    print(f"⚠️ [System] Dataset download warning: {e}")
    # 本地開發如果沒有網路或不想下載，這行會讓程式繼續跑，不會崩潰

# ========= 3. 環境路徑設定 =========
if str(FRONTEND_DIR) not in sys.path:
    sys.path.insert(0, str(FRONTEND_DIR))
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# ========= 4. 啟動前端 =========
# 切換到 frontend 目錄 (讓 app.py 能順利讀到 styles.css)
os.chdir(FRONTEND_DIR)

print(f"🚀 [System] Launching Streamlit App from: {FRONTEND_DIR / 'app.py'}")

with open("app.py", encoding="utf-8") as f:
    exec(f.read())