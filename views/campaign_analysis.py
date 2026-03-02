"""
views/campaign_analysis.py
Tab 5: Campaign Analysis — first/last touch, IPC, days to convert.
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
    margin=dict(l=40, r=40, t=60, b=120),
    showlegend=True,
    legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1)
)


def render_campaign_analysis(df_conversions: pd.DataFrame, df_interactions: pd.DataFrame):
    st.markdown('<div class="tab-header">📢 Campaign Analysis</div>', unsafe_allow_html=True)

    has_campaign = (
        'first_touch_campaign' in df_conversions.columns and
        df_interactions['campaign'].ne('Unknown').any()
    )

    if not has_campaign:
        st.warning(
            "The **Campaign** dimension was not included in this CM360 report. "
            "Add 'Campaign' as a Per Interaction Dimension in CM360 Report Builder to enable this tab."
        )
        return

    if len(df_conversions) == 0:
        st.warning("No conversions match the current filters.")
        return

    # --- 11.1: First vs Last Impression Conversions by Campaign ---
    st.markdown("### First vs Last Touch Conversions by Campaign")

    first_touch = (
        df_conversions[df_conversions['first_touch_campaign'].notna() & (df_conversions['first_touch_campaign'] != 'Unknown')]
        .groupby('first_touch_campaign')
        .size()
        .reset_index(name='first_impression_conversions')
        .rename(columns={'first_touch_campaign': 'campaign'})
    )

    last_touch = (
        df_conversions[df_conversions['last_touch_campaign'].notna() & (df_conversions['last_touch_campaign'] != 'Unknown')]
        .groupby('last_touch_campaign')
        .size()
        .reset_index(name='last_impression_conversions')
        .rename(columns={'last_touch_campaign': 'campaign'})
    )

    campaign_df = first_touch.merge(last_touch, on='campaign', how='outer').fillna(0)
    campaign_df = campaign_df.sort_values('last_impression_conversions', ascending=False)

    max_campaigns = 15
    show_more = st.checkbox(f"Show all {len(campaign_df)} campaigns", value=False) if len(campaign_df) > max_campaigns else False
    display_campaigns = campaign_df if show_more else campaign_df.head(max_campaigns)

    fig1 = go.Figure()
    fig1.add_trace(go.Bar(
        name='First Touch Conversions',
        x=display_campaigns['campaign'],
        y=display_campaigns['first_impression_conversions'],
        marker_color=COLORS['google_blue']
    ))
    fig1.add_trace(go.Bar(
        name='Last Touch Conversions',
        x=display_campaigns['campaign'],
        y=display_campaigns['last_impression_conversions'],
        marker_color=COLORS['conversion_orange']
    ))
    fig1.update_layout(
        barmode='group',
        title='First vs Last Touch Conversions by Campaign',
        xaxis_title='Campaign',
        yaxis_title='Conversions',
        xaxis_tickangle=45,
        **PLOTLY_LAYOUT
    )
    st.plotly_chart(fig1, use_container_width=True)

    # --- 11.2: Impressions Per Conversion by Campaign ---
    st.markdown("### Impressions Per Conversion by Campaign")

    appearances = df_interactions[df_interactions['campaign'] != 'Unknown'].groupby('campaign').size().reset_index(name='total_appearances')
    unique_convs = df_interactions[df_interactions['campaign'] != 'Unknown'].groupby('campaign')['conversion_row_index'].nunique().reset_index(name='n_conversions')
    ipc = appearances.merge(unique_convs, on='campaign')
    ipc['impressions_per_conversion'] = ipc['total_appearances'] / ipc['n_conversions']
    ipc = ipc.merge(campaign_df[['campaign', 'last_impression_conversions']], on='campaign', how='left').fillna(0)
    ipc = ipc.sort_values('last_impression_conversions', ascending=False).head(max_campaigns if not show_more else len(ipc))

    fig2 = px.bar(
        ipc,
        x='campaign',
        y='impressions_per_conversion',
        title='Impressions Per Conversion by Campaign',
        labels={'impressions_per_conversion': 'Impressions / Conversion', 'campaign': 'Campaign'},
        color_discrete_sequence=[COLORS['google_green']]
    )
    fig2.update_layout(xaxis_tickangle=45, **PLOTLY_LAYOUT)
    st.plotly_chart(fig2, use_container_width=True)

    # --- 11.3: Days to Convert by Campaign ---
    st.markdown("### Avg Days to Convert (From Last Impression) by Campaign")

    days_df = (
        df_conversions[df_conversions['last_touch_campaign'].notna() & (df_conversions['last_touch_campaign'] != 'Unknown')]
        .groupby('last_touch_campaign')['days_last_to_conversion']
        .mean()
        .reset_index()
    )
    days_df.columns = ['campaign', 'avg_days_last_to_conversion']
    days_df = days_df.sort_values('avg_days_last_to_conversion', ascending=False).head(max_campaigns if not show_more else len(days_df))

    fig3 = px.bar(
        days_df,
        x='campaign',
        y='avg_days_last_to_conversion',
        title='Avg Days to Convert (From Last Campaign Impression)',
        labels={'avg_days_last_to_conversion': 'Avg Days', 'campaign': 'Campaign'},
        color_discrete_sequence=[COLORS['google_yellow']]
    )
    fig3.update_layout(xaxis_tickangle=45, **PLOTLY_LAYOUT)
    st.plotly_chart(fig3, use_container_width=True)

    # --- 11.4: Campaign Conversion Paths Summary ---
    st.markdown("---")
    st.markdown("### Campaign Path Summary")

    def count_unique_campaigns(path_campaigns):
        if not isinstance(path_campaigns, list):
            return 0
        return len(set(c for c in path_campaigns if c != 'Unknown'))

    campaign_counts = df_conversions['path_campaigns'].apply(count_unique_campaigns)
    avg_campaigns = campaign_counts.mean()
    pct_multi_campaign = (campaign_counts > 1).mean()

    stat_cols = st.columns(2)
    stat_cols[0].metric("Avg Campaigns per Converting User", f"{avg_campaigns:.2f}")
    stat_cols[1].metric("% Users Exposed to 2+ Campaigns", f"{pct_multi_campaign:.0%}")
