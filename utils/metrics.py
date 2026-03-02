"""
utils/metrics.py
Shared metric calculation and filter functions.
"""
import pandas as pd
import streamlit as st


def calc_overall_kpis(df_conversions: pd.DataFrame, df_interactions: pd.DataFrame) -> dict:
    """
    Returns dict with overall KPI values.
    """
    total_impressions = int(df_conversions['actual_path_length'].sum())
    total_conversions = len(df_conversions)
    avg_path_length = df_conversions['actual_path_length'].mean() if total_conversions > 0 else 0
    impressions_per_conversion = total_impressions / total_conversions if total_conversions > 0 else 0
    avg_days_first = df_conversions['days_first_to_conversion'].mean()
    avg_days_last = df_conversions['days_last_to_conversion'].mean()
    pct_view = (df_conversions['attribution_type'] == 'View-through').mean() if total_conversions > 0 else 0
    pct_click = (df_conversions['attribution_type'] == 'Click-through').mean() if total_conversions > 0 else 0
    multi_touch_pct = (df_conversions['actual_path_length'] > 1).mean() if total_conversions > 0 else 0

    return {
        'total_impressions_on_paths': total_impressions,
        'total_conversions': total_conversions,
        'avg_path_length': avg_path_length,
        'impressions_per_conversion': impressions_per_conversion,
        'avg_days_first_to_conversion': avg_days_first,
        'avg_days_last_to_conversion': avg_days_last,
        'pct_view_through': pct_view,
        'pct_click_through': pct_click,
        'multi_touch_pct': multi_touch_pct,
    }


@st.cache_data
def apply_filters(
    df_conversions: pd.DataFrame,
    df_interactions: pd.DataFrame,
    selected_attribution: list,
    date_range,
    selected_channels: list
) -> tuple:
    """
    Apply sidebar filters. Returns (filtered_convs, filtered_ints).
    """
    # Handle date_range being a tuple of 1 or 2 dates (Streamlit date_input quirk)
    if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
        d_start, d_end = date_range
    elif isinstance(date_range, (list, tuple)) and len(date_range) == 1:
        d_start = d_end = date_range[0]
    else:
        d_start = df_conversions['conversion_datetime'].min().date()
        d_end = df_conversions['conversion_datetime'].max().date()

    # Filter df_conversions
    mask = (
        df_conversions['attribution_type'].isin(selected_attribution) &
        (df_conversions['conversion_datetime'].dt.date >= d_start) &
        (df_conversions['conversion_datetime'].dt.date <= d_end)
    )
    filtered_convs = df_conversions[mask].copy()

    # Filter df_interactions to matching conversions
    valid_indices = set(filtered_convs['conversion_row_index'].tolist())
    filtered_ints = df_interactions[df_interactions['conversion_row_index'].isin(valid_indices)].copy()

    # Channel filter (only if not all selected)
    all_channels = df_interactions['channel'].unique()
    if len(selected_channels) < len(all_channels):
        filtered_ints = filtered_ints[filtered_ints['channel'].isin(selected_channels)]

    return filtered_convs, filtered_ints
