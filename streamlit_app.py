"""
UIC Policy Assistant - Streamlit Cloud Entry Point (Golden Version)
這支檔案會：
1. 自動從 HF Dataset 下載索引資料 (解決資料分離問題)
2. 設定正確的 Python 路徑
3. 使用 exec 啟動前端 (保證 Streamlit 互動正常)
"""

import sys
import os
from pathlib import Path

# ========= Step 1: 自動下載資料 (Cloud Native 策略) =========
# 設定 Dataset 來源與本地目標目錄
DATASET_REPO = "Ingee529/uic-policy-rag-data" # 確認這是您的 Dataset ID
ROOT_DIR = Path(__file__).parent.resolve()
LOCAL_DATA_DIR = ROOT_DIR / "backend" / "embeddings_output_GEMINI"

# 建立目錄
LOCAL_DATA_DIR.mkdir(parents=True, exist_ok=True)

# 嘗試下載 (本地如果已經有，snapshot_download 會自動跳過或用快取)
try:
    from huggingface_hub import snapshot_download
    print(f"📥 [System] Checking/Downloading dataset: {DATASET_REPO}")
    
    snapshot_download(
        repo_id=DATASET_REPO,
        repo_type="dataset",
        local_dir=str(LOCAL_DATA_DIR),
        local_dir_use_symlinks=False,
        # 如果 Dataset 是私有的，需要去 HF Settings 加入 HF_TOKEN 環境變數
        token=os.getenv("HF_TOKEN"), 
    )
    print(f"✅ [System] Dataset ready at: {LOCAL_DATA_DIR}")

except Exception as e:
    print(f"⚠️ [System] Dataset download warning: {e}")
    print("   (如果是在本地開發且已有資料，可忽略此訊息)")

# ========= Step 2: 環境路徑設定 =========
# 將 frontend 和 backend 加入 Python 搜尋路徑
frontend_dir = ROOT_DIR / "frontend"
backend_dir = ROOT_DIR / "backend"

if str(frontend_dir) not in sys.path:
    sys.path.insert(0, str(frontend_dir))
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

# ========= Step 3: 啟動前端應用 =========
# 切換工作目錄到 frontend，這樣 app.py 讀取 styles.css 會更容易
os.chdir(frontend_dir)

# 使用 exec 執行 app.py
# 這是 Streamlit 官方推薦的多檔案啟動方式，能確保每次 Rerun 都重新執行代碼
# 注意：我們已經在 frontend/app.py 裡修復了路徑讀取邏輯，所以這裡用 exec 是安全的
print(f"🚀 [System] Launching Streamlit App from: {frontend_dir / 'app.py'}")

with open("app.py", encoding="utf-8") as f:
    exec(f.read())