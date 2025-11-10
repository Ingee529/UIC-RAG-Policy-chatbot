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

# Try to import the RAG backend
USE_REAL_BACKEND = False


def get_base64_image(image_path):
    """將圖片轉換為 base64 編碼"""
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode()


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
    page_title="UIC Policy Assistant",
    page_icon="🏛️",
    layout="wide"
)

load_custom_css()

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
    "What is the annual financial report policy?": {
        "answer": "The University of Illinois System is required to publish an annual financial report each year. This report includes basic financial statements, supplementary schedules, and an independent auditor's opinion. The reporting requirement is mandated by the State Comptroller Act (15 ILCS 405/19.5) to ensure transparency and provide necessary financial information to the public and stakeholders. The fiscal year ends on June 30, and the report consolidates all university and System Office activities.",
        "sources": ["1.1"]
    },
    "How does UIC handle deficit reporting?": {
        "answer": "The University of Illinois System has established procedures for deficit reporting at both the university and System Office levels. Units are required to report deficits in accordance with established procedures to maintain fiscal responsibility and transparency. This ensures that financial challenges are identified early and appropriate corrective actions can be taken.",
        "sources": ["1.4"]
    },
    "What are the policies for conducting business outside Illinois?": {
        "answer": "The University of Illinois System has specific policies governing business activities conducted outside the State of Illinois. These policies ensure compliance with relevant regulations and maintain proper oversight of all university business operations, regardless of location. This helps the university manage risk and maintain accountability for activities beyond state borders.",
        "sources": ["1.5"]
    },
    "What financial reporting standards does UIC follow?": {
        "answer": "The University of Illinois System follows generally accepted accounting principles (GAAP) for all financial activities. The system complies with reporting requirements mandated by state law, including the State Comptroller Act. All financial activities must be properly conducted, recorded, and reported to ensure accuracy, transparency, and accountability.",
        "sources": ["1.2"]
    },
    "How does UIC monitor unit financial health?": {
        "answer": "Each university unit within the University of Illinois System is required to maintain financial health and report regularly on their fiscal status. This monitoring ensures proper stewardship of resources and allows the system to identify and address financial issues proactively. Units must follow established procedures for financial reporting and maintain compliance with university policies.",
        "sources": ["1.3"]
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
    st.image("uic.png", width=150, use_container_width=False)
with col2:
    st.title("UIC Policy Assistant")
    st.caption("AI-powered assistant for University of Illinois Chicago Vice Chancellor's Office policies")

# Sidebar
with st.sidebar:
    st.header("About")
    st.info("""
    This is a demonstration of the MetaRAG system for UIC Vice Chancellor's Office policies.
    """)
    st.subheader("🎓 Faculty Advisor")
    st.markdown("[Fatemeh Sarayloo, Ph.D.](https://business.uic.edu/profiles/sarayloo-fatemeh/)")
    
    # Teaching Assistant with LinkedIn icon
    linkedin_path = Path(__file__).parent / "linkedin.jpeg"
    st.markdown(f"""
    <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px;">
        <h3 style="margin: 0;">🧑‍🏫 Teaching Assistant</h3>
        <img src="data:image/jpeg;base64,{get_base64_image(linkedin_path)}" width="25" style="margin-bottom: 5px;">
    </div>
    """, unsafe_allow_html=True)
    st.markdown("[Mokshit Surana](https://www.linkedin.com/in/mokshitsurana/)")
    
    # Team Members with LinkedIn icon
    st.markdown(f"""
    <div style="display: flex; align-items: center; gap: 10px; margin-top: 15px; margin-bottom: 10px;">
        <h2 style="margin: 0;">👥 Team Members</h2>
        <img src="data:image/jpeg;base64,{get_base64_image(linkedin_path)}" width="25" style="margin-bottom: 5px;">
    </div>
    """, unsafe_allow_html=True)
    st.markdown("""
    [Haswatha Sridharan](https://www.linkedin.com/in/haswatha-sridharan)

    [Vamshi Krishna Aileni](https://linkedin.com/in/vamshi-krishna-1490b4187)

    [Hsin-Jui Yang](https://www.linkedin.com/in/yonce-yang-93a731314/)

    [Honglin Liu](https://www.linkedin.com/in/honglin-liu-8850b038b)
    """)

    st.header("📚 Available Policies")

    # Create a scrollable container for policies
    with st.container():
        st.markdown("""
        <div style="max-height: 400px; overflow-y: auto; padding-right: 10px;">

        <b>Custodial Funds Management:</b><br>
        • Managing Custodial Funds<br>
        • Unit Liaison Responsibilities<br>
        • Expenditure Procedures<br><br>

        <b>Payroll & Employment:</b><br>
        • Employee Work Time Submission<br>
        • Employment Agreement Payments<br>
        • Payroll Overpayment Corrections<br><br>

        <b>Receivables Management:</b><br>
        • Managing Receivables<br>
        • GAR Charges Processing<br>
        • Delinquent Account Collections<br><br>

        <b>Business & Finance Policies:</b><br>
        • BFPP 1.2, 1.3, 1.6

        </div>
        """, unsafe_allow_html=True)

    st.divider()

    if st.button("🔄 Clear Conversation"):
        st.session_state.messages = []
        st.session_state.show_welcome = True
        st.rerun()

    st.divider()
    # 檢查後端狀態（不阻塞界面載入）
    if 'backend_loaded' in st.session_state and st.session_state.backend_loaded:
        st.success("✅ **Live Mode**: Assistant is ready")
        USE_REAL_BACKEND = True
    elif 'backend_error' in st.session_state and st.session_state.backend_error:
        st.warning("⚠️ **Demo Mode**: Using simulated responses")
        st.error(f"Could not load assistant: {st.session_state.backend_error}")
        if st.button("🔄 Try Again"):
            st.session_state.backend_loaded = False
            st.session_state.backend_error = None
            st.session_state.backend_loading = False
            st.rerun()
        USE_REAL_BACKEND = False
    elif 'backend_loading' in st.session_state and st.session_state.backend_loading:
        st.info("🔄 **Loading**: Starting the assistant...")
        if st.button("❌ Cancel"):
            st.session_state.backend_loading = False
            st.session_state.backend_error = "User canceled loading"
            st.rerun()
        USE_REAL_BACKEND = False
    else:
        st.info("🔄 **Ready to help**: Click below to start")
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
        if st.button(f"💡 {question}", key=f"example_{i}", use_container_width=True):
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
        for i, source in enumerate(sources[:3], 1):
            category = source.get('primary_category', 'Document')
            doc_id = source.get('document_id', f'Doc {i}')
            source_map[f'source_{i}'] = {
                'name': f"{category} - {doc_id}",
                'text': source['text'],
                'summary': source.get('summary', ''),
                'type': source.get('content_type', 'N/A')
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

    # Find all citation markers
    pattern = r'【(source_\d+)】'
    matches = list(re.finditer(pattern, content))

    if not matches:
        # No citations found, just display content
        st.markdown(content)
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
        source_key = match.group(1)
        if source_key in source_map:
            source_info = source_map[source_key]
            # Create a small badge-style citation
            badge = f'<sup><small>📄 {source_info["name"]}</small></sup>'
            result_text = result_text[:match.start()] + badge + result_text[match.end():]

    # Display the text with inline citations
    st.markdown(result_text, unsafe_allow_html=True)


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
