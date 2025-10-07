# 🚀 如何執行完整的 RAG Pipeline

## ✅ 已完成的準備工作

1. ✅ CSV 文件已轉換成 TXT
2. ✅ Gemini API 已設定
3. ✅ Chunking 已完成（818 個 chunks）
4. ✅ 程式碼已修改支援 Gemini

---

## 📋 完整執行步驟

### Step 1: Chunking（已完成）✅

```bash
cd code/
source MetaRAG_env/bin/activate
python chunks.py --input_file input_files/ --chunking_method naive --chunk_by paragraph --min_chunk_size 1
```

**結果：** `chunk_output/` 資料夾包含 12 個 JSON 檔案

---

### Step 2: Metadata 生成（使用 Gemini）

```bash
python metadata_gen.py --chunks_dir chunk_output
```

**這步驟會：**
- 使用 Gemini API 為每個 chunk 生成 metadata
- 包括：關鍵字、類別、摘要等
- 需要約 10-20 分鐘（depending on API speed）

**輸出：** `metadata_gen_output/` 資料夾

---

### Step 3: 生成 Embeddings（免費，不需要 API）

```bash
python embeddings.py --embedding_types naive
```

**這步驟會：**
- 使用免費的 Sentence Transformer
- 生成向量embeddings
- 完全在本地運行

**輸出：** `embeddings_output/` 資料夾

---

### Step 4: 建立檢索系統（免費）

首先建立測試問題檔案 `test_queries.json`:

```json
{
    "q1": "What are the financial reporting requirements?",
    "q2": "How should custodial funds be managed?",
    "q3": "What is the policy for payroll processing?",
    "q4": "How are receivables collected?",
    "q5": "What are the procedures for deficit reporting?"
}
```

然後執行檢索：

```bash
python retriever.py --queries_file test_queries.json --top_k 5
```

**輸出：** `retrieval_output/run_XXXXX/` 資料夾

---

## 🎯 測試結果

檢查檢索結果：

```bash
# 查看檢索到的文件片段
cat retrieval_output/run_*/retrieval_results.json | head -50
```

---

## 🚨 常見問題

### Q: Gemini API 呼叫失敗？
**A:** 檢查：
1. API key 是否正確（在 `.env`）
2. 網路連線
3. API 配額是否用完

### Q: Metadata 生成很慢？
**A:** 這是正常的，Gemini free tier 有速率限制。預計：
- 每個 chunk 約 1-2 秒
- 818 個 chunks 需要 15-30 分鐘

### Q: 想跳過 Metadata？
**A:** 可以！Metadata 不是必須的，直接執行：
```bash
python embeddings.py --embedding_types naive --chunking_types naive
python retriever.py --queries_file test_queries.json
```

---

## 📊 資料夾結構

```
code/
├── input_files/              ✅ 你的文件（已完成）
├── chunk_output/             ✅ 分塊結果（已完成）
├── metadata_gen_output/      ⏳ 待生成
├── embeddings_output/        ⏳ 待生成
└── retrieval_output/         ⏳ 待生成
    └── run_XXXXX/
        ├── content_retriever/
        └── ...
```

---

## ✨ 執行建議

### 最快的測試流程（跳過 Metadata）:

```bash
# 1. 已完成 Chunking ✅

# 2. 生成 Embeddings（5-10 分鐘）
python embeddings.py --embedding_types naive --chunking_types naive

# 3. 測試檢索（1 分鐘）
python retriever.py --queries_file test_queries.json --top_k 5
```

### 完整流程（包含 Metadata）:

```bash
# 1. 已完成 Chunking ✅

# 2. 生成 Metadata（15-30 分鐘）
python metadata_gen.py --chunks_dir chunk_output

# 3. 生成 Embeddings（5-10 分鐘）
python embeddings.py

# 4. 測試檢索（1 分鐘）
python retriever.py --queries_file test_queries.json
```

---

## 🎓 下一步：連接前端

當 RAG pipeline 完成後，你可以：

1. 檢查檢索結果是否正確
2. 修改前端讀取這些結果
3. 部署展示

---

## 💡 Tips

- 先執行最快的測試流程，確保一切正常
- 再執行完整流程生成 metadata
- 保留所有輸出檔案，可以重複使用

**Gemini API 免費額度：**
- 每分鐘 15 requests
- 每天 1500 requests
- 足夠處理你的 818 個 chunks！
