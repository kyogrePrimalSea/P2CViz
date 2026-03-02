"""
utils/path_builder.py
Builds the two canonical DataFrames consumed by all view modules:
  - df_interactions : one row per interaction
  - df_conversions  : one row per conversion event
"""
import pandas as pd
import streamlit as st


# ---------------------------------------------------------------------------
# df_interactions builder
# ---------------------------------------------------------------------------

def build_df_interactions(raw_df: pd.DataFrame, optional_cols: dict) -> pd.DataFrame:
    """
    Filter to interaction rows only and add derived columns.
    """
    df = raw_df[raw_df['row_type'] == 'interaction'].copy()

    # Rename core columns to app-internal names
    rename_map = {
        'Conversion ID': 'conversion_id',
        'Activity Date/Time': 'conversion_datetime',
        'Floodlight Attribution Type': 'attribution_type',
        'Path Length': 'path_length',
        'Interaction Date/Time': 'interaction_datetime',
        'Interaction Number': 'interaction_number',
        'Interaction Channel': 'channel',
        'Interaction Type': 'interaction_type',
        'Placement': 'placement',
        'ZIP/Postal Code': 'zip_code',
    }
    # Only rename columns that exist
    rename_map = {k: v for k, v in rename_map.items() if k in df.columns}
    df = df.rename(columns=rename_map)

    # Rename optional columns if present
    for app_name, col_name in optional_cols.items():
        if col_name in df.columns:
            df = df.rename(columns={col_name: app_name})

    # Fill optional columns with 'Unknown' if not present
    for app_name in ['campaign', 'site', 'device', 'ad', 'creative', 'activity_name']:
        if app_name not in df.columns:
            df[app_name] = 'Unknown'

    # Ensure required columns exist
    for col in ['channel', 'interaction_type', 'placement', 'zip_code']:
        if col not in df.columns:
            df[col] = ''

    # interaction_number: 1 = last touch. Convert to int.
    df['interaction_number'] = df['interaction_number'].astype(int)

    # chronological_position: REVERSE of interaction_number so that 1 = EARLIEST touch.
    # Formula: chronological_position = path_length - interaction_number + 1
    df['chronological_position'] = df['path_length'] - df['interaction_number'] + 1

    # is_last_touch: interaction_number == 1
    df['is_last_touch'] = df['interaction_number'] == 1

    # is_first_touch: interaction_number == path_length (i.e. chronological_position == 1)
    df['is_first_touch'] = df['interaction_number'] == df['path_length']

    # position_weight: chronological_position / path_length
    # Ranges from 1/path_length (earliest) to 1.0 (last touch)
    df['position_weight'] = df['chronological_position'] / df['path_length'].replace(0, 1)

    df = df.reset_index(drop=True)
    return df


# ---------------------------------------------------------------------------
# df_conversions builder
# ---------------------------------------------------------------------------

def build_df_conversions(raw_df: pd.DataFrame, df_interactions: pd.DataFrame) -> pd.DataFrame:
    """
    One row per unique conversion (Conversion ID + Activity Date/Time combination).
    """
    # Start from summary rows
    df_conv_raw = raw_df[raw_df['row_type'] == 'conversion'].copy()
    rename_map = {
        'Conversion ID': 'conversion_id',
        'Activity Date/Time': 'conversion_datetime',
        'Floodlight Attribution Type': 'attribution_type',
        'Path Length': 'path_length',
        'ZIP/Postal Code': 'zip_code',
    }
    rename_map = {k: v for k, v in rename_map.items() if k in df_conv_raw.columns}
    df_conv_raw = df_conv_raw.rename(columns=rename_map)

    keep_cols = [c for c in ['conversion_id', 'conversion_datetime', 'attribution_type', 'path_length', 'zip_code'] if c in df_conv_raw.columns]
    df_conv_raw = df_conv_raw[keep_cols]

    # If no zip_code column, add it
    if 'zip_code' not in df_conv_raw.columns:
        df_conv_raw['zip_code'] = ''

    # Group df_interactions by conversion_id to build path lists
    def build_path_col(group, col):
        return group.sort_values('chronological_position')[col].tolist()

    def safe_first(group, col):
        sorted_g = group.sort_values('chronological_position')
        if len(sorted_g) > 0:
            return sorted_g[col].iloc[0]
        return None

    def safe_last(group, col):
        sorted_g = group.sort_values('chronological_position')
        if len(sorted_g) > 0:
            return sorted_g[col].iloc[-1]
        return None

    if len(df_interactions) > 0:
        path_data = df_interactions.groupby('conversion_id').apply(lambda g: pd.Series({
            'path_channels':          build_path_col(g, 'channel'),
            'path_placements':        build_path_col(g, 'placement'),
            'path_interaction_types': build_path_col(g, 'interaction_type'),
            'path_datetimes':         build_path_col(g, 'interaction_datetime'),
            'path_campaigns':         build_path_col(g, 'campaign'),
            'path_sites':             build_path_col(g, 'site'),
            'path_devices':           build_path_col(g, 'device'),
            'first_touch_channel':    safe_first(g, 'channel'),
            'last_touch_channel':     safe_last(g, 'channel'),
            'first_touch_campaign':   safe_first(g, 'campaign'),
            'last_touch_campaign':    safe_last(g, 'campaign'),
            'first_touch_site':       safe_first(g, 'site'),
            'last_touch_site':        safe_last(g, 'site'),
            'first_touch_datetime':   safe_first(g, 'interaction_datetime'),
            'last_touch_datetime':    safe_last(g, 'interaction_datetime'),
            'actual_path_length':     len(g),
        })).reset_index()
    else:
        # No interactions at all — create empty path_data
        path_data = pd.DataFrame(columns=[
            'conversion_id', 'path_channels', 'path_placements', 'path_interaction_types',
            'path_datetimes', 'path_campaigns', 'path_sites', 'path_devices',
            'first_touch_channel', 'last_touch_channel', 'first_touch_campaign',
            'last_touch_campaign', 'first_touch_site', 'last_touch_site',
            'first_touch_datetime', 'last_touch_datetime', 'actual_path_length'
        ])

    # Merge
    df = df_conv_raw.merge(path_data, on='conversion_id', how='left')

    # Fill missing list columns with empty lists
    list_cols = ['path_channels', 'path_placements', 'path_interaction_types',
                 'path_datetimes', 'path_campaigns', 'path_sites', 'path_devices']
    for col in list_cols:
        if col not in df.columns:
            df[col] = [[] for _ in range(len(df))]
        else:
            df[col] = df[col].apply(lambda x: x if isinstance(x, list) else [])

    # Fill missing scalar columns
    str_cols = ['first_touch_channel', 'last_touch_channel', 'first_touch_campaign',
                'last_touch_campaign', 'first_touch_site', 'last_touch_site']
    for col in str_cols:
        if col not in df.columns:
            df[col] = None

    dt_cols = ['first_touch_datetime', 'last_touch_datetime']
    for col in dt_cols:
        if col not in df.columns:
            df[col] = pd.NaT

    if 'actual_path_length' not in df.columns:
        df['actual_path_length'] = 0
    else:
        df['actual_path_length'] = df['actual_path_length'].fillna(0).astype(int)

    # Derived time columns
    df['days_first_to_conversion'] = (
        df['conversion_datetime'] - df['first_touch_datetime']
    ).dt.total_seconds() / 86400

    df['days_last_to_conversion'] = (
        df['conversion_datetime'] - df['last_touch_datetime']
    ).dt.total_seconds() / 86400

    # Human-readable path strings
    df['path_channel_string'] = df['path_channels'].apply(
        lambda x: ' > '.join(x) if isinstance(x, list) and len(x) > 0 else ''
    )
    df['path_placement_string'] = df['path_placements'].apply(
        lambda x: ' > '.join(x) if isinstance(x, list) and len(x) > 0 else ''
    )
    df['path_campaign_string'] = df['path_campaigns'].apply(
        lambda x: ' > '.join([c for c in x if c != 'Unknown']) if isinstance(x, list) else ''
    )

    # Device diversity
    df['devices_on_path'] = df['path_devices'].apply(
        lambda x: list(set(x)) if isinstance(x, list) else []
    )
    df['num_unique_devices'] = df['devices_on_path'].apply(len)
    df['multi_device'] = df['num_unique_devices'] > 1

    df = df.reset_index(drop=True)
    df['conversion_row_index'] = df.index

    return df


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

@st.cache_data
def build_dataframes(raw_df: pd.DataFrame, optional_cols: dict) -> tuple:
    """
    Args: raw_df and optional_cols from load_p2c_report()
    Returns: (df_conversions, df_interactions)
    """
    df_interactions = build_df_interactions(raw_df, optional_cols)
    df_conversions = build_df_conversions(raw_df, df_interactions)

    # Add conversion_row_index to df_interactions
    id_to_idx = df_conversions.set_index('conversion_id')['conversion_row_index'].to_dict()
    df_interactions['conversion_row_index'] = df_interactions['conversion_id'].map(id_to_idx)

    return df_conversions, df_interactions
