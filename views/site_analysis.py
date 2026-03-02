"""
views/site_analysis.py
Tab 6: Site Analysis — identical structure to campaign_analysis but using site column.
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


def render_site_analysis(df_conversions: pd.DataFrame, df_interactions: pd.DataFrame):
    st.markdown('<div class="tab-header">🌐 Site Analysis</div>', unsafe_allow_html=True)

    has_site = (
        'first_touch_site' in df_conversions.columns and
        df_interactions['site'].ne('Unknown').any()
    )

    if not has_site:
        st.warning(
            "The **Site (CM360)** dimension was not included in this CM360 report. "
            "Add 'Site (CM360)' as a Per Interaction Dimension in CM360 Report Builder to enable this tab."
        )
        return

    if len(df_conversions) == 0:
        st.warning("No conversions match the current filters.")
        return

    max_sites = 15
    show_more = False

    # --- First vs Last Touch by Site ---
    st.markdown("### First vs Last Touch Conversions by Site")

    first_touch = (
        df_conversions[df_conversions['first_touch_site'].notna() & (df_conversions['first_touch_site'] != 'Unknown')]
        .groupby('first_touch_site')
        .size()
        .reset_index(name='first_impression_conversions')
        .rename(columns={'first_touch_site': 'site'})
    )

    last_touch = (
        df_conversions[df_conversions['last_touch_site'].notna() & (df_conversions['last_touch_site'] != 'Unknown')]
        .groupby('last_touch_site')
        .size()
        .reset_index(name='last_impression_conversions')
        .rename(columns={'last_touch_site': 'site'})
    )

    site_df = first_touch.merge(last_touch, on='site', how='outer').fillna(0)
    site_df = site_df.sort_values('last_impression_conversions', ascending=False)

    if len(site_df) > max_sites:
        show_more = st.checkbox(f"Show all {len(site_df)} sites", value=False)

    display_sites = site_df if show_more else site_df.head(max_sites)

    fig1 = go.Figure()
    fig1.add_trace(go.Bar(
        name='First Touch Conversions',
        x=display_sites['site'],
        y=display_sites['first_impression_conversions'],
        marker_color=COLORS['google_blue']
    ))
    fig1.add_trace(go.Bar(
        name='Last Touch Conversions',
        x=display_sites['site'],
        y=display_sites['last_impression_conversions'],
        marker_color=COLORS['conversion_orange']
    ))
    fig1.update_layout(
        barmode='group',
        title='First vs Last Touch Conversions by Site',
        xaxis_title='Site',
        yaxis_title='Conversions',
        xaxis_tickangle=45,
        **PLOTLY_LAYOUT
    )
    st.plotly_chart(fig1, use_container_width=True)

    # --- Impressions Per Conversion by Site ---
    st.markdown("### Impressions Per Conversion by Site")

    appearances = df_interactions[df_interactions['site'] != 'Unknown'].groupby('site').size().reset_index(name='total_appearances')
    unique_convs = df_interactions[df_interactions['site'] != 'Unknown'].groupby('site')['conversion_row_index'].nunique().reset_index(name='n_conversions')
    ipc = appearances.merge(unique_convs, on='site')
    ipc['impressions_per_conversion'] = ipc['total_appearances'] / ipc['n_conversions']
    ipc = ipc.merge(site_df[['site', 'last_impression_conversions']], on='site', how='left').fillna(0)
    ipc = ipc.sort_values('last_impression_conversions', ascending=False).head(max_sites if not show_more else len(ipc))

    fig2 = px.bar(
        ipc,
        x='site',
        y='impressions_per_conversion',
        title='Impressions Per Conversion by Site',
        labels={'impressions_per_conversion': 'Impressions / Conversion', 'site': 'Site'},
        color_discrete_sequence=[COLORS['google_green']]
    )
    fig2.update_layout(xaxis_tickangle=45, **PLOTLY_LAYOUT)
    st.plotly_chart(fig2, use_container_width=True)

    # --- Days to Convert by Site ---
    st.markdown("### Avg Days to Convert (From Last Site Impression) by Site")

    days_df = (
        df_conversions[df_conversions['last_touch_site'].notna() & (df_conversions['last_touch_site'] != 'Unknown')]
        .groupby('last_touch_site')['days_last_to_conversion']
        .mean()
        .reset_index()
    )
    days_df.columns = ['site', 'avg_days_last_to_conversion']
    days_df = days_df.sort_values('avg_days_last_to_conversion', ascending=False).head(max_sites if not show_more else len(days_df))

    fig3 = px.bar(
        days_df,
        x='site',
        y='avg_days_last_to_conversion',
        title='Avg Days to Convert (From Last Site Impression)',
        labels={'avg_days_last_to_conversion': 'Avg Days', 'site': 'Site'},
        color_discrete_sequence=[COLORS['google_yellow']]
    )
    fig3.update_layout(xaxis_tickangle=45, **PLOTLY_LAYOUT)
    st.plotly_chart(fig3, use_container_width=True)

    # --- Site Path Summary ---
    st.markdown("---")
    st.markdown("### Site Path Summary")

    def count_unique_sites(path_sites):
        if not isinstance(path_sites, list):
            return 0
        return len(set(s for s in path_sites if s != 'Unknown'))

    site_counts = df_conversions['path_sites'].apply(count_unique_sites)
    avg_sites = site_counts.mean()
    pct_multi_site = (site_counts > 1).mean()

    stat_cols = st.columns(2)
    stat_cols[0].metric("Avg Sites per Converting User", f"{avg_sites:.2f}")
    stat_cols[1].metric("% Users Exposed to 2+ Sites", f"{pct_multi_site:.0%}")
