# UIC Policy Assistant - Frontend

A Streamlit-based demo frontend for the MetaRAG system, designed to showcase policy question-answering capabilities for the UIC Vice Chancellor's Office.

## Features

- 💬 **Chat Interface** - Natural conversation with the policy assistant
- 📄 **Source Citations** - View relevant policy documents for each answer
- 🎯 **Example Questions** - Pre-loaded common policy questions
- 🏛️ **Clean UI** - Professional interface suitable for demonstrations

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Run the App

```bash
streamlit run app.py
```

The app will open in your browser at `http://localhost:8501`

## Demo Mode

This frontend currently runs in **demo mode** with simulated responses. It includes:

- Sample policy documents from UIC Vice Chancellor's Office
- Pre-defined Q&A pairs for common questions
- Simulated retrieval and response generation

## Deploying to Streamlit Cloud

1. Push this code to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your GitHub repository
4. Select `frontend/app.py` as the main file
5. Deploy!

You'll get a public URL like: `https://your-app.streamlit.app`

## Future Enhancements

When you have an API key, you can connect to the actual MetaRAG backend by:

1. Adding API connection code
2. Replacing simulated responses with real retrieval
3. Using actual embeddings and vector search

## Structure

```
frontend/
├── app.py              # Main Streamlit application
├── requirements.txt    # Python dependencies
└── README.md          # This file
```

## Related

- Main project: `../code/` (MetaRAG backend)
- Documentation: `../code/README.md`
