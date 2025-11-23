"""
GEAR Triple Extraction - Extracted from META notebook
Uses GPT-4o-mini for extracting knowledge graph triples
"""

from openai import OpenAI
import json
import os

# Initialize client as None - will be created when needed
client = None

def _get_client():
    """Lazy initialize OpenAI client"""
    global client
    if client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
        client = OpenAI(api_key=api_key)
    return client

def extract_triples_from_text(text: str, query: str = None, model: str = None):
    """
    Extract (subject, predicate, object) triples using OpenAI's new API.

    Args:
        text: context text to extract triples from
        query: (optional) user question, used only to guide extraction in the prompt
        model: (optional) OpenAI model name; if None or empty, uses a default

    Returns:
        List[dict] with keys: subject, predicate, object
    """
    # Choose default model if not provided or invalid
    if not model:
        model = "gpt-4o-mini"  # or "gpt-4.1-mini" depending on what you have

    query_hint = f"\nUser question (for context): {query}\n" if query else ""

    prompt = f"""
    You are an information extraction system.

    From the text below, extract ALL knowledge triples in the form:
    (subject, predicate, object).

    Return them EXACTLY as a JSON list of objects:
    [
      {{"subject": "...", "predicate": "...", "object": "..."}},
      ...
    ]

    Be concise but do not miss important relations.{query_hint}

    Text:
    \"\"\"{text}\"\"\"
    """

    # Use standard OpenAI chat completions API
    api_client = _get_client()
    resp = api_client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )

    raw = resp.choices[0].message.content.strip()

    try:
        triples = json.loads(raw)
        if isinstance(triples, list):
            # Filter to only well-formed triples
            clean = []
            for t in triples:
                if not isinstance(t, dict):
                    continue
                s = t.get("subject")
                p = t.get("predicate")
                o = t.get("object")
                if s and p and o:
                    clean.append({"subject": s, "predicate": p, "object": o})
            return clean
        else:
            return []
    except json.JSONDecodeError:
        # Fallback: avoid breaking the pipeline
        return []
