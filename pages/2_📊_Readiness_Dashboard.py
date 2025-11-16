import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Tuple, Dict, Any

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

# -------------------------------------------------------------------
# Path setup and environment
# -------------------------------------------------------------------
# This file lives in ./pages/, so project root is one level up
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Load .env so GOOGLE_API_KEY etc. are available
env_path = PROJECT_ROOT / ".env"
if env_path.exists():
    load_dotenv(env_path)

# -------------------------------------------------------------------
# Streamlit page config
# -------------------------------------------------------------------
st.set_page_config(
    page_title="MDT Readiness Dashboard",
    page_icon="./assets/favicon.png",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -------------------------------------------------------------------
# Custom CSS (blue clinical theme, consistent with other pages)
# -------------------------------------------------------------------
st.markdown(
    """
<style>
    /* Main background */
    .stApp {
        background-color: #fafbfc;
    }

    /* Header styling - Royal / clinical blues */
    .main-header {
        background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%);
        padding: 2rem 1rem;
        margin: -1rem -1rem 2rem -1rem;
        border-radius: 0 0 15px 15px;
        color: white;
        text-align: center;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }

    .main-header h1 {
        color: white !important;
        margin-bottom: 0.5rem;
        font-weight: 700;
        font-size: 2.5rem;
    }

    .main-header .caption {
        color: #e0e7ff !important;
        font-size: 1.1rem;
        margin-bottom: 0.25rem;
    }

    .last-updated {
        color: #cbd5e1 !important;
        font-size: 0.9rem;
        font-style: italic;
    }

    /* Sidebar styling */
    .stSidebar {
        background: linear-gradient(180deg, #f1f5f9 0%, #e2e8f0 100%);
    }

    .stSidebar .stSelectbox label,
    .stSidebar .stRadio label,
    .stSidebar .stNumberInput label,
    .stSidebar .stSlider label,
    .stSidebar .stMultiSelect label {
        color: #1e40af !important;
        font-weight: 600;
    }

    /* Metric cards */
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 4px solid #3b82f6;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
        margin-bottom: 1rem;
    }

    .metric-card h3 {
        margin: 0;
        font-size: 0.95rem;
        color: #1e40af;
    }

    .metric-card h2 {
        margin: 0.5rem 0 0 0;
        font-size: 1.8rem;
        color: #1e40af;
    }

    .metric-card p {
        margin: 0.25rem 0 0 0;
        font-size: 0.85rem;
        color: #64748b;
    }

    /* Section headers */
    .section-header {
        color: #1e40af;
        border-bottom: 2px solid #e2e8f0;
        padding-bottom: 0.5rem;
        margin-bottom: 1.5rem;
        font-weight: 600;
    }

    /* Patient status badges */
    .status-badge {
        display: inline-block;
        padding: 0.15rem 0.6rem;
        border-radius: 999px;
        font-size: 0.8rem;
        font-weight: 600;
    }

    .status-pending {
        background-color: #fef3c7;
        color: #92400e;
        border: 1px solid #fbbf24;
    }

    .status-in-progress {
        background-color: #eff6ff;
        color: #1d4ed8;
        border: 1px solid #60a5fa;
    }

    .status-complete {
        background-color: #dcfce7;
        color: #166534;
        border: 1px solid #22c55e;
    }

    /* Dataframe wrapper */
    .stDataFrame {
        border-radius: 8px;
        overflow: hidden;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
    }

    /* Expander */
    .streamlit-expanderHeader {
        background-color: #f8fafc;
        border-radius: 8px;
        border: 1px solid #e2e8f0;
    }

    /* Footer */
    .core-footer {
        text-align: center;
        padding: 2rem 0;
        background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
        margin: 2rem -1rem -1rem -1rem;
        border-radius: 15px 15px 0 0;
    }

    .core-footer-title {
        font-size: 1.2rem;
        font-weight: 600;
        color: #1e40af;
        margin-bottom: 0.5rem;
    }

    .core-footer-text {
        color: #64748b;
        font-size: 1rem;
    }

    .core-footer-sub {
        color: #94a3b8;
        font-size: 0.9rem;
        margin-top: 0.5rem;
    }
</style>
""",
    unsafe_allow_html=True,
)

# -------------------------------------------------------------------
# Header
# -------------------------------------------------------------------
today_str = datetime.now().strftime("%d %B %Y")

st.markdown(
    f"""
<div class="main-header">
    <h1>MDT Readiness Dashboard</h1>
    <div class="caption">
        Snapshot of case preparation status for the upcoming multidisciplinary meeting
    </div>
    <div class="last-updated">
        Last updated: {today_str}
    </div>
</div>
""",
    unsafe_allow_html=True,
)

# -------------------------------------------------------------------
# ADK / Coordinator glue
# -------------------------------------------------------------------
try:
    from agents.coordinator import CoordinatorAgent
except ImportError:
    st.error(
        "CoordinatorAgent could not be imported. "
        "Ensure `agents/coordinator.py` exists and `agents/__init__.py` is present."
    )
    st.stop()


@st.cache_resource(show_spinner=True)
def get_coordinator() -> CoordinatorAgent:
    """Initialise CoordinatorAgent once per session."""
    roster_path = PROJECT_ROOT / "mock_db" / "mdt_roster_2025-11-18.json"

    if not roster_path.exists():
        raise FileNotFoundError(f"MDT roster file not found at: {roster_path}")

    model_name = os.getenv("READINESS_MODEL_NAME", "gemini-2.0-flash-lite")

    coordinator = CoordinatorAgent(
        mdt_roster_path=str(roster_path),
        model_name=model_name,
    )
    return coordinator


@st.cache_data(show_spinner=True)
def get_readiness_snapshot() -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Load the MDT roster and run case preparation via CoordinatorAgent.

    For now, this will return PENDING with 0% readiness per patient
    until CaseAgents are implemented.
    """
    coordinator = get_coordinator()

    # Local JSON load, no API calls
    loaded = coordinator.load_roster()
    if not loaded:
        raise RuntimeError("CoordinatorAgent.load_roster() returned False.")

    # This will currently return stubbed PENDING results
    results = coordinator.run_case_preparation()
    mdt_info = coordinator.mdt_info or {}

    rows = []
    patients = coordinator.patients or []

    for patient in patients:
        patient_id = patient.get("patient_id")
        status_entry = results.get(patient_id, {}) if isinstance(results, dict) else {}

        status = status_entry.get("status", "PENDING")
        readiness = status_entry.get("readiness_percentage", 0)

        rows.append(
            {
                "patient_id": patient_id,
                "patient_name": patient.get("patient_name"),
                "age": patient.get("age"),
                "diagnosis_summary": patient.get("diagnosis_summary"),
                "case_priority": patient.get("case_priority"),
                "presenting_oncologist": patient.get("presenting_oncologist"),
                "case_complexity": patient.get("case_complexity"),
                "status": status,
                "readiness_percentage": readiness,
            }
        )

    df = pd.DataFrame(rows)
    return df, mdt_info


# -------------------------------------------------------------------
# Load data with error handling
# -------------------------------------------------------------------
with st.spinner("Loading MDT roster and readiness snapshot..."):
    try:
        readiness_df, mdt_info = get_readiness_snapshot()
    except Exception as exc:
        st.error(f"Unable to load MDT readiness snapshot: {exc}")
        st.stop()

if readiness_df.empty:
    st.warning("MDT roster is empty. Add patients to the roster JSON to populate this dashboard.")
    st.stop()

# -------------------------------------------------------------------
# Sidebar controls
# -------------------------------------------------------------------
with st.sidebar:
    st.markdown("### Dashboard settings")

    meeting_date = mdt_info.get("meeting_date", "Unknown date")
    meeting_location = mdt_info.get("location", "Unknown location")
    meeting_type = mdt_info.get("meeting_type", "Multidisciplinary Team Meeting")

    st.markdown(f"**Meeting type:** {meeting_type}")
    st.markdown(f"**Meeting date:** {meeting_date}")
    st.markdown(f"**Location:** {meeting_location}")

    st.markdown("---")

    status_options = sorted(readiness_df["status"].dropna().unique().tolist())
    selected_status = st.multiselect(
        "Filter by readiness status",
        options=status_options,
        default=status_options,
    )

    min_readiness = st.slider(
        "Minimum readiness percentage",
        min_value=0,
        max_value=100,
        value=0,
        step=5,
    )

    st.markdown("---")

    # Patient selection for detail view
    patient_ids = readiness_df["patient_id"].astype(str).tolist()
    selected_patient_id = st.selectbox(
        "Focus on patient",
        options=["All patients"] + patient_ids,
        index=0,
    )

# Apply filters
filtered_df = readiness_df.copy()
if selected_status:
    filtered_df = filtered_df[filtered_df["status"].isin(selected_status)]
filtered_df = filtered_df[filtered_df["readiness_percentage"] >= min_readiness]

# -------------------------------------------------------------------
# Top-level metrics
# -------------------------------------------------------------------
total_patients = len(readiness_df)
mean_readiness = float(readiness_df["readiness_percentage"].mean())

n_complete = int(
    ((readiness_df["readiness_percentage"] >= 80) & (readiness_df["status"] == "COMPLETE")).sum()
)
n_in_progress = int(
    ((readiness_df["readiness_percentage"] > 0) & (readiness_df["readiness_percentage"] < 80)).sum()
)
n_pending = int((readiness_df["readiness_percentage"] == 0).sum())

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown(
        f"""
        <div class="metric-card">
            <h3>Total MDT patients</h3>
            <h2>{total_patients}</h2>
            <p>Patients scheduled for discussion</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col2:
    st.markdown(
        f"""
        <div class="metric-card">
            <h3>Overall readiness</h3>
            <h2>{mean_readiness:.0f}%</h2>
            <p>Average case preparation completeness</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col3:
    st.markdown(
        f"""
        <div class="metric-card">
            <h3>Cases in progress</h3>
            <h2>{n_in_progress}</h2>
            <p>Readiness score (%)</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col4:
    st.markdown(
        f"""
        <div class="metric-card">
            <h3>Not started</h3>
            <h2>{n_pending}</h2>
            <p>Currently marked as pending</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown("---")

# -------------------------------------------------------------------
# Overall readiness section
# -------------------------------------------------------------------
st.markdown('<h2 class="section-header">Overview</h2>', unsafe_allow_html=True)

overview_col1, overview_col2 = st.columns([1.2, 1.0])

with overview_col1:
    st.subheader("Overall MDT readiness")

    st.write(
        "This progress bar reflects the average readiness percentage across all patients "
        "on the MDT roster."
    )

    st.progress(int(mean_readiness) / 100.0)

    priority_counts = (
        readiness_df["case_priority"]
        .fillna("Unspecified")
        .value_counts()
        .rename_axis("Case priority")
        .reset_index(name="Count")
    )

    st.markdown("#### Cases by priority level")
    st.dataframe(priority_counts, use_container_width=True, hide_index=True)

with overview_col2:
    st.subheader("Status distribution")

    status_counts = (
        readiness_df["status"]
        .fillna("UNKNOWN")
        .value_counts()
        .rename_axis("Status")
        .reset_index(name="Count")
    )

    st.dataframe(status_counts, use_container_width=True, hide_index=True)

# -------------------------------------------------------------------
# Patient table view
# -------------------------------------------------------------------
st.markdown('<h2 class="section-header">Patient-level readiness</h2>', unsafe_allow_html=True)

display_df = filtered_df.copy()

# Create a simple text badge column for status
def format_status(status: str, readiness: int) -> str:
    status = (status or "").upper()
    if status == "COMPLETE" or readiness >= 80:
        cls = "status-complete"
        label = "Complete"
    elif readiness > 0:
        cls = "status-in-progress"
        label = "In progress"
    else:
        cls = "status-pending"
        label = "Pending"
    return f'<span class="status-badge {cls}">{label}</span>'


display_df["Status badge"] = display_df.apply(
    lambda row: format_status(row.get("status", ""), int(row.get("readiness_percentage", 0))),
    axis=1,
)

# Reorder and rename columns for clinicians
table_cols = [
    "patient_id",
    "patient_name",
    "age",
    "diagnosis_summary",
    "case_priority",
    "presenting_oncologist",
    "case_complexity",
    "readiness_percentage",
    "Status badge",
]
table_cols = [c for c in table_cols if c in display_df.columns]

pretty_df = display_df[table_cols].copy()
pretty_df = pretty_df.rename(
    columns={
        "patient_id": "Patient ID",
        "patient_name": "Patient name",
        "age": "Age",
        "diagnosis_summary": "Diagnosis summary",
        "case_priority": "Case priority",
        "presenting_oncologist": "Presenting oncologist",
        "case_complexity": "Case complexity",
        "readiness_percentage": "Readiness (%)",
    }
)

# Use HTML for status badge, keep other columns as text
st.write(
    "Filtered view based on sidebar settings. Status is currently a mock indicator "
    "until automated case preparation is implemented."
)

st.write(
    pretty_df.to_html(escape=False, index=False),
    unsafe_allow_html=True,
)

# -------------------------------------------------------------------
# Focused patient summary
# -------------------------------------------------------------------
st.markdown('<h2 class="section-header">Focused case summary</h2>', unsafe_allow_html=True)

if selected_patient_id != "All patients":
    focus_df = readiness_df[readiness_df["patient_id"].astype(str) == str(selected_patient_id)]

    if focus_df.empty:
        st.info("Selected patient not found in current roster.")
    else:
        row = focus_df.iloc[0]

        left, right = st.columns([1.2, 1.0])

        with left:
            st.markdown("#### Core clinical details")
            st.markdown(f"**Patient ID:** {row.get('patient_id')}")
            st.markdown(f"**Name:** {row.get('patient_name')}")
            st.markdown(f"**Age:** {row.get('age')}")
            st.markdown(f"**Presenting oncologist:** {row.get('presenting_oncologist')}")
            st.markdown(f"**Case priority:** {row.get('case_priority')}")
            st.markdown(f"**Case complexity:** {row.get('case_complexity')}")

            st.markdown("**Diagnosis summary**")
            st.write(row.get("diagnosis_summary"))

        with right:
            st.markdown("#### Readiness status")

            readiness_value = int(row.get("readiness_percentage", 0))
            st.metric(
                label="Readiness for MDT discussion",
                value=f"{readiness_value}%",
            )

            st.progress(readiness_value / 100.0 if readiness_value > 0 else 0.0)

            status_text = row.get("status", "PENDING") or "PENDING"
            st.markdown(f"**Current status:** {status_text}")

            st.info(
                "Automated case preparation is not yet enabled. "
                "Once CaseAgents are implemented, this section will show detailed "
                "checklist items and blockers for this patient."
            )
else:
    st.info("Select a specific patient in the sidebar to view a focused summary.")

# -------------------------------------------------------------------
# Footer
# -------------------------------------------------------------------
st.markdown("---")

st.markdown(
    """
<div class="core-footer">
    <div class="core-footer-title">
        CORE MDT Coordination Prototype
    </div>
    <div class="core-footer-text">
        Designed to support structured case preparation and transparent MDT workflows
    </div>
    <div class="core-footer-sub">
        This dashboard currently uses mock readiness values. Automated case preparation will be enabled once CaseAgents are integrated.
    </div>
</div>
""",
    unsafe_allow_html=True,
)
