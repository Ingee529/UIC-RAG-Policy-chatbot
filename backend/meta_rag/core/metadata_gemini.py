"""
Metadata Extraction using Gemini - Compatible with META notebook format
Extracts the same 12 metadata fields as Mistral version for fair comparison
"""

import os
import json
import time
from typing import Dict, List, Optional
import google.generativeai as genai
from tqdm import tqdm


class GeminiMetadataExtractor:
    """Extract structured metadata from policy text using Gemini (gemini-flash-latest)"""

    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-flash-latest"):
        """
        Initialize the metadata extractor.

        Args:
            api_key: Gemini API key (if None, reads from environment)
            model: Gemini model to use (default: gemini-flash-latest)
        """
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not provided and not found in environment")

        # Configure Gemini
        genai.configure(api_key=self.api_key)

        # Initialize model
        self.model = genai.GenerativeModel(
            model_name=model,
            generation_config={
                "temperature": 0.3,
                "top_p": 0.95,
                "max_output_tokens": 2048,
            }
        )
        self.model_name = model

        print(f"[Gemini] Client initialized: {model}")

    def extract_metadata(self, chunk_text: str) -> Dict:
        """
        Call Gemini API to extract specified metadata from chunk_text, return parsed JSON.

        This extracts the EXACT same 12 fields as the Mistral version for fair comparison.
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

        prompt = f"""Analyze this policy/financial documentation text and extract metadata.

TEXT:
\"\"\"
{chunk_text}
\"\"\"

Extract the following information and output as JSON with these exact keys:
- summary: a brief summary of the text
- keywords: a list of important keywords or phrases
- entities: a list of named entities (persons, organizations, etc.) mentioned
- effective_date: the effective or issuance date of the policy (if present)
- fund_codes: any fund or account codes mentioned (if any)
- ilcs_citations: any ILCS (Illinois Compiled Statutes) citations (e.g., '5 ILCS 430/...') mentioned
- title: the title of the policy or document (if present)
- category: the general category of the policy (e.g., Financial, HR, Academic)
- sub_category: a more specific sub-category of the policy (if applicable)
- topic: the main topic or subject of the policy text
- year: the year associated with the policy (if present)
- content_type: the type of content (e.g., policy, guideline, procedure, report)

If a field is not found or applicable, use an empty string or empty list.
Return ONLY valid JSON, nothing else. Do not include markdown code blocks or explanations."""

        expected_keys = [
            "summary", "keywords", "entities", "effective_date", "fund_codes",
            "ilcs_citations", "title", "category", "sub_category", "topic",
            "year", "content_type"
        ]

        # Retry logic for API calls
        max_retries = 3
        retry_delay = 2.0
        
        for attempt in range(max_retries):
            try:
                # Call API (timeout is handled by the client library)
                response = self.model.generate_content(prompt)
                
                # Handle Gemini API response (may have .text or .candidates[0].content.parts[0].text)
                if hasattr(response, 'text') and response.text:
                    output_text = response.text.strip()
                elif hasattr(response, 'candidates') and response.candidates:
                    # Alternative response format
                    output_text = response.candidates[0].content.parts[0].text.strip()
                else:
                    raise ValueError(f"Unexpected response format: {response}")
                
                if not output_text:
                    raise ValueError("Empty response from Gemini API")
                
                # Success, break out of retry loop
                break
                
            except Exception as api_error:
                if attempt < max_retries - 1:
                    error_msg = str(api_error)
                    if "timeout" in error_msg.lower() or "deadline" in error_msg.lower():
                        print(f"[Gemini extract_metadata] Timeout on attempt {attempt + 1}/{max_retries}, retrying in {retry_delay}s...")
                        time.sleep(retry_delay)
                        retry_delay *= 2  # Exponential backoff
                        continue
                    elif "quota" in error_msg.lower() or "rate limit" in error_msg.lower():
                        print(f"[Gemini extract_metadata] Rate limit on attempt {attempt + 1}/{max_retries}, waiting {retry_delay * 2}s...")
                        time.sleep(retry_delay * 2)
                        retry_delay *= 2
                        continue
                    else:
                        print(f"[Gemini extract_metadata] Error on attempt {attempt + 1}/{max_retries}: {error_msg}, retrying...")
                        time.sleep(retry_delay)
                        continue
                else:
                    # Last attempt failed, raise the error
                    raise
        
        # If we get here, API call succeeded and output_text is defined
        try:
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
            print(f"[Gemini extract_metadata] JSON decode error: {e}")
            if 'output_text' in locals():
                print(f"[Gemini extract_metadata] Problematic output (truncated): {output_text[:300]}...")
            else:
                print(f"[Gemini extract_metadata] No output_text available")
        except Exception as e:
            print(f"[Gemini extract_metadata] Unexpected error: {e}")
            print(f"[Gemini extract_metadata] Error type: {type(e).__name__}")
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
        delay: float = 0.5,
        batch_size: int = 10,
        verbose: bool = True
    ) -> List[Dict]:
        """
        Enrich chunks with metadata from Gemini.

        Args:
            chunks: List of chunk dictionaries
            delay: Delay between API calls (seconds) - Gemini is faster, so 0.5s default
            batch_size: Number of chunks to process before showing progress (unused, kept for compatibility)
            verbose: Print progress messages

        Returns:
            List of enriched chunks
        """
        enriched_chunks = []
        total = len(chunks)

        # Use tqdm progress bar for visual feedback
        iterator = tqdm(chunks, desc="🔍 Extracting metadata (Gemini)", unit="chunk") if verbose else chunks

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

            # Rate limiting (Gemini is faster than Mistral)
            if delay > 0:
                time.sleep(delay)

        if verbose:
            print(f"✅ Enriched {len(enriched_chunks)} chunks with metadata (Gemini)")

        return enriched_chunks


def extract_metadata_batch(
    chunks: List[Dict],
    api_key: Optional[str] = None,
    model: str = "gemini-flash-latest",
    delay: float = 0.5,
    batch_size: int = 10
) -> List[Dict]:
    """
    Convenience function to extract metadata for a batch of chunks.

    Args:
        chunks: List of chunk dictionaries
        api_key: Gemini API key
        model: Gemini model to use
        delay: Delay between API calls
        batch_size: Progress update frequency

    Returns:
        List of enriched chunks
    """
    extractor = GeminiMetadataExtractor(api_key=api_key, model=model)
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

    # You need to set GEMINI_API_KEY environment variable
    if os.getenv("GEMINI_API_KEY"):
        extractor = GeminiMetadataExtractor()
        metadata = extractor.extract_metadata(sample_chunk["text"])

        print("Extracted Metadata:")
        print(json.dumps(metadata, indent=2))
    else:
        print("⚠️  Set GEMINI_API_KEY environment variable to test metadata extraction")
