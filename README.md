# 🎯 C.O.R.E. (Coordinated Oncology Readiness Engine)

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: CC BY 4.0](https://img.shields.io/badge/License-CC%20BY%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by/4.0/)
[![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?logo=Streamlit&logoColor=white)](https://streamlit.io)
[![Google ADK](https://img.shields.io/badge/Google-ADK-4285F4?logo=google&logoColor=white)](https://ai.google.dev/adk)

> **An intelligent multi agent system for proactive MDT case preparation and deep genomic intelligence**

Built for the [Google AI Agents Intensive - 5 Day Course Capstone](https://www.kaggle.com/competitions/agents-intensive-capstone-project/overview) | **Track:** Agents for Good

---

## 📋 Table of Contents

- [Problem Statement](#-problem-statement)
- [Why Agents](#-why-agents)
- [Solution Overview](#-solution-overview)
- [Architecture](#-architecture)
- [Key Features](#-key-features)
- [Results & Evaluation](#-results--evaluation)
- [Installation](#-installation)
- [Usage](#-usage)
- [Project Structure](#-project-structure)
- [Technology Stack](#-technology-stack)
- [License](#-license)
- [Contact](#-contact)

---

## 🎯 Problem Statement

Multidisciplinary Team (MDT) meetings are the backbone of cancer care, bringing oncologists, surgeons, radiologists, pathologists and geneticists into the same room to decide treatment plans. In practice they are fragile, inefficient and expensive:

- Estimated **£50M per year for preparation** and another **£50M for attendance** across the UK (Taylor et al. 2010).
- Workflow analyses show **major workload and bottlenecks** in radiology and pathology services (Kane et al. 2007).
- Decisions are often made on an **“evidential patient”** assembled from partial records rather than a complete view of the case (Hamilton et al. 2016).
- Observational studies describe many MDTs as **“rubber stamp” or “tick box” meetings** where cases are rushed, key specialists are absent and discussion is dominated by a few voices (Fricker 2020).

On top of this, modern precision oncology adds another bottleneck:

- Genomic reports are complex and time consuming to interpret.
- Clinicians manually search OncoKB, ClinVar, ClinicalTrials.gov and PubMed for each actionable mutation.
- **Manual genomic interpretation can easily take 60+ minutes per patient**, which does not scale when an MDT has tens of cases.

The result is a workflow that consumes significant clinical resources while still delivering variable, sometimes incomplete decisions.

---

## 🤖 Why Agents

MDT preparation is naturally multi agent:

- Each domain (EHR, pathology, radiology, genomics, contraindications) has its **own data, tools and failure modes**.
- In real MDTs, **specialists work in parallel**, not sequentially.
- Genomic interpretation, in contrast, requires **sequential reasoning**: clinical significance → trial matching → evidence retrieval → synthesis.

A single monolithic LLM prompt does not reflect that reality.

C.O.R.E. deliberately mirrors MDT behaviour:
- **Parallel domain agents** behave like virtual specialists for EHR, pathology, radiology, genomics and drug safety.
- A **hierarchical synthesis agent** acts as a case manager that integrates specialist inputs into a structured readiness state.
- A **sequential four agent genomics pipeline** performs stepwise mutation interpretation, trial matching and evidence synthesis.
- A **deterministic Coordinator** orchestrates multiple patients and produces a dashboard, keeping the top level logic transparent and testable.

This gives:
- Faster execution through parallelism.
- Modularity, as each specialist can evolve independently.
- Traceability, since each specialist report is visible.
- Depth, via a dedicated genomics pipeline that surfaces treatment options and trials.

---

## 💡 Solution Overview

**C.O.R.E.** is a two phase multi agent system that:

1. **Autonomously prepares MDT cases 48 hours before the meeting**, checking completeness and surfacing blockers.
2. **Runs deep genomic intelligence** for patients with mutation data, producing treatment recommendations and clinical trial matches.

### Phase 1: Case Preparation (Parallel Specialists)

For each patient on the MDT roster:

1. **CoordinatorAgent** loads the roster and spawns one **CaseAgent** per patient.   
2. Each CaseAgent runs a **ParallelAgent** of five specialists:  
   - `PathologyAgent` over a SQLite database  
   - `RadiologyAgent` over a CSV report log  
   - `EHRAgent` over JSON clinical notes  
   - `GenomicsAgent` over a genomics registry  
   - `ContraindicationAgent` over drug safety rules  
3. A **CaseManager** LlmAgent synthesises these into a JSON readiness object with:
   - Structured checklist
   - Detected blockers
   - Overall status: `READY`, `IN_PROGRESS` or `BLOCKED`

### Phase 2: Genomics Intelligence (Sequential Pipeline)

For patients with mutation data:

1. **`MutationInterpreter`**  
   - Uses Google Search via Gemini tools to determine clinical significance, mechanism, actionability and prevalence per mutation.
2. **`ClinicalTrialMatcher`**  
   - Queries the ClinicalTrials.gov API by gene, variant and cancer type for recruiting Phase 2/3 trials.
3. **`EvidenceSearcher`**  
   - Calls PubMed E utilities to retrieve key clinical trials and evidence with PMIDs.
4. **`GenomicsSynthesizer`**  
   - Combines everything into a structured report:
     - Mutation list with actionability
     - Ranked treatment recommendations with evidence levels
     - Matched clinical trials
     - Suggested next steps for the MDT

This pipeline is implemented as a `SequentialAgent` composed of four LlmAgents.  

---

## 🏗️ Architecture

### High level layers

1. **Orchestration Layer**

   - `CoordinatorAgent` (pure Python, no LLM)
   - Loads MDT roster and genomics data.
   - Spawns `CaseAgent` instances (one per patient).
   - Runs Phase 1 and Phase 2.
   - Generates an MDT dashboard plus genomics intelligence outputs. 

2. **Phase 1: CaseAgent (Hierarchical Multi Agent)**

   - **Parallel specialist squad** implemented with `ParallelAgent`:  
     - `EHRAgent`
     - `PathologyAgent`
     - `RadiologyAgent`
     - `GenomicsAgent`
     - `ContraindicationAgent`
   - **CaseManager** LlmAgent aggregates results into a final JSON readiness object.

3. **Phase 2: GenomicsIntelligenceAgent (Sequential Pipeline)**

   - `MutationInterpreter` → `ClinicalTrialMatcher` → `EvidenceSearcher` → `GenomicsSynthesizer`, each an LlmAgent, wrapped in a `SequentialAgent`.

4. **Streamlit UI**

   - `1_🏠_Welcome.py` – narrative overview, architecture and metrics.  
   - `2_📈_Live_Execution.py` – runs Phase 1, shows logs and dashboard.  
   - `3_🧬_Genomics_Insights.py` – runs both phases for a selected patient and visualises mutations, treatments and trials.   

### Agent interaction diagram

```text
User / MDT Roster
          │
          ▼
┌──────────────────────────────┐
│        CoordinatorAgent      │  (deterministic)
└───────────┬──────────────────┘
            │
   ┌────────┴─────────┐
   │                  │
   ▼                  ▼
PHASE 1           PHASE 2
Case Preparation  Genomics Intelligence (conditional)

Patient-specific CaseAgent
┌─────────────────────────────────────────────────────────────┐
│ SequentialAgent: CasePipeline_patientX                      │
│   1) ParallelAgent SpecialistSquad                          │
│      • EHRAgent • PathologyAgent • RadiologyAgent           │
│      • GenomicsAgent • ContraindicationAgent                │
│   2) CaseManager (synthesis)                                │
└─────────────────────────────────────────────────────────────┘

GenomicsIntelligenceAgent (for patients with mutations)
┌─────────────────────────────────────────────────────────────┐
│ SequentialAgent: GenomicsIntelligencePipeline_patientX      │
│   1) MutationInterpreter (Google Search)                    │
│   2) ClinicalTrialMatcher (ClinicalTrials.gov)              │
│   3) EvidenceSearcher (PubMed)                              │
│   4) GenomicsSynthesizer (final report)                     │
└─────────────────────────────────────────────────────────────┘
````

![Architecture Diagram](docs/architecture-diagram.png)

---

## ✨ Key Features
### Multi agent design

* **Two phase workflow**
  * Phase 1: automated case readiness checks.
  * Phase 2: deep genomic intelligence triggered only when mutations are present.

* **Hierarchical multi agent architecture**
  * Parallel domain specialists plus supervisor style synthesis in CaseAgent. 
  * Sequential specialist pipeline for genomics.

* **Deterministic top level orchestration**
  * Coordinator is regular Python code with explicit control flow and logging, which keeps behaviour inspectable and testable. 

### Tool augmented reasoning

* Custom ADK `FunctionTool`s for:

  * EHR JSON, pathology SQLite, radiology CSV, genomics JSON and contraindication rules. 
* External APIs:

  * Google Search via Gemini tools for mutation interpretation. 
  * ClinicalTrials.gov API for trial discovery. 
  * PubMed E utilities for evidence retrieval with PMIDs. 

### Genomics intelligence output

* Clinical significance and actionability per mutation.
* Identification of FDA approved targeted therapies where available.
* Ranked treatment recommendations with evidence levels and key trials.
* Top clinical trial matches with phase and eligibility summaries.
* Concrete next step suggestions for MDT discussion. 

### Observability and clinician facing UI

* Live, coloured logs surfaced in the **Live Execution** page for every step of the Coordinator and CaseAgents. 
* Streamlit dashboards for:

  * MDT readiness status, blockers and checklists.
  * Genomics overview, mutation cards, treatment cards and clinical trial cards, plus JSON and text report downloads. 

---

## 📊 Results & Evaluation

### Phase 1 – Case preparation behaviour

Behavioural evaluation is implemented in `evaluation/core_evaluation.py` using a labelled test set in `evaluation/mdt_eval_labels.json`.

Key metrics from `core_eval_metrics.json`:

* **Total labelled cases:** 3
* **Status accuracy:** 100 percent (all READY/BLOCKED statuses correct)
* **Blocker detection:**

  * Hits: 2
  * Misses: 0
  * False positives: 0
* **Average latency per case (Phase 1):** **3.2 seconds**
* **Total evaluation time:** 9.6 seconds for 3 patients

The Welcome page summarises this as an **approximately 84 percent speedup** compared with a sequential baseline. 

### Phase 2 – Genomics intelligence performance

On synthetic but realistic breast cancer genomics profiles, the system:

* Reduces manual mutation interpretation from **60+ minutes to around 2–3 minutes per patient**, including external API calls.
* Surfaces actionable mutations, FDA approved targeted therapies and relevant trials using Google Search, ClinicalTrials.gov and PubMed.
* Produces structured reports with PMIDs and NCT IDs that can be exported as JSON or text for MDT packs.

These genomics metrics are scenario based rather than formally benchmarked, but the pipeline is fully implemented and observable end to end.

---

## 🚀 Installation

### Prerequisites

* Python 3.10 or higher
* Git
* Google AI API key (for Gemini)

### 1. Clone the repository

```bash
git clone https://github.com/faith-ogun/CORE-adk-capstone.git
cd CORE-adk-capstone
```

### 2. Create a virtual environment

```bash
# macOS / Linux
python3 -m venv venv
source venv/bin/activate

# Windows
python -m venv venv
venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file in the project root:

```env
# Google AI API Key
GOOGLE_API_KEY=your_gemini_api_key_here

# Optional: Email for PubMed E-utilities
ENTREZ_EMAIL=your_email@example.com
```

Get an API key from **Google AI Studio** and paste it into `.env`.

### 5. Initialise mock data

```bash
python3 scripts/setup_mock_data.py
```

This populates the `mock_db` folder with:

* `pathology_db.sqlite` – pathology database
* `radiology_scans.csv` – imaging reports
* `clinical_notes.json` – EHR snapshots
* `genomics_data.json` – mutation profiles
* `mdt_roster_2025-11-18.json` – MDT roster

---

## 💻 Usage

### Option 1 – Streamlit UI (recommended)

From the repository root:

```bash
streamlit run 1_🏠_Welcome.py
```

Open `http://localhost:8501` in your browser.

Pages:

1. **Welcome**

   * Project background, architecture and headline metrics. 

2. **Live Execution**

   * Runs Phase 1 only.
   * Shows live logs, per patient readiness, blockers and a downloadable MDT dashboard. 

3. **Genomics Insights**

   * Runs both Phase 1 and Phase 2.
   * Enter a patient ID (for example `123`) and trigger genomic analysis.
   * View mutation cards, treatment options and clinical trial matches.
   * Download JSON and text versions of the genomics report. 

### Option 2 – Command line coordinator

To run the full pipeline headless:

```bash
cd CORE-adk-capstone
python3 agents.coordinator
```

This will:

* Load the MDT roster.
* Run Phase 1 for all patients.
* Run Phase 2 for patients with mutation data.
* Write:

```text
output/mdt_dashboard.json          # MDT readiness dashboard
output/genomics_intelligence.json  # Genomics reports per patient
```

### Option 3 – Behavioural evaluation

To reproduce the Phase 1 evaluation:

```bash
python3 evaluation.core_evaluation
```

Metrics are written to `evaluation/core_eval_metrics.json`.

---

## 📁 Project Structure

```text
CORE-adk-capstone/
├── 1_🏠_Welcome.py                # Streamlit landing page (narrative + metrics)
├── 2_📈_Live_Execution.py         # Phase 1 live execution UI 
├── 3_🧬_Genomics_Insights.py      # Phase 2 genomics UI 
├── agents/
│   ├── coordinator.py             # Deterministic CoordinatorAgent 
│   ├── case_agent.py              # CaseAgent with Parallel + Sequential pipeline 
│   └── genomics_intelligence.py   # GenomicsIntelligenceAgent sequential pipeline 
├── tools/
│   ├── clinical_trials_api.py     # ClinicalTrials.gov integration
│   └── pubmed_api.py              # PubMed E utilities integration
├── mock_db/
│   ├── pathology_db.sqlite        # Pathology database
│   ├── radiology_scans.csv        # Radiology reports
│   ├── clinical_notes.json        # EHR data
│   ├── genomics_data.json         # Genomic mutation profiles
│   └── mdt_roster_2025-11-18.json # MDT roster
├── evaluation/
│   ├── core_evaluation.py         # Behavioural evaluation script
│   ├── mdt_eval_labels.json       # Ground truth labels 
│   └── core_eval_metrics.json     # Evaluation outputs
├── output/                        # Generated dashboards and reports
├── scripts/
│   └── setup_mock_data.py         # Helper to create mock_db
├── assets/                        # Logos and hero image for Streamlit UI 
├── requirements.txt               # Python dependencies
├── .env.example                   # Environment variable template
└── README.md                      # This file
```

---

## 🛠️ Technology Stack

### Core frameworks

* **Google Agent Development Kit (ADK)**

  * `LlmAgent`, `ParallelAgent`, `SequentialAgent` for agent composition.
* **Gemini 2.0 Flash**

  * LLM used for all reasoning and tool orchestration.
* **Streamlit**

  * Lightweight clinical UI for execution and visualisation.

### External data sources

* **Google Search via Gemini tools** – mutation interpretation and clinical significance. 
* **ClinicalTrials.gov API** – trial matching for actionable mutations. 
* **PubMed E utilities** – literature search and PMIDs. 

### Data storage

* **SQLite** – pathology database.
* **CSV** – radiology reports.
* **JSON** – clinical notes, genomics data, MDT roster and evaluation labels.

---

## 📄 License

All code and documentation in this repository are released under the **Attribution 4.0 International (CC BY 4.0)** licence.

---

## 📧 Contact
**Faith Ogundimu**
Research Ireland Postgraduate Scholar, Royal College of Surgeons in Ireland (RCSI)

* GitHub: [https://github.com/faith-ogun](https://github.com/faith-ogun)
* LinkedIn: [https://www.linkedin.com/in/faith-ogundimu](https://www.linkedin.com/in/faith-ogundimu)
* Email: [faithogundimu25@rcsi.com](mailto:faithogundimu25@rcsi.com)

**Project repository:** [https://github.com/faith-ogun/CORE-adk-capstone](https://github.com/faith-ogun/CORE-adk-capstone)

---

<div align="center">

**Built with ❤️ to reduce MDT friction and bring precision oncology into everyday clinical practice.**

🏥 Agents for Good | 🤖 Google ADK & Gemini | 🧬 Genomic intelligence at scale

</div>
