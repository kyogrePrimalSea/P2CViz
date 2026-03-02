"""
views/assisted_analysis.py
Tab 4: Assisted Conversion Analysis (Position-Weighted).
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


def get_characterisation(path_inclusion_rate, position_weighted_score, first_touch_dominance):
    if first_touch_dominance > 0.6 and position_weighted_score < 50:
        return "Upper-Funnel Initiator 🎬"
    if position_weighted_score > 75 and first_touch_dominance < 0.3:
        return "Conversion Closer 🎯"
    if path_inclusion_rate > 0.5 and position_weighted_score > 50:
        return "Full-Funnel Workhorse 💪"
    if path_inclusion_rate < 0.2:
        return "Niche Touch 🔍"
    return "Mid-Funnel Contributor 🔄"


def render_assisted_analysis(df_conversions: pd.DataFrame, df_interactions: pd.DataFrame):
    st.markdown('<div class="tab-header">🎯 Assisted Conversion Analysis</div>', unsafe_allow_html=True)

    if len(df_interactions) == 0:
        st.warning("No interaction data available with current filters.")
        return

    # Dimension selector
    dimension = st.selectbox(
        "Analyse by",
        options=['Channel', 'Campaign', 'Site', 'Device'],
        index=0
    )
    dimension_col = dimension.lower()

    if dimension_col not in df_interactions.columns:
        st.warning(f"Column '{dimension_col}' not found in the data. Add this dimension in CM360 Report Builder.")
        return

    total_conversions = df_conversions['conversion_row_index'].nunique()

    # --- Build summary for each dimension value ---
    dim_values = [v for v in df_interactions[dimension_col].dropna().unique() if v != 'Unknown' and v != '--']

    if len(dim_values) == 0:
        st.warning(f"No data available for dimension: {dimension}")
        return

    rows = []
    for val in dim_values:
        val_mask = df_interactions[dimension_col] == val
        val_df = df_interactions[val_mask]

        # Metric 1: Path Inclusion Rate
        n_with = val_df['conversion_row_index'].nunique()
        path_inclusion_rate = n_with / total_conversions if total_conversions > 0 else 0

        # Metric 2: Position-Weighted Contribution Score (raw, normalised later)
        raw_score = val_df['position_weight'].sum()

        # Metric 4: First-Touch Dominance Rate
        ft_convs = val_df[val_df['is_first_touch']]['conversion_row_index'].nunique()
        first_touch_dominance = ft_convs / n_with if n_with > 0 else 0

        # Metric 3: Path Lift — groups with/without
        conv_indices_with = set(val_df['conversion_row_index'].unique())
        conv_indices_without = set(df_conversions['conversion_row_index'].tolist()) - conv_indices_with

        group_with = df_conversions[df_conversions['conversion_row_index'].isin(conv_indices_with)]
        group_without = df_conversions[df_conversions['conversion_row_index'].isin(conv_indices_without)]

        avg_pl_with = group_with['path_length'].mean() if len(group_with) > 0 else 0
        avg_pl_without = group_without['path_length'].mean() if len(group_without) > 0 else 0
        path_length_lift = avg_pl_with / avg_pl_without if avg_pl_without > 0 else 1

        avg_days_with = group_with['days_first_to_conversion'].mean() if len(group_with) > 0 else 0
        avg_days_without = group_without['days_first_to_conversion'].mean() if len(group_without) > 0 else 0
        days_lift = avg_days_with / avg_days_without if avg_days_without and avg_days_without > 0 else 1

        # Repeat conversion rate (crude: multiple rows for same conv_id)
        repeat_with = (group_with.groupby('conversion_id').size() > 1).mean() if len(group_with) > 0 else 0
        repeat_without = (group_without.groupby('conversion_id').size() > 1).mean() if len(group_without) > 0 else 0
        repeat_lift = repeat_with / repeat_without if repeat_without > 0 else 1

        rows.append({
            'dimension_value': val,
            'n_conversions': n_with,
            'path_inclusion_rate': path_inclusion_rate,
            'raw_score': raw_score,
            'first_touch_dominance': first_touch_dominance,
            'avg_path_length_with': avg_pl_with,
            'avg_path_length_without': avg_pl_without,
            'path_length_lift': path_length_lift,
            'avg_days_with': avg_days_with if pd.notna(avg_days_with) else 0,
            'avg_days_without': avg_days_without if pd.notna(avg_days_without) else 0,
            'days_lift': days_lift if pd.notna(days_lift) else 1,
            'repeat_conv_rate_with': repeat_with,
            'repeat_conv_rate_without': repeat_without,
            'repeat_conv_lift': repeat_lift,
        })

    summary_df = pd.DataFrame(rows)

    # Normalise position-weighted score to 0–100
    max_raw = summary_df['raw_score'].max()
    summary_df['position_weighted_score'] = (summary_df['raw_score'] / max_raw * 100) if max_raw > 0 else 0

    # Characterisation
    summary_df['characterisation'] = summary_df.apply(
        lambda r: get_characterisation(r['path_inclusion_rate'], r['position_weighted_score'], r['first_touch_dominance']),
        axis=1
    )

    summary_df = summary_df.sort_values('position_weighted_score', ascending=False).reset_index(drop=True)

    # --- Narrative for top channel ---
    if len(summary_df) > 0:
        top = summary_df.iloc[0]
        st.info(
            f"📊 **{top['dimension_value']}** analysis:\n"
            f"- Present in **{top['path_inclusion_rate']:.0%}** of all converting paths\n"
            f"- When {top['dimension_value']} initiates the journey, it accounts for **{top['first_touch_dominance']:.0%}** of first touches\n"
            f"- Paths containing {top['dimension_value']} show a repeat conversion rate of **{top['repeat_conv_rate_with']:.0%}** vs **{top['repeat_conv_rate_without']:.0%}** for paths without it\n"
            f"- Characterisation: **{top['characterisation']}**"
        )

    # --- Summary Table ---
    st.markdown("### Summary Table")
    display_cols = {
        'dimension_value': dimension,
        'path_inclusion_rate': 'Path Inclusion %',
        'position_weighted_score': 'Position-Weighted Score',
        'repeat_conv_lift': 'Repeat Conv Lift',
        'first_touch_dominance': 'First-Touch Dominance %',
        'characterisation': 'Assist Characterisation',
    }
    display_df = summary_df[list(display_cols.keys())].rename(columns=display_cols)
    display_df['Path Inclusion %'] = display_df['Path Inclusion %'].map('{:.1%}'.format)
    display_df['Position-Weighted Score'] = display_df['Position-Weighted Score'].map('{:.1f}'.format)
    display_df['Repeat Conv Lift'] = display_df['Repeat Conv Lift'].map('{:.2f}x'.format)
    display_df['First-Touch Dominance %'] = display_df['First-Touch Dominance %'].map('{:.1%}'.format)
    st.dataframe(display_df, use_container_width=True)

    st.markdown("---")

    # --- Quadrant Scatter Plot ---
    st.markdown("### Assisted Conversion Quadrant")
    median_x = summary_df['path_inclusion_rate'].median()
    median_y = summary_df['position_weighted_score'].median()

    fig_scatter = px.scatter(
        summary_df,
        x='path_inclusion_rate',
        y='position_weighted_score',
        size='n_conversions',
        color='first_touch_dominance',
        text='dimension_value',
        color_continuous_scale='RdYlBu',
        title=f'Assisted Conversion Quadrant — by {dimension}',
        labels={
            'path_inclusion_rate': 'Path Inclusion Rate',
            'position_weighted_score': 'Position-Weighted Score (0–100)',
            'first_touch_dominance': 'First-Touch Dominance'
        }
    )
    # Quadrant lines
    fig_scatter.add_vline(x=median_x, line_dash='dash', line_color='gray')
    fig_scatter.add_hline(y=median_y, line_dash='dash', line_color='gray')

    # Quadrant labels
    x_max = summary_df['path_inclusion_rate'].max()
    y_max = summary_df['position_weighted_score'].max()
    fig_scatter.add_annotation(x=x_max, y=y_max, text="Full-Funnel Workhorse", showarrow=False, font=dict(color='gray', size=10))
    fig_scatter.add_annotation(x=0, y=y_max, text="Closer (Low Reach)", showarrow=False, font=dict(color='gray', size=10))
    fig_scatter.add_annotation(x=x_max, y=0, text="Initiator (High Reach)", showarrow=False, font=dict(color='gray', size=10))
    fig_scatter.add_annotation(x=0, y=0, text="Supporting Role", showarrow=False, font=dict(color='gray', size=10))

    fig_scatter.update_traces(textposition='top center')
    fig_scatter.update_xaxes(tickformat='.0%')
    fig_scatter.update_layout(**PLOTLY_LAYOUT)
    st.plotly_chart(fig_scatter, use_container_width=True)

    st.markdown("---")

    # --- Stacked Bar: Direct vs Assisted ---
    st.markdown("### Direct (Last-Touch) vs Assisted Appearances")
    assist_rows = []
    for val in dim_values:
        val_mask = df_interactions[dimension_col] == val
        lt_count = int(df_interactions[val_mask & df_interactions['is_last_touch']].shape[0])
        non_lt_count = int(df_interactions[val_mask & ~df_interactions['is_last_touch']].shape[0])
        assist_rows.append({'value': val, 'Last-Touch': lt_count, 'Assisted (Non-Last-Touch)': non_lt_count})

    assist_df = pd.DataFrame(assist_rows)
    assist_df['total'] = assist_df['Last-Touch'] + assist_df['Assisted (Non-Last-Touch)']
    assist_df = assist_df.sort_values('total', ascending=False).head(20)

    fig_bar = go.Figure()
    fig_bar.add_trace(go.Bar(name='Last-Touch', x=assist_df['value'], y=assist_df['Last-Touch'], marker_color=COLORS['conversion_orange']))
    fig_bar.add_trace(go.Bar(name='Assisted', x=assist_df['value'], y=assist_df['Assisted (Non-Last-Touch)'], marker_color=COLORS['google_blue']))
    fig_bar.update_layout(
        barmode='stack',
        title=f'Direct vs Assisted Appearances by {dimension}',
        xaxis_title=dimension,
        yaxis_title='Appearances',
        xaxis_tickangle=45,
        **PLOTLY_LAYOUT
    )
    st.plotly_chart(fig_bar, use_container_width=True)
