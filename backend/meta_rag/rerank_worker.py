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
       
        print(f"🔄 Loading reranker model: {model_name}", file=sys.stderr)
        
        # Hugging Face token check
        hf_token = os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_TOKEN")
        
        if hf_token:
            from huggingface_hub import login
            login(token=hf_token)
            
            print(f"✅ Authenticated with Hugging Face token", file=sys.stderr)
        
        tokenizer = AutoTokenizer.from_pretrained(model_name, token=hf_token)
        model = AutoModelForSequenceClassification.from_pretrained(model_name, token=hf_token)
        model.eval()
        
        # Use MPS if available
        if torch.backends.mps.is_available():
            device = torch.device("mps")
            
            print("📱 Using Apple Silicon GPU (MPS)", file=sys.stderr)
        elif torch.cuda.is_available():
            device = torch.device("cuda")
            print("🎮 Using NVIDIA GPU (CUDA)", file=sys.stderr)
        else:
            device = torch.device("cpu")
            print("💻 Using CPU", file=sys.stderr)
        
        model.to(device)
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
        
        # Output result (this is the only JSON that needs to be printed to stdout)
        print(json.dumps({"scores": scores}))
        
    except Exception as e:
        # Error also print to stdout, so the main program can catch it
        print(json.dumps({"error": str(e)}))
        sys.exit(1)

if __name__ == "__main__":
    main()