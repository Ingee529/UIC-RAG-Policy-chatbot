#!/usr/bin/env python3
"""
簡單的單執行緒RAG測試腳本
避免多執行緒鎖死問題
"""
import os
import sys
import json
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["VECLIB_MAXIMUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"

# 禁用FAISS的多執行緒
import faiss
faiss.omp_set_num_threads(1)

from pathlib import Path
import numpy as np

# Add backend to path
BACKEND_DIR = Path(__file__).parent
sys.path.insert(0, str(BACKEND_DIR))

from sentence_transformers import SentenceTransformer
import pickle

def load_backend(embedding_dir):
    """載入RAG後端，單執行緒版本"""
    print("🔧 載入RAG後端 (單執行緒模式)...")

    # Load FAISS index
    index_path = embedding_dir / "index.faiss"
    print(f"📂 載入FAISS索引: {index_path}")
    index = faiss.read_index(str(index_path))
    print(f"✅ FAISS索引已載入: {index.ntotal} 個向量")

    # Load ID mapping
    id_mapping_path = embedding_dir / "id_mapping.pkl"
    print(f"📂 載入ID映射: {id_mapping_path}")
    with open(id_mapping_path, 'rb') as f:
        mapping_data = pickle.load(f)
        index_to_id = mapping_data['index_to_id']
    print(f"✅ ID映射已載入: {len(index_to_id)} 個映射")

    # Load metadata
    metadata_path = embedding_dir / "metadata.json"
    print(f"📂 載入元數據: {metadata_path}")
    with open(metadata_path, 'r') as f:
        metadata = json.load(f)
    print(f"✅ 元數據已載入: {len(metadata)} 個chunks")

    # Load embedding model
    model_name = metadata.get('model_name', 'Snowflake/arctic-embed-s')
    print(f"📂 載入embedding模型: {model_name}")
    model = SentenceTransformer(model_name)
    print(f"✅ Embedding模型已載入")

    return {
        'index': index,
        'index_to_id': index_to_id,
        'metadata': metadata,
        'model': model
    }

def retrieve(backend, query, top_k=5):
    """檢索相關chunks"""
    print(f"\n🔍 查詢: {query}")

    # Encode query
    query_embedding = backend['model'].encode([query], convert_to_numpy=True)

    # Search
    scores, indices = backend['index'].search(query_embedding, top_k)

    # Collect results
    results = []
    for score, idx in zip(scores[0], indices[0]):
        if idx == -1:
            continue

        idx = int(idx)
        chunk_id = backend['index_to_id'][idx]
        chunk_data = backend['metadata'][chunk_id]

        results.append({
            'chunk_id': chunk_id,
            'score': float(score),
            'text': chunk_data.get('text', '')[:200] + '...',  # 只顯示前200字
            'summary': chunk_data.get('summary', ''),
            'primary_category': chunk_data.get('primary_category', ''),
            'document_id': chunk_data.get('document_id', '')
        })

    return results

def analyze_quality(query, results):
    """分析檢索品質"""
    print(f"\n📊 品質分析 - {query}")
    print(f"檢索到 {len(results)} 個結果")

    if not results:
        print("❌ 沒有找到相關結果")
        return {
            'has_results': False,
            'avg_score': 0,
            'top_score': 0
        }

    scores = [r['score'] for r in results]
    avg_score = np.mean(scores)
    top_score = scores[0] if scores else 0

    print(f"平均相似度分數: {avg_score:.4f}")
    print(f"最高分數: {top_score:.4f}")
    print(f"分數範圍: {min(scores):.4f} - {max(scores):.4f}")

    # 顯示top 3結果
    print("\n🏆 Top 3 結果:")
    for i, result in enumerate(results[:3], 1):
        print(f"\n結果 {i} (分數: {result['score']:.4f}):")
        print(f"  分類: {result['primary_category']}")
        print(f"  摘要: {result['summary'][:100]}...")
        print(f"  文本預覽: {result['text'][:150]}...")

    return {
        'has_results': True,
        'num_results': len(results),
        'avg_score': avg_score,
        'top_score': top_score,
        'score_range': (min(scores), max(scores)),
        'categories': [r['primary_category'] for r in results[:3]]
    }

def main():
    """主程式"""
    print("=" * 80)
    print("🚀 UIC Policy Assistant - 簡單測試")
    print("=" * 80)

    # 載入測試問題
    queries_file = BACKEND_DIR / "test_queries.json"
    print(f"\n📂 載入測試問題: {queries_file}")
    with open(queries_file, 'r') as f:
        queries = json.load(f)
    print(f"✅ 載入了 {len(queries)} 個測試問題")

    # 載入後端
    embedding_dir = BACKEND_DIR / "embeddings_output" / "naive" / "naive_embedding"
    backend = load_backend(embedding_dir)

    # 執行檢索並分析
    all_quality = {}
    print("\n" + "=" * 80)
    print("📝 開始測試")
    print("=" * 80)

    for qid, query in queries.items():
        print(f"\n{'='*80}")
        results = retrieve(backend, query, top_k=5)
        quality = analyze_quality(query, results)
        all_quality[qid] = quality

    # 總體品質分析
    print("\n" + "=" * 80)
    print("📊 總體品質分析")
    print("=" * 80)

    has_results_count = sum(1 for q in all_quality.values() if q['has_results'])
    print(f"\n成功檢索率: {has_results_count}/{len(queries)} ({has_results_count/len(queries)*100:.1f}%)")

    if has_results_count > 0:
        avg_scores = [q['avg_score'] for q in all_quality.values() if q['has_results']]
        top_scores = [q['top_score'] for q in all_quality.values() if q['has_results']]

        print(f"整體平均分數: {np.mean(avg_scores):.4f}")
        print(f"最高top分數: {max(top_scores):.4f}")
        print(f"最低top分數: {min(top_scores):.4f}")

        # 評分標準
        print("\n🎯 品質評級:")
        overall_score = np.mean(avg_scores)
        if overall_score > 0.7:
            print("✅ 優秀 - 檢索品質很高")
        elif overall_score > 0.5:
            print("⚠️  良好 - 檢索品質尚可，有改進空間")
        elif overall_score > 0.3:
            print("⚠️  一般 - 檢索品質需要改進")
        else:
            print("❌ 較差 - 檢索品質較低，需要優化")

    # 保存結果
    output_file = BACKEND_DIR / "simple_test_results.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            'queries': queries,
            'quality_metrics': all_quality,
            'overall': {
                'success_rate': has_results_count / len(queries),
                'avg_score': np.mean(avg_scores) if has_results_count > 0 else 0
            }
        }, f, indent=2, ensure_ascii=False)

    print(f"\n💾 結果已保存到: {output_file}")
    print("\n✅ 測試完成!")

if __name__ == "__main__":
    main()
