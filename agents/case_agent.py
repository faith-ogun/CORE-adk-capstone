"""
CaseAgent - Patient-specific autonomous agent for C.O.R.E.

This agent is responsible for a SINGLE patient. It:
1. Maintains a readiness checklist (Clinical, Pathology, Radiology, Genomics).
2. Proactively reaches out to Specialist Agents via A2A (simulated via tools).
3. Validates data and updates status.
4. Flags blockers.

Author: Faith Ogundimu
"""

import json
import logging
import os
import asyncio
from pathlib import Path
from typing import Dict, List, Optional, Any

# Google ADK imports
from google.adk.agents import LlmAgent
from google.adk.models.google_llm import Gemini
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService 
from google.adk.tools.function_tool import FunctionTool
from google.genai import types

# Configure logging
logger = logging.getLogger(__name__)

class CaseAgent:
    def __init__(
        self, 
        patient_id: str, 
        mdt_date: str,
        model_name: str = "gemini-2.0-flash" 
    ):
        self.patient_id = patient_id
        self.mdt_date = mdt_date
        self.model_name = model_name
        
        # Define consistent identifiers for session management
        self.app_name = f"case_agent_{patient_id}"
        self.user_id = "core_system"
        self.session_id = f"case_{patient_id}_{mdt_date}"
        
        # --- 1. Goal State (The Readiness Checklist) ---
        self.readiness_state = {
            "patient_id": patient_id,
            "overall_status": "IN_PROGRESS",
            "checklist": {
                "Clinical_Notes": {"status": "PENDING", "data": None},
                "Pathology_Report": {"status": "PENDING", "data": None},
                "Radiology_Report": {"status": "PENDING", "data": None},
                "Radiology_Images": {"status": "PENDING", "data": None},
                "Genomics_Profile": {"status": "PENDING", "data": None} 
            },
            "blockers": []
        }

        # --- 2. Initialize the ADK Agent ---
        self.agent = self._build_agent()
        
        # --- 3. Initialize Session Service ---
        self.session_service = InMemorySessionService()

        # --- 4. Create a runner specifically for this agent instance ---
        self.runner = Runner(
            agent=self.agent,
            app_name=self.app_name,
            session_service=self.session_service
        )

    def _build_agent(self) -> LlmAgent:
        """Defines the LLM Agent, System Instructions, and Tools."""
        
        # --- Tool Definitions (Closures to access self.readiness_state) ---
        
        def get_readiness_status() -> dict:
            """
            Returns the current checklist status. Use this to see what is missing.
            """
            return self.readiness_state

        def update_checklist(category: str, status: str, summary: str) -> dict:
            """
            Updates the checklist when data is found.
            
            Args:
                category: 'Clinical_Notes', 'Pathology_Report', 'Radiology_Report', 'Radiology_Images', or 'Genomics_Profile'
                status: 'COMPLETE', 'PARTIAL', 'MISSING', 'BLOCKER', or 'NOT_APPLICABLE'
                summary: A brief summary of the data found.
            """
            if category not in self.readiness_state["checklist"]:
                return {"status": "error", "message": f"Invalid category: {category}"}
            
            self.readiness_state["checklist"][category]["status"] = status
            self.readiness_state["checklist"][category]["data"] = summary
            
            # Auto-update overall status
            all_complete = all(v["status"] == "COMPLETE" for k,v in self.readiness_state["checklist"].items())
            has_blockers = any(v["status"] == "BLOCKER" for k,v in self.readiness_state["checklist"].items())
            
            if has_blockers:
                self.readiness_state["overall_status"] = "BLOCKED"
            elif all_complete:
                self.readiness_state["overall_status"] = "READY"
            else:
                self.readiness_state["overall_status"] = "IN_PROGRESS"
                
            logger.info(f"[{self.patient_id}] Updated {category} -> {status}")
            return {"status": "success", "current_state": self.readiness_state["checklist"][category]}

        def flag_blocker(reason: str, severity: str = "HIGH") -> dict:
            """Flags a blocker (e.g., missing report) requiring human attention."""
            blocker = {"reason": reason, "severity": severity, "timestamp": "now"}
            self.readiness_state["blockers"].append(blocker)
            self.readiness_state["overall_status"] = "BLOCKED"
            logger.warning(f"[{self.patient_id}] BLOCKER: {reason}")
            return {"status": "flagged"}

        def request_specialist_data(specialist_type: str, query_details: str) -> dict:
            """
            Requests data from specialist agents by reading actual data files.
            
            Args:
                specialist_type: 'EHR', 'Pathology', 'Radiology', 'Genomics'
                query_details: What you are looking for.
            """
            logger.info(f"[{self.patient_id}] A2A Request -> {specialist_type}: {query_details}")
            
            # Determine base path for data files
            # Assumes data files are in mock_db/ relative to project root
            base_path = Path(__file__).parent.parent / "mock_db"
            
            try:
                if specialist_type == "Genomics":
                    genomics_file = base_path / "genomics_data.json"
                    if not genomics_file.exists():
                        return {"status": "ERROR", "content": f"Genomics data file not found at {genomics_file}"}
                    
                    with open(genomics_file, 'r') as f:
                        genomics_data = json.load(f)
                    
                    patient_key = f"patient_{self.patient_id}"
                    if patient_key not in genomics_data:
                        return {
                            "source": "GenomicsIntelligenceAgent",
                            "status": "NOT_FOUND",
                            "content": f"No genomic data available for patient {self.patient_id}"
                        }
                    
                    patient_genomics = genomics_data[patient_key]
                    
                    # Check if testing wasn't done
                    if patient_genomics.get("status") == "NOT_FOUND":
                        return {
                            "source": "GenomicsIntelligenceAgent",
                            "status": "NOT_FOUND",
                            "content": patient_genomics.get("reason", "Genomic testing not completed"),
                            "recommendation": patient_genomics.get("recommendation", "")
                        }
                    
                    # Format the genomics findings
                    mutations_summary = []
                    for mut in patient_genomics.get("mutations", []):
                        mutations_summary.append(f"{mut['gene']} {mut['variant']} ({mut['interpretation']})")
                    
                    cna_summary = []
                    for cna in patient_genomics.get("copy_number_alterations", []):
                        cna_summary.append(f"{cna['gene']} {cna['alteration']}")
                    
                    content = {
                        "test_info": patient_genomics.get("test_info", {}),
                        "mutations": mutations_summary,
                        "copy_number_alterations": cna_summary,
                        "tmb": patient_genomics.get("tmb", {}),
                        "msi_status": patient_genomics.get("msi_status", "Unknown"),
                        "raw_data": patient_genomics
                    }
                    
                    return {
                        "source": "GenomicsIntelligenceAgent",
                        "status": "FOUND",
                        "content": content
                    }
                
                elif specialist_type == "Pathology":
                    import sqlite3
                    pathology_db = base_path / "pathology_db.sqlite"
                    if not pathology_db.exists():
                        return {"status": "ERROR", "content": f"Pathology database not found at {pathology_db}"}
                    
                    conn = sqlite3.connect(str(pathology_db))
                    cursor = conn.cursor()
                    
                    # Get the most recent pathology report for this patient
                    cursor.execute('''
                        SELECT diagnosis, histological_type, grade, er_status, pr_status, her2_status, 
                               ki67_percentage, nodes_positive, nodes_examined, margins, full_report_text
                        FROM pathology_reports 
                        WHERE patient_id = ?
                        ORDER BY signed_date DESC
                        LIMIT 1
                    ''', (self.patient_id,))
                    
                    row = cursor.fetchone()
                    conn.close()
                    
                    if not row:
                        return {
                            "source": "PathologyAgent",
                            "status": "NOT_FOUND",
                            "content": f"No pathology report found for patient {self.patient_id}"
                        }
                    
                    diagnosis, histological_type, grade, er, pr, her2, ki67, nodes_pos, nodes_exam, margins, full_text = row
                    
                    summary = f"{diagnosis}, {histological_type}, Grade {grade}, ER: {er}, PR: {pr}, HER2: {her2}"
                    if nodes_pos is not None and nodes_exam is not None:
                        summary += f", Nodes: {nodes_pos}/{nodes_exam}"
                    if ki67 is not None:
                        summary += f", Ki67: {ki67}%"
                    
                    return {
                        "source": "PathologyAgent",
                        "status": "FOUND",
                        "content": summary,
                        "full_report": full_text
                    }
                
                elif specialist_type == "Radiology":
                    import csv
                    radiology_file = base_path / "radiology_scans.csv"
                    if not radiology_file.exists():
                        return {"status": "ERROR", "content": f"Radiology data file not found at {radiology_file}"}
                    
                    # Check if we're looking for reports or images
                    looking_for_images = "image" in query_details.lower()
                    
                    with open(radiology_file, 'r') as f:
                        reader = csv.DictReader(f)
                        patient_scans = [row for row in reader if row['patient_id'] == self.patient_id]
                    
                    if not patient_scans:
                        return {
                            "source": "RadiologyAgent",
                            "status": "NOT_FOUND",
                            "content": f"No radiology scans found for patient {self.patient_id}"
                        }
                    
                    if looking_for_images:
                        # Return list of available scans
                        scan_list = [f"{scan['scan_date']} - {scan['modality']} - {scan['body_part']}" for scan in patient_scans]
                        return {
                            "source": "RadiologyAgent",
                            "status": "FOUND",
                            "content": f"Available scans: {', '.join(scan_list)}"
                        }
                    else:
                        # Check for ANY unsigned reports - these are blockers
                        unsigned_scans = [s for s in patient_scans if s['report_status'] == 'DRAFT']
                        if unsigned_scans:
                            # Flag the unsigned report as a blocker
                            unsigned_details = []
                            for scan in unsigned_scans:
                                unsigned_details.append(
                                    f"{scan['scan_date']} {scan['modality']} ({scan['body_part']})"
                                )
                            return {
                                "source": "RadiologyAgent",
                                "status": "BLOCKER",
                                "content": f"UNSIGNED REPORT(S) DETECTED: {', '.join(unsigned_details)}",
                                "alert": f"Critical: {len(unsigned_scans)} radiology report(s) awaiting signature",
                                "details": unsigned_scans[0]['findings_summary'] if unsigned_scans else None
                            }
                        
                        # Only return signed reports if no unsigned reports exist
                        signed_scans = [s for s in patient_scans if s['report_status'] == 'SIGNED']
                        if not signed_scans:
                            return {
                                "source": "RadiologyAgent",
                                "status": "NOT_FOUND",
                                "content": f"No radiology reports available for patient {self.patient_id}"
                            }
                        
                        most_recent = signed_scans[-1]
                        return {
                            "source": "RadiologyAgent",
                            "status": "FOUND",
                            "content": f"{most_recent['scan_date']} {most_recent['modality']}: {most_recent['findings_summary']}"
                        }
                
                elif specialist_type == "EHR":
                    clinical_file = base_path / "clinical_notes.json"
                    if not clinical_file.exists():
                        return {"status": "ERROR", "content": f"Clinical notes file not found at {clinical_file}"}
                    
                    with open(clinical_file, 'r') as f:
                        clinical_data = json.load(f)
                    
                    patient_key = f"patient_{self.patient_id}"
                    if patient_key not in clinical_data:
                        return {
                            "source": "EHRAgent",
                            "status": "NOT_FOUND",
                            "content": f"No clinical notes found for patient {self.patient_id}"
                        }
                    
                    patient = clinical_data[patient_key]
                    demo = patient.get("demographics", {})
                    dx = patient.get("diagnosis", {})
                    comorbid = patient.get("comorbidities", [])
                    meds = patient.get("current_medications", [])
                    allergies = patient.get("allergies", [])
                    
                    summary = f"{demo.get('age')}yo {demo.get('sex')}, {demo.get('menopausal_status')}"
                    summary += f"\nDiagnosis: {dx.get('primary')} (Stage {dx.get('stage')})"
                    if comorbid:
                        summary += f"\nComorbidities: {', '.join(comorbid)}"
                    if allergies:
                        summary += f"\nAllergies: {', '.join(allergies)}"
                    summary += f"\nECOG: {patient.get('performance_status', {}).get('ecog')}"
                    
                    return {
                        "source": "EHRAgent",
                        "status": "FOUND",
                        "content": summary,
                        "full_data": patient
                    }
                
                else:
                    return {"status": "ERROR", "content": f"Unknown specialist type: {specialist_type}"}
                    
            except Exception as e:
                logger.exception(f"[{self.patient_id}] Error fetching {specialist_type} data: {e}")
                return {"status": "ERROR", "content": str(e)}

        # --- System Instruction ---
        instruction = f"""
        You are the CaseAgent for Patient {self.patient_id}. 
        GOAL: Achieve 100% readiness on the 5-point checklist.

        1. START by calling `get_readiness_status` to see what is PENDING.
        2. For every PENDING item, call `request_specialist_data` for the relevant specialist:
           - Clinical_Notes -> 'EHR'
           - Pathology_Report -> 'Pathology'
           - Radiology_Report / Images -> 'Radiology'
           - Genomics_Profile -> 'Genomics'
        3. When you receive data, check the response status:
           - If status is "FOUND": Call `update_checklist` with status='COMPLETE'
           - If status is "BLOCKER": Call `update_checklist` with status='BLOCKER' AND call `flag_blocker` with the reason
           - If status is "NOT_FOUND": Call `update_checklist` with status='PENDING' to note the issue
           - If status is "ERROR": Call `flag_blocker`
        4. If `Genomics` returns actionable mutations, explicitly mention them in the summary.
        5. CRITICAL: Always check if the specialist response has status='BLOCKER' - this means critical data is missing or unsigned.
        6. Stop when all items are checked.
        """

        return LlmAgent(
            name=f"CaseAgent_{self.patient_id}",
            model=Gemini(model=self.model_name),
            instruction=instruction,
            tools=[
                FunctionTool(get_readiness_status),
                FunctionTool(update_checklist),
                FunctionTool(flag_blocker),
                FunctionTool(request_specialist_data)
            ]
        )

    async def run_check(self):
        """Runs the autonomous check loop."""
        logger.info(f"[{self.patient_id}] Agent activating...")
        
        # Create the session first before running
        try:
            await self.session_service.create_session(
                app_name=self.app_name,
                user_id=self.user_id,
                session_id=self.session_id
            )
            logger.debug(f"[{self.patient_id}] Created session: {self.session_id}")
        except Exception as e:
            # Session might already exist, that's fine
            logger.debug(f"[{self.patient_id}] Session creation note: {e}")
        
        # Create properly formatted trigger message
        trigger_msg = types.Content(
            role="user",
            parts=[types.Part(text="Begin case readiness check. Review status and fetch missing data.")]
        )

        # Run the agent with proper parameters
        async for event in self.runner.run_async(
            new_message=trigger_msg,
            user_id=self.user_id,
            session_id=self.session_id
        ):
            pass  # Let the agent execute its tools autonomously

        logger.info(f"[{self.patient_id}] Run complete. Status: {self.readiness_state['overall_status']}")
        return self.readiness_state

# --- Quick Test ---
if __name__ == "__main__":
    import asyncio 
    from dotenv import load_dotenv
    load_dotenv()
    
    async def main():
        if not os.getenv("GOOGLE_API_KEY"):
            print("❌ Error: GOOGLE_API_KEY not found in environment variables.")
            return

        print("Testing Single CaseAgent...")
        agent = CaseAgent("123", "2025-11-18")
        result = await agent.run_check()
        print(json.dumps(result, indent=2))
    
    asyncio.run(main())