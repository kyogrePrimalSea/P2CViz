"""
views/ngram_view.py
Tab 7: N-gram Path Analysis — frequency table, Sankey diagram, transition heatmap.
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from utils.ngram import compute_ngram_frequencies, extract_ngrams

PLOTLY_LAYOUT = dict(
    font=dict(family="Google Sans, Arial, sans-serif", size=12),
    plot_bgcolor='white',
    paper_bgcolor='white',
    margin=dict(l=40, r=40, t=60, b=80),
    showlegend=True,
    legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1)
)


def build_sankey(df_conversions: pd.DataFrame, dimension: str, min_freq: int) -> go.Figure:
    bigrams = compute_ngram_frequencies(df_conversions, dimension, n=2)
    if len(bigrams) == 0:
        return None
    bigrams = bigrams[bigrams['count'] >= min_freq]
    if len(bigrams) == 0:
        return None

    sources = [ng[0] for ng in bigrams['ngram']]
    targets = [ng[1] for ng in bigrams['ngram']]
    all_nodes = list(dict.fromkeys(sources + targets))
    node_idx = {node: i for i, node in enumerate(all_nodes)}

    fig = go.Figure(go.Sankey(
        node=dict(
            pad=15,
            thickness=20,
            line=dict(color="black", width=0.5),
            label=all_nodes,
            color="#4285F4"
        ),
        link=dict(
            source=[node_idx[s] for s in sources],
            target=[node_idx[t] for t in targets],
            value=bigrams['count'].tolist(),
            color="rgba(66, 133, 244, 0.4)"
        )
    ))
    fig.update_layout(
        title_text=f"Conversion Path Flow — {dimension}",
        font_size=11,
        paper_bgcolor='white'
    )
    return fig


def build_transition_heatmap(bigrams_df: pd.DataFrame, dimension: str) -> go.Figure:
    if len(bigrams_df) == 0:
        return None

    src_list = [ng[0] for ng in bigrams_df['ngram']]
    tgt_list = [ng[1] for ng in bigrams_df['ngram']]
    counts = bigrams_df['count'].tolist()

    heat_df = pd.DataFrame({'source': src_list, 'target': tgt_list, 'count': counts})
    pivot = heat_df.pivot_table(index='source', columns='target', values='count', fill_value=0)

    top_n = 15
    top_sources = pivot.sum(axis=1).nlargest(top_n).index
    top_targets = pivot.sum(axis=0).nlargest(top_n).index
    pivot = pivot.loc[pivot.index.isin(top_sources), pivot.columns.isin(top_targets)]

    fig = px.imshow(
        pivot,
        labels=dict(x=f"Next {dimension}", y=f"Previous {dimension}", color="Count"),
        title=f"Transition Heatmap: Which {dimension} follows which?",
        color_continuous_scale='Blues',
        aspect='auto'
    )
    fig.update_xaxes(tickangle=45)
    return fig


def render_ngram_analysis(df_conversions: pd.DataFrame, df_interactions: pd.DataFrame):
    st.markdown('<div class="tab-header">🔢 N-gram Path Analysis</div>', unsafe_allow_html=True)

    if len(df_conversions) == 0:
        st.warning("No conversions match the current filters.")
        return

    # --- Controls ---
    col1, col2, col3, col4 = st.columns(4)
    dimension = col1.selectbox("Path Dimension", ['Channel', 'Campaign', 'Site', 'Device'])
    n_value = col2.slider("N (path length)", min_value=1, max_value=5, value=2)
    min_freq = col3.number_input("Min frequency", min_value=1, value=5, step=5)
    normalize = col4.checkbox("Normalize by total paths", value=True)

    # Check dimension availability
    path_col_map = {
        'Campaign': 'path_campaigns',
        'Channel': 'path_channels',
        'Site': 'path_sites',
        'Device': 'path_devices',
    }
    path_col = path_col_map.get(dimension, 'path_channels')

    if path_col not in df_conversions.columns:
        st.warning(f"Column '{path_col}' not available. Add the {dimension} dimension to your CM360 report.")
        return

    # Check if there's any actual data
    has_data = df_conversions[path_col].apply(lambda x: isinstance(x, list) and len(x) >= n_value).any()
    if not has_data:
        st.warning(f"Not enough path data for {n_value}-gram analysis on {dimension}.")
        return

    # --- N-gram computation ---
    ngrams_df = compute_ngram_frequencies(df_conversions, dimension, n_value)

    if len(ngrams_df) == 0:
        st.warning(f"No {n_value}-grams found in the data.")
        return

    # --- Frequency Table ---
    st.markdown(f"### Top {dimension} {n_value}-grams")
    display_df = ngrams_df[ngrams_df['count'] >= min_freq].head(25).copy()

    if len(display_df) == 0:
        st.warning(f"No {n_value}-grams meet the minimum frequency of {min_freq}.")
    else:
        display_df['pct_display'] = display_df['pct_of_paths'].map('{:.1%}'.format)
        st.dataframe(
            display_df[['ngram_str', 'count', 'pct_display']].rename(columns={
                'ngram_str': 'Path Sequence',
                'count': 'Count',
                'pct_display': '% of Paths'
            }),
            use_container_width=True
        )

    # --- Bar chart of top ngrams ---
    if len(display_df) > 0:
        y_col = 'pct_of_paths' if normalize else 'count'
        y_label = '% of Paths' if normalize else 'Count'

        fig_bar = px.bar(
            display_df.head(15),
            x='count' if not normalize else 'pct_of_paths',
            y='ngram_str',
            orientation='h',
            title=f'Top {dimension} {n_value}-grams',
            labels={y_col: y_label, 'ngram_str': 'Path Sequence'},
            color_discrete_sequence=['#4285F4']
        )
        if normalize:
            fig_bar.update_xaxes(tickformat='.1%')
        fig_bar.update_yaxes(autorange='reversed')
        fig_bar.update_layout(**PLOTLY_LAYOUT)
        st.plotly_chart(fig_bar, use_container_width=True)

    st.markdown("---")

    # --- Sankey Diagram ---
    if n_value >= 2:
        st.markdown("### Conversion Path Flow (Sankey)")
        with st.spinner("Building Sankey diagram..."):
            fig_sankey = build_sankey(df_conversions, dimension, int(min_freq))
        if fig_sankey:
            st.plotly_chart(fig_sankey, use_container_width=True)
        else:
            st.info("Not enough bigram data to build a Sankey diagram with the current frequency filter.")

    # --- Transition Heatmap ---
    show_heatmap = st.checkbox("Show Transition Heatmap", value=(n_value == 2))
    if show_heatmap:
        st.markdown("### Transition Heatmap")
        bigrams_df = compute_ngram_frequencies(df_conversions, dimension, n=2)
        bigrams_df = bigrams_df[bigrams_df['count'] >= min_freq]
        if len(bigrams_df) > 0:
            fig_heat = build_transition_heatmap(bigrams_df, dimension)
            if fig_heat:
                fig_heat.update_layout(**{k: v for k, v in PLOTLY_LAYOUT.items() if k != 'showlegend'})
                st.plotly_chart(fig_heat, use_container_width=True)
        else:
            st.info("Not enough data for transition heatmap.")
