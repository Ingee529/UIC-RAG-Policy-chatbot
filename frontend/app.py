"""
UIC Vice Chancellor's Office - Policy Assistant
A demo frontend for the MetaRAG system
(Hybrid Version: Compatible with both Localhost and Hugging Face Spaces)
"""
import streamlit as st
import json
import random
import re
from pathlib import Path
import sys
import base64
import os
import shutil

# ========= 1. 智慧路徑設定 (Smart Path Setup) =========
# 目標：準確找到 FRONTEND_DIR, BACKEND_DIR 和 ROOT_DIR

try:
    # 情況 A: 本地直接執行 (有 __file__)
    CURRENT_FILE = Path(__file__).resolve()
    FRONTEND_DIR = CURRENT_FILE.parent
except NameError:
    # 情況 B: 在 HF Space 被 exec() 執行 (無 __file__)
    # 假設當前工作目錄是在 frontend (因為 streamlit_app.py 做了 chdir)
    # 或者當前工作目錄是根目錄
    cwd = Path.cwd()
    if (cwd / "app.py").exists() and (cwd / "styles.css").exists():
         # 我們就在 frontend 目錄裡
        FRONTEND_DIR = cwd
    elif (cwd / "frontend" / "app.py").exists():
        # 我們在根目錄
        FRONTEND_DIR = cwd / "frontend"
    else:
        # 盲猜 (HF 標準路徑)
        FRONTEND_DIR = Path("/app/frontend")

# 尋找 ROOT_DIR (專案根目錄)
# 邏輯：FRONTEND_DIR 的上一層應該就是 ROOT_DIR
ROOT_DIR = FRONTEND_DIR.parent

# 定義 BACKEND_DIR
BACKEND_DIR = ROOT_DIR / "backend"

# 除錯訊息 (可以在終端機看到)
print(f"📂 [Path Debug] FRONTEND_DIR: {FRONTEND_DIR}")
print(f"📂 [Path Debug] BACKEND_DIR: {BACKEND_DIR}")
print(f"📂 [Path Debug] ROOT_DIR: {ROOT_DIR}")

# Add backend directory to Python path
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Try to import the RAG backend
USE_REAL_BACKEND = False


# ========= 小工具函式 =========
def get_base64_image(image_path: Path) -> str:
    """將圖片轉換為 base64 編碼（找不到檔案時回傳空字串）"""
    # 嘗試多個位置找圖片
    candidates = [
        image_path,
        FRONTEND_DIR / image_path.name,
        ROOT_DIR / image_path.name
    ]
    
    for path in candidates:
        if path.exists():
            try:
                with open(path, "rb") as img_file:
                    return base64.b64encode(img_file.read()).decode()
            except Exception:
                continue
    return ""


def setup_documents_directory() -> Path:
    """
    設置文檔目錄：
    本地開發時：嘗試從 backend/input_files 複製到 frontend/documents (方便下載)
    雲端時：若 Dataset 有掛載則複製，否則略過
    """
    documents_dir = FRONTEND_DIR / "documents"
    input_files_dir = BACKEND_DIR / "input_files"

    # 如果 documents_dir 不存在，建立它
    documents_dir.mkdir(exist_ok=True, parents=True)

    # 只有當來源目錄存在時才複製
    if input_files_dir.exists():
        # 為了避免每次啟動都大量複製 IO，可以檢查是否已經有檔案
        # 這裡簡單處理：只檢查 .txt，您也可以改成檢查 .pdf
        if not any(documents_dir.iterdir()): 
            print("📂 [Setup] Copying documents to frontend directory...")
            try:
                for file_path in input_files_dir.glob("*.*"): # 複製所有檔案
                     if file_path.is_file():
                        dest_path = documents_dir / file_path.name
                        if not dest_path.exists():
                            shutil.copy2(file_path, dest_path)
            except Exception as e:
                print(f"⚠️ [Setup] Copy documents failed: {e}")
    
    return documents_dir


def get_document_path(document_id=None, source_text: str = "") -> Path | None:
    """根據 document_id 或 source_text 嘗試對應到檔案"""
    
    # 搜尋順序：
    # 1. backend/input_files (原始位置 - 本地最準)
    # 2. frontend/documents (複製位置)
    search_dirs = [
        BACKEND_DIR / "input_files",
        FRONTEND_DIR / "documents"
    ]
    
    # 也許在子目錄裡 (例如 '1 Fiscal Environment')
    # 我們先收集所有可能的 PDF/TXT 檔案路徑
    all_candidates = []
    for d in search_dirs:
        if d.exists():
            # 遞迴搜尋所有檔案
            all_candidates.extend(list(d.rglob("*.pdf")))
            all_candidates.extend(list(d.rglob("*.txt")))

    if not all_candidates:
        return None

    target_file = None

    # A. 從 source_text 中提取文檔標題 (RAG 回傳的 pattern)
    if source_text:
        match = re.search(r'Document Title:\s*([^\n]+)', source_text)
        if match:
            doc_title = match.group(1).strip()
            # 提取編號部分（如 1.6, 2.1, 4.3.2）
            number_match = re.search(r'(\d+(?:\.\d+)+)', doc_title)
            
            if number_match:
                doc_number = number_match.group(1) # e.g. "1.6"
                
                # 策略 1: 檔名包含 "1.6 " (注意空格) 或 "1.6_"
                for f in all_candidates:
                    if f.name.startswith(doc_number + " ") or f.name.startswith(doc_number + "_"):
                        return f
                    # 有些檔名可能是 "1.6_Exceptions..."
                    if doc_number in f.name:
                         target_file = f # 先暫存，繼續找更精確的
            
            # 如果沒有編號，嘗試用標題文字模糊比對
            clean_title = doc_title.split("–")[0].strip()[:20] # 取前20字
            for f in all_candidates:
                if clean_title.lower() in f.name.lower():
                    return f

    # B. document_id 直接對應檔名 (Demo 模式)
    if document_id:
        doc_id_clean = str(document_id).lower().replace(" ", "_").replace(".", "_")
        for f in all_candidates:
            if doc_id_clean in f.stem.lower():
                return f

    return target_file


def create_download_button(file_path: Path | None, button_text: str = "📥 Download Document") -> None:
    """建立下載按鈕"""
    if file_path and file_path.exists():
        try:
            with open(file_path, "rb") as f:
                file_data = f.read()
            
            suffix = file_path.suffix.lower()
            if suffix == ".pdf":
                mime_type = "application/pdf"
            elif suffix == ".docx":
                 mime_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            else:
                mime_type = "text/plain"
                
            st.download_button(
                label=button_text,
                data=file_data,
                file_name=file_path.name,
                mime=mime_type,
            )
        except Exception as e:
            # 本地開發時顯示錯誤，線上環境則隱藏細節
            st.caption(f"⚠️ File unavailable: {file_path.name}")
            print(f"Download Error: {e}")
    else:
        # 檔案找不到
        st.caption("📄 Document file not available")


def load_custom_css():
    """載入 styles.css 檔案 (雙棲路徑版)"""
    css_content = None
    css_path = None
    
    # 定義搜尋路徑優先級
    possible_paths = [
        FRONTEND_DIR / "styles.css",       # 1. frontend 目錄下 (標準位置)
        ROOT_DIR / "styles.css",           # 2. 根目錄下 (備用)
        Path("styles.css"),                # 3. 當前工作目錄 (Relative)
        Path("frontend/styles.css")        # 4. 相對 frontend (Relative)
    ]
    
    for path in possible_paths:
        try:
            if path.exists() and path.is_file():
                with open(path, "r", encoding="utf-8") as f:
                    css_content = f.read()
                css_path = path
                print(f"✅ Loaded CSS from: {path}")
                break
        except Exception:
            continue
            
    if css_content:
        st.markdown(f"<style>{css_content}</style>", unsafe_allow_html=True)
    else:
        st.warning("⚠️ Warning: styles.css not found. The app will look unstyled.")
        print("❌ CSS Load Failed: Checked all paths but found nothing.")


def get_backend_safe():
    """安全地載入 RAG backend"""
    if "backend" not in st.session_state:
        st.session_state.backend = None
        st.session_state.backend_loaded = False
        st.session_state.backend_error = None
        st.session_state.backend_loading = False

    if st.session_state.backend_loaded and st.session_state.backend is not None:
        return st.session_state.backend

    if st.session_state.backend_error or st.session_state.backend_loading:
        return None

    if not st.session_state.backend_loaded:
        st.session_state.backend_loading = True
        try:
            with st.spinner("Loading RAG backend..."):
                from rag_backend import get_backend # 假設 rag_backend 在 path 裡

                st.session_state.backend = get_backend()
                st.session_state.backend_loaded = True
                st.session_state.backend_loading = False
                return st.session_state.backend
        except Exception as e:
            st.session_state.backend_error = str(e)
            st.session_state.backend_loading = False
            st.error(f"❌ Failed to load RAG backend: {e}")
            return None

    return st.session_state.backend


# ========= Streamlit 頁面基本設定 =========
st.set_page_config(
    page_title="UIC Policy Assistant Prototype",
    page_icon="🏛️",
    layout="wide",
)

load_custom_css()
setup_documents_directory()

# ========= Demo 用的 sample 文件 & QA =========
SAMPLE_DOCS = {
    "1.1": {
        "title": "System Annual Financial Report",
        "content": "The University of Illinois System must publish an annual financial report. "
        "The report contains basic financial statements, supplementary schedules, and the independent auditor's "
        "opinion of these statements issued by the Special Assistant Auditors for the State Auditor General.",
    },
    "1.2": {
        "title": "Conducting, Recording and Reporting Financial Activity",
        "content": "The University of Illinois System follows generally accepted accounting principles and complies "
        "with reporting requirements for conducting, recording, and reporting financial activities.",
    },
    "1.3": {
        "title": "Unit Financial Health",
        "content": "Each university unit must maintain financial health and report regularly on their fiscal status "
        "to ensure proper stewardship of resources.",
    },
    "1.4": {
        "title": "University and System Offices Deficit Reporting",
        "content": "Universities and System Offices must report deficits in accordance with established procedures "
        "to maintain fiscal responsibility and transparency.",
    },
    "1.5": {
        "title": "Conducting Business Outside the State of Illinois",
        "content": "The University of Illinois System has specific policies governing business activities conducted "
        "outside the State of Illinois to ensure compliance with regulations.",
    },
}

SAMPLE_QA = {
    "What happens if a university or system office has a financial deficit?": {
        "answer": """If a unit or system office records a deficit, the Budget Office or Comptroller may request a Deficit Remedial Business Plan.
This plan explains how the deficit will be resolved and must be reviewed by the Vice President/Chief Financial Officer & Comptroller.
Each university (UIC, UIS, Urbana-Champaign) follows its own deficit-elimination guidelines and forms.
""",
        "sources": [
            "Category: Fiscal Environment\n"
            "Document Title: 1.4 University and System Offices Deficit Reporting – Business & Finance\n"
            "Pages: 1 (Procedure section)"
        ],
    },
    "Who has the authority to grant exceptions to university financial policies?": {
        "answer": (
            "Only the Vice President, Chief Financial Officer (CFO) & Comptroller has authority to grant exceptions "
            "to business and financial policies, procedures, and processes. Such exceptions are allowed only when "
            "special circumstances justify them and when they serve the best interest of the University of Illinois "
            "System and the State of Illinois. The Comptroller will notify relevant units whenever changes or "
            "exceptions are approved."
        ),
        "sources": [
            "Category: Fiscal Environment\n"
            "Document Title: 1.6 Exceptions to Business and Financial Policies, Procedures, and Processes – Business & Finance\n"
            "Page: 1 (Policy Statement and Procedure sections)"
        ],
    },
}

# ========= Session state 初始化 =========
if "messages" not in st.session_state:
    st.session_state.messages = []
if "show_welcome" not in st.session_state:
    st.session_state.show_welcome = True

# ========= Header =========
col1, col2 = st.columns([1, 5])
with col1:
    uic_logo_path = FRONTEND_DIR / "uic.png"
    if uic_logo_path.exists():
        st.image(str(uic_logo_path), width=150)
with col2:
    st.title("UIC Policy Assistant Prototype")
    st.caption("AI-powered assistant for University of Illinois Chicago Vice Chancellor's Office policies")

# ========= Sidebar =========
with st.sidebar:
    st.markdown(
        '<div style="margin-top: -30px; margin-bottom: 5px;">'
        '<div style="font-size: 1.05em; font-weight: bold; color: #001E62; margin: 0; padding: 0;">About</div>'
        "</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div style="font-size: 1em; margin-bottom: 8px;">UIC Policy Assistant </br> (Demo Version)</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div style="font-size: 1.05em; font-weight: bold; color: #001E62; margin-top: 5px; margin-bottom: 3px;">'
        "🎓 Faculty Advisor</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div style="font-size: 1em; margin-bottom: 6px;">'
        '<a href="https://business.uic.edu/profiles/sarayloo-fatemeh/">Fatemeh Sarayloo, Ph.D.</a>'
        "</div>",
        unsafe_allow_html=True,
    )

    # LinkedIn 圖片處理
    linkedin_path = FRONTEND_DIR / "linkedin.jpeg"
    linkedin_b64 = get_base64_image(linkedin_path)

    # Teaching Assistant
    if linkedin_b64:
        st.markdown(
            f"""
        <div style="display: flex; align-items: center; gap: 6px; margin-top: 5px; margin-bottom: 3px;">
            <div style="font-size: 1.05em; font-weight: bold; color: #001E62;">🧑‍🏫 Teaching Assistant</div>
            <img src="data:image/jpeg;base64,{linkedin_b64}" width="20" style="margin-bottom: 2px;">
        </div>
        """,
            unsafe_allow_html=True,
        )
    st.markdown(
        '<div style="font-size: 1em; margin-bottom: 6px;"><a href="https://www.linkedin.com/in/mokshitsurana/">'
        "Mokshit Surana</a></div>",
        unsafe_allow_html=True,
    )

    # Team Members
    if linkedin_b64:
        st.markdown(
            f"""
        <div style="display: flex; align-items: center; gap: 6px; margin-top: 5px; margin-bottom: 3px;">
            <div style="font-size: 1.05em; font-weight: bold; color: #001E62;">👥 Team Members</div>
            <img src="data:image/jpeg;base64,{linkedin_b64}" width="20" style="margin-bottom: 2px;">
        </div>
        """,
            unsafe_allow_html=True,
        )
    st.markdown(
        """
    <div style="font-size: 1em; line-height: 1.3; margin-bottom: 8px;">
    <a href="https://www.linkedin.com/in/haswatha-sridharan">Haswatha Sridharan</a><br>
    <a href="https://linkedin.com/in/vamshi-krishna-1490b4187">Vamshi Krishna Aileni</a><br>
    <a href="https://www.linkedin.com/in/yonce-yang-93a731314/">Hsin-Jui Yang</a><br>
    <a href="https://www.linkedin.com/in/honglin-liu-8850b038b">Honglin Liu</a>
    </div>
    """,
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div style="margin-top: 5px; margin-bottom: 5px;">'
        '<div style="font-size: 1.05em; font-weight: bold; color: #001E62; margin: 0;">📚 Available Policies</div>'
        "</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        """
    <div style="font-size: 1em; line-height: 1.4; margin-bottom: 8px;">
    <b>Fiscal Environment</b><br>
    <b>Custodial Funds</b><br>
    <b>Budget</b><br>
    <b>Payroll</b><br>
    <b>Receivables</b><br>
    </div>
    """,
        unsafe_allow_html=True,
    )

    st.markdown('<div style="margin: 5px 0;"></div>', unsafe_allow_html=True)

    if st.button("🔄 Clear Conversation"):
        st.session_state.messages = []
        st.session_state.show_welcome = True
        st.rerun()

    st.markdown('<div style="margin: 5px 0;"></div>', unsafe_allow_html=True)

    # 後端狀態
    if st.session_state.get("backend_loaded") and st.session_state.get("backend") is not None:
        st.markdown(
            '<div style="font-size: 1em; margin-bottom: 5px;">✅ <strong>Live Mode</strong>: Ready</div>',
            unsafe_allow_html=True,
        )
        USE_REAL_BACKEND = True
    elif st.session_state.get("backend_error"):
        st.markdown(
            '<div style="font-size: 1em; margin-bottom: 3px;">⚠️ <strong>Demo Mode</strong></div>',
            unsafe_allow_html=True,
        )
        err = st.session_state.backend_error[:80]
        st.markdown(
            f'<div style="font-size: 0.9em; color: #d9534f; margin-bottom: 5px;">Error: {err}...</div>',
            unsafe_allow_html=True,
        )
        if st.button("🔄 Try Again"):
            st.session_state.backend_loaded = False
            st.session_state.backend_error = None
            st.session_state.backend_loading = False
            st.rerun()
        USE_REAL_BACKEND = False
    elif st.session_state.get("backend_loading"):
        st.markdown(
            '<div style="font-size: 1em; margin-bottom: 5px;">🔄 <strong>Loading</strong>...</div>',
            unsafe_allow_html=True,
        )
        if st.button("❌ Cancel"):
            st.session_state.backend_loading = False
            st.session_state.backend_error = "User canceled loading"
            st.rerun()
        USE_REAL_BACKEND = False
    else:
        st.markdown(
            '<div style="font-size: 1em; margin-bottom: 5px;">🔄 <strong>Ready</strong></div>',
            unsafe_allow_html=True,
        )
        if st.button("🔥 Start Assistant"):
            _ = get_backend_safe()
            st.rerun()
        USE_REAL_BACKEND = False


# ========= Welcome + Example questions =========
if st.session_state.show_welcome and len(st.session_state.messages) == 0:
    st.markdown("### Welcome! 👋")
    st.markdown("Ask me anything about UIC Vice Chancellor's Office policies. Here are some examples:")

    if 'SAMPLE_QA' in globals():
        example_questions = list(SAMPLE_QA.keys())
        cols = st.columns(1)
        for i, question in enumerate(example_questions[:3]):
            if st.button(f"💡 {question}", key=f"example_{i}"):
                st.session_state.show_welcome = False
                st.session_state.messages.append({"role": "user", "content": question})
                qa = SAMPLE_QA[question]
                st.session_state.messages.append(
                    {"role": "assistant", "content": qa["answer"], "sources": qa["sources"]}
                )
                st.rerun()
    st.divider()


# ========= 來源顯示與下載 (Updated) =========
def render_with_source_popovers(content: str, sources):
    """將 citation 轉成 [1] 並在 expander 中顯示來源 & 下載"""
    if not sources:
        st.markdown(content)
        return

    # 建立 source_map
    if isinstance(sources[0], dict):  # RAG 模式
        source_map = {}
        
        for i, source in enumerate(sources[:3], 1):
            category = source.get("primary_category", "Document")
            doc_path_rel = source.get("doc") or ""
            doc_name = source.get("doc_name", doc_path_rel or f"Document {i}")

            # 【關鍵修改】: 使用 get_document_path 統一尋找檔案
            # 它會自動去 backend/input_files 和 frontend/documents 找
            resolved_file = get_document_path(source_text=f"Document Title: {doc_name}")
            
            # 如果還是沒找到，且 doc_path_rel 是相對路徑，試試看直接拼湊
            if not resolved_file and doc_path_rel:
                candidate = BACKEND_DIR / "input_files" / doc_path_rel
                if candidate.exists():
                    resolved_file = candidate

            source_map[f"source_{i}"] = {
                "name": f"{category} - {doc_name}",
                "text": source.get("text", ""),
                "summary": source.get("summary", ""),
                "type": source.get("content_type", "N/A"),
                "page": source.get("page"),
                "score": source.get("score"),
                "file_path": str(resolved_file) if resolved_file else None,
            }
    else:  # Demo 模式 (來源是字串或 ID)
        source_map = {}
        for i, source_id in enumerate(sources, 1):
            if 'SAMPLE_DOCS' in globals() and source_id in SAMPLE_DOCS:
                doc = SAMPLE_DOCS[source_id]
                source_map[f"source_{i}"] = {
                    "name": f"Policy {source_id}: {doc['title']}",
                    "text": doc["content"],
                    "summary": "",
                    "type": "Policy",
                }
            else:
                source_map[f"source_{i}"] = {
                    "name": f"Source {i}",
                    "text": str(source_id),
                    "summary": "",
                    "type": "Policy Document",
                }

    # 找 citation 標記
    pattern_new = r"\[(\d+)\]"
    pattern_old = r"【(source_\d+)】"
    matches_new = list(re.finditer(pattern_new, content))
    matches_old = list(re.finditer(pattern_old, content))

    if matches_new:
        citation_style = "new"
        matches = matches_new
    elif matches_old:
        citation_style = "old"
        matches = matches_old
    else:
        # 沒有 citation，直接顯示內容
        st.markdown(content)
        matches = []
        citation_style = "none"

    # 替換內文引用標記
    if matches:
        result_text = content
        for match in reversed(matches):
            citation_num = match.group(1)
            if citation_style == "new":
                source_key = f"source_{citation_num}"
            else:
                source_key = citation_num

            if source_key in source_map:
                if citation_style == "new":
                    badge = f"<sup>[{citation_num}]</sup>"
                else:
                    badge = f'<sup><small>📄 {source_map[source_key]["name"]}</small></sup>'
                result_text = result_text[: match.start()] + badge + result_text[match.end() :]
        
        st.markdown(result_text, unsafe_allow_html=True)

    # 顯示來源摺疊區塊 & 下載按鈕
    if source_map:
        with st.expander("📄 View Sources & Download Documents"):
            for i, (source_key, source_info) in enumerate(source_map.items(), 1):
                st.markdown(f"**[{i}] {source_info.get('name', f'Source {i}')}**")
                
                # 顯示摘要或原文片段
                snippet = (source_info.get("text") or "").strip()
                if snippet:
                    lines = [l.strip() for l in snippet.split("\n") if l.strip()]
                    is_heading = len(snippet) < 200 or len(lines) < 3
                    display_snippet = snippet[:400] + ("..." if len(snippet) > 400 else "")
                    st.markdown("**Original Snippet:**")
                    st.markdown(f"_{display_snippet}_")
                    if is_heading:
                        st.caption(
                            "⚠️ This snippet appears to contain only headings/titles. "
                            "Please download the full document for complete content."
                        )

                # 顯示 Metadata
                page = source_info.get("page")
                score = source_info.get("score")
                meta_bits = []
                if page is not None:
                    meta_bits.append(f"📄 Page: {page}")
                if score is not None:
                    try:
                        meta_bits.append(f"⭐ Score: {float(score):.3f}")
                    except Exception:
                        meta_bits.append(f"⭐ Score: {score}")
                if meta_bits:
                    st.caption(" | ".join(meta_bits))

                # 建立下載按鈕
                file_path_str = source_info.get("file_path")
                doc_path = Path(file_path_str) if file_path_str else None
                
                # 若上方沒找到路徑，最後再試一次 get_document_path
                if not doc_path or not doc_path.exists():
                    doc_path = get_document_path(None, source_info.get("text", ""))

                create_download_button(doc_path, f"📥 Download Source {i}")
                st.divider()


# ========= 顯示歷史訊息 =========
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        if message["role"] == "assistant" and message.get("sources"):
            render_with_source_popovers(message["content"], message["sources"])
        else:
            st.markdown(message["content"])

# ========= Chat input =========
if prompt := st.chat_input("Ask a question about UIC policies..."):
    st.session_state.show_welcome = False
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Searching policy documents..."):
            backend = get_backend_safe()
            if backend is not None:
                try:
                    result = backend.generate_answer(prompt, top_k=5)
                    response = result["answer"]
                    sources = result["sources"]
                    print(f"[DEBUG] Using RAG backend, got {len(sources)} sources")
                except Exception as e:
                    st.error(f"❌ Error querying backend: {e}")
                    import traceback
                    st.error(traceback.format_exc())
                    response = "Sorry, there was an error processing your query."
                    sources = []
            else:
                # Demo Mode Fallback
                if 'SAMPLE_QA' in globals() and prompt in SAMPLE_QA:
                    qa = SAMPLE_QA[prompt]
                    response = qa["answer"]
                    sources = qa["sources"]
                else:
                    response = (
                        f'I found some information that might be relevant to your question about "{prompt}".\n\n'
                        "Based on the UIC Vice Chancellor's Office policies, the University of Illinois System "
                        "follows established procedures and compliance requirements for all business and financial "
                        "activities.\n\n"
                        "For specific details about your question, I recommend reviewing the relevant policy "
                        "documents or contacting the Vice Chancellor's Office directly.\n\n"
                        "**Note:** This is a demo system. For official policy guidance, please consult the official "
                        "UIC policy documentation."
                    )
                    sources = []
                    if 'SAMPLE_DOCS' in globals():
                         sources = random.sample(list(SAMPLE_DOCS.keys()), min(2, len(SAMPLE_DOCS)))

        if sources:
            render_with_source_popovers(response, sources)
        else:
            st.markdown(response)

    st.session_state.messages.append(
        {"role": "assistant", "content": response, "sources": sources}
    )

# ========= Footer =========
st.divider()
st.caption("🤖 Powered by MetaRAG | University of Illinois Chicago | IDS 560 Analytics Strategy and Practice")