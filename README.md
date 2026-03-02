# CM360 Path-to-Conversion Analyser

A Streamlit application that ingests a Campaign Manager 360 (CM360) Path-to-Conversion (P2C) CSV export and produces a multi-tab interactive analytics dashboard.

## Features

| Tab | Description |
|-----|-------------|
| 📊 Overall Stats | KPI cards, daily conversions chart, attribution split |
| 👤 User Paths | Random or manual path viewer — see individual conversion journeys |
| 📱 Device Analysis | Per-device metrics: path inclusion, first/last touch, avg days to convert |
| 🎯 Assisted Conversions | Position-weighted contribution scores, quadrant scatter, path lift analysis |
| 📢 Campaign Analysis | First vs last touch by campaign, impressions per conversion, days to convert |
| 🌐 Site Analysis | Same as Campaign but by publisher site |
| 🔢 N-gram Analysis | Most common channel/campaign/site sequences, Sankey flow, transition heatmap |
| ⭕ Venn Diagram | Conversion ID overlap across Floodlight activities or attribution types |
| 📈 Frequency | Impression frequency distribution with saturation insight |
| 🔗 UTM Sources | UTM cross-reference (requires Custom Floodlight Variable) |

---

## Local Setup

### Prerequisites

- Python 3.10+
- pip

### Install and Run

```bash
# Clone or download this repo
cd P2PViz

# Install dependencies
pip install -r requirements.txt

# Run the app
streamlit run app.py
```

The app will open at `http://localhost:8501`.

---

## CM360 Report Setup

### Step 1: Create the Report

1. Navigate to **Campaign Manager 360 → Reporting → Report Builder**
2. Click **+ New Report**
3. Select Report Type: **Path to Conversion**
4. Set Export Format: **CSV**
5. Ensure Pivot mode is **Non-pivoted** (default — do NOT use "Pivot On Interaction Path")

### Step 2: Required Columns (auto-included)

These columns are always in the P2C report and require no action:

- `Conversion ID`
- `Activity Date/Time`
- `Floodlight Attribution Type`
- `Path Length`
- `ZIP/Postal Code`
- `Interaction Date/Time`
- `Interaction Number`
- `Interaction Channel`
- `Interaction Type`
- `Placement`

### Step 3: Optional Columns (add for richer analysis)

In the CM360 Report Builder, under **Per Interaction Dimensions**, add:

| CM360 Label | Enables |
|-------------|---------|
| `Campaign` | Campaign Analysis tab, campaign filtering |
| `Site (CM360)` | Site Analysis tab |
| `Device` | Device Analysis tab |
| `Activity` | Multi-activity Venn diagram |

### Step 4: Date Range & Filters

- Set your desired date range
- Under **Floodlight Configuration**, select the relevant advertiser config
- Under **Activity**, select the Floodlight activities you want to analyse

### Step 5: Export

- Run the report and export as **CSV**
- The file is tab-separated (despite the `.csv` extension)

---

## Deploying to Streamlit Cloud

1. Push this repo to GitHub (public or private)
2. Go to [share.streamlit.io](https://share.streamlit.io) → **New App**
3. Connect your GitHub repo
4. Set entrypoint to `app.py`
5. Click **Deploy**

Streamlit Cloud reads `requirements.txt` automatically. The result is a shareable public URL with no server management required.

---

## File Structure

```
P2PViz/
├── app.py                        # Main Streamlit entrypoint
├── requirements.txt
├── README.md
├── utils/
│   ├── __init__.py
│   ├── parser.py                 # CSV loading, header detection, type conversion
│   ├── path_builder.py           # Build df_conversions and df_interactions
│   ├── metrics.py                # Shared metric calculation and filter functions
│   └── ngram.py                  # N-gram extraction utilities
└── views/
    ├── __init__.py
    ├── overview.py               # Tab 1: Overall Stats
    ├── user_paths.py             # Tab 2: Sample User Path
    ├── device_analysis.py        # Tab 3: Device Analysis
    ├── assisted_analysis.py      # Tab 4: Assisted Conversion Analysis
    ├── campaign_analysis.py      # Tab 5: Campaign Analysis
    ├── site_analysis.py          # Tab 6: Site Analysis
    ├── ngram_view.py             # Tab 7: N-gram Analysis
    ├── venn_view.py              # Tab 8: Multi-Conversion Venn
    ├── frequency_view.py         # Tab 9: Conversion Frequency
    └── utm_view.py               # Tab 10: UTM Cross-Reference
```

---

## Data Notes

- The CM360 P2C export is **tab-separated** (not comma-separated)
- `Interaction Number 1` = **last touch** (most recent before conversion). Higher numbers = earlier in path.
- The app re-numbers interactions chronologically (1 = earliest, N = last touch) for display
- `Conversion ID` is exported in scientific notation (e.g. `1.0001E+19`) — the parser handles this automatically
- Conversions with no interaction rows (unattributed) are included in total counts but excluded from path-based metrics
