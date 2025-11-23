"""
Chunking Strategy - EXACT implementation from META notebook
Hybrid strategy using structural info (headings, paragraphs) with natural breakpoints
"""

from typing import List, Dict


def chunk_blocks(doc_name: str, blocks: List[Dict], max_size: int = 3000, overlap: int = 200) -> List[Dict]:
    """
    Chunk parsed blocks into overlapping text chunks with rich metadata.
    EXACT implementation from META notebook.

    Hybrid strategy:
      - Use structural info from parse_document (heading + paragraphs).
      - Inside each block, split by natural breakpoints (double newline, newline, sentence, space)
        with a hard cap at max_size.
      - Maintain overlap at character level.
      - Preserve traceability to paragraphs and pages.

    Args:
        doc_name: Document name
        blocks: List of blocks from parse_document
        max_size: Maximum chunk size in characters (default: 3000, as used in notebook)
        overlap: Character overlap between chunks (default: 200)

    Returns:
        List of chunk dictionaries with metadata
    """
    def _find_natural_split(text, start, hard_end):
        """
        Find a good split location between [start, hard_end],
        preferring natural separators, else fall back to hard_end.
        """
        split_at = hard_end
        for sep in ["\n\n", "\n", ". ", " "]:
            idx = text.rfind(sep, start, hard_end)
            if idx != -1 and idx + len(sep) <= hard_end:
                split_at = idx + len(sep)
                break
        return split_at

    chunks = []

    for block_idx, block in enumerate(blocks):
        heading = block.get("heading")
        page = block.get("page", None)
        paragraphs = block.get("paragraphs", [])

        # --- Build a single block_text and record spans for each paragraph ---

        segments = []  # list of {kind: 'heading'/'para', 'para_idx': int|None, 'start': int, 'end': int}
        pieces = []
        offset = 0

        # Optional heading as its own segment (for context)
        if heading:
            h_text = str(heading).strip()
            if h_text:
                pieces.append(h_text)
                start = offset
                end = start + len(h_text)
                segments.append({
                    "kind": "heading",
                    "para_idx": None,
                    "start": start,
                    "end": end
                })
                offset = end

        # Add paragraphs separated by "\n\n"
        for i, p in enumerate(paragraphs):
            p_text = p["text"] if isinstance(p, dict) else str(p)
            p_text = p_text.strip()
            if not p_text:
                continue

            if pieces:
                pieces.append("\n\n")
                offset += 2  # for "\n\n"

            start = offset
            pieces.append(p_text)
            end = start + len(p_text)

            segments.append({
                "kind": "para",
                "para_idx": i,
                "start": start,
                "end": end
            })
            offset = end

        block_text = "".join(pieces).strip()
        if not block_text:
            continue

        text_len = len(block_text)

        # Pre-compute paragraph-only spans for traceability
        para_spans = [
            (seg["start"], seg["end"], seg["para_idx"])
            for seg in segments
            if seg["kind"] == "para"
        ]

        # --- Slide through block_text to create chunks ---

        pos = 0
        while pos < text_len:
            hard_end = min(text_len, pos + max_size)
            split_at = _find_natural_split(block_text, pos, hard_end)

            # Fallback in case something goes weird
            if split_at <= pos:
                split_at = hard_end

            chunk_text = block_text[pos:split_at].strip()
            if not chunk_text:
                # Move forward to avoid infinite loop
                pos = hard_end
                continue

            chunk_start = pos
            chunk_end = split_at

            # Determine all paragraph indices that intersect this chunk
            touched_paras = []
            primary_para_idx = None
            for (p_start, p_end, p_idx) in para_spans:
                if p_start < chunk_end and p_end > chunk_start:  # intervals overlap
                    touched_paras.append(p_idx)
                    if primary_para_idx is None:
                        primary_para_idx = p_idx

            chunk_meta = {
                "doc": doc_name,
                "page": page,
                "heading": heading,
                "block_index": block_idx,
                # first paragraph index overlapped by this chunk (for backward compatibility)
                "paragraph_index": primary_para_idx,
                # all paragraph indices overlapped by this chunk
                "paragraph_indices": touched_paras,
                # char span inside this block_text
                "char_span": [chunk_start, chunk_end],
                "text": chunk_text
            }
            chunks.append(chunk_meta)

            # Advance with overlap (character-level)
            next_pos = split_at - overlap
            pos = next_pos if next_pos > pos else split_at
            if pos >= text_len:
                break

    return chunks


if __name__ == "__main__":
    # Test chunking with sample block
    sample_blocks = [
        {
            "heading": "Financial Policy",
            "page": 1,
            "paragraphs": [
                {"text": "The University of Illinois System follows generally accepted accounting principles."},
                {"text": "All units must maintain proper financial records. Regular audits are conducted to ensure compliance."},
                {"text": "Budget planning is a critical component of fiscal responsibility. Each department must submit annual budget proposals."}
            ]
        }
    ]

    print("Testing hybrid chunking strategy (EXACT from notebook):\n")
    chunks = chunk_blocks("test_doc.pdf", sample_blocks, max_size=100, overlap=20)

    for i, chunk in enumerate(chunks, 1):
        print(f"Chunk {i}:")
        print(f"  Heading: {chunk['heading']}")
        print(f"  Page: {chunk['page']}")
        print(f"  Text: {chunk['text'][:100]}...")
        print(f"  Char span: {chunk['char_span']}")
        print()
