"""K-means clustering on account whitespace vectors (POC3 §05.4)."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

import numpy as np
from sklearn.cluster import KMeans

from app.modules.whitespace.constants import KMEANS_K, KMEANS_N_INIT, KMEANS_RANDOM_STATE


def run_clustering(scoring_result: Dict[str, Any]) -> Dict[str, Any]:
    by_account: Dict[str, Dict[str, Any]] = scoring_result["by_account"]
    product_ids: List[str] = scoring_result["product_ids"]

    account_ids: List[str] = []
    vectors: List[List[float]] = []
    for aid, ac in sorted(by_account.items()):
        if ac["total_ws_potential_eur"] <= 0:
            ac["cluster_id"] = -1
            continue
        account_ids.append(aid)
        vectors.append(ac["vector"])

    if not account_ids:
        return {
            **scoring_result,
            "clustered_account_ids": [],
            "cluster_totals": [],
            "top_cluster_ids": [],
            "cluster_members": {},
        }

    X = np.array(vectors, dtype=float)
    n = len(account_ids)
    k = min(KMEANS_K, n)
    if k < KMEANS_K:
        km = KMeans(
            n_clusters=k,
            random_state=KMEANS_RANDOM_STATE,
            n_init=KMEANS_N_INIT,
        )
    else:
        km = KMeans(
            n_clusters=KMEANS_K,
            random_state=KMEANS_RANDOM_STATE,
            n_init=KMEANS_N_INIT,
        )
    labels = km.fit_predict(X)

    cluster_potential: Dict[int, float] = {}
    cluster_members: Dict[int, List[str]] = {}
    for i, aid in enumerate(account_ids):
        lbl = int(labels[i])
        by_account[aid]["cluster_id"] = lbl
        pot = float(by_account[aid]["total_ws_potential_eur"])
        cluster_potential[lbl] = cluster_potential.get(lbl, 0.0) + pot
        cluster_members.setdefault(lbl, []).append(aid)

    ranked: List[Tuple[int, float]] = sorted(
        cluster_potential.items(), key=lambda x: -x[1]
    )
    top_cluster_ids = [c[0] for c in ranked[:3]]

    return {
        **scoring_result,
        "clustered_account_ids": account_ids,
        "cluster_totals": ranked,
        "cluster_members": cluster_members,
        "top_cluster_ids": top_cluster_ids,
        "product_ids": product_ids,
    }
