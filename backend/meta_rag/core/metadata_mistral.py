"""
Metadata Extraction using Mistral - Exact implementation from META notebook
Extracts structured metadata from policy text chunks
"""

import os
import json
import time
from typing import Dict, List, Optional
from mistralai.client import MistralClient
from tqdm import tqdm


class MetadataExtractor:
    """Extract structured metadata from policy text using Mistral open-mistral-7b"""

    def __init__(self, api_key: Optional[str] = None, model: str = "open-mistral-7b"):
        """
        Initialize the metadata extractor.

        Args:
            api_key: Mistral API key (if None, reads from environment)
            model: Mistral model to use (default: open-mistral-7b)
        """
        self.api_key = api_key or os.getenv("MISTRAL_API_KEY")
        if not self.api_key:
            raise ValueError("MISTRAL_API_KEY not provided and not found in environment")

        self.client = MistralClient(api_key=self.api_key)
        self.model = model

        print(f"[Mistral] Client initialized: {type(self.client)} | Model: {model}")

    def _call_mistral_chat(self, messages, **kw):
        """
        Call Mistral chat with a list of messages.
        Tries the common method shapes across SDK versions.
        """
        # Guard: messages must be a list[dict] (role/content)
        if not (isinstance(messages, (list, tuple)) and all(isinstance(m, dict) for m in messages)):
            raise TypeError("`messages` must be a list of dicts like "
                            "[{'role':'system','content':'...'}, {'role':'user','content':'...'}]")

        # Newer SDKs: client.chat(...)
        try:
            return self.client.chat(model=self.model, messages=messages, **kw)
        except TypeError:
            # Some SDKs: client.chat.complete(...)
            return self.client.chat.complete(model=self.model, messages=messages, **kw)

    def _extract_text_from_response(self, resp):
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

    def extract_metadata(self, chunk_text: str) -> Dict:
        """
        Call Mistral API to extract specified metadata from chunk_text, return parsed JSON.

        This is the EXACT implementation from the META notebook.
        """
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
            resp = self._call_mistral_chat(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": user_prompt},
                ]
            )
            output_text = self._extract_text_from_response(resp).strip()

            # Clean optional ``` fences
            if output_text.startswith("```json"):
                output_text = output_text[len("```json"):].strip()
            elif output_text.startswith("```"):
                output_text = output_text[len("```"):].strip()
            if output_text.endswith("```"):
                output_text = output_text[:-3].strip()

            # KEY FIX: isolate the first JSON object only
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
            import traceback
            traceback.print_exc()

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

    def enrich_chunks(
        self,
        chunks: List[Dict],
        delay: float = 1.0,
        batch_size: int = 10,
        verbose: bool = True
    ) -> List[Dict]:
        """
        Enrich chunks with metadata from Mistral.

        Args:
            chunks: List of chunk dictionaries
            delay: Delay between API calls (seconds)
            batch_size: Number of chunks to process before showing progress (unused, kept for compatibility)
            verbose: Print progress messages

        Returns:
            List of enriched chunks
        """
        enriched_chunks = []
        total = len(chunks)

        # Use tqdm progress bar for visual feedback
        iterator = tqdm(chunks, desc="🔍 Extracting metadata", unit="chunk") if verbose else chunks

        for chunk in iterator:
            text = chunk.get("text", "")
            if not text:
                enriched_chunks.append(chunk)
                continue

            # Extract metadata
            metadata = self.extract_metadata(text)

            # Merge metadata into chunk
            enriched_chunk = {**chunk, **metadata}
            enriched_chunks.append(enriched_chunk)

            # Rate limiting
            if delay > 0:
                time.sleep(delay)

        if verbose:
            print(f"✅ Enriched {len(enriched_chunks)} chunks with metadata")

        return enriched_chunks


def extract_metadata_batch(
    chunks: List[Dict],
    api_key: Optional[str] = None,
    model: str = "open-mistral-7b",
    delay: float = 1.0,
    batch_size: int = 10
) -> List[Dict]:
    """
    Convenience function to extract metadata for a batch of chunks.

    Args:
        chunks: List of chunk dictionaries
        api_key: Mistral API key
        model: Mistral model to use
        delay: Delay between API calls
        batch_size: Progress update frequency

    Returns:
        List of enriched chunks
    """
    extractor = MetadataExtractor(api_key=api_key, model=model)
    return extractor.enrich_chunks(chunks, delay=delay, batch_size=batch_size)


if __name__ == "__main__":
    # Test metadata extraction
    sample_chunk = {
        "text": """
        The University of Illinois System must publish an annual financial report.
        The report contains basic financial statements, supplementary schedules,
        and the independent auditor's opinion issued by the Special Assistant Auditors
        for the State Auditor General. This requirement is outlined in the Business
        and Finance Policies and Procedures (BFPP) Section 1.1.
        """,
        "doc": "test_document.txt",
        "heading": "Annual Financial Report Requirements"
    }

    # You need to set MISTRAL_API_KEY environment variable
    if os.getenv("MISTRAL_API_KEY"):
        extractor = MetadataExtractor()
        metadata = extractor.extract_metadata(sample_chunk["text"])

        print("Extracted Metadata:")
        print(json.dumps(metadata, indent=2))
    else:
        print("⚠️  Set MISTRAL_API_KEY environment variable to test metadata extraction")
