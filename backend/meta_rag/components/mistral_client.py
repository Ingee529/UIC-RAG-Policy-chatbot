"""
Mistral Client Setup - Extracted from META notebook
Provides _call_mistral_chat function for answer generation
"""

# --- Mistral setup (works across recent SDKs) ---
import os, json, time
from mistralai.client import MistralClient

# Optional Colab compat: gracefully fall back to env var if google.colab.userdata isn't available
try:
    from google.colab import userdata  # type: ignore
    _maybe_key = userdata.get("MISTRAL_API_KEY")
except Exception:
    _maybe_key = None

# Prefer env var, else colab userdata, else empty (will error clearly if not set)
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY") or _maybe_key or ""
MODEL_NAME = "open-mistral-7b"  # <-- use a valid model for your account

if not MISTRAL_API_KEY:
    raise RuntimeError("MISTRAL_API_KEY is not set. Export it in your environment or Colab userdata.")

mistral_client = MistralClient(api_key=MISTRAL_API_KEY)
print(f"[Mistral] Client initialized: {type(mistral_client)} | Model: {MODEL_NAME}")

def _call_mistral_chat(messages, model=MODEL_NAME, **kw):
    """
    Call Mistral chat with a list of messages:
        messages = [
            {"role": "system", "content": "..."},
            {"role": "user",   "content": "..."}
        ]
    Tries the common method shapes across SDK versions.
    """
    # Guard: messages must be a list[dict] (role/content)
    if not (isinstance(messages, (list, tuple)) and all(isinstance(m, dict) for m in messages)):
        raise TypeError("`messages` must be a list of dicts like "
                        "[{'role':'system','content':'...'}, {'role':'user','content':'...'}]")

    # Newer SDKs: client.chat(...)
    try:
        return mistral_client.chat(model=model, messages=messages, **kw)
    except TypeError:
        # Some SDKs: client.chat.complete(...)
        return mistral_client.chat.complete(model=model, messages=messages, **kw)

def _extract_text_from_response(resp):
    """
    Normalize different response shapes into a text string.
    Returns "" if no text was found.
    """
    # Already a string
    if isinstance(resp, str):
        return resp.strip()

    # Common SDK object paths
    try:
        return resp.choices[0].message.content.strip()
    except Exception:
        pass
    try:
        return resp["choices"][0]["message"]["content"].strip()
    except Exception:
        pass

    # Some SDKs stream or keep delta/content on choices[0].delta.content
    try:
        return resp.choices[0].delta.content.strip()
    except Exception:
        pass
    try:
        return resp["choices"][0]["delta"]["content"].strip()
    except Exception:
        pass

    # Fallback to string
    try:
        return str(resp).strip()
    except Exception:
        return ""

import json
import time

def extract_metadata(chunk_text):
    """Call Mistral API to extract specified metadata from chunk_text, return parsed JSON."""
    chunk_text = (chunk_text or "").strip()

    # Skip very short / useless chunks to save time and tokens
    if len(chunk_text) < 50:
        return {
            "summary": "",
            "keywords": [],
            "entities": [],
            "effective_date": "",
            "fund_codes": [],
            "ilcs_citations": [],
            "title": "",
            "category": "",
            "sub_category": "",
            "topic": "",
            "year": "",
            "content_type": ""
        }

    system_prompt = (
        "You are a helpful assistant that extracts specified metadata from policy text. "
        "Always output JSON only."
    )
    user_prompt = (
        "Text:\n\"\"\"\n" + chunk_text + "\n\"\"\"\n"
        "Extract the following information and output as JSON with keys: "
        "summary, keywords, entities, effective_date, fund_codes, ilcs_citations, title, "
        "category, sub_category, topic, year, content_type.\n"
        "- summary: a brief summary of the text\n"
        "- keywords: a list of important keywords or phrases\n"
        "- entities: a list of named entities (persons, organizations, etc.) mentioned\n"
        "- effective_date: the effective or issuance date of the policy (if present)\n"
        "- fund_codes: any fund or account codes mentioned (if any)\n"
        "- ilcs_citations: any ILCS (Illinois Compiled Statutes) citations (e.g., '5 ILCS 430/...') mentioned\n"
        "- title: the title of the policy or document (if present)\n"
        "- category: the general category of the policy (e.g., Financial, HR, Academic)\n"
        "- sub_category: a more specific sub-category of the policy (if applicable)\n"
        "- topic: the main topic or subject of the policy text\n"
        "- year: the year associated with the policy (if present)\n"
        "- content_type: the type of content (e.g., policy, guideline, procedure, report)\n"
        "If a field is not found or applicable, use an empty string or empty list. JSON only, no explanation."
    )

    expected_keys = [
        "summary", "keywords", "entities", "effective_date", "fund_codes",
        "ilcs_citations", "title", "category", "sub_category", "topic",
        "year", "content_type"
    ]

    try:
        resp = _call_mistral_chat(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_prompt},
            ],
            model=MODEL_NAME
        )
        output_text = _extract_text_from_response(resp).strip()

        # Clean optional ``` fences
        if output_text.startswith("```json"):
            output_text = output_text[len("```json"):].strip()
        elif output_text.startswith("```"):
            output_text = output_text[len("```"):].strip()
        if output_text.endswith("```"):
            output_text = output_text[:-3].strip()

        # ---- KEY FIX: isolate the first JSON object only ----
        start = output_text.find("{")
        end = output_text.rfind("}")
        if start != -1 and end != -1 and end > start:
            json_str = output_text[start:end+1]
        else:
            json_str = output_text  # fallback, may still be pure JSON

        metadata = json.loads(json_str)

        # Ensure all expected keys exist with sane defaults
        for k in expected_keys:
            if k not in metadata:
                metadata[k] = [] if k in ["keywords", "entities", "fund_codes", "ilcs_citations"] else ""

        return metadata

    except json.JSONDecodeError as e:
        print(f"[extract_metadata] JSON decode error: {e}")
        print(f"[extract_metadata] Problematic output (truncated): {output_text[:300]}...")
    except Exception as e:
        print(f"[extract_metadata] Unexpected error: {e}")

    # Fallback on any error
    return {
        "summary": "",
        "keywords": [],
        "entities": [],
        "effective_date": "",
        "fund_codes": [],
        "ilcs_citations": [],
        "title": "",
        "category": "",
        "sub_category": "",
        "topic": "",
        "year": "",
        "content_type": ""
    }
