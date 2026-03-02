"""
views/venn_view.py
Tab 8: Multi-Conversion Venn Diagram — overlap across Floodlight activities or attribution types.
"""
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
try:
    from matplotlib_venn import venn2, venn3
    VENN_AVAILABLE = True
except ImportError:
    VENN_AVAILABLE = False


def render_venn(df_conversions: pd.DataFrame, metadata: dict = None):
    st.markdown('<div class="tab-header">⭕ Multi-Conversion Venn Diagram</div>', unsafe_allow_html=True)

    if not VENN_AVAILABLE:
        st.error(
            "The `matplotlib-venn` package is not installed. "
            "Run `pip install matplotlib-venn` to enable this tab."
        )
        return

    if len(df_conversions) == 0:
        st.warning("No conversions match the current filters.")
        return

    # --- Availability check ---
    has_activity_col = (
        'activity_name' in df_conversions.columns and
        (df_conversions['activity_name'] != 'Unknown').any()
    )
    has_multiple_attribution = df_conversions['attribution_type'].nunique() > 1

    if not has_activity_col and not has_multiple_attribution:
        st.warning(
            "Not enough distinct segments to build a Venn. "
            "Add 'Activity' as a dimension in CM360 Report Builder for richer overlap analysis."
        )
        return

    # --- Segment selector ---
    if has_activity_col:
        segment_col = 'activity_name'
        segment_label = "Activity"
    else:
        segment_col = 'attribution_type'
        segment_label = "Attribution Type"

    all_segments = sorted(df_conversions[segment_col].dropna().unique().tolist())

    if len(all_segments) < 2:
        st.warning("Need at least 2 distinct segments to draw a Venn diagram.")
        return

    mode = st.radio("Compare", ["2 Segments", "3 Segments"], horizontal=True)
    col1, col2 = st.columns(2)

    seg_a = col1.selectbox(f"{segment_label} A", all_segments, index=0, key='venn_a')
    remaining_b = [s for s in all_segments if s != seg_a]
    seg_b = col2.selectbox(f"{segment_label} B", remaining_b, key='venn_b')

    seg_c = None
    if mode == "3 Segments":
        remaining_c = [s for s in all_segments if s not in [seg_a, seg_b]]
        if remaining_c:
            seg_c = st.selectbox(f"{segment_label} C", remaining_c, key='venn_c')
        else:
            st.warning("Not enough segments for a 3-way Venn.")
            mode = "2 Segments"

    # --- Set construction ---
    set_a = set(df_conversions[df_conversions[segment_col] == seg_a]['conversion_id'])
    set_b = set(df_conversions[df_conversions[segment_col] == seg_b]['conversion_id'])
    set_c = set(df_conversions[df_conversions[segment_col] == seg_c]['conversion_id']) if seg_c else set()

    # --- Venn rendering ---
    fig, ax = plt.subplots(figsize=(8, 6))

    if mode == "2 Segments":
        v = venn2([set_a, set_b], set_labels=(seg_a, seg_b), ax=ax)
        if v.get_patch_by_id('10'):
            v.get_patch_by_id('10').set_color('#4285F4')
            v.get_patch_by_id('10').set_alpha(0.6)
        if v.get_patch_by_id('01'):
            v.get_patch_by_id('01').set_color('#EA4335')
            v.get_patch_by_id('01').set_alpha(0.6)
        if v.get_patch_by_id('11'):
            v.get_patch_by_id('11').set_color('#34A853')
            v.get_patch_by_id('11').set_alpha(0.6)
    else:
        v = venn3([set_a, set_b, set_c], set_labels=(seg_a, seg_b, seg_c), ax=ax)

    ax.set_title(f"Conversion ID Overlap — {segment_label}", fontsize=13)
    st.pyplot(fig)
    plt.close()

    # --- Segment breakdown table ---
    st.markdown("### Segment Breakdown")
    total = len(df_conversions)

    if mode == "2 Segments":
        only_a = set_a - set_b
        only_b = set_b - set_a
        both = set_a & set_b

        breakdown_data = [
            {segment_label: f"Only {seg_a}", 'Count': len(only_a), '% of Total': f"{len(only_a)/total:.1%}"},
            {segment_label: f"Only {seg_b}", 'Count': len(only_b), '% of Total': f"{len(only_b)/total:.1%}"},
            {segment_label: f"Both {seg_a} & {seg_b}", 'Count': len(both), '% of Total': f"{len(both)/total:.1%}"},
        ]
        segment_data = {f"Only {seg_a}": only_a, f"Only {seg_b}": only_b, f"Both": both}
    else:
        a_only = set_a - set_b - set_c
        b_only = set_b - set_a - set_c
        c_only = set_c - set_a - set_b
        ab_only = (set_a & set_b) - set_c
        ac_only = (set_a & set_c) - set_b
        bc_only = (set_b & set_c) - set_a
        abc = set_a & set_b & set_c

        breakdown_data = [
            {segment_label: f"Only {seg_a}", 'Count': len(a_only), '% of Total': f"{len(a_only)/total:.1%}"},
            {segment_label: f"Only {seg_b}", 'Count': len(b_only), '% of Total': f"{len(b_only)/total:.1%}"},
            {segment_label: f"Only {seg_c}", 'Count': len(c_only), '% of Total': f"{len(c_only)/total:.1%}"},
            {segment_label: f"{seg_a} & {seg_b} only", 'Count': len(ab_only), '% of Total': f"{len(ab_only)/total:.1%}"},
            {segment_label: f"{seg_a} & {seg_c} only", 'Count': len(ac_only), '% of Total': f"{len(ac_only)/total:.1%}"},
            {segment_label: f"{seg_b} & {seg_c} only", 'Count': len(bc_only), '% of Total': f"{len(bc_only)/total:.1%}"},
            {segment_label: f"All three", 'Count': len(abc), '% of Total': f"{len(abc)/total:.1%}"},
        ]
        segment_data = {
            f"Only {seg_a}": a_only, f"Only {seg_b}": b_only, f"Only {seg_c}": c_only,
            f"{seg_a}&{seg_b}": ab_only, f"{seg_a}&{seg_c}": ac_only, f"{seg_b}&{seg_c}": bc_only,
            f"All": abc
        }

    st.dataframe(pd.DataFrame(breakdown_data), use_container_width=True)

    # --- Download ---
    rows = []
    for seg, ids in segment_data.items():
        for cid in ids:
            rows.append({'segment': seg, 'conversion_id': cid})
    if rows:
        seg_df = pd.DataFrame(rows)
        st.download_button(
            "📥 Download Segment Conversion IDs (CSV)",
            data=seg_df.to_csv(index=False),
            file_name="venn_segments.csv",
            mime="text/csv"
        )
