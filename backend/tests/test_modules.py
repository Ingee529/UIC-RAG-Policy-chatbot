"""
Test script for all new backend modules
Run this to verify everything is working before building the full index
"""

import os
import sys
from pathlib import Path


def test_parser():
    """Test document parser"""
    print("\n" + "="*60)
    print("Testing Document Parser")
    print("="*60)

    try:
        from meta_rag.core.parser import parse_directory

        input_dir = Path(__file__).parent / "input_files"
        if not input_dir.exists():
            print(f"❌ Input directory not found: {input_dir}")
            return False

        docs = parse_directory(str(input_dir))

        if not docs:
            print("⚠️  No documents parsed")
            return False

        print(f"\n✅ Successfully parsed {len(docs)} documents:")
        for name, blocks in list(docs.items())[:5]:
            print(f"  - {name}: {len(blocks)} blocks")

        # Show sample block
        first_doc_blocks = list(docs.values())[0]
        if first_doc_blocks:
            sample_block = first_doc_blocks[0]
            print(f"\n📄 Sample block:")
            print(f"  Heading: {sample_block.get('heading', 'None')}")
            print(f"  Text length: {len(sample_block.get('text', ''))}")
            print(f"  Text preview: {sample_block.get('text', '')[:150]}...")

        return True

    except Exception as e:
        print(f"❌ Parser test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_chunking():
    """Test chunking strategies"""
    print("\n" + "="*60)
    print("Testing Chunking Strategies")
    print("="*60)

    try:
        from meta_rag.components.chunking import recursive_chunk_text, semantic_chunk_text
        from sentence_transformers import SentenceTransformer

        sample_text = """
        The University of Illinois System follows generally accepted accounting principles.
        All units must maintain proper financial records. Regular audits are conducted to ensure compliance.
        Budget planning is a critical component of fiscal responsibility. Each department must submit
        annual budget proposals. These proposals are reviewed by the comptroller's office.
        The financial health of each unit is monitored quarterly. Deficits must be reported immediately.
        Units are required to develop remediation plans for any budget shortfalls.
        """

        # Test recursive chunking
        print("\n1️⃣ Testing recursive chunking...")
        recursive_chunks = recursive_chunk_text(sample_text, max_size=30, overlap=5)
        print(f"  ✅ Generated {len(recursive_chunks)} chunks")
        print(f"  First chunk: {recursive_chunks[0][:80]}...")

        # Test semantic chunking
        print("\n2️⃣ Testing semantic chunking...")
        print("  Loading embedding model...")
        model = SentenceTransformer('all-MiniLM-L6-v2')
        semantic_chunks = semantic_chunk_text(sample_text, max_size=30, model=model)
        print(f"  ✅ Generated {len(semantic_chunks)} chunks")
        print(f"  First chunk: {semantic_chunks[0][:80]}...")

        return True

    except Exception as e:
        print(f"❌ Chunking test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_metadata_extraction():
    """Test metadata extraction (requires OpenAI API key)"""
    print("\n" + "="*60)
    print("Testing Metadata Extraction")
    print("="*60)

    # Check for API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("⚠️  OPENAI_API_KEY not found in environment")
        print("⚠️  Skipping metadata extraction test")
        print("💡 Set OPENAI_API_KEY in .env to test this feature")
        return None  # Not a failure, just skipped

    try:
        from meta_rag.core.metadata import MetadataExtractor

        sample_text = """
        The University of Illinois System must publish an annual financial report.
        The report contains basic financial statements, supplementary schedules,
        and the independent auditor's opinion issued by the Special Assistant Auditors
        for the State Auditor General. This requirement is outlined in the Business
        and Finance Policies and Procedures (BFPP) Section 1.1 and is effective
        for fiscal year 2024.
        """

        print("🔑 OpenAI API key found")
        print("📡 Extracting metadata...")

        extractor = MetadataExtractor()
        metadata = extractor.extract_metadata(sample_text)

        print(f"\n✅ Metadata extracted successfully:")
        print(f"  Summary: {metadata.get('summary', 'N/A')[:100]}...")
        print(f"  Keywords: {metadata.get('keywords', [])}")
        print(f"  Category: {metadata.get('category', 'N/A')}")
        print(f"  Content Type: {metadata.get('content_type', 'N/A')}")

        return True

    except Exception as e:
        print(f"❌ Metadata extraction test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_integration():
    """Test full integration"""
    print("\n" + "="*60)
    print("Testing Integration")
    print("="*60)

    try:
        from meta_rag.core.parser import parse_directory
        from meta_rag.components.chunking import chunk_all_documents
        from sentence_transformers import SentenceTransformer

        print("1️⃣ Parsing documents...")
        input_dir = Path(__file__).parent / "input_files"
        docs = parse_directory(str(input_dir))
        print(f"  ✅ Parsed {len(docs)} documents")

        print("\n2️⃣ Loading embedding model...")
        model = SentenceTransformer('all-MiniLM-L6-v2')
        print("  ✅ Model loaded")

        print("\n3️⃣ Chunking documents...")
        chunks = chunk_all_documents(docs, model=model, strategy="auto")
        print(f"  ✅ Generated {len(chunks)} chunks")

        if chunks:
            sample_chunk = chunks[0]
            print(f"\n📄 Sample chunk:")
            print(f"  Document: {sample_chunk.get('doc', 'N/A')}")
            print(f"  Heading: {sample_chunk.get('heading', 'None')}")
            print(f"  Tokens: {sample_chunk.get('tokens', 0)}")
            print(f"  Text: {sample_chunk.get('text', '')[:100]}...")

        return True

    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("🧪 MetaRAG Backend Module Tests")
    print("="*60)

    # Load environment variables
    from dotenv import load_dotenv
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        print(f"✅ Loaded environment from: {env_path}")
    else:
        print(f"⚠️  No .env file found at: {env_path}")

    results = {}

    # Run tests
    results['parser'] = test_parser()
    results['chunking'] = test_chunking()
    results['metadata'] = test_metadata_extraction()
    results['integration'] = test_integration()

    # Summary
    print("\n" + "="*60)
    print("📊 Test Summary")
    print("="*60)

    for test_name, result in results.items():
        if result is True:
            status = "✅ PASS"
        elif result is False:
            status = "❌ FAIL"
        else:
            status = "⚠️  SKIP"
        print(f"{test_name.capitalize():20s}: {status}")

    # Overall result
    failures = [name for name, result in results.items() if result is False]

    print("\n" + "="*60)
    if not failures:
        print("✅ All tests passed! Ready to build the index.")
        print("\nNext steps:")
        print("  1. If you haven't set OPENAI_API_KEY, add it to .env")
        print("  2. Run: python build_index.py --no-metadata  (quick test)")
        print("  3. Run: python build_index.py  (full build with metadata)")
        return 0
    else:
        print(f"❌ {len(failures)} test(s) failed: {', '.join(failures)}")
        print("\nPlease fix the issues before building the index.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
