import numpy as np

def zscore_anomaly(values, threshold=3.0):
    if len(values) < 5:
        return False, 0.0
    arr = np.array(values, dtype=float)
    z = (arr[-1] - arr.mean()) / (arr.std() + 1e-6)
    return abs(z) >= threshold, float(z)

def mad_anomaly(values, k=5.0):
    # écart médian absolu
    arr = np.array(values, dtype=float)
    median = np.median(arr)
    mad = np.median(np.abs(arr - median)) + 1e-6
    score = np.abs(arr[-1] - median) / (1.4826 * mad)
    return score >= k, float(score)
