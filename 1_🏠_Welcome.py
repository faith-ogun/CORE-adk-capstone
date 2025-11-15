import streamlit as st
from streamlit.components.v1 import html
from datetime import datetime

# -------------------------- Page config & styling --------------------------
st.set_page_config(
    page_title="C.O.R.E. - MDT Readiness System",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for professional styling - Blue theme matching logo
st.markdown("""
<style>
    /* Main background and text */
    .stApp {
        background-color: #fafbfc;
    }
    
    /* Logo container */
    .logo-container {
        background: white;
        padding: 2rem;
        border-radius: 15px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        margin-bottom: 2rem;
        text-align: center;
    }
    
    /* Stats cards - Consistent blue */
    .stats-container {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 1.5rem;
        margin: 2rem 0;
    }
    
    .stat-card {
        background: white;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        text-align: center;
        border-top: 4px solid #1e88e5;
        transition: transform 0.3s ease, box-shadow 0.3s ease;
    }
    
    .stat-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 8px 16px -4px rgba(30, 136, 229, 0.3);
    }
    
    .stat-value {
        font-size: 2.5rem;
        font-weight: 800;
        color: #004e89;
        margin-bottom: 0.5rem;
    }
    
    .stat-label {
        color: #64748b;
        font-size: 0.9rem;
        font-weight: 600;
    }
    
    /* Feature cards - Unified blue theme */
    .feature-card {
        background: white;
        padding: 2rem;
        border-radius: 15px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        border-left: 5px solid #1e88e5;
        margin-bottom: 2rem;
        transition: transform 0.3s ease, box-shadow 0.3s ease;
    }
    
    .feature-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 16px -4px rgba(30, 136, 229, 0.2);
        border-left-color: #004e89;
    }
    
    .feature-card-secondary {
        border-left-color: #42b8dd;
    }
    
    .feature-card-secondary:hover {
        border-left-color: #1e88e5;
    }
    
    .feature-title {
        color: #004e89;
        font-size: 1.4rem;
        font-weight: 700;
        margin-bottom: 1rem;
    }
    
    .feature-description {
        color: #374151;
        line-height: 1.7;
        font-size: 1rem;
    }
    
    /* Section headers */
    .section-header {
        color: #004e89;
        font-size: 2.2rem;
        font-weight: 700;
        text-align: center;
        margin: 3rem 0 2rem 0;
        border-bottom: 3px solid #e3f2fd;
        padding-bottom: 1rem;
    }
    
    /* Timeline styling */
    .timeline-item {
        background: white;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
        margin-bottom: 1rem;
        border-left: 4px solid #1e88e5;
    }
    
    .timeline-item-complete {
        border-left-color: #42b8dd;
    }
    
    .timeline-item-current {
        border-left-color: #ffa726;
        background: #fff8e1;
    }
    
    .timeline-item-future {
        border-left-color: #cbd5e1;
        opacity: 0.7;
    }
    
    .timeline-date {
        color: #004e89;
        font-weight: 700;
        font-size: 1.1rem;
        margin-bottom: 0.5rem;
    }
    
    .timeline-content {
        color: #374151;
        line-height: 1.6;
    }
    
    /* Badge styling - Blue themed */
    .badge {
        display: inline-block;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.85rem;
        margin: 0.25rem;
    }
    
    .badge-primary {
        background: #e3f2fd;
        color: #004e89;
        border: 1px solid #90caf9;
    }
    
    .badge-secondary {
        background: #e0f7fa;
        color: #006064;
        border: 1px solid #80deea;
    }
    
    .badge-warning {
        background: #fff8e1;
        color: #f57f17;
        border: 1px solid #ffd54f;
    }
    
    /* Call to action */
    .cta-container {
        background: linear-gradient(135deg, #e3f2fd 0%, #e0f7fa 100%);
        padding: 2rem;
        border-radius: 15px;
        text-align: center;
        margin: 2rem 0;
        border: 2px solid #90caf9;
    }
    
    /* Footer styling */
    .footer-section {
        background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
        padding: 2rem;
        margin: 3rem -1rem -1rem -1rem;
        border-radius: 20px 20px 0 0;
        text-align: center;
    }
    
    /* Sidebar styling */
    .stSidebar {
        background: linear-gradient(180deg, #f1f5f9 0%, #e2e8f0 100%);
    }
    
    /* Info boxes - Blue themed */
    .info-box {
        background: #e3f2fd;
        border-left: 4px solid #1e88e5;
        padding: 1.5rem;
        border-radius: 8px;
        margin: 1.5rem 0;
    }
    
    .info-box h4 {
        color: #004e89;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    # Logo in sidebar
    st.image("./assets/core_logo_2.png", use_container_width=True)
    
    st.markdown("---")
    
    # Quick stats in sidebar
    st.markdown("""
    <div style="background: white; padding: 1rem; border-radius: 10px; margin: 1rem 0;">
        <h4 style="color: #004e89; margin-bottom: 1rem; text-align: center;">Development Status</h4>
        <div style="margin: 0.75rem 0;">
            <div style="color: #64748b; font-size: 0.85rem;">Progress</div>
            <div style="background: #e2e8f0; border-radius: 10px; height: 8px; margin-top: 0.25rem;">
                <div style="background: linear-gradient(90deg, #1e88e5 0%, #42b8dd 100%); width: 15%; height: 100%; border-radius: 10px;"></div>
            </div>
            <div style="color: #1e88e5; font-size: 0.75rem; margin-top: 0.25rem; font-weight: 600;">15% Complete</div>
        </div>
        <div style="margin: 0.75rem 0;">
            <div style="color: #64748b; font-size: 0.85rem;">Days Remaining</div>
            <div style="color: #004e89; font-size: 1.5rem; font-weight: 700;">16</div>
        </div>
        <div style="margin: 0.75rem 0;">
            <div style="color: #64748b; font-size: 0.85rem;">Submission Deadline</div>
            <div style="color: #004e89; font-size: 0.9rem; font-weight: 600;">Dec 1, 2025</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    st.markdown("""
    <div style="text-align: center; padding: 0.5rem;">
        <p style="color: #64748b; font-size: 0.8rem;">
            Built for<br/>
            <strong style="color: #004e89;">Google AI Agents Intensive</strong><br/>
            Capstone Project
        </p>
    </div>
    """, unsafe_allow_html=True)

# Hero Section - Image
st.image("./assets/hero_image.png", use_container_width=True)

# Description below hero
st.markdown(f"""
<div style="text-align: center; padding: 2rem 1rem; max-width: 900px; margin: 0 auto;">
    <p style="color: #374151; font-size: 1.2rem; line-height: 1.8; margin-bottom: 1rem;">
        An intelligent multi-agent system that autonomously prepares cancer MDT cases 48 hours before meetings,
        ensuring 100% case readiness while providing AI-powered genomic intelligence for precision medicine decisions.
    </p>
    <p style="color: #94a3b8; font-size: 1rem; font-style: italic;">
        Active Development • Last updated: {datetime.now().strftime("%B %d, %Y")}
    </p>
</div>
""", unsafe_allow_html=True)

st.markdown("<br/>", unsafe_allow_html=True)

# Key Metrics Section
st.markdown("""
<div class="stats-container">
    <div class="stat-card">
        <div class="stat-value">96%</div>
        <div class="stat-label">Target Precision<br/>(Case Readiness)</div>
    </div>
    <div class="stat-card">
        <div class="stat-value">70%</div>
        <div class="stat-label">Time Reduction<br/>(MDT Prep)</div>
    </div>
    <div class="stat-card">
        <div class="stat-value">6.8s</div>
        <div class="stat-label">Avg Processing<br/>(Per Case)</div>
    </div>
    <div class="stat-card">
        <div class="stat-value">87%</div>
        <div class="stat-label">Actionable Genomics<br/>(Breast Cancer)</div>
    </div>
</div>
""", unsafe_allow_html=True)

# Problem & Solution Section
st.markdown('<h2 class="section-header">The Challenge</h2>', unsafe_allow_html=True)

col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    <div class="feature-card">
        <div class="feature-title">Current MDT Reality</div>
        <div class="feature-description">
            <ul style="margin: 0; padding-left: 1.5rem;">
                <li><strong>40-60%</strong> of cases arrive incomplete at MDT meetings</li>
                <li><strong>3-5 hours</strong> of manual coordination per meeting</li>
                <li><strong>Fragmented data</strong> across pathology, radiology, genomics</li>
                <li><strong>Delayed decisions</strong> impacting patient care</li>
                <li><strong>Missed opportunities</strong> in precision medicine</li>
            </ul>
        </div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div class="feature-card feature-card-secondary">
        <div class="feature-title">C.O.R.E. Solution</div>
        <div class="feature-description">
            <ul style="margin: 0; padding-left: 1.5rem;">
                <li><strong>Autonomous agents</strong> proactively assemble case data</li>
                <li><strong>Real-time validation</strong> of data completeness</li>
                <li><strong>AI-powered genomics</strong> interpretation with Gemini 2.0</li>
                <li><strong>Clinical trial matching</strong> via real external APIs</li>
                <li><strong>Evidence-based recommendations</strong> with citations</li>
            </ul>
        </div>
    </div>
    """, unsafe_allow_html=True)

# Multi-Agent System Overview
st.markdown('<h2 class="section-header">Multi-Agent Architecture</h2>', unsafe_allow_html=True)

# Agent types
agent_features = [
    {
        "title": "CoordinatorAgent",
        "description": "Orchestrates the entire workflow using Gemini 2.0 Flash. Spawns Case Agents for each patient, monitors progress, manages sessions, and generates the final readiness dashboard.",
        "badges": ["Gemini 2.0", "Session Management", "A2A Protocol"]
    },
    {
        "title": "Autonomous CaseAgents",
        "description": "Goal-oriented agents (one per patient) that autonomously request data, validate completeness, handle conflicts, and escalate blockers. Each agent uses LLM reasoning to make intelligent decisions.",
        "badges": ["Goal-Oriented", "LLM Reasoning", "Autonomous"]
    },
    {
        "title": "Specialist Agents",
        "description": "Data access agents for Pathology (SQLite/MCP), Radiology (CSV), EHR (JSON), providing validated data from mock hospital systems with intelligent filtering.",
        "badges": ["MCP Tools", "Custom Tools", "Data Validation"]
    },
    {
        "title": "GenomicsIntelligenceAgent",
        "description": "The key differentiator. LLM-powered genomic analysis using Gemini + real external APIs (cBioPortal, ClinicalTrials.gov, PubMed) to interpret mutations, match clinical trials, and cite evidence.",
        "badges": ["Gemini 2.0", "3 Real APIs", "RAG", "Clinical Intelligence"]
    }
]

col1, col2 = st.columns(2)

for i, agent in enumerate(agent_features):
    with col1 if i % 2 == 0 else col2:
        card_class = "feature-card" if i % 2 == 0 else "feature-card feature-card-secondary"
        badges_html = "".join([f'<span class="badge badge-primary">{badge}</span>' for badge in agent['badges']])
        st.markdown(f"""
        <div class="{card_class}">
            <div class="feature-title">{agent['title']}</div>
            <div class="feature-description">
                {agent['description']}
            </div>
            <div style="margin-top: 1rem;">
                {badges_html}
            </div>
        </div>
        """, unsafe_allow_html=True)

# Key Features Section
st.markdown('<h2 class="section-header">Capstone Requirements Met</h2>', unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("""
    <div class="info-box">
        <h4>Multi-Agent System</h4>
        <ul style="margin: 0; padding-left: 1.5rem; color: #374151; font-size: 0.9rem;">
            <li>Sequential agents</li>
            <li>Parallel agents</li>
            <li>Loop agents</li>
            <li>LLM-powered reasoning</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div class="info-box">
        <h4>Tools & APIs</h4>
        <ul style="margin: 0; padding-left: 1.5rem; color: #374151; font-size: 0.9rem;">
            <li>MCP integration</li>
            <li>Custom tools</li>
            <li>3 real external APIs</li>
            <li>OpenAPI tools</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown("""
    <div class="info-box">
        <h4>Observability</h4>
        <ul style="margin: 0; padding-left: 1.5rem; color: #374151; font-size: 0.9rem;">
            <li>Tracing (@trace)</li>
            <li>Prometheus metrics</li>
            <li>Structured logging</li>
            <li>Evaluation framework</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

# Development Timeline
st.markdown('<h2 class="section-header">Development Timeline</h2>', unsafe_allow_html=True)

col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    <h4 style="color: #004e89; margin-bottom: 1rem;">Week 1: Core Development</h4>
    
    <div class="timeline-item timeline-item-complete">
        <div class="timeline-date">Nov 15 (Day 1)</div>
        <div class="timeline-content">Project setup, architecture design, mock data creation</div>
    </div>
    
    <div class="timeline-item timeline-item-current">
        <div class="timeline-date" style="color: #f57f17;">Nov 16-17 (Days 2-3)</div>
        <div class="timeline-content">Implement CoordinatorAgent & CaseAgent with ADK</div>
    </div>
    
    <div class="timeline-item timeline-item-future">
        <div class="timeline-date" style="color: #64748b;">Nov 18-19 (Days 4-5)</div>
        <div class="timeline-content">Build Specialist Agents (Pathology, Radiology, EHR)</div>
    </div>
    
    <div class="timeline-item timeline-item-future">
        <div class="timeline-date" style="color: #64748b;">Nov 20-21 (Days 6-7)</div>
        <div class="timeline-content">Develop GenomicsIntelligenceAgent with real APIs</div>
    </div>
    
    <div class="timeline-item timeline-item-future">
        <div class="timeline-date" style="color: #64748b;">Nov 22 (Day 8)</div>
        <div class="timeline-content">Create Streamlit UI pages</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    <h4 style="color: #004e89; margin-bottom: 1rem;">Week 2: Polish & Submit</h4>
    
    <div class="timeline-item timeline-item-future">
        <div class="timeline-date" style="color: #64748b;">Nov 23-24 (Days 9-10)</div>
        <div class="timeline-content">Add evaluation framework + run tests</div>
    </div>
    
    <div class="timeline-item timeline-item-future">
        <div class="timeline-date" style="color: #64748b;">Nov 25-26 (Days 11-12)</div>
        <div class="timeline-content">Write comprehensive documentation</div>
    </div>
    
    <div class="timeline-item timeline-item-future">
        <div class="timeline-date" style="color: #64748b;">Nov 27 (Day 13)</div>
        <div class="timeline-content">Deploy to Streamlit Community Cloud</div>
    </div>
    
    <div class="timeline-item timeline-item-future">
        <div class="timeline-date" style="color: #64748b;">Nov 28-29 (Days 14-15)</div>
        <div class="timeline-content">Create YouTube video (<3 min)</div>
    </div>
    
    <div class="timeline-item" style="border-left-color: #004e89; background: #e3f2fd;">
        <div class="timeline-date">Dec 1 (Day 16)</div>
        <div class="timeline-content">Make repo public + submit to Kaggle</div>
    </div>
    """, unsafe_allow_html=True)

# Call to Action
st.markdown("""
<div class="cta-container">
    <h3 style="color: #004e89; margin-bottom: 1rem;">Ready to Explore?</h3>
    <p style="color: #64748b; font-size: 1.1rem; margin-bottom: 1.5rem;">
        Navigate through the modules in the sidebar to see C.O.R.E. in action
    </p>
    <div>
        <span class="badge badge-warning">Under Active Development</span>
        <span class="badge badge-primary">Multi-Agent System</span>
        <span class="badge badge-secondary">AI-Powered Genomics</span>
    </div>
</div>
""", unsafe_allow_html=True)

# Technology Stack
st.markdown('<h2 class="section-header">Technology Stack</h2>', unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("""
    <div class="feature-card">
        <div class="feature-title">AI & Agents</div>
        <div class="feature-description">
            <ul style="margin: 0; padding-left: 1.5rem; font-size: 0.9rem;">
                <li><strong>Google ADK</strong> - Agent framework</li>
                <li><strong>Gemini 2.0 Flash</strong> - LLM reasoning</li>
                <li><strong>A2A Protocol</strong> - Agent communication</li>
            </ul>
        </div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div class="feature-card feature-card-secondary">
        <div class="feature-title">External APIs</div>
        <div class="feature-description">
            <ul style="margin: 0; padding-left: 1.5rem; font-size: 0.9rem;">
                <li><strong>cBioPortal</strong> - Mutation data</li>
                <li><strong>ClinicalTrials.gov</strong> - Trial matching</li>
                <li><strong>PubMed</strong> - Literature search</li>
            </ul>
        </div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown("""
    <div class="feature-card">
        <div class="feature-title">Infrastructure</div>
        <div class="feature-description">
            <ul style="margin: 0; padding-left: 1.5rem; font-size: 0.9rem;">
                <li><strong>Streamlit</strong> - Web UI</li>
                <li><strong>SQLite/CSV/JSON</strong> - Mock data</li>
                <li><strong>Prometheus</strong> - Metrics</li>
            </ul>
        </div>
    </div>
    """, unsafe_allow_html=True)

# Footer Section
st.markdown("""
<div class="footer-section">
    <h3 style="color: #004e89; margin-bottom: 2rem;">Project Links</h3>
    <p style="color: #64748b; font-size: 1.1rem; margin-bottom: 2rem;">
        Building the future of MDT efficiency with AI
    </p>
""", unsafe_allow_html=True)

# Footer links
footer_col1, footer_col2, footer_col3, footer_col4 = st.columns(4)

with footer_col1:
    st.markdown("""
    <a href="https://github.com/YOUR_USERNAME/CORE-adk-capstone" target="_blank" style="text-decoration: none;">
        <div style="background: white; padding: 1.5rem; border-radius: 15px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); text-align: center; transition: all 0.3s ease;" onmouseover="this.style.transform='translateY(-3px)'; this.style.boxShadow='0 8px 16px rgba(0,0,0,0.1)'" onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 2px 4px rgba(0,0,0,0.05)'">
            <img src="https://cdn-icons-png.flaticon.com/512/25/25231.png" style="width: 70px; height: 70px; margin-bottom: 0.75rem;">
            <div style="font-size: 0.85rem; color: #374151; font-weight: 600;">GitHub Repo</div>
        </div>
    </a>
    """, unsafe_allow_html=True)

with footer_col2:
    st.markdown("""
    <a href="https://www.kaggle.com/competitions/agents-intensive-capstone" target="_blank" style="text-decoration: none;">
        <div style="background: white; padding: 1.5rem; border-radius: 15px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); text-align: center; transition: all 0.3s ease;" onmouseover="this.style.transform='translateY(-3px)'; this.style.boxShadow='0 8px 16px rgba(0,0,0,0.1)'" onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 2px 4px rgba(0,0,0,0.05)'">
            <img src="https://cdn4.iconfinder.com/data/icons/logos-and-brands/512/189_Kaggle_logo_logos-512.png" style="width: 70px; height: 70px; margin-bottom: 0.75rem;">
            <div style="font-size: 0.85rem; color: #374151; font-weight: 600;">Kaggle Capstone</div>
        </div>
    </a>
    """, unsafe_allow_html=True)

with footer_col3:
    st.markdown("""
    <a href="https://ai.google.dev/adk" target="_blank" style="text-decoration: none;">
        <div style="background: white; padding: 1.5rem; border-radius: 15px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); text-align: center; transition: all 0.3s ease;" onmouseover="this.style.transform='translateY(-3px)'; this.style.boxShadow='0 8px 16px rgba(0,0,0,0.1)'" onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 2px 4px rgba(0,0,0,0.05)'">
            <img src="https://www.gstatic.com/lamda/images/gemini_sparkle_v002_d4735304ff6292a690345.svg" style="width: 70px; height: 70px; margin-bottom: 0.75rem;">
            <div style="font-size: 0.85rem; color: #374151; font-weight: 600;">Google ADK</div>
        </div>
    </a>
    """, unsafe_allow_html=True)

with footer_col4:
    st.markdown("""
    <a href="https://www.rcsi.com/" target="_blank" style="text-decoration: none;">
        <div style="background: white; padding: 1.5rem; border-radius: 15px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); text-align: center; transition: all 0.3s ease;" onmouseover="this.style.transform='translateY(-3px)'; this.style.boxShadow='0 8px 16px rgba(0,0,0,0.1)'" onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 2px 4px rgba(0,0,0,0.05)'">
            <img src="https://www.rcsi.com/assets/images/logos/logo-uni.svg" style="width: 70px; height: 70px; margin-bottom: 0.75rem;">
            <div style="font-size: 0.85rem; color: #374151; font-weight: 600;">RCSI</div>
        </div>
    </a>
    """, unsafe_allow_html=True)

st.markdown('<br/>', unsafe_allow_html=True)

# Final Footer
st.markdown("---")

st.markdown(f"""
<div style="text-align: center; padding: 2rem 0; background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%); margin: 2rem -1rem -1rem -1rem; border-radius: 15px 15px 0 0;">
    <div style="font-size: 1.2rem; font-weight: 600; color: #004e89; margin-bottom: 0.5rem;">
        C.O.R.E. - Coordinated Oncology Readiness Engine
    </div>
    <div style="color: #64748b; font-size: 1rem;">
        Developed by <strong style="color: #004e89;">Faith Ogundimu</strong> • PhD Student @ RCSI
    </div>
    <div style="color: #94a3b8; font-size: 0.9rem; margin-top: 0.5rem;">
        Built for Google AI Agents Intensive Capstone • Track: Agents for Good
    </div>
    <div style="color: #cbd5e1; font-size: 0.85rem; margin-top: 1rem; font-style: italic;">
        © {datetime.now().year} • Advancing MDT efficiency through multi-agent systems
    </div>
</div>
""", unsafe_allow_html=True)