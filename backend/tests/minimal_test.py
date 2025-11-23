#!/usr/bin/env python3
"""
極簡RAG測試 - 完全避開多執行緒問題
使用最小依賴，先設置所有環境變數再載入任何庫
"""

# 第一步：在載入任何庫之前設置所有環境變數
import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["VECLIB_MAXIMUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["TORCH_NUM_THREADS"] = "1"

# 第二步：現在才載入其他庫
import sys
import json
import pickle
import numpy as np
from pathlib import Path

print("=" * 80)
print("🚀 UIC Policy Assistant - 極簡測試")
print("=" * 80)

# 第三步：最後才載入可能有問題的庫
print("\n📦 載入模型庫...")

# 先設置FAISS不使用多執行緒
import faiss
faiss.omp_set_num_threads(1)
print("✅ FAISS已設置為單執行緒")

# 最後才載入SentenceTransformer，且設置為單執行緒
print("📦 載入SentenceTransformer (可能需要一些時間)...")
import torch
torch.set_num_threads(1)

from sentence_transformers import SentenceTransformer
print("✅ SentenceTransformer已載入")

def main():
    BACKEND_DIR = Path(__file__).parent

    # 載入測試問題
    queries_file = BACKEND_DIR / "test_queries.json"
    print(f"\n📂 載入測試問題: {queries_file}")
    with open(queries_file, 'r') as f:
        queries = json.load(f)
    print(f"✅ 載入了 {len(queries)} 個測試問題\n")

    for qid, query_text in queries.items():
        print(f"{qid}: {query_text}")

    # 設置路徑
    embedding_dir = BACKEND_DIR / "embeddings_output" / "naive" / "naive_embedding"

    # 載入FAISS索引
    print(f"\n📂 載入FAISS索引...")
    index_path = embedding_dir / "index.faiss"
    index = faiss.read_index(str(index_path))
    print(f"✅ FAISS索引: {index.ntotal} 個向量, 維度: {index.d}")

    # 載入ID映射
    print(f"\n📂 載入ID映射...")
    id_mapping_path = embedding_dir / "id_mapping.pkl"
    with open(id_mapping_path, 'rb') as f:
        mapping_data = pickle.load(f)
        index_to_id = mapping_data['index_to_id']
    print(f"✅ ID映射: {len(index_to_id)} 個")

    # 載入元數據
    print(f"\n📂 載入元數據...")
    metadata_path = embedding_dir / "metadata.json"
    with open(metadata_path, 'r') as f:
        metadata = json.load(f)
    print(f"✅ 元數據: {len(metadata)} 個chunks")

    # 載入embedding模型 - 這是最可能卡住的地方
    print(f"\n📂 載入embedding模型 (這可能需要30-60秒，請耐心等待)...")
    model_name = metadata.get('model_name', 'Snowflake/arctic-embed-s')
    print(f"   模型: {model_name}")

    try:
        model = SentenceTransformer(model_name, device='cpu')  # 強制使用CPU
        print(f"✅ Embedding模型已載入")
    except Exception as e:
        print(f"❌ 模型載入失敗: {e}")
        return

    # 開始測試
    print("\n" + "=" * 80)
    print("📝 開始測試 5 個問題")
    print("=" * 80)

    all_results = {}

    for qid, query_text in queries.items():
        print(f"\n{'='*80}")
        print(f"🔍 {qid}: {query_text}")
        print("="*80)

        try:
            # Encode query
            print("   正在編碼查詢...")
            query_embedding = model.encode([query_text], convert_to_numpy=True, show_progress_bar=False)
            print(f"   ✅ 查詢已編碼: shape={query_embedding.shape}")

            # Search
            print("   正在搜尋FAISS索引...")
            top_k = 5
            scores, indices = index.search(query_embedding, top_k)
            print(f"   ✅ 搜尋完成，找到 {len(indices[0])} 個結果")

            # Collect results
            results = []
            for rank, (score, idx) in enumerate(zip(scores[0], indices[0]), 1):
                if idx == -1:
                    continue

                idx = int(idx)
                if idx not in index_to_id:
                    print(f"   ⚠️  警告: 索引 {idx} 不在映射中")
                    continue

                chunk_id = index_to_id[idx]
                chunk_data = metadata.get(chunk_id, {})

                result = {
                    'rank': rank,
                    'score': float(score),
                    'chunk_id': chunk_id,
                    'text': chunk_data.get('text', ''),
                    'summary': chunk_data.get('summary', ''),
                    'primary_category': chunk_data.get('primary_category', ''),
                    'document_id': chunk_data.get('document_id', '')
                }
                results.append(result)

            all_results[qid] = {
                'query': query_text,
                'results': results
            }

            # 顯示結果
            print(f"\n📊 檢索結果分析:")
            if results:
                scores_list = [r['score'] for r in results]
                print(f"   找到 {len(results)} 個相關chunks")
                print(f"   最高分數: {max(scores_list):.4f}")
                print(f"   平均分數: {np.mean(scores_list):.4f}")
                print(f"   分數範圍: {min(scores_list):.4f} - {max(scores_list):.4f}")

                print(f"\n   🏆 Top 3 結果:")
                for result in results[:3]:
                    print(f"\n   排名 {result['rank']} | 分數: {result['score']:.4f}")
                    print(f"   分類: {result['primary_category']}")
                    print(f"   摘要: {result['summary'][:120]}...")
                    print(f"   內容: {result['text'][:150]}...")
            else:
                print(f"   ❌ 沒有找到相關結果")

        except Exception as e:
            print(f"   ❌ 處理查詢時發生錯誤: {e}")
            import traceback
            traceback.print_exc()

    # 總體分析
    print("\n" + "=" * 80)
    print("📊 總體品質分析")
    print("=" * 80)

    total_queries = len(queries)
    successful_queries = sum(1 for r in all_results.values() if r.get('results'))

    print(f"\n✅ 成功率: {successful_queries}/{total_queries} ({successful_queries/total_queries*100:.1f}%)")

    if successful_queries > 0:
        all_scores = []
        all_top_scores = []

        for qid, data in all_results.items():
            if data.get('results'):
                scores = [r['score'] for r in data['results']]
                all_scores.extend(scores)
                all_top_scores.append(scores[0])

        print(f"\n分數統計:")
        print(f"  整體平均分數: {np.mean(all_scores):.4f}")
        print(f"  Top結果平均分數: {np.mean(all_top_scores):.4f}")
        print(f"  最高分數: {max(all_scores):.4f}")
        print(f"  最低分數: {min(all_scores):.4f}")

        # 品質評級
        avg_top_score = np.mean(all_top_scores)
        print(f"\n🎯 品質評級:")
        if avg_top_score > 0.7:
            grade = "優秀 ⭐⭐⭐⭐⭐"
            assessment = "檢索品質很高，模型能準確找到相關內容"
        elif avg_top_score > 0.5:
            grade = "良好 ⭐⭐⭐⭐"
            assessment = "檢索品質不錯，但仍有改進空間"
        elif avg_top_score > 0.3:
            grade = "一般 ⭐⭐⭐"
            assessment = "檢索品質一般，需要優化"
        else:
            grade = "需要改進 ⭐⭐"
            assessment = "檢索品質較低，建議調整策略"

        print(f"  等級: {grade}")
        print(f"  評估: {assessment}")

        # 分類分析
        print(f"\n📑 檢索內容分類分布:")
        category_counts = {}
        for data in all_results.values():
            if data.get('results'):
                for result in data['results'][:3]:  # 只看top 3
                    cat = result['primary_category']
                    category_counts[cat] = category_counts.get(cat, 0) + 1

        for cat, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"  {cat}: {count} 次")

    # 保存結果
    output_file = BACKEND_DIR / "minimal_test_results.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            'test_config': {
                'embedding_model': model_name,
                'embedding_dir': str(embedding_dir),
                'top_k': 5
            },
            'results': all_results,
            'summary': {
                'total_queries': total_queries,
                'successful_queries': successful_queries,
                'success_rate': successful_queries / total_queries if total_queries > 0 else 0,
                'avg_top_score': np.mean(all_top_scores) if successful_queries > 0 else 0
            }
        }, f, indent=2, ensure_ascii=False)

    print(f"\n💾 詳細結果已保存到: {output_file}")
    print("\n✅ 測試完成!")
    print("=" * 80)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  測試被用戶中斷")
    except Exception as e:
        print(f"\n\n❌ 測試失敗: {e}")
        import traceback
        traceback.print_exc()
