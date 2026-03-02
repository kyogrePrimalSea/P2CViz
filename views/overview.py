"""
views/overview.py
Tab 1: Overall Stats — KPI cards, secondary metrics, daily conversions chart.
"""
import streamlit as st
import pandas as pd
import plotly.express as px

COLORS = {
    'google_blue': '#4285F4',
    'google_red': '#EA4335',
    'google_yellow': '#FBBC05',
    'google_green': '#34A853',
    'conversion_orange': '#FF6B35',
    'light_blue': '#74B3F0',
    'dark_blue': '#1A3A6B',
}

PLOTLY_LAYOUT = dict(
    font=dict(family="Google Sans, Arial, sans-serif", size=12),
    plot_bgcolor='white',
    paper_bgcolor='white',
    margin=dict(l=40, r=40, t=60, b=80),
    showlegend=True,
    legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1)
)


def render_overview(df_conversions: pd.DataFrame, df_interactions: pd.DataFrame, metadata: dict):
    st.markdown('<div class="tab-header">📊 Overall Stats</div>', unsafe_allow_html=True)

    # --- Metadata Banner ---
    date_range = metadata.get('date_range', 'Unknown')
    floodlight_config = metadata.get('floodlight_config', 'Unknown')
    account_id = metadata.get('account_id', 'Unknown')
    st.info(
        f"📅 **Date Range:** {date_range}   |   "
        f"🔧 **Account ID:** {account_id}   |   "
        f"🏷️ **Floodlight Config:** {floodlight_config}"
    )

    if len(df_conversions) == 0:
        st.warning("No conversions match the current filters.")
        return

    # --- KPI Row 1 (6 cards) ---
    total_impressions = int(df_conversions['actual_path_length'].sum())
    total_conversions = len(df_conversions)
    avg_path_length = df_conversions['actual_path_length'].mean()
    imp_per_conv = total_impressions / total_conversions if total_conversions > 0 else 0
    avg_days_first = df_conversions['days_first_to_conversion'].mean()
    avg_days_last = df_conversions['days_last_to_conversion'].mean()

    cols = st.columns(6)
    cols[0].metric("Total Impressions (on Paths)", f"{total_impressions:,.0f}")
    cols[1].metric("Total Conversions", f"{total_conversions:,.0f}")
    cols[2].metric("Avg Path Length", f"{avg_path_length:.2f}")
    cols[3].metric("Impressions per Conversion", f"{imp_per_conv:.2f}")
    cols[4].metric("Avg Days First Touch → Conv", f"{avg_days_first:.2f}" if pd.notna(avg_days_first) else "N/A")
    cols[5].metric("Avg Days Last Touch → Conv", f"{avg_days_last:.2f}" if pd.notna(avg_days_last) else "N/A")

    st.markdown("---")

    # --- KPI Row 2 (3 cards) ---
    vt_count = int((df_conversions['attribution_type'] == 'View-through').sum())
    ct_count = int((df_conversions['attribution_type'] == 'Click-through').sum())
    multi_touch_count = int((df_conversions['actual_path_length'] > 1).sum())
    multi_touch_rate = multi_touch_count / total_conversions if total_conversions > 0 else 0

    cols2 = st.columns(3)
    cols2[0].metric("View-Through Conversions", f"{vt_count:,.0f}")
    cols2[1].metric("Click-Through Conversions", f"{ct_count:,.0f}")
    cols2[2].metric(
        "Multi-Touch Paths (2+ interactions)",
        f"{multi_touch_count:,.0f} ({multi_touch_rate:.0%})"
    )

    st.markdown("---")

    # --- Attribution Type Distribution ---
    col_left, col_right = st.columns(2)

    with col_left:
        attr_counts = df_conversions['attribution_type'].value_counts().reset_index()
        attr_counts.columns = ['Attribution Type', 'Count']
        fig_attr = px.pie(
            attr_counts,
            values='Count',
            names='Attribution Type',
            title='Conversion Attribution Type Split',
            color_discrete_sequence=[COLORS['google_blue'], COLORS['google_red'], COLORS['google_yellow']]
        )
        fig_attr.update_layout(**PLOTLY_LAYOUT)
        st.plotly_chart(fig_attr, use_container_width=True)

    with col_right:
        # Path length distribution
        path_dist = df_conversions['actual_path_length'].value_counts().sort_index().reset_index()
        path_dist.columns = ['Path Length', 'Count']
        path_dist = path_dist[path_dist['Path Length'] <= 20]  # cap display at 20
        fig_path = px.bar(
            path_dist,
            x='Path Length',
            y='Count',
            title='Distribution of Path Lengths',
            color_discrete_sequence=[COLORS['google_blue']]
        )
        fig_path.update_layout(**PLOTLY_LAYOUT)
        st.plotly_chart(fig_path, use_container_width=True)

    # --- Conversion Volume Over Time ---
    if 'conversion_datetime' in df_conversions.columns:
        daily = (
            df_conversions
            .groupby(df_conversions['conversion_datetime'].dt.date)
            .size()
            .reset_index()
        )
        daily.columns = ['date', 'conversions']
        daily = daily.dropna(subset=['date'])

        fig = px.line(
            daily,
            x='date',
            y='conversions',
            title='Daily Conversions Over Campaign Period',
            color_discrete_sequence=[COLORS['google_blue']]
        )
        fig.update_layout(
            xaxis_title='Date',
            yaxis_title='Conversions',
            hovermode='x unified',
            **PLOTLY_LAYOUT
        )
        st.plotly_chart(fig, use_container_width=True)

    # --- Activities listed ---
    if metadata.get('activities'):
        st.markdown("**Floodlight Activities in this report:**")
        for act in metadata['activities']:
            st.markdown(f"- {act}")
