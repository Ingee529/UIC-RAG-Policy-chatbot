import sys
import json
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import numpy as np

def main():
    # Read input from stdin
    try:
        input_data = json.load(sys.stdin)
        query = input_data['query']
        chunks = input_data['chunks']
        
        # Load model (this takes time, but ensures isolation)
        model_name = "BAAI/bge-reranker-base"
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModelForSequenceClassification.from_pretrained(model_name)
        model.eval()
        
        # Use MPS if available
        if torch.backends.mps.is_available():
            device = torch.device("mps")
        else:
            device = torch.device("cpu")
        model.to(device)
        
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
        
        # Output result
        print(json.dumps({"scores": scores}))
        
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)

if __name__ == "__main__":
    main()

