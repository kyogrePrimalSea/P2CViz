"""
views/frequency_view.py
Tab 9: Conversion Frequency Distribution — impressions before conversion.
"""
import streamlit as st
import pandas as pd
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

SORT_ORDER = [str(i) for i in range(1, 30)] + ['30+']


def compute_freq_dist(df_conversions: pd.DataFrame) -> pd.DataFrame:
    """Compute frequency distribution bucketed by path_length."""
    freq_df = df_conversions.copy()

    def bucket(pl):
        if pd.isna(pl):
            return '0'
        pl = int(pl)
        if pl >= 30:
            return '30+'
        return str(pl)

    freq_df['freq_bucket'] = freq_df['path_length'].apply(bucket)
    overall_freq = freq_df.groupby('freq_bucket').size().reset_index(name='conversions')
    overall_freq.columns = ['frequency', 'conversions']
    total = overall_freq['conversions'].sum()
    overall_freq['pct_of_conversions'] = overall_freq['conversions'] / total if total > 0 else 0

    # Sort correctly
    overall_freq['freq_sort'] = overall_freq['frequency'].map(
        lambda x: SORT_ORDER.index(str(x)) if str(x) in SORT_ORDER else 99
    )
    overall_freq = overall_freq.sort_values('freq_sort').reset_index(drop=True)
    return overall_freq


def render_frequency(df_conversions: pd.DataFrame):
    st.markdown('<div class="tab-header">📈 Conversion Frequency Distribution</div>', unsafe_allow_html=True)

    if len(df_conversions) == 0:
        st.warning("No conversions match the current filters.")
        return

    # --- Overall frequency dist ---
    overall_freq = compute_freq_dist(df_conversions)

    # --- Activity selector (if activity_name column available) ---
    selected_activities = []
    activity_freqs = {}

    has_activity = (
        'activity_name' in df_conversions.columns and
        df_conversions['activity_name'].ne('Unknown').any()
    )

    if has_activity:
        all_activities = sorted(df_conversions['activity_name'].dropna().unique().tolist())
        all_activities = [a for a in all_activities if a != 'Unknown']
        selected_activities = st.multiselect(
            "Show activities separately",
            options=all_activities,
            default=[]
        )
        for act in selected_activities:
            act_df = df_conversions[df_conversions['activity_name'] == act]
            activity_freqs[act] = compute_freq_dist(act_df)

    ACTIVITY_COLORS = [COLORS['conversion_orange'], COLORS['google_green'], COLORS['google_yellow'], COLORS['google_red']]

    # --- Chart 1: Total Count ---
    st.markdown("### Conversion Count by Frequency (Number of Impressions)")
    fig1 = go.Figure()
    fig1.add_trace(go.Bar(
        x=overall_freq['frequency'],
        y=overall_freq['conversions'],
        name='Overall',
        marker_color=COLORS['google_blue']
    ))
    for i, act in enumerate(selected_activities):
        adf = activity_freqs.get(act, pd.DataFrame())
        if len(adf) > 0:
            fig1.add_trace(go.Bar(
                x=adf['frequency'],
                y=adf['conversions'],
                name=act[:40],
                marker_color=ACTIVITY_COLORS[i % len(ACTIVITY_COLORS)]
            ))
    fig1.update_layout(
        barmode='group',
        title='Frequency Distribution — Total Conversion Count',
        xaxis_title='Number of Impressions Before Conversion',
        yaxis_title='Conversions',
        **PLOTLY_LAYOUT
    )
    st.plotly_chart(fig1, use_container_width=True)

    # --- Chart 2: % of Conversions ---
    st.markdown("### % of Conversions by Frequency")
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(
        x=overall_freq['frequency'],
        y=overall_freq['pct_of_conversions'],
        mode='lines+markers',
        name='Overall',
        line=dict(color=COLORS['google_blue'], width=2)
    ))
    for i, act in enumerate(selected_activities):
        adf = activity_freqs.get(act, pd.DataFrame())
        if len(adf) > 0:
            fig2.add_trace(go.Scatter(
                x=adf['frequency'],
                y=adf['pct_of_conversions'],
                mode='lines+markers',
                name=act[:40],
                line=dict(color=ACTIVITY_COLORS[i % len(ACTIVITY_COLORS)], width=2)
            ))
    fig2.update_yaxes(tickformat='.0%')
    fig2.update_layout(
        title='Frequency Distribution — Percent of Conversions',
        xaxis_title='Number of Impressions Before Conversion',
        yaxis_title='% of Conversions',
        **PLOTLY_LAYOUT
    )
    st.plotly_chart(fig2, use_container_width=True)

    # --- Saturation Insight ---
    st.markdown("---")
    cumulative = overall_freq.copy()
    cumulative['cumulative_pct'] = cumulative['pct_of_conversions'].cumsum()
    thresh_rows = cumulative[cumulative['cumulative_pct'] >= 0.80]
    if len(thresh_rows) > 0:
        saturation_freq = thresh_rows['frequency'].iloc[0]
        st.info(
            f"💡 **80% of conversions occur within {saturation_freq} impressions.** "
            f"Serving more than {saturation_freq} impressions may represent diminishing returns."
        )

    # Show 50% threshold too
    thresh_50 = cumulative[cumulative['cumulative_pct'] >= 0.50]
    if len(thresh_50) > 0:
        sat_50 = thresh_50['frequency'].iloc[0]
        st.info(f"💡 **50% of conversions occur within {sat_50} impressions.**")
