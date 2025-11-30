"""
C.O.R.E. Agent Engine Entry Point
Deploys CaseAgent to Vertex AI Agent Engine via `adk deploy agent_engine`

Author: Faith Ogundimu
"""

import os
import vertexai
from google.adk.agents import Agent
from google.adk.tools.function_tool import FunctionTool

# Initialize Vertex AI
vertexai.init(
    project=os.environ.get("GOOGLE_CLOUD_PROJECT"),
    location=os.environ.get("GOOGLE_CLOUD_LOCATION", "global"),
)

# ============= Domain Tools =============
# These mirror the tools in CaseAgent but as standalone functions
# for Agent Engine deployment

def fetch_patient_summary(patient_id: str) -> dict:
    """
    Fetches a comprehensive patient summary for MDT preparation.
    Aggregates data from EHR, pathology, radiology, and genomics.
    
    Args:
        patient_id: Patient identifier (e.g., "123", "456", "789")
    
    Returns:
        dict: Patient readiness status with checklist and blockers
    """
    import json
    from pathlib import Path
    
    base_path = Path(__file__).parent.parent / "mock_db"
    
    result = {
        "patient_id": patient_id,
        "checklist": {},
        "blockers": [],
        "overall_status": "READY"
    }
    
    # 1. Clinical Notes
    try:
        with open(base_path / "clinical_notes.json", 'r') as f:
            data = json.load(f)
        key = f"patient_{patient_id}"
        if key in data:
            p = data[key]
            result["checklist"]["Clinical"] = f"Age: {p['demographics']['age']}, Dx: {p['diagnosis']['primary']}, Stage: {p['diagnosis']['stage']}"
        else:
            result["checklist"]["Clinical"] = "NOT FOUND"
            result["blockers"].append("Clinical data missing")
    except Exception as e:
        result["checklist"]["Clinical"] = f"Error: {str(e)}"
    
    # 2. Pathology (SQLite)
    try:
        import sqlite3
        conn = sqlite3.connect(str(base_path / "pathology_db.sqlite"))
        cursor = conn.cursor()
        cursor.execute('''
            SELECT diagnosis, histological_type, grade, er_status, pr_status, her2_status
            FROM pathology_reports WHERE patient_id = ? ORDER BY signed_date DESC LIMIT 1
        ''', (patient_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            result["checklist"]["Pathology"] = f"Dx: {row[0]}, Type: {row[1]}, Grade: {row[2]}, ER:{row[3]}, PR:{row[4]}, HER2:{row[5]}"
        else:
            result["checklist"]["Pathology"] = "NOT FOUND"
    except Exception as e:
        result["checklist"]["Pathology"] = f"Error: {str(e)}"
    
    # 3. Radiology (CSV)
    try:
        import csv
        with open(base_path / "radiology_scans.csv", 'r') as f:
            reader = csv.DictReader(f)
            scans = [row for row in reader if row['patient_id'] == patient_id]
        if scans:
            unsigned = [s for s in scans if s['report_status'] == 'DRAFT']
            if unsigned:
                result["checklist"]["Radiology"] = f"BLOCKER: {len(unsigned)} UNSIGNED report(s)"
                result["blockers"].append("Unsigned radiology reports")
                result["overall_status"] = "BLOCKED"
            else:
                latest = scans[-1]
                result["checklist"]["Radiology"] = f"Latest ({latest['modality']}): {latest['findings_summary']}"
        else:
            result["checklist"]["Radiology"] = "No scans found"
    except Exception as e:
        result["checklist"]["Radiology"] = f"Error: {str(e)}"
    
    # 4. Genomics
    try:
        with open(base_path / "genomics_data.json", 'r') as f:
            data = json.load(f)
        key = f"patient_{patient_id}"
        p = data.get(key)
        if p and p.get("status") != "NOT_FOUND":
            muts = [f"{m['gene']} {m['variant']}" for m in p.get("mutations", [])]
            result["checklist"]["Genomics"] = f"Mutations: {', '.join(muts) if muts else 'None'}"
        else:
            result["checklist"]["Genomics"] = "Genomic testing NOT completed"
            result["blockers"].append("Genomics pending")
            if result["overall_status"] != "BLOCKED":
                result["overall_status"] = "IN_PROGRESS"
    except Exception as e:
        result["checklist"]["Genomics"] = f"Error: {str(e)}"
    
    return result


def search_clinical_trials(gene: str, cancer_type: str = "breast cancer") -> dict:
    """
    Searches ClinicalTrials.gov for trials targeting a specific gene mutation.
    
    Args:
        gene: Gene name (e.g., "PIK3CA", "BRCA1")
        cancer_type: Cancer type for filtering
    
    Returns:
        dict: Matching clinical trials
    """
    import requests
    
    try:
        url = "https://clinicaltrials.gov/api/v2/studies"
        params = {
            "query.term": f"{gene} {cancer_type}",
            "filter.overallStatus": "RECRUITING",
            "pageSize": 5
        }
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            trials = []
            for study in data.get("studies", []):
                protocol = study.get("protocolSection", {})
                ident = protocol.get("identificationModule", {})
                trials.append({
                    "nct_id": ident.get("nctId"),
                    "title": ident.get("briefTitle"),
                    "status": protocol.get("statusModule", {}).get("overallStatus")
                })
            return {"status": "success", "trials": trials, "count": len(trials)}
        else:
            return {"status": "error", "message": f"API returned {response.status_code}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ============= Root Agent =============
# This is what Agent Engine deploys

root_agent = Agent(
    name="core_mdt_agent",
    model="gemini-2.0-flash",
    description="C.O.R.E. - Coordinated Oncology Readiness Engine. Prepares cancer MDT cases by aggregating patient data and identifying blockers.",
    instruction="""
    You are C.O.R.E., an AI assistant for cancer Multidisciplinary Team (MDT) case preparation.
    
    Your capabilities:
    1. Fetch patient summaries using fetch_patient_summary(patient_id)
    2. Search for clinical trials using search_clinical_trials(gene, cancer_type)
    
    When a user asks about a patient:
    1. Use fetch_patient_summary to get their readiness status
    2. Report the checklist items (Clinical, Pathology, Radiology, Genomics)
    3. Highlight any BLOCKERS that need resolution before MDT
    4. If mutations are found, offer to search for relevant clinical trials
    
    Be concise and clinical in your responses. Flag urgent issues clearly.
    
    Available test patients: 123, 456, 789
    """,
    tools=[
        FunctionTool(fetch_patient_summary),
        FunctionTool(search_clinical_trials)
    ]
)
