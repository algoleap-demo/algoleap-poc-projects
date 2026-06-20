"""POC3: k-means produces KMEANS_K clusters when n_samples is sufficient."""

import numpy as np
from sklearn.cluster import KMeans

from app.modules.whitespace.constants import KMEANS_K, KMEANS_N_INIT, KMEANS_RANDOM_STATE


def test_kmeans_fixed_k_on_synthetic():
    rng = np.random.default_rng(42)
    X = rng.random((25, 6))
    km = KMeans(
        n_clusters=KMEANS_K,
        random_state=KMEANS_RANDOM_STATE,
        n_init=KMEANS_N_INIT,
    )
    labels = km.fit_predict(X)
    assert len(set(labels)) == KMEANS_K
