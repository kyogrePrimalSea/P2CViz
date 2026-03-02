"""
utils/ngram.py
N-gram extraction utilities for conversion path analysis.
"""
import pandas as pd
import streamlit as st
from collections import Counter


def extract_ngrams(path_list: list, n: int) -> list:
    """
    Given a list like ['Channel A', 'Channel B', 'Channel C'],
    return all n-grams as tuples.
    For n=2: [('Channel A', 'Channel B'), ('Channel B', 'Channel C')]
    """
    return list(zip(*[path_list[i:] for i in range(n)]))


@st.cache_data
def compute_ngram_frequencies(df_conversions: pd.DataFrame, dimension: str, n: int) -> pd.DataFrame:
    """
    dimension: one of 'Campaign', 'Channel', 'Site', 'Device'
    Returns DataFrame with columns: ngram (tuple), ngram_str, count, pct_of_paths
    """
    path_col_map = {
        'Campaign': 'path_campaigns',
        'Channel': 'path_channels',
        'Site': 'path_sites',
        'Device': 'path_devices',
    }

    path_col = path_col_map.get(dimension, 'path_channels')

    if path_col not in df_conversions.columns:
        return pd.DataFrame(columns=['ngram', 'ngram_str', 'count', 'pct_of_paths'])

    all_ngrams = []
    for path in df_conversions[path_col]:
        if isinstance(path, list) and len(path) >= n:
            all_ngrams.extend(extract_ngrams(path, n))

    if not all_ngrams:
        return pd.DataFrame(columns=['ngram', 'ngram_str', 'count', 'pct_of_paths'])

    counter = Counter(all_ngrams)
    total_paths = len(df_conversions)

    result = pd.DataFrame([
        {
            'ngram': ng,
            'ngram_str': ' \u2192 '.join(str(x) for x in ng),
            'count': cnt,
            'pct_of_paths': cnt / total_paths
        }
        for ng, cnt in counter.most_common()
    ])

    return result
