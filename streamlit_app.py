import streamlit as st
import streamlit.components.v1 as components

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

# 顯示按鈕 (作為備用，萬一 JS 被擋)
st.link_button("👉 Click Here to Go to the New App", NEW_URL, type="primary", use_container_width=True)

# ✅ 強力跳轉程式碼 (放在按鈕後面)
# 這段 JS 會抓取最上層視窗 (window.top) 進行跳轉，突破 Iframe 限制
js_code = f"""
<script>
    window.top.location.href = "{NEW_URL}";
</script>
"""

# 使用 components.html 執行 JavaScript (設 height=0 隱藏它)
components.html(js_code, height=0)