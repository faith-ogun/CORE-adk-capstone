"""
C.O.R.E. Genomics Intelligence Page
Deep genomic analysis with treatment recommendations and clinical trial matching
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
    page_title="C.O.R.E. - Genomics Intelligence",
    page_icon="./assets/favicon.png",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS - Blue theme matching other pages
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
    
    /* Metric cards - blue themed */
    .metric-card {
        background-color: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        text-align: center;
        border-top: 4px solid #3b82f6;
        transition: transform 0.3s ease, box-shadow 0.3s ease;
    }
    
    .metric-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 8px 16px rgba(59, 130, 246, 0.2);
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
    
    /* Mutation cards */
    .mutation-card {
        background: white;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        border-left: 5px solid #3b82f6;
        margin-bottom: 1.5rem;
        transition: transform 0.3s ease, box-shadow 0.3s ease;
    }
    
    .mutation-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 16px -4px rgba(59, 130, 246, 0.2);
    }
    
    .mutation-card-actionable {
        border-left-color: #10b981;
        background: linear-gradient(135deg, #ffffff 0%, #f0fdf4 100%);
    }
    
    .mutation-card-not-actionable {
        border-left-color: #94a3b8;
    }
    
    .mutation-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 1rem;
    }
    
    .mutation-gene {
        font-size: 1.4rem;
        font-weight: 700;
        color: #1e40af;
    }
    
    .mutation-variant {
        font-size: 1.1rem;
        color: #64748b;
        margin-left: 0.5rem;
    }
    
    /* Treatment cards */
    .treatment-card {
        background: white;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        margin-bottom: 1rem;
        border-top: 3px solid #10b981;
    }
    
    .treatment-priority {
        display: inline-block;
        background: linear-gradient(135deg, #10b981 0%, #059669 100%);
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.85rem;
        margin-bottom: 1rem;
    }
    
    .treatment-name {
        font-size: 1.2rem;
        font-weight: 700;
        color: #1e40af;
        margin-bottom: 0.5rem;
    }
    
    .treatment-evidence {
        color: #64748b;
        font-size: 0.9rem;
        margin-top: 0.5rem;
    }
    
    /* Trial cards */
    .trial-card {
        background: white;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        margin-bottom: 1rem;
        border-left: 4px solid #3b82f6;
        transition: all 0.3s ease;
    }
    
    .trial-card:hover {
        transform: translateX(5px);
        box-shadow: 0 4px 8px rgba(59, 130, 246, 0.2);
    }
    
    .trial-header {
        display: flex;
        justify-content: space-between;
        align-items: start;
        margin-bottom: 1rem;
    }
    
    .trial-nct {
        font-size: 1.1rem;
        font-weight: 700;
        color: #1e40af;
    }
    
    .trial-title {
        color: #374151;
        margin-bottom: 0.5rem;
        line-height: 1.5;
    }
    
    /* Badges */
    .badge {
        display: inline-block;
        padding: 0.4rem 0.8rem;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.8rem;
        margin: 0.25rem;
    }
    
    .badge-actionable {
        background: #d1fae5;
        color: #065f46;
        border: 1px solid #6ee7b7;
    }
    
    .badge-not-actionable {
        background: #f1f5f9;
        color: #475569;
        border: 1px solid #cbd5e1;
    }
    
    .badge-phase-3 {
        background: #dbeafe;
        color: #1e40af;
        border: 1px solid #93c5fd;
    }
    
    .badge-phase-2 {
        background: #e0f7fa;
        color: #006064;
        border: 1px solid #80deea;
    }
    
    .badge-level-1 {
        background: #d1fae5;
        color: #065f46;
        border: 1px solid #6ee7b7;
    }
    
    .badge-high-match {
        background: #fef3c7;
        color: #92400e;
        border: 1px solid #fde68a;
    }
    
    /* Info boxes */
    .info-box {
        background: #dbeafe;
        border-left: 4px solid #3b82f6;
        padding: 1.5rem;
        border-radius: 8px;
        margin: 1.5rem 0;
    }
    
    .info-box h4 {
        color: #1e40af;
        margin-bottom: 1rem;
    }
    
    .warning-box {
        background: #fef3c7;
        border-left: 4px solid #f59e0b;
        padding: 1.5rem;
        border-radius: 8px;
        margin: 1.5rem 0;
    }
    
    .success-box {
        background: #d1fae5;
        border-left: 4px solid #10b981;
        padding: 1.5rem;
        border-radius: 8px;
        margin: 1.5rem 0;
    }
    
    /* Section dividers */
    .section-divider {
        border-top: 2px solid #e2e8f0;
        margin: 2rem 0;
    }
    
    /* Section headers */
    .section-header {
        color: #1e40af;
        font-size: 1.8rem;
        font-weight: 700;
        margin: 2rem 0 1rem 0;
        border-bottom: 3px solid #dbeafe;
        padding-bottom: 0.5rem;
    }
    
    /* Pipeline visualization */
    .pipeline-step {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #3b82f6;
        margin-bottom: 0.5rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    
    .pipeline-step-complete {
        border-left-color: #10b981;
        background: linear-gradient(135deg, #ffffff 0%, #f0fdf4 100%);
    }
    
    /* Executive summary box */
    .executive-summary {
        background: linear-gradient(135deg, #dbeafe 0%, #e0f7fa 100%);
        padding: 2rem;
        border-radius: 15px;
        border: 2px solid #93c5fd;
        margin: 1.5rem 0;
    }
    
    .executive-summary h3 {
        color: #1e40af;
        margin-bottom: 1rem;
    }
    
    .executive-summary p {
        color: #374151;
        line-height: 1.8;
        font-size: 1.05rem;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'genomics_data' not in st.session_state:
    st.session_state.genomics_data = None
if 'genomics_running' not in st.session_state:
    st.session_state.genomics_running = False
if 'case_data' not in st.session_state:
    st.session_state.case_data = None

# Header
st.markdown("""
<div class="main-header">
    <h1>Genomics Intelligence</h1>
    <div class="caption">Deep mutation analysis • Treatment recommendations • Clinical trial matching</div>
</div>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    # Logo in sidebar
    st.image("./assets/core_logo_2.png", use_container_width=True)
    
    st.markdown("---")
    
    st.markdown("### About Genomics Intelligence")
    
    st.markdown("""
    <div style="background: white; padding: 1rem; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
        <p style="color: #374151; font-size: 0.9rem; line-height: 1.6; margin: 0;">
            The Genomics Intelligence Agent performs deep analysis on patient mutations using:
        </p>
        <ul style="color: #64748b; font-size: 0.85rem; margin-top: 0.5rem;">
            <li><strong>Google Search</strong> - Clinical significance</li>
            <li><strong>ClinicalTrials.gov</strong> - Trial matching</li>
            <li><strong>PubMed</strong> - Evidence base</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # API Key Status
    api_key = os.getenv("GOOGLE_API_KEY")
    if api_key:
        st.success("✓ API Key Configured")
    else:
        st.error("✗ API Key Missing")
        st.info("Set GOOGLE_API_KEY in .env file")
    
    st.markdown("---")
    
    # Model Selection
    st.markdown("#### Model Settings")
    model_choice = st.selectbox(
        "Gemini Model:",
        ["gemini-2.0-flash", "gemini-2.0-flash-lite"],
        help="Model used for genomic analysis"
    )
    
    st.markdown("---")
    
    st.markdown("""
    <div style="background: #dbeafe; padding: 1rem; border-radius: 8px; border-left: 4px solid #3b82f6;">
        <p style="color: #1e40af; font-weight: 600; font-size: 0.9rem; margin: 0;">
            Pipeline: 4 Sequential Agents
        </p>
        <ol style="color: #374151; font-size: 0.85rem; margin: 0.5rem 0 0 1rem; padding: 0;">
            <li>MutationInterpreter</li>
            <li>ClinicalTrialMatcher</li>
            <li>EvidenceSearcher</li>
            <li>GenomicsSynthesizer</li>
        </ol>
    </div>
    """, unsafe_allow_html=True)

# Main content
st.markdown("### Patient Selection")

# Info about the two-phase system
st.markdown("""
<div class="info-box">
    <h4>Two-Phase Genomic Analysis</h4>
    <p style="color: #374151; margin: 0;">
        Genomics Intelligence runs <strong>after</strong> case preparation completes. 
        It automatically analyzes patients with detected mutations to provide actionable treatment recommendations.
    </p>
</div>
""", unsafe_allow_html=True)

# Patient selection
col1, col2 = st.columns([2, 1])

with col1:
    patient_id = st.text_input(
        "Enter Patient ID:",
        value="123",
        help="Patient ID from the MDT roster"
    )

with col2:
    st.markdown("<br/>", unsafe_allow_html=True)
    run_analysis = st.button(
        "Run Genomic Analysis",
        type="primary",
        use_container_width=True,
        disabled=st.session_state.genomics_running
    )

# Run analysis
if run_analysis and not st.session_state.genomics_running:
    st.session_state.genomics_running = True
    
    with st.spinner("Running genomic intelligence pipeline..."):
        async def run_genomics_workflow():
            try:
                # Create coordinator
                coordinator = CoordinatorAgent(
                    mdt_roster_path="mock_db/mdt_roster_2025-11-18.json",
                    genomics_data_path="mock_db/genomics_data.json",
                    model_name=model_choice
                )
                
                # Load data
                if not coordinator.load_roster():
                    st.error("Failed to load MDT roster")
                    return None, None
                
                coordinator.load_genomics_data()
                
                # Spawn agents
                if not coordinator.spawn_case_agents():
                    st.error("Failed to spawn CaseAgents")
                    return None, None
                
                # Phase 1: Case Preparation
                st.info("Phase 1: Running case preparation...")
                await coordinator.run_case_preparation_async()
                
                # Phase 2: Genomics Intelligence
                st.info("Phase 2: Running genomics intelligence...")
                genomics_results = await coordinator.run_genomics_intelligence_async()
                
                return coordinator.results, genomics_results
                
            except Exception as e:
                st.error(f"Error: {e}")
                import traceback
                st.error(traceback.format_exc())
                return None, None
        
        # Execute
        case_results, genomics_results = asyncio.run(run_genomics_workflow())
        
        if genomics_results and patient_id in genomics_results:
            st.session_state.genomics_data = genomics_results[patient_id]
            st.session_state.case_data = case_results.get(patient_id) if case_results else None
            st.success("✓ Genomic analysis complete!")
        elif genomics_results:
            st.warning(f"Patient {patient_id} not found in genomics results. Available patients: {', '.join(genomics_results.keys())}")
        else:
            st.error("Failed to generate genomics intelligence")
        
        st.session_state.genomics_running = False
        st.rerun()

# Display results
if st.session_state.genomics_data:
    data = st.session_state.genomics_data
    
    # Check for errors
    if data.get("status") == "ERROR":
        st.error(f"Analysis failed: {data.get('error', 'Unknown error')}")
        if data.get("raw_output"):
            with st.expander("View raw output"):
                st.code(data["raw_output"][:1000])
    else:
        # Executive Summary
        if "executive_summary" in data:
            st.markdown(f"""
            <div class="executive-summary">
                <h3>Executive Summary</h3>
                <p>{data['executive_summary']}</p>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
        
        # Overview Metrics
        st.markdown('<h2 class="section-header">Overview</h2>', unsafe_allow_html=True)
        
        col1, col2, col3, col4 = st.columns(4)
        
        mutations = data.get("mutations", [])
        treatments = data.get("treatment_recommendations", [])
        trials = data.get("clinical_trials", [])
        actionable = sum(1 for m in mutations if "fda" in m.get("actionability", "").lower())
        
        with col1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{len(mutations)}</div>
                <div class="metric-label">Mutations Analyzed</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value" style="color: #10b981;">{actionable}</div>
                <div class="metric-label">Actionable Mutations</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value" style="color: #3b82f6;">{len(treatments)}</div>
                <div class="metric-label">Treatment Options</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value" style="color: #f59e0b;">{len(trials)}</div>
                <div class="metric-label">Clinical Trials</div>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
        
        # Mutations Section
        st.markdown('<h2 class="section-header">Detected Mutations</h2>', unsafe_allow_html=True)
        
        for mutation in mutations:
            is_actionable = "fda" in mutation.get("actionability", "").lower()
            card_class = "mutation-card mutation-card-actionable" if is_actionable else "mutation-card mutation-card-not-actionable"
            badge_class = "badge-actionable" if is_actionable else "badge-not-actionable"
            badge_text = "FDA-Approved Therapy" if is_actionable else "Research/Trials Only"
            
            st.markdown(f"""
            <div class="{card_class}">
                <div class="mutation-header">
                    <div>
                        <span class="mutation-gene">{mutation.get('gene', 'Unknown')}</span>
                        <span class="mutation-variant">{mutation.get('variant', '')}</span>
                    </div>
                    <span class="badge {badge_class}">{badge_text}</span>
                </div>
                <p style="color: #374151; margin-bottom: 0.5rem;">
                    <strong>Clinical Significance:</strong> {mutation.get('significance', 'Unknown')}
                </p>
                <p style="color: #374151; margin-bottom: 0.5rem;">
                    <strong>Actionability:</strong> {mutation.get('actionability', 'Unknown')}
                </p>
                <p style="color: #374151; margin: 0;">
                    <strong>Recommended Treatment:</strong> {mutation.get('recommended_treatment', 'See treatment recommendations')}
                </p>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
        
        # Treatment Recommendations
        if treatments:
            st.markdown('<h2 class="section-header">Treatment Recommendations</h2>', unsafe_allow_html=True)
            
            for treatment in treatments:
                priority = treatment.get("priority", "?")
                evidence_level = treatment.get("evidence_level", "Unknown")
                therapy = treatment.get('therapy', 'Unknown therapy')
                indication = treatment.get('indication', 'Not specified')
                key_trial = treatment.get('key_trial', 'N/A')
                pmid = treatment.get('pmid')
                
                # Determine badge color based on evidence level
                badge_class = "badge-level-1" if "1" in str(evidence_level) else "badge-phase-2"
                
                # Build the HTML properly to avoid escaping issues
                pmid_html = f' • <strong>PMID:</strong> {pmid}' if pmid else ''
                
                treatment_html = f"""
                <div class="treatment-card">
                    <div style="display: flex; justify-content: space-between; align-items: start;">
                        <span class="treatment-priority">Priority {priority}</span>
                        <span class="badge {badge_class}">{evidence_level}</span>
                    </div>
                    <div class="treatment-name">{therapy}</div>
                    <p style="color: #374151; margin: 0.5rem 0;">
                        <strong>Indication:</strong> {indication}
                    </p>
                    <div class="treatment-evidence">
                        <strong>Key Trial:</strong> {key_trial}{pmid_html}
                    </div>
                </div>
                """
                
                st.markdown(treatment_html, unsafe_allow_html=True)
        
        st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
        
        # Clinical Trials
        if trials:
            st.markdown('<h2 class="section-header">Matching Clinical Trials</h2>', unsafe_allow_html=True)
            
            for trial in trials:
                phase = trial.get("phase", "Unknown")
                match = trial.get("eligibility_match", "Unknown")
                
                # Badge classes
                phase_badge = "badge-phase-3" if "3" in phase else "badge-phase-2"
                match_badge = "badge-high-match" if "high" in match.lower() else "badge-phase-2"
                
                st.markdown(f"""
                <div class="trial-card">
                    <div class="trial-header">
                        <div>
                            <div class="trial-nct">{trial.get('nct_id', 'Unknown')}</div>
                            <p class="trial-title">{trial.get('title', 'No title available')}</p>
                        </div>
                    </div>
                    <div>
                        <span class="badge {phase_badge}">{phase}</span>
                        <span class="badge {match_badge}">Match: {match}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        
        st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
        
        # Next Steps
        if "next_steps" in data:
            st.markdown('<h2 class="section-header">Recommended Next Steps</h2>', unsafe_allow_html=True)
            
            st.markdown(f"""
            <div class="success-box">
                <h4>Clinical Action Items</h4>
                <p style="color: #374151; line-height: 1.8; margin: 0;">
                    {data['next_steps']}
                </p>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
        
        # Download Options
        st.markdown("### Download Report")
        
        col1, col2 = st.columns(2)
        
        with col1:
            report_json = json.dumps(data, indent=2)
            st.download_button(
                label="📥 Download Full Report (JSON)",
                data=report_json,
                file_name=f"genomics_report_patient_{patient_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json",
                use_container_width=True
            )
        
        with col2:
            # Create readable text report
            text_report = f"""
GENOMICS INTELLIGENCE REPORT
Patient ID: {patient_id}
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

{'='*80}
EXECUTIVE SUMMARY
{'='*80}
{data.get('executive_summary', 'N/A')}

{'='*80}
MUTATIONS ({len(mutations)})
{'='*80}
"""
            for mut in mutations:
                text_report += f"""
Gene: {mut.get('gene', 'Unknown')} {mut.get('variant', '')}
Significance: {mut.get('significance', 'Unknown')}
Actionability: {mut.get('actionability', 'Unknown')}
Treatment: {mut.get('recommended_treatment', 'N/A')}

"""
            
            text_report += f"""
{'='*80}
TREATMENT RECOMMENDATIONS ({len(treatments)})
{'='*80}
"""
            for tx in treatments:
                text_report += f"""
Priority {tx.get('priority', '?')}: {tx.get('therapy', 'Unknown')}
Indication: {tx.get('indication', 'N/A')}
Evidence: {tx.get('evidence_level', 'Unknown')}
Key Trial: {tx.get('key_trial', 'N/A')}

"""
            
            text_report += f"""
{'='*80}
CLINICAL TRIALS ({len(trials)})
{'='*80}
"""
            for trial in trials:
                text_report += f"""
{trial.get('nct_id', 'Unknown')} - {trial.get('phase', 'Unknown')}
{trial.get('title', 'No title')}
Eligibility Match: {trial.get('eligibility_match', 'Unknown')}

"""
            
            text_report += f"""
{'='*80}
NEXT STEPS
{'='*80}
{data.get('next_steps', 'N/A')}
"""
            
            st.download_button(
                label="📄 Download Text Report",
                data=text_report,
                file_name=f"genomics_report_patient_{patient_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                mime="text/plain",
                use_container_width=True
            )

else:
    # Placeholder when no data
    st.markdown("""
    <div class="info-box">
        <h4>Getting Started</h4>
        <p style="color: #374151; margin: 0;">
            Enter a patient ID and click <strong>"Run Genomic Analysis"</strong> to begin. 
            The system will automatically analyze mutations and provide treatment recommendations.
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Show pipeline visualization
    st.markdown('<h2 class="section-header">Analysis Pipeline</h2>', unsafe_allow_html=True)
    
    st.markdown("""
    <div class="pipeline-step">
        <strong>Step 1: Mutation Interpretation</strong> (Google Search)<br/>
        Analyzes clinical significance, mechanism, and actionability of each mutation
    </div>
    <div class="pipeline-step">
        <strong>Step 2: Clinical Trial Matching</strong> (ClinicalTrials.gov)<br/>
        Searches for recruiting trials targeting detected mutations
    </div>
    <div class="pipeline-step">
        <strong>Step 3: Evidence Search</strong> (PubMed)<br/>
        Retrieves supporting literature and key clinical trials
    </div>
    <div class="pipeline-step">
        <strong>Step 4: Report Synthesis</strong> (Gemini)<br/>
        Generates structured treatment recommendations and next steps
    </div>
    """, unsafe_allow_html=True)
    
    # Example patients
    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
    st.markdown("### Example Patients")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        <div style="background: white; padding: 1.5rem; border-radius: 12px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); border-left: 4px solid #10b981;">
            <h4 style="color: #1e40af; margin-bottom: 1rem;">Patient 123</h4>
            <p style="color: #374151; font-size: 0.9rem; margin: 0;">
                <strong>Mutations:</strong> PIK3CA H1047R, TP53 R273H<br/>
                <strong>Status:</strong> Actionable mutations detected<br/>
                <strong>Expected:</strong> FDA-approved treatments available
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div style="background: white; padding: 1.5rem; border-radius: 12px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); border-left: 4px solid #3b82f6;">
            <h4 style="color: #1e40af; margin-bottom: 1rem;">Patient 456</h4>
            <p style="color: #374151; font-size: 0.9rem; margin: 0;">
                <strong>Mutations:</strong> BRCA1 185delAG<br/>
                <strong>Status:</strong> High-impact mutation<br/>
                <strong>Expected:</strong> Multiple treatment options
            </p>
        </div>
        """, unsafe_allow_html=True)

# Footer
st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
st.caption("C.O.R.E. Genomics Intelligence | Powered by Google Gemini, ClinicalTrials.gov & PubMed")