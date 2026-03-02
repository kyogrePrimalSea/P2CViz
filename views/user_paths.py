"""
views/user_paths.py
Tab 2: Sample User Path Viewer — random or manual path exploration.
"""
import random
import streamlit as st
import pandas as pd

CHANNEL_ICONS = {
    'standard display': '🖥️',
    'paid search': '🔍',
    'organic search': '🌿',
    'social': '👥',
    'video': '▶️',
    'email': '📧',
    'direct': '🎯',
    '--': '❓',
}


def get_channel_icon(channel_str: str) -> str:
    return CHANNEL_ICONS.get(str(channel_str).lower().strip(), '📢')


def fmt_dt(dt) -> str:
    """Format a datetime for display."""
    try:
        if pd.isna(dt):
            return 'Unknown'
        return pd.Timestamp(dt).strftime('%d/%m/%Y %H:%M')
    except Exception:
        return str(dt)


def render_user_paths(df_conversions: pd.DataFrame, df_interactions: pd.DataFrame):
    st.markdown('<div class="tab-header">👤 Sample User Path Viewer</div>', unsafe_allow_html=True)
    st.caption(
        "Each Conversion ID represents one anonymous conversion event. "
        "The same physical user may have multiple IDs across different events."
    )

    if len(df_conversions) == 0:
        st.warning("No conversions match the current filters.")
        return

    # --- Controls ---
    col1, col2, col3 = st.columns([2, 2, 3])

    generate_btn = col1.button("🎲 Generate Random Path")

    multi_touch_count = int((df_conversions['actual_path_length'] > 1).sum())
    multi_touch_only = col2.checkbox(
        f"Multi-touch only ({multi_touch_count:,} conversions)",
        value=True
    )

    conv_id_input = col3.text_input("Or enter Conversion ID directly")

    # --- State Management ---
    if 'selected_conv_id' not in st.session_state:
        st.session_state['selected_conv_id'] = None

    if generate_btn:
        if multi_touch_only:
            pool = df_conversions[df_conversions['actual_path_length'] > 1]['conversion_id'].tolist()
        else:
            pool = df_conversions['conversion_id'].tolist()
        if pool:
            st.session_state['selected_conv_id'] = random.choice(pool)
        else:
            st.warning("No conversions available in the current selection.")

    if conv_id_input.strip():
        st.session_state['selected_conv_id'] = conv_id_input.strip()

    selected_id = st.session_state.get('selected_conv_id')

    if selected_id is None:
        st.info("Click **Generate Random Path** or enter a Conversion ID above to view a journey.")
        return

    # --- Lookup ---
    conv_matches = df_conversions[df_conversions['conversion_id'] == selected_id]
    if len(conv_matches) == 0:
        st.warning(f"Conversion ID `{selected_id}` not found in the current filtered dataset.")
        return

    conv_row = conv_matches.iloc[0]
    path_ints = df_interactions[df_interactions['conversion_id'] == selected_id].sort_values('chronological_position')

    st.markdown(f"**Conversion ID:** `{selected_id}`")
    st.markdown("---")

    # --- Path Display (horizontal cards using columns) ---
    n_interactions = len(path_ints)
    total_cards = n_interactions + 1  # +1 for conversion card

    if n_interactions == 0:
        st.info("This conversion has no recorded interaction rows (unattributed).")
    else:
        # Display in rows of up to 5 cards
        chunk_size = 5
        all_rows = list(path_ints.iterrows())

        for chunk_start in range(0, n_interactions, chunk_size):
            chunk = all_rows[chunk_start:chunk_start + chunk_size]
            # Add conversion card in last chunk if fits
            is_last_chunk = (chunk_start + chunk_size >= n_interactions)
            extra = 1 if is_last_chunk else 0
            cols = st.columns(len(chunk) + extra)

            for ci, (_, row) in enumerate(chunk):
                icon = get_channel_icon(row.get('channel', ''))
                placement = str(row.get('placement', ''))
                placement_display = (placement[:50] + '...') if len(placement) > 50 else placement
                with cols[ci]:
                    st.markdown(
                        f"""
                        <div style="border:1px solid #DADCE0; border-radius:8px; padding:12px; background:#F8F9FA; min-height:160px;">
                            <div style="font-size:24px; text-align:center;">{icon}</div>
                            <div style="font-size:11px; color:#5F6368; text-align:center;">{fmt_dt(row.get('interaction_datetime'))}</div>
                            <div style="font-weight:bold; font-size:13px; text-align:center; margin-top:4px;">{row.get('channel', '')}</div>
                            <div style="font-size:11px; color:#444; margin-top:4px;">{placement_display}</div>
                            <div style="font-size:11px; color:#777; margin-top:4px;">Type: {row.get('interaction_type', '')}</div>
                            <div style="font-size:11px; color:#777;">Position: {int(row.get('chronological_position', 0))} of {int(row.get('path_length', 0))}</div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

            # Conversion card in last chunk
            if is_last_chunk:
                with cols[-1]:
                    st.markdown(
                        f"""
                        <div style="border:2px solid #FF6B35; border-radius:8px; padding:12px; background:#FFF3EE; min-height:160px;">
                            <div style="font-size:24px; text-align:center;">⭐</div>
                            <div style="font-size:11px; color:#5F6368; text-align:center;">{fmt_dt(conv_row.get('conversion_datetime'))}</div>
                            <div style="font-weight:bold; font-size:13px; text-align:center; color:#FF6B35; margin-top:4px;">CONVERSION</div>
                            <div style="font-size:11px; color:#444; margin-top:4px;">Attribution: {conv_row.get('attribution_type', '')}</div>
                            <div style="font-size:11px; color:#444;">Path Length: {int(conv_row.get('path_length', 0))}</div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

            st.markdown("")  # spacing between rows

    # --- Conversion Summary Stats ---
    st.markdown("---")
    st.markdown("**Conversion Summary**")
    stat_cols = st.columns(6)
    stat_cols[0].metric("Total Interactions", str(conv_row.get('actual_path_length', 0)))
    stat_cols[1].metric("Attribution Type", str(conv_row.get('attribution_type', '')))
    stat_cols[2].metric("First Interaction", fmt_dt(conv_row.get('first_touch_datetime')))
    stat_cols[3].metric("Last Interaction", fmt_dt(conv_row.get('last_touch_datetime')))

    days_in_path = conv_row.get('days_first_to_conversion')
    stat_cols[4].metric(
        "Days in Path",
        f"{days_in_path:.1f}" if pd.notna(days_in_path) else "N/A"
    )

    unique_channels = path_ints['channel'].nunique() if len(path_ints) > 0 else 0
    stat_cols[5].metric("Unique Channels", str(unique_channels))
