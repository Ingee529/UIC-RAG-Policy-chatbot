"""
Enhanced Document Parser - Adapted from META notebook
Supports PDF, DOCX, and text files with improved heading detection
"""

import os
import re
import fitz  # PyMuPDF
import docx
from typing import List, Dict, Optional


def _split_paragraphs_with_spans(text: str) -> List[Dict]:
    """
    Split text into paragraphs with start/end char spans for traceability.
    Returns a list of dicts: {para_idx, start, end, text}
    """
    paragraphs = []
    cursor = 0
    para_idx = 0

    parts = re.split(r'\n\s*\n', text)  # split on blank lines

    for part in parts:
        part = part.strip()
        if not part:
            continue
        start = text.find(part, cursor)
        end = start + len(part)
        paragraphs.append({
            "para_idx": para_idx,
            "start": start,
            "end": end,
            "text": part
        })
        para_idx += 1
        cursor = end

    return paragraphs


def _is_major_pdf_heading(text: str, font_sizes: List[float], base_size: float) -> bool:
    """
    Conservative major-heading detector for PDFs.

    Detects:
      - Big titles with large fonts
      - Numbered sections (1. Something, 2) Something, 1.1 Subsection)
      - ALL CAPS short lines with larger fonts
    """
    text = text.strip()
    if not text:
        return False

    # Don't consider very long lines as headings
    if len(text) > 120:
        return False

    max_font = max(font_sizes) if font_sizes else base_size

    # Pattern for numbered sections: "1. Something", "2) Something", "1.1 Subsection"
    numbered_pattern = re.compile(r"^\d+(\.\d+)*[\.\)]\s+")

    # 1) Big title or very large text
    if max_font >= base_size * 1.7:
        return True

    # 2) Numbered sections with slightly larger font
    if numbered_pattern.match(text) and max_font >= base_size * 1.25:
        return True

    # 3) ALL CAPS, fairly short, and noticeably larger than body text
    if text.isupper() and len(text) < 80 and max_font >= base_size * 1.4:
        return True

    return False


def _merge_small_pdf_blocks(blocks: List[Dict], min_chars: int = 1500) -> List[Dict]:
    """
    Merge consecutive small blocks to reduce fragmentation.

    Strategy:
      - If current block and previous block share the same heading (or both None),
        and at least one is smaller than min_chars, merge them.
    """
    if not blocks:
        return blocks

    merged = [blocks[0]]

    for blk in blocks[1:]:
        last = merged[-1]

        same_heading = (blk.get("heading") == last.get("heading"))
        both_no_heading = (blk.get("heading") is None and last.get("heading") is None)

        if (same_heading or both_no_heading) and (
            len(last["text"]) < min_chars or len(blk["text"]) < min_chars
        ):
            # Merge blk into last
            separator = "\n\n"
            if last["text"] and last["text"][-1] not in ".!?":
                separator = " "
            
            new_text = (last["text"] + separator + blk["text"]).strip()
            last["text"] = new_text
            last["paragraphs"] = _split_paragraphs_with_spans(new_text)
        else:
            merged.append(blk)

    # Reassign block_idx to keep them contiguous
    for i, blk in enumerate(merged):
        blk["block_idx"] = i

    return merged


def parse_document(filepath: str) -> List[Dict]:
    """
    Parse a document and return structured blocks.

    Returns blocks with:
      - heading (str or None)
      - page (int or None) - first page where the block starts
      - block_idx (int)
      - text (combined text content)
      - paragraphs: [{para_idx, start, end, text}]
      - source_file: filename
    """
    blocks = []
    block_idx = 0
    ext = filepath.lower()
    filename = os.path.basename(filepath)

    # ---------------- DOCX ----------------
    if ext.endswith(".docx"):
        doc = docx.Document(filepath)
        current_heading = None
        current_text_parts = []

        def _flush():
            nonlocal block_idx, current_heading, current_text_parts
            if current_text_parts or current_heading:
                full_text = "\n\n".join(current_text_parts).strip()
                if full_text:
                    paragraph_spans = _split_paragraphs_with_spans(full_text)
                    blocks.append({
                        "heading": current_heading,
                        "page": None,
                        "block_idx": block_idx,
                        "text": full_text,
                        "paragraphs": paragraph_spans,
                        "source_file": filename
                    })
                    block_idx += 1
            current_heading = None
            current_text_parts = []

        for para in doc.paragraphs:
            text = para.text.strip()
            if not text:
                continue
            style = para.style.name if para.style else ""
            if style.lower().startswith("heading"):
                _flush()
                current_heading = text
            else:
                current_text_parts.append(text)

        _flush()

    # ---------------- PDF ----------------
    elif ext.endswith(".pdf"):
        doc = fitz.open(filepath)
        all_blocks = []

        # Pre-pass to estimate dominant font size (using mode, like notebook)
        font_sizes = []
        for page in doc:
            page_dict = page.get_text("dict")
            for block in page_dict.get("blocks", []):
                if block.get("type") == 0:  # text block
                    for line in block.get("lines", []):
                        for span in line.get("spans", []):
                            font_sizes.append(round(span.get("size", 11.0), 1))

        # Use mode (most frequent) as base_size, like notebook
        if font_sizes:
            base_size = max(set(font_sizes), key=font_sizes.count)
        else:
            base_size = 11.0

        # Per-page iteration with per-page flush (like notebook)
        for page in doc:
            page_number = page.number + 1
            page_dict = page.get_text("dict")

            # Per-page variables
            current_heading = None
            current_text_parts = []
            current_block_start_page = page_number

            def _flush_pdf():
                nonlocal block_idx, current_heading, current_text_parts, current_block_start_page
                if current_text_parts or current_heading:
                    full_text = " ".join(current_text_parts).strip()
                    if full_text:
                        paragraph_spans = _split_paragraphs_with_spans(full_text)
                        all_blocks.append({
                            "heading": current_heading,
                            "page": current_block_start_page,
                            "block_idx": block_idx,
                            "text": full_text,
                            "paragraphs": paragraph_spans,
                            "source_file": filename
                        })
                        block_idx += 1
                current_heading = None
                current_text_parts = []
                current_block_start_page = page_number

            for block in page_dict.get("blocks", []):
                if block.get("type") == 0:  # text block
                    # Extract text WITHOUT adding spaces/newlines (like notebook)
                    text_parts = []
                    block_fonts = []

                    for line in block.get("lines", []):
                        for span in line.get("spans", []):
                            span_text = span.get("text", "")
                            if span_text.strip():
                                text_parts.append(span_text)
                                block_fonts.append(span.get("size", base_size))

                    block_text = " ".join(text_parts).strip()  # Join spans with spaces
                    if not block_text:
                        continue

                    # Check if this block is a heading
                    is_heading = _is_major_pdf_heading(block_text, block_fonts, base_size)

                    if is_heading:
                        _flush_pdf()
                        current_heading = block_text.strip(": ")  # Strip colon like notebook
                    else:
                        current_text_parts.append(block_text)

            # Flush at end of each page (like notebook)
            _flush_pdf()

        # Merge small blocks
        all_blocks = _merge_small_pdf_blocks(all_blocks, min_chars=1500)
        blocks = all_blocks

    # ---------------- TXT ----------------
    elif ext.endswith(".txt"):
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        # Simple text parsing - treat the entire file as one block
        paragraph_spans = _split_paragraphs_with_spans(content)
        blocks.append({
            "heading": None,
            "page": None,
            "block_idx": 0,
            "text": content,
            "paragraphs": paragraph_spans,
            "source_file": filename
        })

    else:
        raise ValueError(f"Unsupported file format: {ext}")

    return blocks


def parse_directory(directory_path: str, extensions: Optional[List[str]] = None) -> Dict[str, List[Dict]]:
    """
    Parse all documents in a directory (recursively searches subdirectories).

    Args:
        directory_path: Path to directory containing documents
        extensions: List of file extensions to parse (default: ['.pdf', '.docx', '.txt'])

    Returns:
        Dictionary mapping filenames to lists of blocks
    """
    if extensions is None:
        extensions = ['.pdf', '.docx', '.txt']

    documents_blocks = {}

    if not os.path.exists(directory_path):
        raise FileNotFoundError(f"Directory not found: {directory_path}")

    # Walk through directory recursively
    for root, dirs, files in os.walk(directory_path):
        for filename in files:
            # Skip hidden files and check extension
            if filename.startswith('.'):
                continue
            if not any(filename.lower().endswith(ext) for ext in extensions):
                continue

            filepath = os.path.join(root, filename)
            try:
                blocks = parse_document(filepath)
                # Use relative path from input dir as key for better identification
                rel_path = os.path.relpath(filepath, directory_path)
                documents_blocks[rel_path] = blocks
                print(f"✅ Parsed {rel_path}: {len(blocks)} blocks")
            except Exception as e:
                print(f"❌ Error parsing {filename}: {e}")

    return documents_blocks


if __name__ == "__main__":
    # Test the parser
    import sys
    if len(sys.argv) > 1:
        test_file = sys.argv[1]
        blocks = parse_document(test_file)
        print(f"\nParsed {len(blocks)} blocks from {test_file}")
        for i, block in enumerate(blocks[:3]):
            print(f"\nBlock {i}:")
            print(f"  Heading: {block.get('heading')}")
            print(f"  Text length: {len(block.get('text', ''))}")
            print(f"  First 100 chars: {block.get('text', '')[:100]}")
