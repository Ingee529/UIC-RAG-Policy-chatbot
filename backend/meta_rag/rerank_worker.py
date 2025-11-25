import sys
import json
import os
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import numpy as np

def main():
    # Read input from stdin
    try:
        input_data = json.load(sys.stdin)
        query = input_data['query']
        chunks = input_data['chunks']
        
        # Load model
        model_name = os.getenv("RERANKER_MODEL_NAME", "BAAI/bge-reranker-base")
        # ✅ 修正語法：括號要在最後面
        print(f"🔄 Loading reranker model: {model_name}", file=sys.stderr)
        
        # Hugging Face token check
        hf_token = os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_TOKEN")
        
        if hf_token:
            from huggingface_hub import login
            login(token=hf_token)
            # ✅ 修正語法
            print(f"✅ Authenticated with Hugging Face token", file=sys.stderr)
        
        tokenizer = AutoTokenizer.from_pretrained(model_name, token=hf_token)
        model = AutoModelForSequenceClassification.from_pretrained(model_name, token=hf_token)
        model.eval()
        
        # Use MPS if available
        if torch.backends.mps.is_available():
            device = torch.device("mps")
            # ✅ 修正語法
            print("📱 Using Apple Silicon GPU (MPS)", file=sys.stderr)
        elif torch.cuda.is_available():
            device = torch.device("cuda")
            # ✅ 補上 file=sys.stderr (原本漏了，這很重要！)
            print("🎮 Using NVIDIA GPU (CUDA)", file=sys.stderr)
        else:
            device = torch.device("cpu")
            # ✅ 修正語法
            print("💻 Using CPU", file=sys.stderr)
        
        model.to(device)
        # ✅ 修正語法
        print(f"✅ Reranker model loaded successfully on {device}", file=sys.stderr)
        
        # Prepare pairs
        pairs = []
        for chunk in chunks:
            pairs.append([query, chunk['text']])
            
        # Inference
        inputs = tokenizer(
            pairs,
            padding=True,
            truncation=True,
            return_tensors='pt',
            max_length=512
        )
        inputs = {key: val.to(device) for key, val in inputs.items()}
        
        with torch.no_grad():
            logits = model(**inputs).logits
            
        if logits.size(-1) == 2:
            scores = logits[:, 1]
        else:
            scores = logits.view(-1)
            
        scores = scores.cpu().numpy().tolist()
        
        # Output result (這是唯一需要印到 stdout 的 JSON，保持原樣)
        print(json.dumps({"scores": scores}))
        
    except Exception as e:
        # Error 也印成 JSON 到 stdout，讓主程式接住
        print(json.dumps({"error": str(e)}))
        sys.exit(1)

if __name__ == "__main__":
    main()