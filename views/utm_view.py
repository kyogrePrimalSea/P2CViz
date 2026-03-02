"""
views/utm_view.py
Tab 10: UTM Cross-Reference — UTM source breakdown if available.
"""
import streamlit as st
import pandas as pd
import plotly.express as px

PLOTLY_LAYOUT = dict(
    font=dict(family="Google Sans, Arial, sans-serif", size=12),
    plot_bgcolor='white',
    paper_bgcolor='white',
    margin=dict(l=40, r=40, t=60, b=80),
    showlegend=True,
    legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1)
)

UTM_CANDIDATE_COLS = [
    'utm_source', 'utm source', 'UTM Source',
    'landing page', 'Landing Page', 'URL',
    'custom floodlight variable', 'u1', 'u2',
]


def render_utm(df_conversions: pd.DataFrame):
    st.markdown('<div class="tab-header">🔗 UTM Cross-Reference</div>', unsafe_allow_html=True)

    if len(df_conversions) == 0:
        st.warning("No conversions match the current filters.")
        return

    # --- Availability check ---
    utm_col = None
    col_lower = {c.lower(): c for c in df_conversions.columns}
    for candidate in UTM_CANDIDATE_COLS:
        if candidate.lower() in col_lower:
            utm_col = col_lower[candidate.lower()]
            break

    if utm_col is None:
        st.warning(
            "No UTM source column detected in this report. "
            "To enable this tab, add a Custom Floodlight Variable capturing `utm_source` to your CM360 report."
        )
        st.markdown("""
        **How to add UTM tracking:**
        1. In CM360, go to **Floodlight → Custom Variables**
        2. Create a Custom Floodlight Variable (u-variable) that captures `utm_source` from the landing page URL
        3. Add this variable as a dimension in your P2C report
        """)
        return

    st.success(f"UTM column detected: **{utm_col}**")

    # --- UTM Source Table ---
    st.markdown("### UTM Source Distribution")
    st.caption(
        "Count of conversions with each UTM source recorded on the user's path (at conversion or earlier). "
        "'0' or blank indicates no UTM parameters were captured."
    )

    utm_counts = df_conversions.groupby(utm_col).size().reset_index(name='Conversions')
    utm_counts.columns = ['UTM Source', 'Conversions']
    utm_counts = utm_counts.sort_values('Conversions', ascending=False)
    total = utm_counts['Conversions'].sum()
    utm_counts['% of Total'] = (utm_counts['Conversions'] / total).map('{:.1%}'.format)
    utm_counts['Note'] = utm_counts['UTM Source'].apply(
        lambda x: '⚠️ No UTM captured' if str(x) in ['0', '', 'nan', 'None'] else ''
    )

    st.dataframe(utm_counts, use_container_width=True)

    # --- Donut Chart ---
    st.markdown("### UTM Source Breakdown (Top 10, excluding no-UTM)")
    no_utm_vals = ['0', '', 'nan', 'None']
    utm_chart = utm_counts[~utm_counts['UTM Source'].astype(str).isin(no_utm_vals)].head(10)

    if len(utm_chart) > 0:
        fig = px.pie(
            utm_chart,
            values='Conversions',
            names='UTM Source',
            title='UTM Source Distribution (excluding no-UTM)',
            hole=0.4,
            color_discrete_sequence=px.colors.qualitative.G10
        )
        fig.update_layout(**PLOTLY_LAYOUT)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No conversions with UTM sources found.")

    # --- No UTM summary ---
    no_utm_count = utm_counts[utm_counts['UTM Source'].astype(str).isin(no_utm_vals)]['Conversions'].sum()
    if no_utm_count > 0:
        st.warning(
            f"⚠️ **{no_utm_count:,} conversions ({no_utm_count/total:.0%})** had no UTM parameters captured. "
            "Ensure your landing pages pass UTM parameters to CM360 Custom Floodlight Variables."
        )
