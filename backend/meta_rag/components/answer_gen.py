"""
Answer Generation with Citations - Extracted from META notebook
Uses Mistral for generating final answers with source citations
"""

# --- Enhanced answer + citations block (fixed) ---
def generate_answer_with_citations_v2(query, chunk_indices, call_llm_fn=None):
    """
    Generate an answer AND a nicely formatted 'Sources' block.

    Returns
    -------
    answer_text : str
        The LLM's answer text (which should include [1], [2], ... citations).
    sources_block : str
        Human-readable mapping of [i] -> Document title/name, page range, and source path/URL.
    """

    # 1) Build the numbered context that the LLM will see
    context_lines = []
    for i, idx in enumerate(chunk_indices, start=1):
        ch = all_chunks[idx]
        content = ch.get("text", "").strip()
        context_lines.append(f"[{i}] {content}")
    context_str = "\n".join(context_lines)

    # 2) Build the prompt
    system_msg = "You are a helpful policy QA assistant. Answer questions using the provided documents."
    user_msg = (
        f"{context_str}\n\n"
        f"Question: {query}\n"
        "Answer concisely and cite sources by the bracketed numbers [1], [2], [3] that correspond to the snippets above. "
        "Only cite claims you can support from the provided snippets. If unsure, say you don't know."
    )

    # 3) Call the LLM with a PROPER messages=[...] list
    messages = [
        {"role": "system", "content": system_msg},
        {"role": "user",   "content": user_msg},
    ]

    if call_llm_fn is None:
        resp = _call_mistral_chat(messages, model=MODEL_NAME)
    else:
        # If you pass a custom fn, it must accept the same messages list
        resp = call_llm_fn(messages, model=MODEL_NAME)

    # Normalize to text (works with different SDK return shapes)
    answer_text = _extract_text_from_response(resp)

    # 4) Build a nice "Sources" block mapping [i] -> metadata
    lines = ["Sources used:"]
    for i, idx in enumerate(chunk_indices, start=1):
        ch = all_chunks[idx]
        # Try several common metadata keys (adjust to your schema)
        doc_name = (
            ch.get("doc_name")
            or ch.get("title")
            or ch.get("doc_title")
            or ch.get("file_name")
            or "Unknown document"
        )
        page_start = ch.get("page_start")
        page_end = ch.get("page_end")
        single_page = ch.get("page")
        if page_start is not None and page_end is not None:
            page_part = f" (pages {page_start}–{page_end})"
        elif page_start is not None:
            page_part = f" (page {page_start})"
        elif single_page is not None:
            page_part = f" (page {single_page})"
        else:
            page_part = ""

        category = ch.get("category") or ""
        subcat = ch.get("sub_category") or ch.get("subcat") or ""
        cat_part = f" — {category}/{subcat}" if (category or subcat) else ""

        src = ch.get("source_url") or ch.get("pdf_path") or ch.get("source") or "N/A"

        lines.append(f"[{i}] {doc_name}{page_part}{cat_part}")
        lines.append(f"     Source: {src}")

    sources_block = "\n".join(lines)
    return answer_text, sources_block
