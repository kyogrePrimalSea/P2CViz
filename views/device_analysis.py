"""
views/device_analysis.py
Tab 3: Device Analysis — per-device metrics table and comparison charts.
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

COLORS = {
    'google_blue': '#4285F4',
    'google_red': '#EA4335',
    'google_yellow': '#FBBC05',
    'google_green': '#34A853',
    'conversion_orange': '#FF6B35',
}

PLOTLY_LAYOUT = dict(
    font=dict(family="Google Sans, Arial, sans-serif", size=12),
    plot_bgcolor='white',
    paper_bgcolor='white',
    margin=dict(l=40, r=40, t=60, b=80),
    showlegend=True,
    legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1)
)

DEVICE_CATEGORIES = ['Mobile', 'Desktop', 'Tablet', 'ConnectedTV', 'OutOfHome']

DEVICE_ALIASES = {
    'pc': 'Desktop',
    'desktop': 'Desktop',
    'ctv': 'ConnectedTV',
    'connected tv': 'ConnectedTV',
    'connectedtv': 'ConnectedTV',
    'ooh': 'OutOfHome',
    'out of home': 'OutOfHome',
    'outofhome': 'OutOfHome',
    'mobile': 'Mobile',
    'tablet': 'Tablet',
}

DEVICE_ICONS = {
    'Mobile': '📱',
    'Desktop': '💻',
    'Tablet': '📋',
    'ConnectedTV': '📺',
    'OutOfHome': '🏙️',
}


def normalise_device(val: str) -> str:
    """Map raw device strings to canonical category names."""
    if pd.isna(val) or str(val).strip() == '':
        return 'Unknown'
    cleaned = str(val).strip().lower()
    return DEVICE_ALIASES.get(cleaned, val.strip())


def render_device_analysis(df_conversions: pd.DataFrame, df_interactions: pd.DataFrame):
    st.markdown('<div class="tab-header">📱 Device Analysis</div>', unsafe_allow_html=True)

    if len(df_interactions) == 0:
        st.warning("No interaction data available with current filters.")
        return

    # Check if Device column is present
    has_device = df_interactions['device'].ne('Unknown').any()
    if not has_device:
        st.warning(
            "The **Device** dimension was not included in this CM360 report. "
            "Add 'Device' as a Per Interaction Dimension in CM360 Report Builder to enable this tab."
        )
        return

    # Normalise device column
    df_int = df_interactions.copy()
    df_int['device_normalised'] = df_int['device'].apply(normalise_device)

    total_conversions = df_conversions['conversion_row_index'].nunique()

    # --- Per-Device Metrics ---
    rows = []
    for device in DEVICE_CATEGORIES:
        dev_mask = df_int['device_normalised'] == device
        dev_df = df_int[dev_mask]

        n_convs_with = dev_df['conversion_row_index'].nunique()
        pct_on_path = n_convs_with / total_conversions if total_conversions > 0 else 0

        if n_convs_with == 0:
            rows.append({
                'device': device,
                'pct_on_path': 0,
                'pct_first_touch': 0,
                'pct_last_touch': 0,
                'avg_ipc': 0,
                'avg_days_last': 0,
                'n_convs': 0,
            })
            continue

        ft_convs = dev_df[dev_df['is_first_touch']]['conversion_row_index'].nunique()
        lt_convs = dev_df[dev_df['is_last_touch']]['conversion_row_index'].nunique()
        pct_first = ft_convs / n_convs_with if n_convs_with > 0 else 0
        pct_last = lt_convs / n_convs_with if n_convs_with > 0 else 0

        avg_ipc = dev_df.groupby('conversion_row_index').size().mean()

        # Avg days last device touch → conversion
        # For each conversion containing device, find LAST occurrence, compute days to conversion
        last_device_touch = (
            dev_df
            .sort_values('chronological_position')
            .groupby('conversion_row_index')
            .agg(last_dt=('interaction_datetime', 'last'))
            .reset_index()
        )
        last_device_touch = last_device_touch.merge(
            df_conversions[['conversion_row_index', 'conversion_datetime']],
            on='conversion_row_index',
            how='left'
        )
        last_device_touch['days_to_conv'] = (
            last_device_touch['conversion_datetime'] - last_device_touch['last_dt']
        ).dt.total_seconds() / 86400
        avg_days = last_device_touch['days_to_conv'].mean()

        rows.append({
            'device': device,
            'pct_on_path': pct_on_path,
            'pct_first_touch': pct_first,
            'pct_last_touch': pct_last,
            'avg_ipc': avg_ipc,
            'avg_days_last': avg_days if pd.notna(avg_days) else 0,
            'n_convs': n_convs_with,
        })

    device_df = pd.DataFrame(rows)

    # --- Per-Device Rows Display ---
    st.markdown("### Per-Device Summary")
    for _, r in device_df.iterrows():
        icon = DEVICE_ICONS.get(r['device'], '📡')
        cols = st.columns([1, 2, 2, 2, 2, 2])
        cols[0].markdown(f"**{icon} {r['device']}**")
        cols[1].metric("On Paths", f"{r['pct_on_path']:.0%}")
        cols[2].metric("First Touch", f"{r['pct_first_touch']:.0%}")
        cols[3].metric("Last Touch", f"{r['pct_last_touch']:.0%}")
        cols[4].metric("Avg IPC", f"{r['avg_ipc']:.2f}")
        cols[5].metric("Avg Days to Conv", f"{r['avg_days_last']:.2f}")

    st.markdown("---")

    # --- Device Comparison Bar Charts ---
    st.markdown("### Device Comparison Charts")
    ch1, ch2, ch3 = st.columns(3)

    with ch1:
        fig1 = px.bar(
            device_df.sort_values('pct_on_path', ascending=True),
            x='pct_on_path',
            y='device',
            orientation='h',
            title='Path Inclusion Rate by Device',
            labels={'pct_on_path': 'Inclusion Rate', 'device': 'Device'},
            color_discrete_sequence=[COLORS['google_blue']]
        )
        fig1.update_xaxes(tickformat='.0%')
        fig1.update_layout(**PLOTLY_LAYOUT)
        st.plotly_chart(fig1, use_container_width=True)

    with ch2:
        fig2 = go.Figure()
        fig2.add_trace(go.Bar(
            name='First Touch %',
            x=device_df['device'],
            y=device_df['pct_first_touch'],
            marker_color=COLORS['google_blue']
        ))
        fig2.add_trace(go.Bar(
            name='Last Touch %',
            x=device_df['device'],
            y=device_df['pct_last_touch'],
            marker_color=COLORS['conversion_orange']
        ))
        fig2.update_layout(
            barmode='group',
            title='First vs Last Touch % by Device',
            yaxis_tickformat='.0%',
            **PLOTLY_LAYOUT
        )
        st.plotly_chart(fig2, use_container_width=True)

    with ch3:
        fig3 = px.bar(
            device_df.sort_values('avg_days_last', ascending=True),
            x='avg_days_last',
            y='device',
            orientation='h',
            title='Avg Days to Convert by Device',
            labels={'avg_days_last': 'Avg Days', 'device': 'Device'},
            color_discrete_sequence=[COLORS['google_green']]
        )
        fig3.update_layout(**PLOTLY_LAYOUT)
        st.plotly_chart(fig3, use_container_width=True)

    # --- Device overlap (multi-device paths) ---
    st.markdown("---")
    st.markdown("### Multi-Device Path Analysis")
    multi_device_pct = df_conversions['multi_device'].mean() if 'multi_device' in df_conversions.columns else 0
    md_col1, md_col2 = st.columns(2)
    md_col1.metric("Multi-Device Paths", f"{multi_device_pct:.0%}")
    md_col2.metric("Single-Device Paths", f"{1-multi_device_pct:.0%}")
