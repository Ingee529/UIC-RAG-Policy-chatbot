import streamlit as st

# 設定頁面
st.set_page_config(
    page_title="UIC Policy Assistant - Redirecting...",
    page_icon="🚀",
    layout="centered"
)

# 你的 Hugging Face Space 網址 (請確認這是對的)
NEW_URL = "https://huggingface.co/spaces/Ingee529/UIC-RAG-Policy-chatbot"

# 介面顯示
st.title("🚀 We've Moved to a Faster Server!")

st.markdown("""
### To provide better AI answers and document analysis,
### we have migrated to a high-performance GPU server.
""")

st.divider()

# 大按鈕
st.link_button("👉 Click Here to Go to the New App", NEW_URL, type="primary", use_container_width=True)

# 嘗試自動跳轉 (部分瀏覽器支援)
st.markdown(f'<meta http-equiv="refresh" content="0;url={NEW_URL}">', unsafe_allow_html=True)

# 顯示新網址連結 (備用)
st.markdown(f"New Link: [{NEW_URL}]({NEW_URL})")