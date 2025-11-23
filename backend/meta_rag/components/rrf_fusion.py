"""
Reciprocal Rank Fusion - Extracted from META notebook
"""

from collections import defaultdict

def rrf_fuse(rank_lists, k: int = 60):
    """
    Reciprocal Rank Fusion (RRF).

    rank_lists: list of ranked lists, e.g. [
        [doc_id_1, doc_id_2, ...],   # list 1
        [doc_id_3, doc_id_2, ...],   # list 2
        ...
    ]

    k: damping factor (standard RRF uses 60)

    Returns:
        fused_list: list of doc_ids sorted by RRF score (descending)
    """
    scores = defaultdict(float)

    for r_list in rank_lists:
        for rank, doc_id in enumerate(r_list):
            # rank is 0-based, so add 1
            scores[doc_id] += 1.0 / (k + rank + 1)

    # Sort by fused score descending
    fused = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    fused_list = [doc_id for doc_id, _ in fused]
    return fused_list
