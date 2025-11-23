"""
UIC Vice Chancellor's Office - Policy Assistant
A demo frontend for the MetaRAG system
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

# Add backend directory to Python path
backend_dir = Path(__file__).parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

# Try to import the RAG backend
USE_REAL_BACKEND = False


def get_base64_image(image_path):
    """將圖片轉換為 base64 編碼"""
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode()


def setup_documents_directory():
    """設置文檔目錄，從 backend/input_files 複製文檔到 frontend/documents"""
    frontend_dir = Path(__file__).parent
    backend_dir = frontend_dir.parent / "backend"
    documents_dir = frontend_dir / "documents"
    input_files_dir = backend_dir / "input_files"
    
    # 創建 documents 目錄
    documents_dir.mkdir(exist_ok=True)
    
    # 如果 input_files 存在，複製文檔
    if input_files_dir.exists():
        for file_path in input_files_dir.glob("*.txt"):
            dest_path = documents_dir / file_path.name
            if not dest_path.exists():
                shutil.copy2(file_path, dest_path)
    
    return documents_dir


def get_document_path(document_id, source_text=""):
    """根據 document_id 或 source_text 獲取文檔文件路徑"""
    documents_dir = Path(__file__).parent / "documents"
    
    if not documents_dir.exists():
        return None
    
    # 從 source_text 中提取文檔標題
    if source_text:
        # 嘗試從 "Document Title: X.X ..." 中提取
        match = re.search(r'Document Title:\s*([^\n]+)', source_text)
        if match:
            doc_title = match.group(1).strip()
            
            # 提取編號部分（如 1.6, 2.1, 4.3.2 等）
            number_match = re.search(r'(\d+(?:\.\d+)+)', doc_title)
            if number_match:
                doc_number = number_match.group(1)
                # 將編號轉換為文件名格式（如 1.6 -> 1_6, 4.3.2 -> 4_3_2）
                file_number = doc_number.replace('.', '_')
                
                # 查找匹配的文件
                for file_path in documents_dir.glob("*.txt"):
                    stem = file_path.stem
                    # 檢查文件名是否包含這個編號
                    if file_number in stem or stem.startswith(file_number.split('_')[0] + '_'):
                        return file_path
                
                # 如果沒找到，嘗試部分匹配（如 1.6 匹配 1_6 開頭的文件）
                for file_path in documents_dir.glob("*.txt"):
                    stem = file_path.stem
                    # 檢查是否以編號的第一部分開頭
                    first_part = file_number.split('_')[0]
                    if stem.startswith(first_part + '_'):
                        return file_path
    
    # 如果 document_id 是文件名的一部分
    if document_id:
        # 清理 document_id
        doc_id_clean = str(document_id).lower().replace(' ', '_').replace('.', '_')
        # 嘗試直接匹配
        for file_path in documents_dir.glob("*.txt"):
            stem = file_path.stem.lower()
            if doc_id_clean in stem or stem in doc_id_clean:
                return file_path
    
    return None


def create_download_button(file_path, button_text="📥 Download Document"):
    """創建下載按鈕"""
    if file_path and file_path.exists():
        with open(file_path, "rb") as f:
            file_data = f.read()
            # Choose MIME type based on extension (PDF vs text)
            suffix = file_path.suffix.lower()
            if suffix == ".pdf":
                mime_type = "application/pdf"
            else:
                mime_type = "text/plain"
            st.download_button(
                label=button_text,
                data=file_data,
                file_name=file_path.name,
                mime=mime_type
            )
    else:
        st.info("📄 Document file not available for download")


def load_custom_css():
    """載入 styles.css 檔案"""
    try:
        # 使用絕對路徑確保能找到 CSS 文件
        css_path = Path(__file__).parent / "styles.css"
        with open(css_path, "r", encoding="utf-8") as f:
            css_content = f.read()
            st.markdown(f"<style>{css_content}</style>", unsafe_allow_html=True)
            
        # 僅載入 CSS，移除 JS 注入以避免閃爍與快取問題
        
    except FileNotFoundError:
        st.error(f"❌ 樣式檔 'styles.css' 未找到。路徑: {css_path}")
    except Exception as e:
        st.error(f"❌ 載入樣式檔時發生錯誤: {e}")


def get_backend_safe():
    """安全地獲取後端，如果失敗則返回 None"""
    # 使用 session_state 來存儲 backend，這樣在 Streamlit 重新運行時不會丟失
    if 'backend' not in st.session_state:
        st.session_state.backend = None
        st.session_state.backend_loaded = False
        st.session_state.backend_error = None
        st.session_state.backend_loading = False

    # 如果已經載入成功，直接返回
    if st.session_state.backend_loaded and st.session_state.backend is not None:
        return st.session_state.backend

    # 如果之前載入失敗，返回 None
    if st.session_state.backend_error:
        return None

    # 如果正在載入中，返回 None
    if st.session_state.backend_loading:
        return None

    # 嘗試載入後端
    if not st.session_state.backend_loaded:
        st.session_state.backend_loading = True
        try:
            with st.spinner("Loading RAG backend..."):
                from rag_backend import get_backend
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

# Page configuration
st.set_page_config(
    page_title="UIC Policy Assistant Prototype",
    page_icon="🏛️",
    layout="wide"
)

load_custom_css()

# Setup documents directory
setup_documents_directory()

# Sample documents (excerpts from actual policy files)
SAMPLE_DOCS = {
    "1.1": {
        "title": "System Annual Financial Report",
        "content": "The University of Illinois System must publish an annual financial report. The report contains basic financial statements, supplementary schedules, and the independent auditor's opinion of these statements issued by the Special Assistant Auditors for the State Auditor General."
    },
    "1.2": {
        "title": "Conducting, Recording and Reporting Financial Activity",
        "content": "The University of Illinois System follows generally accepted accounting principles and complies with reporting requirements for conducting, recording, and reporting financial activities."
    },
    "1.3": {
        "title": "Unit Financial Health",
        "content": "Each university unit must maintain financial health and report regularly on their fiscal status to ensure proper stewardship of resources."
    },
    "1.4": {
        "title": "University and System Offices Deficit Reporting",
        "content": "Universities and System Offices must report deficits in accordance with established procedures to maintain fiscal responsibility and transparency."
    },
    "1.5": {
        "title": "Conducting Business Outside the State of Illinois",
        "content": "The University of Illinois System has specific policies governing business activities conducted outside the State of Illinois to ensure compliance with regulations."
    }
}

# Sample Q&A pairs
SAMPLE_QA = {
    "What happens if a university or system office has a financial deficit?": {
        "answer": """If a unit or system office records a deficit, the Budget Office or Comptroller may request a Deficit Remedial Business Plan.
 This plan explains how the deficit will be resolved and must be reviewed by the Vice President/Chief Financial Officer & Comptroller.
 Each university (UIC, UIS, Urbana-Champaign) follows its own deficit-elimination guidelines and forms.
""",
        "sources": ["Category: Fiscal Environment\nDocument Title: 1.4 University and System Offices Deficit Reporting – Business & Finance\nPages: 1 (Procedure section)"]
    },
    "Who has the authority to grant exceptions to university financial policies?": {
        "answer": "Only the Vice President, Chief Financial Officer (CFO) & Comptroller has authority to grant exceptions to business and financial policies, procedures, and processes. Such exceptions are allowed only when special circumstances justify them and when they serve the best interest of the University of Illinois System and the State of Illinois. The Comptroller will notify relevant units whenever changes or exceptions are approved.",
        "sources": ["Category: Fiscal Environment\nDocument Title: 1.6 Exceptions to Business and Financial Policies, Procedures, and Processes – Business & Finance\nPage: 1 (Policy Statement and Procedure sections)"]
    }
}

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []

if "show_welcome" not in st.session_state:
    st.session_state.show_welcome = True

# Header
col1, col2 = st.columns([1, 5])
with col1:
    # Use absolute path from this file
    uic_logo_path = Path(__file__).parent / "uic.png"
    if uic_logo_path.exists():
        st.image(str(uic_logo_path), width=150)
with col2:
    st.title("UIC Policy Assistant Prototype")
    st.caption("AI-powered assistant for University of Illinois Chicago Vice Chancellor's Office policies")

# Sidebar
with st.sidebar:
    st.markdown('<div style="margin-top: -30px; margin-bottom: 5px;"><div style="font-size: 1.05em; font-weight: bold; color: #001E62; margin: 0; padding: 0;">About</div></div>', unsafe_allow_html=True)
    st.markdown('<div style="font-size: 1em; margin-bottom: 8px;">UIC Policy Assistant </br> (Demo Version)</div>', unsafe_allow_html=True)
    
    st.markdown('<div style="font-size: 1.05em; font-weight: bold; color: #001E62; margin-top: 5px; margin-bottom: 3px;">🎓 Faculty Advisor</div>', unsafe_allow_html=True)
    st.markdown('<div style="font-size: 1em; margin-bottom: 6px;"><a href="https://business.uic.edu/profiles/sarayloo-fatemeh/">Fatemeh Sarayloo, Ph.D.</a></div>', unsafe_allow_html=True)
    
    # Teaching Assistant with LinkedIn icon
    linkedin_path = Path(__file__).parent / "linkedin.jpeg"
    st.markdown(f"""
    <div style="display: flex; align-items: center; gap: 6px; margin-top: 5px; margin-bottom: 3px;">
        <div style="font-size: 1.05em; font-weight: bold; color: #001E62;">🧑‍🏫 Teaching Assistant</div>
        <img src="data:image/jpeg;base64,{get_base64_image(linkedin_path)}" width="20" style="margin-bottom: 2px;">
    </div>
    """, unsafe_allow_html=True)
    st.markdown('<div style="font-size: 1em; margin-bottom: 6px;"><a href="https://www.linkedin.com/in/mokshitsurana/">Mokshit Surana</a></div>', unsafe_allow_html=True)
    
    # Team Members with LinkedIn icon
    st.markdown(f"""
    <div style="display: flex; align-items: center; gap: 6px; margin-top: 5px; margin-bottom: 3px;">
        <div style="font-size: 1.05em; font-weight: bold; color: #001E62;">👥 Team Members</div>
        <img src="data:image/jpeg;base64,{get_base64_image(linkedin_path)}" width="20" style="margin-bottom: 2px;">
    </div>
    """, unsafe_allow_html=True)
    st.markdown("""
    <div style="font-size: 1em; line-height: 1.3; margin-bottom: 8px;">
    <a href="https://www.linkedin.com/in/haswatha-sridharan">Haswatha Sridharan</a><br>
    <a href="https://linkedin.com/in/vamshi-krishna-1490b4187">Vamshi Krishna Aileni</a><br>
    <a href="https://www.linkedin.com/in/yonce-yang-93a731314/">Hsin-Jui Yang</a><br>
    <a href="https://www.linkedin.com/in/honglin-liu-8850b038b">Honglin Liu</a>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div style="margin-top: 5px; margin-bottom: 5px;"><div style="font-size: 1.05em; font-weight: bold; color: #001E62; margin: 0;">📚 Available Policies</div></div>', unsafe_allow_html=True)

    # Create a scrollable container for policies
    st.markdown("""
    <div style="font-size: 1em; line-height: 1.4; margin-bottom: 8px;">
    <b>Fiscal Environment</b><br>
    <b>Custodial Funds</b><br>
    <b>Budget</b><br>
    <b>Payroll</b><br>
    <b>Receivables</b><br>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div style="margin: 5px 0;"></div>', unsafe_allow_html=True)

    if st.button("🔄 Clear Conversation"):
        st.session_state.messages = []
        st.session_state.show_welcome = True
        st.rerun()

    st.markdown('<div style="margin: 5px 0;"></div>', unsafe_allow_html=True)
    # 檢查後端狀態（不阻塞界面載入）
    if 'backend_loaded' in st.session_state and st.session_state.backend_loaded:
        st.markdown('<div style="font-size: 1em; margin-bottom: 5px;">✅ <strong>Live Mode</strong>: Ready</div>', unsafe_allow_html=True)
        USE_REAL_BACKEND = True
    elif 'backend_error' in st.session_state and st.session_state.backend_error:
        st.markdown('<div style="font-size: 1em; margin-bottom: 3px;">⚠️ <strong>Demo Mode</strong></div>', unsafe_allow_html=True)
        st.markdown(f'<div style="font-size: 0.9em; color: #d9534f; margin-bottom: 5px;">Error: {st.session_state.backend_error[:30]}...</div>', unsafe_allow_html=True)
        if st.button("🔄 Try Again"):
            st.session_state.backend_loaded = False
            st.session_state.backend_error = None
            st.session_state.backend_loading = False
            st.rerun()
        USE_REAL_BACKEND = False
    elif 'backend_loading' in st.session_state and st.session_state.backend_loading:
        st.markdown('<div style="font-size: 1em; margin-bottom: 5px;">🔄 <strong>Loading</strong>...</div>', unsafe_allow_html=True)
        if st.button("❌ Cancel"):
            st.session_state.backend_loading = False
            st.session_state.backend_error = "User canceled loading"
            st.rerun()
        USE_REAL_BACKEND = False
    else:
        st.markdown('<div style="font-size: 1em; margin-bottom: 5px;">🔄 <strong>Ready</strong></div>', unsafe_allow_html=True)
        if st.button("🔥 Start Assistant"):
            backend = get_backend_safe()
            st.rerun()
        USE_REAL_BACKEND = False

# Welcome message and example questions
if st.session_state.show_welcome and len(st.session_state.messages) == 0:
    st.markdown("### Welcome! 👋")
    st.markdown("Ask me anything about UIC Vice Chancellor's Office policies. Here are some examples:")

    # Display example questions as clickable pills
    example_questions = list(SAMPLE_QA.keys())

    cols = st.columns(1)
    for i, question in enumerate(example_questions[:3]):
        if st.button(f"💡 {question}", key=f"example_{i}"):
            st.session_state.show_welcome = False
            # Add user message
            st.session_state.messages.append({"role": "user", "content": question})

            # Generate response for the example question
            qa = SAMPLE_QA[question]
            st.session_state.messages.append({
                "role": "assistant",
                "content": qa["answer"],
                "sources": qa["sources"]
            })
            st.rerun()

    st.divider()

# Helper function to replace source citations with popovers
def render_with_source_popovers(content, sources):
    """Replace 【source_X】markers with clickable popovers"""
    if not sources:
        return content

    # Check if sources is a list of dicts (RAG mode)
    if isinstance(sources[0], dict):
        # Create source mapping
        source_map = {}
        # Use absolute paths to avoid cwd issues
        backend_dir = (Path(__file__).resolve().parent.parent / "backend").resolve()
        input_files_dir = (backend_dir / "input_files").resolve()

        for i, source in enumerate(sources[:3], 1):
            category = source.get('primary_category', 'Document')
            # MetaRAG uses 'doc' / 'doc_name' for the original file path/name
            doc_path_rel = source.get('doc') or ""
            doc_name = source.get('doc_name', doc_path_rel if doc_path_rel else f"Document {i}")

            # Try to resolve the actual file path under backend/input_files
            resolved_file = None
            candidate = None
            matches = []
            if doc_path_rel:
                # 1) First try the exact relative path from metadata (e.g., "1 Fiscal Environment/1.4 ....pdf")
                candidate = input_files_dir / doc_path_rel
                if candidate.exists():
                    resolved_file = candidate
                else:
                    # 2) Try matching just by file name anywhere under input_files
                    filename = Path(doc_path_rel).name
                    matches = list(input_files_dir.rglob(filename))
                    if matches:
                        resolved_file = matches[0]
                    else:
                        # 3) Last‑resort fuzzy match: look for PDFs whose name contains the first part of doc_name
                        stem_hint = Path(doc_name).stem[:20]  # use first ~20 chars as hint
                        for pdf_path in input_files_dir.rglob("*.pdf"):
                            if stem_hint and stem_hint in pdf_path.stem:
                                resolved_file = pdf_path
                                break

            source_map[f'source_{i}'] = {
                'name': f"{category} - {doc_name}",
                'text': source.get('text', ''),
                'summary': source.get('summary', ''),
                'type': source.get('content_type', 'N/A'),
                'page': source.get('page'),
                'score': source.get('score'),
                # Save resolved backend file path (if any) for download
                'file_path': str(resolved_file) if resolved_file else None,
                'debug_doc': doc_path_rel,
                'debug_candidate': str(candidate) if candidate is not None else "",
                'debug_candidate_exists': bool(candidate and candidate.exists()),
                'debug_match_count': len(matches) if matches is not None else 0,
            }
    else:
        # Demo mode
        source_map = {}
        for i, source_id in enumerate(sources, 1):
            if source_id in SAMPLE_DOCS:
                doc = SAMPLE_DOCS[source_id]
                source_map[f'source_{i}'] = {
                    'name': f"Policy {source_id}: {doc['title']}",
                    'text': doc['content'],
                    'summary': '',
                    'type': 'Policy'
                }
            else:
                # Handle string sources (not in SAMPLE_DOCS)
                source_map[f'source_{i}'] = {
                    'name': f"Source {i}",
                    'text': source_id,  # Use the source string as text
                    'summary': '',
                    'type': 'Policy Document'
                }

    # Find all citation markers - support both [1] and 【source_1】 formats
    pattern_new = r'\[(\d+)\]'  # Matches [1], [2], etc.
    pattern_old = r'【(source_\d+)】'  # Matches 【source_1】, 【source_2】, etc.

    matches_new = list(re.finditer(pattern_new, content))
    matches_old = list(re.finditer(pattern_old, content))

    # Use new format if found, otherwise use old format
    if matches_new:
        # Convert [1] to source_map keys
        citation_style = 'new'
        matches = matches_new
    elif matches_old:
        citation_style = 'old'
        matches = matches_old
    else:
        # No citations found, just display content
        st.markdown(content)
        # Display sources in an expander if available
        if source_map:
            with st.expander("📄 View Sources & Download Documents"):
                for i, (source_key, source_info) in enumerate(source_map.items(), 1):
                    st.markdown(f"**Source {i}: {source_info.get('name', f'Source {i}')}**")

                    # ✅ 原文片段（Original Snippet）- chunk text
                    snippet = (source_info.get('text') or "").strip()
                    if snippet:
                        # Check if snippet appears to be only headings/titles (too short or mostly line breaks)
                        lines = snippet.split('\n')
                        non_empty_lines = [l.strip() for l in lines if l.strip()]
                        is_likely_heading_only = (
                            len(snippet) < 200 or  # Very short
                            len(non_empty_lines) < 3 or  # Too few lines
                            (len(non_empty_lines) <= 5 and all(len(l) < 80 for l in non_empty_lines))  # All short lines
                        )
                        
                        if is_likely_heading_only:
                            st.markdown(f"**Original Snippet:**")
                            st.markdown(f"_{snippet[:400]}_")
                            st.caption("⚠️ This snippet appears to contain only headings/titles. Please download the full document for complete content.")
                        else:
                            display_snippet = snippet[:400] + ("..." if len(snippet) > 400 else "")
                            st.markdown(f"**Original Snippet:**")
                            st.markdown(f"_{display_snippet}_")

                    # ✅ Metadata: page / score
                    page = source_info.get('page')
                    score = source_info.get('score')
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

                    # 添加下載按鈕（優先使用 RAG 模式解析出的 backend 檔案路徑）
                    file_path_str = source_info.get('file_path')
                    doc_path = Path(file_path_str) if file_path_str else None

                    # Demo/sample 模式：退回到舊的文字匹配邏輯
                    if not doc_path:
                        doc_path = get_document_path(None, source_info.get('text', ''))

                    if doc_path and doc_path.exists():
                        create_download_button(doc_path, f"📥 Download Source {i}")
                    st.divider()
        return

    # Display content with inline popovers
    last_end = 0
    cols_content = []

    for match in matches:
        # Add text before citation
        if match.start() > last_end:
            cols_content.append(('text', content[last_end:match.start()]))

        # Add citation popover
        source_key = match.group(1)
        if source_key in source_map:
            cols_content.append(('citation', source_key, source_map[source_key]))

        last_end = match.end()

    # Add remaining text
    if last_end < len(content):
        cols_content.append(('text', content[last_end:]))

    # Replace citations with inline small badges
    result_text = content
    for match in reversed(matches):  # Reverse to maintain string positions
        citation_num = match.group(1)
        # Convert citation to source_key
        if citation_style == 'new':
            # [1] -> source_1
            source_key = f'source_{citation_num}'
        else:
            # 【source_1】 -> already source_1
            source_key = citation_num

        if source_key in source_map:
            source_info = source_map[source_key]
            # Keep citation as [1], [2] format for cleaner look
            if citation_style == 'new':
                badge = f'<sup>[{citation_num}]</sup>'
            else:
                badge = f'<sup><small>📄 {source_info["name"]}</small></sup>'
            result_text = result_text[:match.start()] + badge + result_text[match.end():]

    # Display the text with inline citations
    st.markdown(result_text, unsafe_allow_html=True)

    # Display sources with download buttons in an expander
    if source_map:
        with st.expander("📄 View Sources & Download Documents"):
            for i, (source_key, source_info) in enumerate(source_map.items(), 1):
                st.markdown(f"**[{i}] {source_info.get('name', f'Source {i}')}**")

                # ✅ 原文片段（Original Snippet）- chunk text
                snippet = (source_info.get('text') or "").strip()
                if snippet:
                    # Check if snippet appears to be only headings/titles
                    lines = snippet.split('\n')
                    non_empty_lines = [l.strip() for l in lines if l.strip()]
                    is_likely_heading_only = (
                        len(snippet) < 200 or
                        len(non_empty_lines) < 3 or
                        (len(non_empty_lines) <= 5 and all(len(l) < 80 for l in non_empty_lines))
                    )
                    
                    if is_likely_heading_only:
                        st.markdown(f"**Original Snippet:**")
                        st.markdown(f"_{snippet[:400]}_")
                        st.caption("⚠️ This snippet appears to contain only headings/titles. Please download the full document for complete content.")
                    else:
                        display_snippet = snippet[:400] + ("..." if len(snippet) > 400 else "")
                        st.markdown(f"**Original Snippet:**")
                        st.markdown(f"_{display_snippet}_")

                # ✅ Metadata: page / score
                page = source_info.get('page')
                score = source_info.get('score')
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

                # 添加下載按鈕（優先使用 RAG 模式解析出的 backend 檔案路徑）
                file_path_str = source_info.get('file_path')
                doc_path = Path(file_path_str) if file_path_str else None

                # Demo/sample 模式：退回到舊的文字匹配邏輯
                if not doc_path:
                    doc_path = get_document_path(None, source_info.get('text', ''))

                if doc_path and doc_path.exists():
                    create_download_button(doc_path, f"📥 Download Source {i}")
                st.divider()


# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        # Display content with inline citation popovers
        if message["role"] == "assistant" and "sources" in message and message["sources"]:
            render_with_source_popovers(message["content"], message["sources"])
        else:
            st.markdown(message["content"])

# Chat input
if prompt := st.chat_input("Ask a question about UIC policies..."):
    st.session_state.show_welcome = False

    # Add user message
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)

    # Generate response
    with st.chat_message("assistant"):
        with st.spinner("Searching policy documents..."):
            backend = get_backend_safe()
            if backend is not None:
                # Use real RAG backend
                try:
                    result = backend.generate_answer(prompt, top_k=5)
                    response = result['answer']
                    sources = result['sources']
                    # Debug: 確認使用了真實的 RAG backend
                    print(f"[DEBUG] Using RAG backend, got {len(sources)} sources")
                except Exception as e:
                    st.error(f"❌ Error querying backend: {e}")
                    import traceback
                    st.error(traceback.format_exc())
                    response = "Sorry, there was an error processing your query."
                    sources = []
            else:
                # Use demo mode
                if prompt in SAMPLE_QA:
                    qa = SAMPLE_QA[prompt]
                    response = qa["answer"]
                    sources = qa["sources"]
                else:
                    response = f"""I found some information that might be relevant to your question about "{prompt}".

Based on the UIC Vice Chancellor's Office policies, the University of Illinois System follows established procedures and compliance requirements for all business and financial activities.

For specific details about your question, I recommend reviewing the relevant policy documents or contacting the Vice Chancellor's Office directly.

**Note:** This is a demo system. For official policy guidance, please consult the official UIC policy documentation."""
                    sources = random.sample(list(SAMPLE_DOCS.keys()), min(2, len(SAMPLE_DOCS)))

        # Display response with inline citation popovers
        if sources:
            render_with_source_popovers(response, sources)
        else:
            st.markdown(response)

    # Add assistant message with sources
    st.session_state.messages.append({
        "role": "assistant",
        "content": response,
        "sources": sources
    })

# Footer
st.divider()
st.caption("🤖 Powered by MetaRAG | University of Illinois Chicago | IDS 560 Analytics Strategy and Practice")
