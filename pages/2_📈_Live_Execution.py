"""
C.O.R.E. Live Execution Page
Real-time agent execution with full observability for clinicians
"""

import streamlit as st
import asyncio
import json
import logging
from pathlib import Path
from datetime import datetime
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import your agents
try:
    from agents.coordinator import CoordinatorAgent
except ImportError:
    st.error("Could not import CoordinatorAgent. Check your file structure.")
    st.stop()

# Page config
st.set_page_config(
    page_title="C.O.R.E. - Live Execution",
    page_icon="./assets/favicon.png",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS - Clean blue theme matching other pages
st.markdown("""
<style>
    /* Main background */
    .stApp {
        background-color: #fafbfc;
    }
    
    /* Header styling - consistent with other pages */
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
    }
    
    /* Sidebar styling */
    .stSidebar {
        background: linear-gradient(180deg, #f1f5f9 0%, #e2e8f0 100%);
    }
    
    /* Status cards - blue themed */
    .status-ready {
        background-color: #dbeafe;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #3b82f6;
    }
    
    .status-blocked {
        background-color: #fee2e2;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #ef4444;
    }
    
    .status-progress {
        background-color: #fef3c7;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #f59e0b;
    }
    
    /* Log container - clean monospace */
    .log-container {
        background-color: #f8fafc;
        padding: 1rem;
        border-radius: 8px;
        font-family: 'Courier New', monospace;
        font-size: 0.85rem;
        max-height: 400px;
        overflow-y: auto;
        border: 1px solid #cbd5e1;
    }
    
    .log-info { color: #3b82f6; }
    .log-success { color: #10b981; font-weight: 600; }
    .log-warning { color: #f59e0b; font-weight: 600; }
    .log-error { color: #ef4444; font-weight: 600; }
    
    /* Metric cards - consistent blue */
    .metric-card {
        background-color: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        text-align: center;
        border-top: 4px solid #3b82f6;
    }
    
    .metric-value {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1e40af;
    }
    
    .metric-label {
        font-size: 0.9rem;
        color: #64748b;
        margin-top: 0.5rem;
        font-weight: 600;
    }
    
    /* Info box styling */
    .info-box {
        background: #dbeafe;
        border-left: 4px solid #3b82f6;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
    }
    
    /* Section dividers */
    .section-divider {
        border-top: 2px solid #e2e8f0;
        margin: 2rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'execution_logs' not in st.session_state:
    st.session_state.execution_logs = []
if 'dashboard_data' not in st.session_state:
    st.session_state.dashboard_data = None
if 'execution_running' not in st.session_state:
    st.session_state.execution_running = False

# Custom logging handler to capture logs in Streamlit
class StreamlitLogHandler(logging.Handler):
    def emit(self, record):
        log_entry = self.format(record)
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Determine log level class for styling
        level_class = "log-info"
        if record.levelname == "SUCCESS":
            level_class = "log-success"
        elif record.levelname == "WARNING":
            level_class = "log-warning"
        elif record.levelname == "ERROR":
            level_class = "log-error"
        
        # Extract agent name if present
        agent_name = "System"
        if hasattr(record, 'name') and record.name:
            if 'case_agent' in record.name.lower():
                agent_name = "CaseAgent"
            elif 'coordinator' in record.name.lower():
                agent_name = "Coordinator"
        
        formatted_log = f"[{timestamp}] [{record.levelname}] [{agent_name}] {record.getMessage()}"
        st.session_state.execution_logs.append((formatted_log, level_class))

# Setup logging
def setup_logging():
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # Remove existing handlers
    logger.handlers = []
    
    # Add our custom handler
    handler = StreamlitLogHandler()
    formatter = logging.Formatter('%(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

# Header - consistent with other pages
st.markdown("""
<div class="main-header">
    <h1>Live Agent Execution</h1>
    <div class="caption">Real-time multi-agent case preparation with full observability</div>
</div>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    # Logo in sidebar
    st.image("./assets/core_logo_2.png", use_container_width=True)
    
    st.markdown("---")
    
    st.markdown("### Configuration")
    
    # API Key Status
    api_key = os.getenv("GOOGLE_API_KEY")
    if api_key:
        st.success("API Key Configured")
    else:
        st.error("API Key Missing")
        st.info("Set GOOGLE_API_KEY in your .env file")
    
    st.markdown("---")
    
    # Data Source Selection
    st.markdown("#### Data Source")
    
    data_source = st.radio(
        "Choose data source:",
        ["Use Mock Data", "Upload Files"],
        help="Mock data is pre-loaded for demo purposes"
    )
    
    if data_source == "Use Mock Data":
        st.info("Using existing mock_db files")
        roster_path = "mock_db/mdt_roster_2025-11-18.json"
    else:
        st.warning("File upload not yet implemented")
        st.info("Coming soon: Upload patient files directly")
        roster_path = None
    
    st.markdown("---")
    
    # Model Selection
    st.markdown("#### Model Settings")
    model_choice = st.selectbox(
        "Gemini Model:",
        ["gemini-2.0-flash", "gemini-2.0-flash-lite", "gemini-2.5-flash-lite"],
        help="gemini-2.0-flash recommended for best results"
    )
    
    st.markdown("---")
    
    # Info
    st.markdown("#### System Information")
    st.caption("**Architecture:**")
    st.caption("• 1 CoordinatorAgent")
    st.caption("• N CaseAgents (one per patient)")
    st.caption("• 5 Baby Agents per case")
    st.caption("")
    st.caption("Total: 20+ agents working concurrently")

# Main content area
tab1, tab2, tab3 = st.tabs(["Execution", "Dashboard", "Logs"])

with tab1:
    st.markdown("### Execute Case Preparation")
    
    st.markdown("""
    <div class="info-box">
    Click the button below to start the autonomous case preparation workflow. 
    The system will:
    <ul style="margin: 0.5rem 0; padding-left: 1.5rem;">
        <li>Load the MDT roster</li>
        <li>Spawn CaseAgents for each patient</li>
        <li>Execute parallel data gathering (Clinical, Pathology, Radiology, Genomics, Contraindications)</li>
        <li>Generate readiness dashboard</li>
    </ul>
    </div>
    """, unsafe_allow_html=True)
    
    # Execution button
    if st.button("Run Case Preparation", type="primary", disabled=st.session_state.execution_running or not api_key, use_container_width=True):
        st.session_state.execution_running = True
        st.session_state.execution_logs = []
        st.session_state.dashboard_data = None
        
        # Setup logging
        setup_logging()
        
        # Progress container
        progress_container = st.container()
        log_container = st.container()
        
        with progress_container:
            st.info("Starting case preparation workflow...")
        
        # Run async workflow
        async def run_workflow():
            try:
                # Create coordinator
                coordinator = CoordinatorAgent(
                    mdt_roster_path=roster_path,
                    model_name=model_choice
                )
                
                # Load roster
                if not coordinator.load_roster():
                    st.error("Failed to load MDT roster")
                    return None
                
                # Spawn agents
                if not coordinator.spawn_case_agents():
                    st.error("Failed to spawn CaseAgents")
                    return None
                
                # Run case preparation
                await coordinator.run_case_preparation_async()
                
                # Generate dashboard
                dashboard = coordinator.generate_dashboard()
                
                return dashboard
                
            except Exception as e:
                logging.error(f"Execution error: {e}")
                return None
        
        # Execute
        dashboard = asyncio.run(run_workflow())
        
        if dashboard:
            st.session_state.dashboard_data = dashboard
            with progress_container:
                st.success("Case preparation complete")
        else:
            with progress_container:
                st.error("Case preparation failed. Check logs for details.")
        
        st.session_state.execution_running = False
        st.rerun()
    
    # Show live logs during execution
    if st.session_state.execution_logs:
        st.markdown("### Execution Logs")
        log_html = '<div class="log-container">'
        for log, level_class in st.session_state.execution_logs[-50:]:  # Show last 50 logs
            log_html += f'<div class="{level_class}">{log}</div>'
        log_html += '</div>'
        st.markdown(log_html, unsafe_allow_html=True)

with tab2:
    st.markdown("### MDT Readiness Dashboard")
    
    if st.session_state.dashboard_data is None:
        st.info("Run case preparation to generate dashboard")
    else:
        dashboard = st.session_state.dashboard_data
        
        # Summary metrics
        st.markdown("#### Overview")
        
        col1, col2, col3, col4, col5 = st.columns(5)
        
        summary = dashboard.get("summary", {})
        
        with col1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{summary.get('total_patients', 0)}</div>
                <div class="metric-label">Total Patients</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value" style="color: #10b981;">{summary.get('ready', 0)}</div>
                <div class="metric-label">Ready</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value" style="color: #f59e0b;">{summary.get('in_progress', 0)}</div>
                <div class="metric-label">In Progress</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value" style="color: #ef4444;">{summary.get('blocked', 0)}</div>
                <div class="metric-label">Blocked</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col5:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{summary.get('readiness_percentage', 0)}%</div>
                <div class="metric-label">Readiness</div>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
        
        # Blockers section
        blockers = dashboard.get("blockers", [])
        if blockers:
            st.markdown("#### Blockers Requiring Attention")
            for blocker in blockers:
                with st.expander(f"Patient {blocker['patient_id']} - {blocker['category']}", expanded=True):
                    st.error(blocker['issue'])
        
        st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
        
        # Patient details
        st.markdown("#### Patient Details")
        
        patients = dashboard.get("patient_details", [])
        for patient in patients:
            status = patient.get("overall_status", "UNKNOWN")
            
            # Status indicator
            if status == "READY":
                status_indicator = "READY"
            elif status == "BLOCKED":
                status_indicator = "BLOCKED"
            else:
                status_indicator = "IN PROGRESS"
            
            with st.expander(f"Patient {patient['patient_id']} - {patient['mrn']} - {status_indicator}"):
                # Priority
                st.markdown(f"**Priority:** {patient.get('case_priority', 'Standard')}")
                
                # Checklist
                st.markdown("**Readiness Checklist:**")
                checklist = patient.get("checklist", {})
                
                for category, data in checklist.items():
                    # Check for blockers
                    has_blocker = "BLOCKER" in str(data) or "UNSIGNED" in str(data)
                    has_missing = "NOT" in str(data) or "missing" in str(data).lower()
                    
                    if has_blocker:
                        st.error(f"**{category}:** {data}")
                    elif has_missing:
                        st.warning(f"**{category}:** {data}")
                    else:
                        st.success(f"**{category}:** {data}")
                
                # Notes
                if patient.get("notes"):
                    st.info(f"**Notes:** {patient['notes']}")
        
        st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
        
        # Download options
        st.markdown("#### Download Options")
        
        col1, col2 = st.columns(2)
        
        with col1:
            dashboard_json = json.dumps(dashboard, indent=2)
            st.download_button(
                label="Download Dashboard (JSON)",
                data=dashboard_json,
                file_name=f"mdt_dashboard_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json",
                use_container_width=True
            )
        
        with col2:
            if st.session_state.execution_logs:
                logs_text = "\n".join([log for log, _ in st.session_state.execution_logs])
                st.download_button(
                    label="Download Execution Logs",
                    data=logs_text,
                    file_name=f"execution_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                    mime="text/plain",
                    use_container_width=True
                )

with tab3:
    st.markdown("### Execution Logs")
    
    if not st.session_state.execution_logs:
        st.info("No logs yet. Run case preparation to see execution logs.")
    else:
        # Filter options
        col1, col2 = st.columns([3, 1])
        
        with col1:
            log_filter = st.multiselect(
                "Filter by level:",
                ["INFO", "SUCCESS", "WARNING", "ERROR"],
                default=["INFO", "SUCCESS", "WARNING", "ERROR"]
            )
        
        with col2:
            if st.button("Clear Logs", use_container_width=True):
                st.session_state.execution_logs = []
                st.rerun()
        
        # Display filtered logs
        log_html = '<div class="log-container">'
        for log, level_class in st.session_state.execution_logs:
            # Extract level from log
            level = None
            for l in ["INFO", "SUCCESS", "WARNING", "ERROR"]:
                if f"[{l}]" in log:
                    level = l
                    break
            
            if level in log_filter:
                log_html += f'<div class="{level_class}">{log}</div>'
        log_html += '</div>'
        
        st.markdown(log_html, unsafe_allow_html=True)
        
        # Download logs
        if st.session_state.execution_logs:
            logs_text = "\n".join([log for log, _ in st.session_state.execution_logs])
            st.download_button(
                label="Download Full Logs",
                data=logs_text,
                file_name=f"full_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                mime="text/plain",
                use_container_width=True
            )

# Footer
st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
st.caption("C.O.R.E. - Clinical Oncology Readiness Engine | Powered by Google Agent Development Kit")