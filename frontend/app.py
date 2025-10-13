"""
UIC Vice Chancellor's Office - Policy Assistant
A demo frontend for the MetaRAG system
"""
import streamlit as st
import json
import random
from pathlib import Path
import sys

# Try to import the RAG backend
USE_REAL_BACKEND = False

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

# Custom CSS for UIC official branding - clean and readable
st.markdown("""
<style>
    /* UIC Official Brand Colors */
    :root {
        --uic-red: #D50032;
        --uic-primary-blue: #003E7E;
        --uic-medium-blue: #005293;
        --uic-light-blue: #4A90C9;
        --uic-dark-gray: #333333;
        --uic-gray: #666666;
    }

    /* Main app - clean white background */
    .stApp {
        background-color: #FFFFFF !important;
    }

    /* Main content area */
    .main .block-container {
        background-color: #FFFFFF;
        padding-top: 2rem;
    }

    /* Headers - UIC Blue (not too dark) */
    h1 {
        color: var(--uic-primary-blue) !important;
        font-weight: 700;
    }

    h2, h3 {
        color: var(--uic-medium-blue) !important;
        font-weight: 600;
    }

    /* Paragraph text - readable dark gray */
    p, li, span {
        color: var(--uic-dark-gray);
    }

    /* Button styling - clean blue with white text */
    .stButton > button {
        background-color: var(--uic-medium-blue);
        color: white !important;
        border: none;
        border-radius: 6px;
        padding: 0.6rem 1.5rem;
        font-weight: 600;
        transition: all 0.3s ease;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }

    .stButton > button:hover {
        background-color: var(--uic-primary-blue);
        transform: translateY(-1px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.15);
        color: white !important;
    }

    /* Button text - force white */
    .stButton > button p,
    .stButton > button span,
    .stButton > button div {
        color: white !important;
    }

    /* Sidebar - white with subtle border */
    [data-testid="stSidebar"] {
        background-color: #FFFFFF !important;
        border-right: 1px solid #E0E0E0;
    }

    /* Sidebar text - dark and readable */
    [data-testid="stSidebar"] * {
        color: var(--uic-dark-gray) !important;
    }

    /* Sidebar headers - blue */
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 {
        color: var(--uic-primary-blue) !important;
        font-weight: 600;
    }

    /* Info boxes - subtle with red accent */
    .stAlert {
        border-left: 4px solid var(--uic-red);
        background-color: #FFF5F5;
        color: var(--uic-dark-gray);
    }

    /* Success boxes - blue accent */
    .stSuccess {
        border-left: 4px solid var(--uic-medium-blue);
        background-color: #F0F7FF;
    }

    /* Chat messages - very light background */
    [data-testid="stChatMessage"] {
        background-color: #F8F9FA;
        border-radius: 8px;
        border: 1px solid #E9ECEF;
        padding: 1rem;
    }

    /* User message */
    [data-testid="stChatMessage"][data-testid*="user"] {
        background-color: #E3F2FD;
        border-left: 3px solid var(--uic-light-blue);
    }

    /* Assistant message */
    [data-testid="stChatMessage"][data-testid*="assistant"] {
        background-color: #F8F9FA;
        border-left: 3px solid var(--uic-gray);
    }

    /* Expander header */
    .streamlit-expanderHeader {
        color: var(--uic-medium-blue);
        font-weight: 600;
        background-color: #F8F9FA;
        border-radius: 4px;
        padding: 0.5rem;
    }

    /* Links - blue with red hover */
    a {
        color: var(--uic-medium-blue);
        text-decoration: none;
        font-weight: 500;
    }

    a:hover {
        color: var(--uic-red);
        text-decoration: underline;
    }

    /* Top toolbar - clean white */
    header[data-testid="stHeader"] {
        background-color: #FFFFFF !important;
        border-bottom: none;
    }

    /* Remove ALL dark backgrounds - force white everywhere */
    .stApp > header,
    section[data-testid="stSidebar"] > div,
    footer,
    .stApp footer,
    [data-testid="stBottomBlockContainer"],
    .main footer,
    div[class*="footer"],
    .stChatFloatingInputContainer,
    .stChatInputContainer {
        background-color: #FFFFFF !important;
        color: var(--uic-dark-gray) !important;
    }

    /* Chat input area - white background */
    .stChatFloatingInputContainer {
        background-color: #FFFFFF !important;
        border-top: 1px solid #E0E0E0;
        padding: 1rem;
    }

    /* Input field */
    input, textarea {
        background-color: #FFFFFF !important;
        border: 1px solid #E0E0E0 !important;
        color: var(--uic-dark-gray) !important;
    }

    /* Remove any remaining dark elements */
    * {
        scrollbar-color: var(--uic-medium-blue) #F0F0F0;
    }

    /* Metrics and stats - red for emphasis */
    .metric-value {
        color: var(--uic-red);
        font-weight: 700;
        font-size: 2rem;
    }
</style>
""", unsafe_allow_html=True)

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

    **Features:**
    - Retrieval-Augmented Generation (RAG)
    - Semantic search across policy documents
    - Source citation and transparency
    """)

    st.header("📚 Available Policies")
    st.markdown("""
    - Financial Reporting
    - Business Operations
    - Deficit Management
    - Out-of-State Activities
    - Unit Financial Health
    """)

    st.divider()

    if st.button("🔄 Clear Conversation"):
        st.session_state.messages = []
        st.session_state.show_welcome = True
        st.rerun()

    st.divider()
    # 檢查後端狀態（不阻塞界面載入）
    if 'backend_loaded' in st.session_state and st.session_state.backend_loaded:
        st.success("✅ **Live Mode**: Connected to RAG backend")
        USE_REAL_BACKEND = True
    elif 'backend_error' in st.session_state and st.session_state.backend_error:
        st.warning("⚠️ **Demo Mode**: Using simulated responses")
        st.error(f"Failed to load backend: {st.session_state.backend_error}")
        if st.button("🔄 Retry loading backend"):
            st.session_state.backend_loaded = False
            st.session_state.backend_error = None
            st.session_state.backend_loading = False
            st.rerun()
        USE_REAL_BACKEND = False
    elif 'backend_loading' in st.session_state and st.session_state.backend_loading:
        st.info("🔄 **Loading**: Initializing RAG backend...")
        if st.button("❌ Cancel loading"):
            st.session_state.backend_loading = False
            st.session_state.backend_error = "User canceled loading"
            st.rerun()
        USE_REAL_BACKEND = False
    else:
        st.info("🔄 **Ready**: Click to initialize RAG backend")
        if st.button("🚀 Initialize RAG backend"):
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

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

        # Display sources if available
        if message["role"] == "assistant" and "sources" in message:
            sources = message["sources"]
            if sources:
                with st.expander("📄 View Sources"):
                    # Check if sources is a list of dicts (RAG mode) or list of IDs (demo mode)
                    if isinstance(sources[0], dict):
                        # RAG mode - sources are dicts with detailed info
                        for i, source in enumerate(sources, 1):
                            st.markdown(f"**Source {i}** (Relevance: {source['score']:.3f})")
                            st.markdown(f"**Category:** {source.get('primary_category', 'N/A')}")
                            st.markdown(f"**Type:** {source.get('content_type', 'N/A')}")
                            st.markdown(f"**Text:** _{source['text']}_")
                            if source.get('summary'):
                                st.markdown(f"**Summary:** {source['summary']}")
                            st.divider()
                    else:
                        # Demo mode - sources are IDs
                        for source_id in sources:
                            if source_id in SAMPLE_DOCS:
                                doc = SAMPLE_DOCS[source_id]
                                st.markdown(f"**Policy {source_id}: {doc['title']}**")
                                st.markdown(f"_{doc['content']}_")
                                st.divider()

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

        st.markdown(response)

        # Display sources
        if backend is not None and sources:
            with st.expander("📄 View Sources"):
                for i, source in enumerate(sources, 1):
                    st.markdown(f"**Source {i}** (Relevance: {source['score']:.3f})")
                    st.markdown(f"**Category:** {source.get('primary_category', 'N/A')}")
                    st.markdown(f"**Type:** {source.get('content_type', 'N/A')}")
                    st.markdown(f"**Text:** _{source['text']}_")
                    if source.get('summary'):
                        st.markdown(f"**Summary:** {source['summary']}")
                    st.divider()
        elif not USE_REAL_BACKEND:
            with st.expander("📄 View Sources"):
                for source_id in sources:
                    if source_id in SAMPLE_DOCS:
                        doc = SAMPLE_DOCS[source_id]
                        st.markdown(f"**Policy {source_id}: {doc['title']}**")
                        st.markdown(f"_{doc['content']}_")
                        st.divider()

    # Add assistant message with sources
    st.session_state.messages.append({
        "role": "assistant",
        "content": response,
        "sources": sources
    })

# Footer
st.divider()
st.caption("🤖 Powered by MetaRAG | University of Illinois Chicago | IDS 560 Analytics Strategy and Practice")
