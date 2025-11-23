#!/usr/bin/env python3
"""
Test if backend data is properly set up for frontend

This script checks:
1. Required files exist
2. File formats are correct
3. Data can be loaded
4. Frontend can access the data
"""

import os
import json
import pickle
from pathlib import Path


def test_backend_data():
    """Test backend data setup"""

    print("🧪 Testing Backend Data Setup")
    print("=" * 60)

    target_dir = Path("embeddings_output/naive/naive_embedding")

    if not target_dir.exists():
        print(f"❌ Target directory does not exist: {target_dir}")
        print(f"\n📁 Please create the directory structure first:")
        print(f"   mkdir -p {target_dir}")
        return False

    print(f"✅ Target directory exists: {target_dir}")

    # Required files
    required_files = {
        "index.faiss": "FAISS vector index",
        "metadata.json": "Chunk metadata",
        "id_mapping.pkl": "ID mapping"
    }

    optional_files = {
        "document_list.json": "Document list (optional)"
    }

    all_good = True

    print(f"\n📋 Checking required files...")
    for filename, description in required_files.items():
        filepath = target_dir / filename
        if filepath.exists():
            size = filepath.stat().st_size
            size_mb = size / (1024 * 1024)
            print(f"   ✅ {filename:20s} ({size_mb:.2f} MB) - {description}")
        else:
            print(f"   ❌ {filename:20s} MISSING - {description}")
            all_good = False

    print(f"\n📋 Checking optional files...")
    for filename, description in optional_files.items():
        filepath = target_dir / filename
        if filepath.exists():
            size = filepath.stat().st_size
            size_kb = size / 1024
            print(f"   ✅ {filename:20s} ({size_kb:.2f} KB) - {description}")
        else:
            print(f"   ⚠️  {filename:20s} not found - {description}")

    if not all_good:
        print(f"\n❌ Missing required files!")
        print(f"\n📥 Please ensure your teammate's data is placed in:")
        print(f"   {target_dir.absolute()}")
        return False

    # Test loading files
    print(f"\n🔍 Testing file loading...")

    # Test metadata.json
    try:
        metadata_path = target_dir / "metadata.json"
        with open(metadata_path, 'r', encoding='utf-8') as f:
            metadata = json.load(f)

        chunk_count = len(metadata)
        print(f"   ✅ metadata.json loaded: {chunk_count} chunks")

        # Check format
        if chunk_count > 0:
            first_key = list(metadata.keys())[0]
            first_chunk = metadata[first_key]

            required_fields = ["chunk_id", "text", "document_id", "content_type",
                             "primary_category", "summary"]
            missing_fields = [f for f in required_fields if f not in first_chunk]

            if missing_fields:
                print(f"   ⚠️  Missing fields in metadata: {missing_fields}")
            else:
                print(f"   ✅ Metadata format valid")
                print(f"      Sample chunk_id: {first_chunk['chunk_id']}")
                print(f"      Sample category: {first_chunk['primary_category']}")

    except Exception as e:
        print(f"   ❌ Error loading metadata.json: {e}")
        all_good = False

    # Test id_mapping.pkl
    try:
        id_mapping_path = target_dir / "id_mapping.pkl"
        with open(id_mapping_path, 'rb') as f:
            id_mapping = pickle.load(f)

        print(f"   ✅ id_mapping.pkl loaded")

        if "index_to_id" in id_mapping and "id_to_index" in id_mapping:
            mapping_count = len(id_mapping["index_to_id"])
            print(f"      Mappings: {mapping_count}")
        else:
            print(f"   ⚠️  Unexpected id_mapping format")

    except Exception as e:
        print(f"   ❌ Error loading id_mapping.pkl: {e}")
        all_good = False

    # Test FAISS index
    try:
        import faiss

        index_path = target_dir / "index.faiss"
        index = faiss.read_index(str(index_path))

        vector_count = index.ntotal
        dimension = index.d

        print(f"   ✅ FAISS index loaded")
        print(f"      Vectors: {vector_count}")
        print(f"      Dimension: {dimension}")

        # Check if counts match
        if vector_count != chunk_count:
            print(f"   ⚠️  Warning: FAISS vectors ({vector_count}) != metadata chunks ({chunk_count})")
        else:
            print(f"   ✅ Vector and chunk counts match")

    except ImportError:
        print(f"   ⚠️  faiss not installed (optional for this test)")
    except Exception as e:
        print(f"   ❌ Error loading FAISS index: {e}")
        all_good = False

    # Test frontend import
    print(f"\n🔌 Testing frontend compatibility...")
    try:
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent / "frontend"))

        from rag_backend import get_backend

        backend = get_backend()
        print(f"   ✅ Backend loaded by frontend")
        print(f"      Index vectors: {backend.index.ntotal if hasattr(backend, 'index') else 'N/A'}")

        # Try a test query
        try:
            test_query = "What are custodial funds?"
            results = backend.retrieve(test_query, top_k=3)
            print(f"   ✅ Test query successful")
            print(f"      Results: {len(results)}")
            if results:
                print(f"      Top score: {results[0]['score']:.4f}")
        except Exception as e:
            print(f"   ⚠️  Test query failed: {e}")

    except Exception as e:
        print(f"   ⚠️  Frontend test skipped: {e}")

    # Final summary
    print(f"\n" + "=" * 60)
    if all_good:
        print("✅ All tests passed!")
        print("\n🎯 Ready to use with frontend:")
        print("   cd ../frontend")
        print("   streamlit run app.py")
    else:
        print("❌ Some tests failed")
        print("\n🔧 Troubleshooting:")
        print("   1. Check if all required files are present")
        print("   2. Run: python convert_mgr_to_frontend.py")
        print("   3. Ask teammate for missing files")

    return all_good


if __name__ == "__main__":
    success = test_backend_data()

    if not success:
        exit(1)
