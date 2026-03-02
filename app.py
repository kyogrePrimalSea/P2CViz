"""
app.py
CM360 Path-to-Conversion Analyser — main Streamlit entrypoint.
"""
import io
import streamlit as st
import pandas as pd

from utils.parser import load_p2c_report, load_p2c_report_from_bytes, download_from_gdrive
from utils.path_builder import build_dataframes
from utils.metrics import apply_filters
from views.overview import render_overview
from views.user_paths import render_user_paths
from views.device_analysis import render_device_analysis
from views.assisted_analysis import render_assisted_analysis
from views.campaign_analysis import render_campaign_analysis
from views.site_analysis import render_site_analysis
from views.ngram_view import render_ngram_analysis
from views.venn_view import render_venn
from views.frequency_view import render_frequency
from views.utm_view import render_utm

# ---------------------------------------------------------------------------
# Page config — must be the FIRST Streamlit call
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="CM360 Path-to-Conversion Analyser",
    page_icon="🔄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------------------------------------------------------------
# Global CSS
# ---------------------------------------------------------------------------
st.markdown("""
<style>
    .metric-card {
        background: white;
        border: 1px solid #DADCE0;
        border-radius: 8px;
        padding: 16px;
        text-align: center;
    }
    .metric-value {
        font-size: 28px;
        font-weight: bold;
        color: #1A3A6B;
    }
    .metric-label {
        font-size: 11px;
        color: #5F6368;
        margin-top: 4px;
    }
    .tab-header {
        font-size: 20px;
        font-weight: bold;
        color: #1A3A6B;
        margin-bottom: 16px;
    }
    div[data-testid="stMetricValue"] {
        font-size: 28px;
        font-weight: bold;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Title
# ---------------------------------------------------------------------------
st.title("🔄 CM360 Path-to-Conversion Analyser")
st.caption("Upload a CM360 Path-to-Conversion CSV export or paste a Google Drive link to begin analysis.")

# ---------------------------------------------------------------------------
# File loading — two methods
# ---------------------------------------------------------------------------
st.markdown("### Load Report")
load_method = st.radio(
    "How would you like to load your report?",
    ["📁 Upload File", "🔗 Google Drive Link"],
    horizontal=True
)

raw_df = None
metadata = None
optional_cols = None
load_error = None

if load_method == "📁 Upload File":
    uploaded_file = st.file_uploader(
        "Upload CM360 P2C Report (TSV/CSV)",
        type=['csv', 'tsv', 'txt'],
        help="Export a Path-to-Conversion report from Campaign Manager 360. Must be tab-separated unpivoted format."
    )
    if uploaded_file is not None:
        with st.spinner("Parsing report..."):
            try:
                raw_df, metadata, optional_cols = load_p2c_report(uploaded_file)
            except Exception as e:
                load_error = str(e)

else:  # Google Drive
    gdrive_url = st.text_input(
        "Paste Google Drive shareable link",
        placeholder="https://drive.google.com/file/d/..."
    )
    if gdrive_url.strip():
        with st.spinner("Downloading from Google Drive..."):
            try:
                file_bytes = download_from_gdrive(gdrive_url.strip())
                raw_df, metadata, optional_cols = load_p2c_report_from_bytes(file_bytes)
            except Exception as e:
                load_error = str(e)

# ---------------------------------------------------------------------------
# Error display or welcome screen
# ---------------------------------------------------------------------------
if load_error:
    st.error(f"Failed to load report: {load_error}")
    st.info("Please ensure the file is a valid CM360 Path-to-Conversion export in tab-separated format.")

if raw_df is None:
    st.info("👆 Upload a CM360 Path-to-Conversion CSV to get started.")
    st.markdown("""
    **Required report columns (auto-detected):**
    - `Conversion ID`, `Activity Date/Time`, `Floodlight Attribution Type`, `Path Length`
    - `Interaction Date/Time`, `Interaction Number`, `Interaction Channel`, `Interaction Type`, `Placement`

    **Optional columns (add in CM360 Report Builder for richer analysis):**
    - `Campaign` — enables Campaign Analysis tab
    - `Site (CM360)` — enables Site Analysis tab
    - `Device` — enables Device Analysis tab
    - `Activity` — enables multi-activity Venn diagram

    **CM360 Report Setup:**
    1. Go to **Campaign Manager 360 → Reporting → Report Builder**
    2. Report Type: **Path to Conversion**
    3. Pivot mode: **Non-pivoted** (default)
    4. Export Format: **CSV**
    5. Add optional dimensions under "Per Interaction Dimensions"
    """)
    st.stop()

# ---------------------------------------------------------------------------
# Build canonical dataframes
# ---------------------------------------------------------------------------
with st.spinner("Building dataframes..."):
    df_conversions, df_interactions = build_dataframes(raw_df, optional_cols)

# ---------------------------------------------------------------------------
# Sidebar Filters
# ---------------------------------------------------------------------------
with st.sidebar:
    st.title("🔍 Filters")
    st.markdown("---")

    # Attribution Type
    all_attribution = sorted(df_conversions['attribution_type'].dropna().unique().tolist())
    selected_attribution = st.multiselect(
        "Attribution Type",
        options=all_attribution,
        default=all_attribution,
        help="View-through, Click-through, Unattributed"
    )

    # Date Range
    min_date = df_conversions['conversion_datetime'].min().date()
    max_date = df_conversions['conversion_datetime'].max().date()
    date_range = st.date_input(
        "Conversion Date Range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date
    )

    # Channel filter
    all_channels = sorted([
        c for c in df_interactions['channel'].dropna().unique().tolist()
        if c not in ('--', '')
    ])
    selected_channels = st.multiselect(
        "Interaction Channels",
        options=all_channels,
        default=all_channels
    )

    # Campaign filter — only show if Campaign column was in report
    if df_interactions['campaign'].ne('Unknown').any():
        all_campaigns = sorted([
            c for c in df_interactions['campaign'].dropna().unique().tolist()
            if c not in ('Unknown', '')
        ])
        if all_campaigns:
            selected_campaigns = st.multiselect(
                "Campaigns",
                options=all_campaigns,
                default=all_campaigns
            )
    else:
        st.caption("ℹ️ Add 'Campaign' dimension to CM360 report to enable campaign filtering.")

    st.markdown("---")
    st.caption(f"📊 {len(df_conversions):,} conversions loaded")
    if metadata:
        st.caption(f"📅 {metadata.get('date_range', 'Unknown period')}")
        st.caption(f"🔧 Account: {metadata.get('account_id', 'Unknown')}")
        if metadata.get('activities'):
            for act in metadata['activities']:
                st.caption(f"🎯 {act}")

    st.markdown("---")
    st.caption("**Optional columns detected:**")
    for app_name in optional_cols:
        st.caption(f"✅ {app_name}")

# ---------------------------------------------------------------------------
# Apply filters
# ---------------------------------------------------------------------------
if not selected_attribution:
    selected_attribution = all_attribution  # default to all if nothing selected

filtered_convs, filtered_ints = apply_filters(
    df_conversions,
    df_interactions,
    selected_attribution,
    date_range,
    selected_channels
)

if len(filtered_convs) == 0:
    st.warning("⚠️ No conversions match the current filter selection. Please adjust the sidebar filters.")
    st.stop()

st.caption(f"Showing **{len(filtered_convs):,}** conversions after filters.")

# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------
tabs = st.tabs([
    "📊 Overall Stats",
    "👤 User Paths",
    "📱 Device Analysis",
    "🎯 Assisted Conversions",
    "📢 Campaign Analysis",
    "🌐 Site Analysis",
    "🔢 N-gram Analysis",
    "⭕ Venn Diagram",
    "📈 Frequency",
    "🔗 UTM Sources",
])

with tabs[0]:
    render_overview(filtered_convs, filtered_ints, metadata)

with tabs[1]:
    render_user_paths(filtered_convs, filtered_ints)

with tabs[2]:
    render_device_analysis(filtered_convs, filtered_ints)

with tabs[3]:
    render_assisted_analysis(filtered_convs, filtered_ints)

with tabs[4]:
    render_campaign_analysis(filtered_convs, filtered_ints)

with tabs[5]:
    render_site_analysis(filtered_convs, filtered_ints)

with tabs[6]:
    render_ngram_analysis(filtered_convs, filtered_ints)

with tabs[7]:
    render_venn(filtered_convs, metadata)

with tabs[8]:
    render_frequency(filtered_convs)

with tabs[9]:
    render_utm(filtered_convs)
