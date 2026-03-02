"""
utils/parser.py
CM360 Path-to-Conversion CSV parser.
Handles comma-separated OR tab-separated CM360 exports with metadata header rows.
Separator is auto-detected from the file content.
"""
import tempfile
import os
import pandas as pd
import streamlit as st


# ---------------------------------------------------------------------------
# Separator auto-detection
# ---------------------------------------------------------------------------

def detect_separator(filepath: str) -> str:
    """
    Sniff the first 20 non-empty lines to determine whether the file uses
    commas or tabs as its delimiter.
    Returns ',' or '\t'.
    """
    with open(filepath, 'r', encoding='utf-8-sig') as f:
        sample_lines = []
        for line in f:
            if line.strip():
                sample_lines.append(line)
            if len(sample_lines) >= 20:
                break

    tab_count = sum(line.count('\t') for line in sample_lines)
    comma_count = sum(line.count(',') for line in sample_lines)
    return '\t' if tab_count >= comma_count else ','


# ---------------------------------------------------------------------------
# Header detection
# ---------------------------------------------------------------------------

def find_header_row_index(filepath: str, sep: str) -> int:
    """
    Scans line by line. Returns the index of the column header row.
    The header row is the line immediately after a line whose first cell
    stripped equals 'Report Fields'.
    """
    with open(filepath, 'r', encoding='utf-8-sig') as f:
        lines = f.readlines()

    for i, line in enumerate(lines):
        first_cell = line.split(sep)[0].strip().strip('"')
        if first_cell.lower() == 'report fields':
            # Header is the very next non-blank line
            for j in range(i + 1, len(lines)):
                if lines[j].strip():
                    return j

    # Fallback: look for a line containing 'Conversion ID' and 'Interaction Number'
    for i, line in enumerate(lines):
        if 'Conversion ID' in line and 'Interaction Number' in line:
            return i

    raise ValueError(
        "Could not find header row. Expected a 'Report Fields' label row followed by "
        "the column header row containing 'Conversion ID' and 'Interaction Number'."
    )


# ---------------------------------------------------------------------------
# Metadata extraction
# ---------------------------------------------------------------------------

def extract_metadata(filepath: str, header_row_index: int, sep: str) -> dict:
    """
    Reads all rows before header_row_index.
    First cell = key, second cell = value (if present).
    Special case: 'Activity' key can appear multiple times — collect as list.
    """
    metadata = {
        'activities': [],
        'date_range': '',
        'account_id': '',
        'report_timezone': '',
        'floodlight_config': '',
        'date_generated': '',
        'max_click_interactions': '',
        'max_impression_interactions': '',
    }

    with open(filepath, 'r', encoding='utf-8-sig') as f:
        lines = f.readlines()

    for i, line in enumerate(lines):
        if i >= header_row_index:
            break
        parts = [p.strip().strip('"') for p in line.split(sep)]
        if len(parts) < 2 or not parts[0]:
            continue
        key = parts[0].lower()
        value = parts[1] if len(parts) > 1 else ''

        if key == 'activity':
            metadata['activities'].append(value)
        elif key == 'date range':
            metadata['date_range'] = value
        elif key == 'account id':
            metadata['account_id'] = value
        elif key == 'report time zone':
            metadata['report_timezone'] = value
        elif key == 'floodlight configuration':
            metadata['floodlight_config'] = value
        elif key == 'date/time generated':
            metadata['date_generated'] = value
        elif key == 'max number of click interactions':
            metadata['max_click_interactions'] = value
        elif key == 'max number of impression interactions':
            metadata['max_impression_interactions'] = value

    return metadata


# ---------------------------------------------------------------------------
# Raw DataFrame loader
# ---------------------------------------------------------------------------

def load_raw_df(filepath: str, header_row_index: int, sep: str) -> pd.DataFrame:
    """
    Load the comma- or tab-separated data starting from header_row_index.
    Use dtype=str to prevent pandas from mangling Conversion IDs in scientific notation.
    """
    df = pd.read_csv(
        filepath,
        sep=sep,
        skiprows=header_row_index,
        dtype=str,
        encoding='utf-8-sig',
        quoting=0,          # QUOTE_MINIMAL — handles quoted fields in CSV exports
        on_bad_lines='warn'
    )
    # Strip all column name whitespace
    df.columns = [c.strip() for c in df.columns]
    # Drop fully empty rows
    df = df.dropna(how='all')
    # Drop rows where Conversion ID is blank or NaN
    df = df[df['Conversion ID'].notna() & (df['Conversion ID'].str.strip() != '')]
    return df


# ---------------------------------------------------------------------------
# Conversion ID normalisation
# ---------------------------------------------------------------------------

def normalise_conversion_id(val: str) -> str:
    """
    Convert scientific notation string like '1.0001E+19' to a stable string key.
    Strategy: convert to float, then to int (accepts minor precision loss for grouping),
    then back to string. This gives a consistent grouping key even if not the exact original ID.
    """
    try:
        return str(int(float(val.strip())))
    except (ValueError, AttributeError):
        return str(val).strip()


# ---------------------------------------------------------------------------
# Type conversions
# ---------------------------------------------------------------------------

def apply_type_conversions(df: pd.DataFrame) -> pd.DataFrame:
    """Apply correct types to each column after loading raw string df."""
    # Conversion ID — normalise scientific notation
    df['Conversion ID'] = df['Conversion ID'].apply(normalise_conversion_id)

    # Activity Date/Time — conversion event timestamp (DD/MM/YYYY H:MM)
    df['Activity Date/Time'] = pd.to_datetime(
        df['Activity Date/Time'],
        dayfirst=True,
        errors='coerce'
    )

    # Path Length
    df['Path Length'] = pd.to_numeric(df['Path Length'], errors='coerce').fillna(0).astype(int)

    # Interaction Date/Time — will be NaT for Type A (summary) rows
    if 'Interaction Date/Time' in df.columns:
        df['Interaction Date/Time'] = pd.to_datetime(
            df['Interaction Date/Time'],
            dayfirst=True,
            errors='coerce'
        )
    else:
        df['Interaction Date/Time'] = pd.NaT

    # Interaction Number — will be NaN for Type A rows
    if 'Interaction Number' in df.columns:
        df['Interaction Number'] = pd.to_numeric(df['Interaction Number'], errors='coerce')
    else:
        df['Interaction Number'] = float('nan')

    return df


# ---------------------------------------------------------------------------
# Row type classification
# ---------------------------------------------------------------------------

def classify_row_types(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add 'row_type' column:
    - 'conversion': Interaction Number is NaN (Type A summary row)
    - 'interaction': Interaction Number is not NaN (Type B interaction row)
    """
    df['row_type'] = df['Interaction Number'].apply(
        lambda x: 'conversion' if pd.isna(x) else 'interaction'
    )
    return df


# ---------------------------------------------------------------------------
# Optional column detection
# ---------------------------------------------------------------------------

OPTIONAL_COLUMNS = {
    'Campaign': 'campaign',
    'Site (CM360)': 'site',
    'Device': 'device',
    'Ad': 'ad',
    'Creative': 'creative',
    'Activity': 'activity_name',
}


def detect_optional_columns(df: pd.DataFrame) -> dict:
    """
    Returns dict of {app_name: actual_column_name} for optional columns present in df.
    """
    present = {}
    for col_name, app_name in OPTIONAL_COLUMNS.items():
        if col_name in df.columns:
            present[app_name] = col_name
    return present


# ---------------------------------------------------------------------------
# Google Drive download helper
# ---------------------------------------------------------------------------

def download_from_gdrive(url: str) -> bytes:
    """
    Download a file from a Google Drive shareable link.
    Converts sharing URL to direct download URL.
    """
    import re
    import urllib.request

    # Extract file ID from various Google Drive URL formats
    patterns = [
        r'/file/d/([a-zA-Z0-9_-]+)',
        r'id=([a-zA-Z0-9_-]+)',
        r'/d/([a-zA-Z0-9_-]+)',
    ]
    file_id = None
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            file_id = match.group(1)
            break

    if not file_id:
        raise ValueError("Could not extract file ID from Google Drive URL. "
                         "Please ensure you are using a shareable link.")

    download_url = f"https://drive.google.com/uc?export=download&id={file_id}"

    # Use urllib to handle redirects (including the virus-scan warning page for large files)
    req = urllib.request.Request(download_url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as response:
        content = response.read()

    # If Google returns an HTML confirmation page (large file warning), handle it
    if content[:5] == b'<!DOC' or content[:5] == b'<html':
        import re as re2
        confirm_match = re2.search(rb'confirm=([0-9A-Za-z_]+)', content)
        if confirm_match:
            confirm_token = confirm_match.group(1).decode()
            confirm_url = f"https://drive.google.com/uc?export=download&id={file_id}&confirm={confirm_token}"
            req2 = urllib.request.Request(confirm_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req2) as response2:
                content = response2.read()

    return content


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

@st.cache_data
def load_p2c_report(uploaded_file) -> tuple:
    """
    Args: uploaded_file — Streamlit UploadedFile object
    Returns: (raw_df, metadata_dict, optional_columns_dict)

    raw_df has:
    - All original columns, stripped
    - 'Conversion ID' as normalised string
    - 'Activity Date/Time' as datetime
    - 'Interaction Date/Time' as datetime (NaT for conversion rows)
    - 'Interaction Number' as float (NaN for conversion rows)
    - 'Path Length' as int
    - 'row_type' column: 'conversion' or 'interaction'
    """
    # Save to temp file (needed for line-by-line header scan)
    with tempfile.NamedTemporaryFile(mode='wb', suffix='.csv', delete=False) as tmp:
        tmp.write(uploaded_file.read())
        tmp_path = tmp.name

    try:
        sep = detect_separator(tmp_path)
        header_idx = find_header_row_index(tmp_path, sep)
        metadata = extract_metadata(tmp_path, header_idx, sep)
        df = load_raw_df(tmp_path, header_idx, sep)
        df = apply_type_conversions(df)
        df = classify_row_types(df)
        optional_cols = detect_optional_columns(df)
    finally:
        os.unlink(tmp_path)

    return df, metadata, optional_cols


@st.cache_data
def load_p2c_report_from_bytes(file_bytes: bytes, filename: str = 'report.csv') -> tuple:
    """
    Same as load_p2c_report but accepts raw bytes (e.g. from Google Drive download).
    Separator is auto-detected (comma or tab).
    """
    with tempfile.NamedTemporaryFile(mode='wb', suffix='.csv', delete=False) as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name

    try:
        sep = detect_separator(tmp_path)
        header_idx = find_header_row_index(tmp_path, sep)
        metadata = extract_metadata(tmp_path, header_idx, sep)
        df = load_raw_df(tmp_path, header_idx, sep)
        df = apply_type_conversions(df)
        df = classify_row_types(df)
        optional_cols = detect_optional_columns(df)
    finally:
        os.unlink(tmp_path)

    return df, metadata, optional_cols
