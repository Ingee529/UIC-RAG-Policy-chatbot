"""
UIC Vice Chancellor's Office - Policy Assistant
A demo frontend for the MetaRAG system
(Final Fixed Version: Live RAG Buttons, No Sample Docs, Smooth Transition)
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
import time
import math
import zipfile
import io

# ========= (Smart Path Setup) =========
try:
    current_path = Path(__file__).resolve()
    if current_path.name == "streamlit_app.py":
        ROOT_DIR = current_path.parent
        FRONTEND_DIR = ROOT_DIR / "frontend"
    else:
        FRONTEND_DIR = current_path.parent
        ROOT_DIR = FRONTEND_DIR.parent
except NameError:
    cwd = Path.cwd()
    if (cwd / "frontend").exists():
        ROOT_DIR = cwd
        FRONTEND_DIR = cwd / "frontend"
    elif (cwd / "app.py").exists() and (cwd.parent / "backend").exists():
        FRONTEND_DIR = cwd
        ROOT_DIR = cwd.parent
    else:
        ROOT_DIR = Path("/app")
        FRONTEND_DIR = Path("/app/frontend")

BACKEND_DIR = ROOT_DIR / "backend"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

USE_REAL_BACKEND = False


# ========= Helpers =========

def get_base64_image(image_path: Path) -> str:
    candidates = [image_path, FRONTEND_DIR / image_path.name, ROOT_DIR / image_path.name]
    for path in candidates:
        if path.exists():
            try:
                with open(path, "rb") as img_file:
                    return base64.b64encode(img_file.read()).decode()
            except Exception:
                continue
    return ""

def setup_documents_directory() -> Path:
    documents_dir = FRONTEND_DIR / "documents"
    input_files_dir = BACKEND_DIR / "input_files"
    documents_dir.mkdir(exist_ok=True, parents=True)
    if input_files_dir.exists() and not any(documents_dir.iterdir()):
        try:
            for file_path in input_files_dir.glob("*.*"):
                if file_path.is_file():
                    shutil.copy2(file_path, documents_dir / file_path.name)
        except Exception:
            pass
    return documents_dir

def get_document_path(document_id=None, source_text: str = "") -> Path | None:
    search_dirs = [BACKEND_DIR / "input_files", FRONTEND_DIR / "documents"]
    file_map = {}
    for d in search_dirs:
        if d.exists():
            for f in d.rglob("*"):
                if f.is_file() and f.suffix.lower() in ['.pdf', '.txt', '.docx']:
                    file_map[f.name.lower()] = f
                    file_map[f.stem.lower()] = f

    if source_text:
        match = re.search(r'Document Title:\s*([^\n]+)', source_text)
        if match:
            doc_title = match.group(1).strip()
            if doc_title.lower() in file_map: return file_map[doc_title.lower()]
            
            number_match = re.search(r'(\d+(?:\.\d+)+)', doc_title)
            if number_match:
                doc_num = number_match.group(1)
                for name, path in file_map.items():
                    if name.startswith(doc_num + " ") or name.startswith(doc_num + "_") or name.startswith(doc_num + "."):
                        return path
            
            clean_title = doc_title.lower().replace('–', '-').split(' - ')[0].strip()[:20]
            for name, path in file_map.items():
                if clean_title in name: return path

    if document_id:
        doc_id_clean = str(document_id).lower().replace(" ", "_")
        for name, path in file_map.items():
            if name.startswith(doc_id_clean): return path
        if doc_id_clean in file_map: return file_map[doc_id_clean]
    return None

def create_download_button(file_path: Path | None, button_text: str = "📥 Download Document") -> None:
    if file_path and file_path.exists():
        try:
            with open(file_path, "rb") as f:
                file_data = f.read()
            suffix = file_path.suffix.lower()
            mime_type = "application/pdf" if suffix == ".pdf" else "text/plain"
            st.download_button(label=button_text, data=file_data, file_name=file_path.name, mime=mime_type)
        except Exception as e:
            st.error(f"❌ File Error: {str(e)}")
    else:
        st.caption("📄 Document file not available")

def load_custom_css():
    possible_paths = [FRONTEND_DIR / "styles.css", ROOT_DIR / "styles.css", Path("styles.css"), Path("frontend/styles.css")]
    for path in possible_paths:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
            return
    st.warning("⚠️ Warning: styles.css not found.")

def get_backend_safe():
    if "backend" not in st.session_state:
        st.session_state.backend = None
        st.session_state.backend_loaded = False
    if st.session_state.backend_loaded: return st.session_state.backend
    try:
        with st.spinner("Loading RAG backend..."):
            from rag_backend import get_backend
            st.session_state.backend = get_backend()
            st.session_state.backend_loaded = True
            return st.session_state.backend
    except Exception as e:
        st.error(f"❌ Failed to load RAG backend: {e}")
        return None

def stream_text(text, delay=0.02):
    for word in text.split(" "):
        yield word + " "
        time.sleep(delay)

def convert_history_to_txt():
    history_text = "UIC Policy Assistant - Chat History\n" + "=" * 40 + "\n\n"
    for msg in st.session_state.messages:
        role = "User" if msg["role"] == "user" else "Assistant"
        content = msg["content"]
        history_text += f"[{role}]:\n{content}\n"
        if role == "Assistant" and msg.get("sources"):
            history_text += "\n[Sources Referenced]:\n"
            if isinstance(msg["sources"][0], dict):
                for i, src in enumerate(msg["sources"][:3], 1):
                    doc_name = src.get('doc_name', 'Document')
                    history_text += f"  {i}. {doc_name}\n"
            else:
                for i, src in enumerate(msg["sources"], 1):
                    history_text += f"  {i}. {src}\n"
        history_text += "\n" + "-" * 40 + "\n\n"
    return history_text

def create_chat_zip(min_relevance_score=0.0):
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
        chat_txt = convert_history_to_txt()
        zip_file.writestr("chat_history.txt", chat_txt)
        added_files = set()
        for msg in st.session_state.messages:
            if msg["role"] == "assistant" and msg.get("sources") and isinstance(msg["sources"][0], dict):
                for source in msg["sources"]:
                    score = source.get("score") or source.get("rerank_score")
                    if score is not None:
                        try:
                            if float(score) < min_relevance_score: continue
                        except: pass
                    doc_name = source.get("doc_name", "doc")
                    file_path = None
                    if source.get('file_path'): file_path = Path(source['file_path'])
                    if not file_path or not file_path.exists():
                        file_path = get_document_path(source_text=f"Document Title: {doc_name}")
                    if file_path and file_path.exists() and file_path.name not in added_files:
                        try:
                            zip_file.write(file_path, arcname=f"cited_documents/{file_path.name}")
                            added_files.add(file_path.name)
                        except Exception as e:
                            print(f"⚠️ Zip failed: {e}")
    return zip_buffer.getvalue()


# ========= Streamlit Page Configuration =========
st.set_page_config(page_title="UIC Policy Assistant Prototype", page_icon="🏛️", layout="wide")
load_custom_css()
setup_documents_directory()

# ========= Sample Questions =========
SAMPLE_QUESTIONS = [
    "What happens if a university or system office has a financial deficit?",
    "Who has the authority to grant exceptions to university financial policies?",
]

# ========= Session state Initialization =========
if "messages" not in st.session_state: st.session_state.messages = []
if "show_welcome" not in st.session_state: st.session_state.show_welcome = True 
if "trigger_query" not in st.session_state: st.session_state.trigger_query = None

# ========= Header =========
col1, col2 = st.columns([1, 5])
with col1:
    uic_logo_path = FRONTEND_DIR / "uic.png"
    if uic_logo_path.exists(): st.image(str(uic_logo_path), width=150)
with col2:
    st.title("UIC Policy Assistant Prototype")
    st.caption("AI-powered assistant for University of Illinois Chicago Vice Chancellor's Office policies")

# ========= Sidebar =========
with st.sidebar:
    st.markdown('<div style="margin-top: -30px; margin-bottom: 5px;"><div style="font-size: 1.05em; font-weight: bold; color: #001E62; margin: 0; padding: 0;">About</div></div>', unsafe_allow_html=True)
    st.markdown('<div style="font-size: 1em; margin-bottom: 8px;">UIC Policy Assistant </br> (Demo Version)</div>', unsafe_allow_html=True)
    
    st.markdown('<div style="font-size: 1.05em; font-weight: bold; color: #001E62; margin-top: 5px; margin-bottom: 3px;">🎓 Faculty Advisor</div>', unsafe_allow_html=True)
    st.markdown('<div style="font-size: 1em; margin-bottom: 6px;"><a href="https://business.uic.edu/profiles/sarayloo-fatemeh/" target="_blank" style="text-decoration: none; color: #001E62;">Fatemeh Sarayloo, Ph.D.</a></div>', unsafe_allow_html=True)

    linkedin_path = FRONTEND_DIR / "linkedin.jpeg"
    linkedin_b64 = get_base64_image(linkedin_path)
    linkedin_img_tag = f'<img src="data:image/jpeg;base64,{linkedin_b64}" width="20" style="margin-bottom: 2px;">' if linkedin_b64 else ""

    st.markdown(f"""<div style="display: flex; align-items: center; gap: 6px; margin-top: 5px; margin-bottom: 3px;"><div style="font-size: 1.05em; font-weight: bold; color: #001E62;">🧑‍🏫 Teaching Assistant</div>{linkedin_img_tag}</div>""", unsafe_allow_html=True)
    st.markdown('<div style="font-size: 1em; margin-bottom: 6px;"><a href="https://www.linkedin.com/in/mokshitsurana/" target="_blank" style="text-decoration: none; color: #001E62;">Mokshit Surana</a></div>', unsafe_allow_html=True)

    st.markdown(f"""<div style="display: flex; align-items: center; gap: 6px; margin-top: 5px; margin-bottom: 3px;"><div style="font-size: 1.05em; font-weight: bold; color: #001E62;">👥 Team Members</div>{linkedin_img_tag}</div>""", unsafe_allow_html=True)
    st.markdown("""
    <div style="font-size: 1em; line-height: 1.3; margin-bottom: 8px;">
    <a href="https://www.linkedin.com/in/haswatha-sridharan" target="_blank" style="text-decoration: none; color: #001E62;">Haswatha Sridharan</a><br>
    <a href="https://linkedin.com/in/vamshi-krishna-1490b4187" target="_blank" style="text-decoration: none; color: #001E62;">Vamshi Krishna Aileni</a><br>
    <a href="https://www.linkedin.com/in/yonce-yang-93a731314/" target="_blank" style="text-decoration: none; color: #001E62;">Hsin-Jui Yang</a><br>
    <a href="https://www.linkedin.com/in/honglin-liu-8850b038b" target="_blank" style="text-decoration: none; color: #001E62;">Honglin Liu</a>
    </div>""", unsafe_allow_html=True)

    st.markdown('<div style="margin-top: 5px; margin-bottom: 5px;"><div style="font-size: 1.05em; font-weight: bold; color: #001E62;">📚 Available Policies</div></div>', unsafe_allow_html=True)
    st.markdown('<div style="font-size: 1em; line-height: 1.4; margin-bottom: 8px;"><b>Fiscal Environment</b><br><b>Custodial Funds</b><br><b>Budget</b><br><b>Payroll</b><br><b>Receivables</b><br></div>', unsafe_allow_html=True)

    st.markdown('<div style="margin: 5px 0;"></div>', unsafe_allow_html=True)

    if st.button("🔄 Clear Conversation"):
        st.session_state.messages = []
        st.session_state.show_welcome = True
        st.rerun()

    if st.session_state.messages:
        st.markdown('<div style="margin: 5px 0;"></div>', unsafe_allow_html=True)
        st.markdown('<div style="font-size: 1.05em; font-weight: bold; color: #001E62;">📥 Export Results</div>', unsafe_allow_html=True)
        filter_low_quality = st.checkbox("Only include highly relevant docs", value=True, help="Filter out documents with low AI relevance scores")
        threshold = 0.0 if filter_low_quality else -999.0
        zip_data = create_chat_zip(min_relevance_score=threshold)
        st.download_button(label="📦 Download Chat & Docs (.zip)", data=zip_data, file_name="uic_policy_export.zip", mime="application/zip", use_container_width=True)
        st.caption("Includes chat history and cited PDF files.")

    st.markdown('<div style="margin: 5px 0;"></div>', unsafe_allow_html=True)

    if st.session_state.get("backend_loaded"):
        st.markdown('✅ <strong>Live Mode</strong>: Ready', unsafe_allow_html=True)
    else:
        if st.button("🔥 Start Assistant"):
            _ = get_backend_safe()
            st.rerun()

# ========= Welcome Buttons (Live RAG) =========
welcome_placeholder = st.empty()

# 2. Check display conditions
if st.session_state.show_welcome and not st.session_state.messages:
    # 3. Put all content into this placeholder container
    with welcome_placeholder.container():
        st.markdown("### Welcome! 👋")
        st.markdown("Ask me anything about UIC Vice Chancellor's Office policies. Here are some examples:")
        
        if 'SAMPLE_QUESTIONS' in globals():
            cols = st.columns(1)
            for i, question in enumerate(SAMPLE_QUESTIONS):
                if st.button(f"💡 {question}", key=f"example_{i}"):
                    # A. Set trigger question
                    st.session_state.trigger_query = question
                    st.session_state.show_welcome = False
                    
                    # B. make the button disappear instantly
                    welcome_placeholder.empty()
                    
                    # C. Force refresh (enter chat mode)
                    st.rerun()
        st.divider()

# ========= Render Function =========
def render_with_source_popovers(content: str, sources):
    if not sources:
        st.markdown(content)
        return

    if isinstance(sources[0], dict):
        source_map = {}
        for i, source in enumerate(sources[:3], 1):
            doc_name = source.get("doc_name", f"Document {i}")
            resolved_file = get_document_path(source_text=f"Document Title: {doc_name}")
            score = source.get("score") or source.get("rerank_score")
            source_map[f"source_{i}"] = {
                "name": f"{source.get('primary_category', 'Doc')} - {doc_name}",
                "text": source.get("text", ""),
                "file_path": str(resolved_file) if resolved_file else None,
                "page": source.get("page"),
                "score": score
            }
    else:
        source_map = {f"source_{i}": {"name": str(s), "text": "", "file_path": None} for i, s in enumerate(sources, 1)}

    result_text = content
    matches = list(re.finditer(r"\[(\d+)\]", content))
    for match in reversed(matches):
        citation_num = match.group(1)
        source_key = f"source_{citation_num}"
        if source_key in source_map:
            badge = f"<sup>[{citation_num}]</sup>"
            result_text = result_text[:match.start()] + badge + result_text[match.end():]
    
    st.markdown(result_text, unsafe_allow_html=True)

    if source_map:
        with st.expander("📄 View Sources & Download Documents"):
            for i, (k, info) in enumerate(source_map.items(), 1):
                st.markdown(f"**[{i}] {info['name']}**")
                if info['text']:
                    lines = [l.strip() for l in info['text'].split("\n") if l.strip()]
                    is_heading = len(info['text']) < 200 or len(lines) < 3
                    display_snippet = info['text'][:400] + ("..." if len(info['text']) > 400 else "")
                    st.markdown("**Original Snippet:**")
                    st.markdown(f"_{display_snippet}_")
                    if is_heading: st.caption("⚠️ This snippet appears to contain only headings/titles.")
                
                meta_bits = []
                if info.get("page"): meta_bits.append(f"📄 Page: {info['page']}")
                if info.get("score") is not None:
                    try:
                        raw_score = float(info['score'])
                        prob = 1 / (1 + math.exp(-raw_score)) * 100
                        icon = "🟢" if prob >= 75 else "🟡" if prob >= 40 else "🔴"
                        meta_bits.append(f"{icon} Relevance: {prob:.1f}%")
                    except:
                        meta_bits.append(f"⭐ Score: {info['score']}")
                if meta_bits: st.caption(" | ".join(meta_bits))
                
                doc_path = Path(info['file_path']) if info['file_path'] else None
                if not doc_path: doc_path = get_document_path(None, info['text'])
                create_download_button(doc_path, f"📥 Download Source {i}")
                st.divider()

# ========= Display History Messages =========
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        if message["role"] == "assistant" and message.get("sources"):
            render_with_source_popovers(message["content"], message["sources"])
        else:
            st.markdown(message["content"])

# ========= Chat Input (Unified) =========
# 1. General input
user_input = st.chat_input("Ask a question about UIC policies...")

# 2. Button trigger
if st.session_state.trigger_query:
    user_input = st.session_state.trigger_query
    st.session_state.trigger_query = None 

# 3. Process input
if user_input:
    st.session_state.show_welcome = False
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"): st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.status("Thinking...", expanded=True) as status:
            st.write("🔍 Searching policy documents...")
            backend = get_backend_safe()
            response = ""
            sources = []
            if backend:
                try:
                    # Here we perform RAG query
                    result = backend.generate_answer(user_input, top_k=5)
                    response = result["answer"]
                    sources = result["sources"]
                    status.update(label="Complete!", state="complete", expanded=False)
                except Exception as e:
                    status.update(label="Error", state="error")
                    response = "Sorry, there was an error processing your query."
                    print(f"❌ Error: {e}")
            else:
                
                response = "⚠️ Backend is offline. Please check API keys or logs."
                status.update(label="Error", state="error")

        message_placeholder = st.empty()
        message_placeholder.write_stream(stream_text(response))
        
        message_placeholder.empty()
        with message_placeholder.container():
            if sources:
                render_with_source_popovers(response, sources)
            else:
                st.markdown(response)

    st.session_state.messages.append({"role": "assistant", "content": response, "sources": sources})
    st.rerun()

# ========= Footer =========
st.divider()
st.caption("🤖 Powered by MetaRAG | University of Illinois Chicago | IDS 560 Analytics Strategy and Practice")