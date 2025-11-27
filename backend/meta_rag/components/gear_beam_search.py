"""
GEAR Beam Search - Extracted from META notebook
"""

# Step 7: Diverse Triple Beam Search — clean implementation

import math

def get_neighbors(triple, all_triples):
    """
    Find all triples in all_triples that share subject or object with the given triple (excluding itself).
    """
    s0, _, o0 = triple
    neighbors = []
    for t in all_triples:
        s, _, o = t
        if t == triple:
            continue
        if s == s0 or s == o0 or o == s0 or o == o0:
            neighbors.append(t)
    return neighbors

def score_triple(triple, query_emb):
    """
    Compute cosine similarity between the triple and the query embedding.
    """
    s, p, o = triple
    triple_text = f"{s} {p} {o}"
    triple_emb = model.encode([triple_text], convert_to_tensor=True)
    return float(util.pytorch_cos_sim(query_emb, triple_emb)[0])

def diverse_triple_beam_search(query, T_q, all_triples, beam_size=3, max_length=3, gamma=1.0):
    """
    Perform Diverse Triple Beam Search as in GEAR (GEAR: §4.2, Algorithm 1).
    - query: input query string
    - T_q: list of initial triple candidates
    - all_triples: full triple list to search over
    Returns: top beam paths (each is a list of triples)
    """
    query_emb = model.encode([query], convert_to_tensor=True)

    # Initialize beams with single triples from T_q
    beams = []
    for t in T_q:
        score = score_triple(t, query_emb)
        beams.append((score, [t]))

    # Keep top beam_size beams
    beams = sorted(beams, key=lambda x: x[0], reverse=True)[:beam_size]

    for _ in range(1, max_length):
        candidates = []
        for score, seq in beams:
            last_triple = seq[-1]
            for neighbor in get_neighbors(last_triple, all_triples):
                if neighbor in seq:
                    continue  # skip already visited
                new_seq = seq + [neighbor]
                new_score = score_triple(neighbor, query_emb)
                avg_score = (score * len(seq) + new_score) / len(new_seq)
                candidates.append((avg_score, new_seq))

        # Apply diversity penalty using exponential rank weighting
        candidates = sorted(candidates, key=lambda x: x[0], reverse=True)
        penalized = []
        for rank, (score, path) in enumerate(candidates):
            penalty = math.exp(-min(rank, gamma))
            penalized.append((score * penalty, path))

        beams = sorted(penalized, key=lambda x: x[0], reverse=True)[:beam_size]

    return [path for _, path in beams]
