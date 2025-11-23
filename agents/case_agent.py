"""
CaseAgent - Patient-specific autonomous agent for C.O.R.E.
Refactored to use Parallel and Sequential Workflow Agents.
"""

import json
import logging
import os
import sqlite3
import csv
import asyncio
from pathlib import Path
from typing import Dict, List, Optional, Any

# Google ADK imports
from google.adk.agents import LlmAgent, ParallelAgent, SequentialAgent
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
        self.app_name = f"case_agent_{patient_id}"
        self.user_id = "core_system"
        self.session_id = f"case_{patient_id}_{mdt_date}"
        
        # Base path for mock data
        self.base_path = Path(__file__).parent.parent / "mock_db"

        # Initialize the Workflow Agent
        self.agent = self._build_pipeline_agent()
        self.session_service = InMemorySessionService()
        self.runner = Runner(
            agent=self.agent,
            app_name=self.app_name,
            session_service=self.session_service
        )

    def _build_pipeline_agent(self):
        """Builds the Sequential -> Parallel agent structure."""

        # --- 1. Define Domain-Specific Tools (Closures to capture patient_id) ---

        def fetch_clinical_notes() -> str:
            """Retrieves EHR clinical notes, demographics, and comorbidities."""
            try:
                path = self.base_path / "clinical_notes.json"
                with open(path, 'r') as f:
                    data = json.load(f)
                
                key = f"patient_{self.patient_id}"
                if key not in data:
                    return f"No EHR data found for {self.patient_id}"
                
                p = data[key]
                summary = (f"Age: {p['demographics']['age']}, Dx: {p['diagnosis']['primary']}, "
                           f"Stage: {p['diagnosis']['stage']}, "
                           f"Comorbidities: {', '.join(p.get('comorbidities', []))}")
                return summary
            except Exception as e:
                return f"Error fetching EHR: {str(e)}"

        def fetch_pathology() -> str:
            """Queries the pathology SQLite database for the latest report."""
            try:
                db_path = self.base_path / "pathology_db.sqlite"
                conn = sqlite3.connect(str(db_path))
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT diagnosis, histological_type, grade, er_status, pr_status, her2_status, signed_date
                    FROM pathology_reports 
                    WHERE patient_id = ? ORDER BY signed_date DESC LIMIT 1
                ''', (self.patient_id,))
                row = cursor.fetchone()
                conn.close()
                
                if not row:
                    return "No pathology reports found."
                return f"Date: {row[6]}, Dx: {row[0]}, Type: {row[1]}, Grade: {row[2]}, ER:{row[3]}, PR:{row[4]}, HER2:{row[5]}"
            except Exception as e:
                return f"Error fetching Pathology: {str(e)}"

        def fetch_radiology() -> str:
            """Parses CSV for the latest signed radiology reports."""
            try:
                csv_path = self.base_path / "radiology_scans.csv"
                with open(csv_path, 'r') as f:
                    reader = csv.DictReader(f)
                    scans = [row for row in reader if row['patient_id'] == self.patient_id]
                
                if not scans: 
                    return "No radiology scans found."
                
                # Check for critical unsigned drafts (Blockers)
                unsigned = [s for s in scans if s['report_status'] == 'DRAFT']
                if unsigned:
                    return f"BLOCKER: {len(unsigned)} UNSIGNED report(s) found. Latest draft: {unsigned[0]['findings_summary']}"
                
                latest = scans[-1] 
                return f"Latest Scan ({latest['modality']}): {latest['findings_summary']}"
            except Exception as e:
                return f"Error fetching Radiology: {str(e)}"

        def fetch_genomics() -> str:
            """Retrieves genomic profile and mutations."""
            try:
                path = self.base_path / "genomics_data.json"
                with open(path, 'r') as f:
                    data = json.load(f)
                
                key = f"patient_{self.patient_id}"
                p = data.get(key)
                
                if not p: return "No genomic data."
                if p.get("status") == "NOT_FOUND": return "Genomic testing NOT completed."
                
                muts = [f"{m['gene']} {m['variant']}" for m in p.get("mutations", [])]
                return f"Mutations: {', '.join(muts) if muts else 'None'}. TMB: {p.get('tmb', {}).get('interpretation', 'N/A')}"
            except Exception as e:
                return f"Error fetching Genomics: {str(e)}"

        def fetch_contraindications() -> str:
            """Loads contraindication rules for treatment planning."""
            try:
                path = self.base_path / "contraindication_rules.json"
                with open(path, 'r') as f:
                    data = json.load(f)

                drugs = data.get("drugs", {})
                drug_count = len(drugs)

                # Extract drugs relevant to breast cancer
                bc_drugs = []
                for drug_name, drug_info in drugs.items():
                    indications = drug_info.get("indications", [])
                    for indication in indications:
                        if "breast" in indication.lower():
                            bc_drugs.append(drug_name)
                            break
                        
                summary = f"Loaded {drug_count} drug profiles. "
                summary += f"Breast cancer relevant: {', '.join(bc_drugs[:5])}"
                if len(bc_drugs) > 5:
                    summary += f" (and {len(bc_drugs)-5} more)"

                return summary
            except Exception as e:
                return f"Error loading contraindication rules: {str(e)}"
        
        # --- 2. Define the "Baby" Agents (LlmAgents) ---
        
        ehr_agent = LlmAgent(
            name="EHRAgent",
            model=Gemini(model=self.model_name),
            instruction="You are the Clinical Data specialist. Retrieve clinical notes using your tool. Summarize the patient's diagnosis and physical status concisely. Output ONLY the summary.",
            tools=[FunctionTool(fetch_clinical_notes)],
            output_key="ehr_result"
        )

        path_agent = LlmAgent(
            name="PathologyAgent",
            model=Gemini(model=self.model_name),
            instruction="You are the Pathology specialist. Query the database using your tool. Return the most recent histological diagnosis and receptor status. Output ONLY the summary.",
            tools=[FunctionTool(fetch_pathology)],
            output_key="pathology_result"
        )

        rad_agent = LlmAgent(
            name="RadiologyAgent",
            model=Gemini(model=self.model_name),
            instruction="You are the Radiology specialist. Search the scan logs using your tool. Identify if there are any UNSIGNED reports (critical blockers) or summarize the latest findings. Output ONLY the summary.",
            tools=[FunctionTool(fetch_radiology)],
            output_key="radiology_result"
        )

        gen_agent = LlmAgent(
            name="GenomicsAgent",
            model=Gemini(model=self.model_name),
            instruction="You are the Genomics specialist. Check the genomic registry using your tool. List key pathogenic mutations or state if testing is missing. Output ONLY the summary.",
            tools=[FunctionTool(fetch_genomics)],
            output_key="genomics_result"
        )

        contra_agent = LlmAgent(
            name="ContraindicationAgent",
            model=Gemini(model=self.model_name),
            instruction="You are the Drug Safety specialist. Load the contraindication database using your tool. Report how many drug profiles are available for treatment planning. Output ONLY the summary.",
            tools=[FunctionTool(fetch_contraindications)],
            output_key="contraindication_result"
        )

        # --- 3. The Parallel Agent (The Team) ---
        data_squad = ParallelAgent(
            name="SpecialistSquad",
            sub_agents=[ehr_agent, path_agent, rad_agent, gen_agent, contra_agent],
            description="Parallel fetch of all medical domains."
        )

        # --- 4. The Synthesis Agent (The Case Manager) ---
        synthesis_instruction = f"""
        You are the Case Manager for Patient {self.patient_id}.
        
        You have received reports from your specialist team:
        1. **Clinical**: {{ehr_result}}
        2. **Pathology**: {{pathology_result}}
        3. **Radiology**: {{radiology_result}}
        4. **Genomics**: {{genomics_result}}
        5. **Contraindications**: {{contraindication_result}}  ← NEW!
        
        Your Task:
        Analyze these 5 inputs and produce a FINAL JSON readiness object.
        
        Rules:
        - If any report contains "BLOCKER" or "UNSIGNED", set overall_status to "BLOCKED".
        - If any report says "not found" or "missing", set overall_status to "IN_PROGRESS" (unless it's a blocker).
        - If all data is present and clear, set overall_status to "READY".
        
        Output format MUST be valid JSON:
        {{
            "patient_id": "{self.patient_id}",
            "overall_status": "READY/IN_PROGRESS/BLOCKED",
            "checklist": {{
                "Clinical": "Summary...",
                "Pathology": "Summary...",
                "Radiology": "Summary...",
                "Genomics": "Summary...",
                "Contraindications": "Summary..."  ← NEW!
            }},
            "notes": "Brief explanation of status"
        }}
        """

        case_manager = LlmAgent(
            name="CaseManager",
            model=Gemini(model=self.model_name),
            instruction=synthesis_instruction,
        )

        # --- 5. The Sequential Pipeline ---
        pipeline = SequentialAgent(
            name=f"CasePipeline_{self.patient_id}",
            sub_agents=[data_squad, case_manager],
            description="Coordinates parallel data fetching and final case synthesis."
        )

        return pipeline

    async def run_check(self):
        """Runs the pipeline."""
        logger.info(f"[{self.patient_id}] Starting Case Pipeline (Parallel Fetching)...")
        
        # 1. Create Session
        try:
            await self.session_service.create_session(
                app_name=self.app_name,
                user_id=self.user_id,
                session_id=self.session_id
            )
        except Exception as e:
            logger.debug(f"[{self.patient_id}] Session creation note: {e}")
        
        trigger_msg = types.Content(
            role="user",
            parts=[types.Part(text="Start case analysis.")]
        )

        final_response_text = ""
        
        # 2. Run and Extract Text Safely
        async for event in self.runner.run_async(
            new_message=trigger_msg,
            user_id=self.user_id,
            session_id=self.session_id
        ):
            if hasattr(event, "content") and event.content:
                raw_content = event.content
                text_extraction = ""
                
                # Handle different content types (String vs Object)
                if isinstance(raw_content, str):
                    text_extraction = raw_content
                elif hasattr(raw_content, "parts"):
                    # Extract text from all parts (skips function calls)
                    parts_text = []
                    for part in raw_content.parts:
                        if hasattr(part, "text") and part.text:
                            parts_text.append(part.text)
                    text_extraction = "".join(parts_text)
                
                # Update final response only if we found actual text
                if text_extraction.strip():
                    final_response_text = text_extraction

        # 3. Parse JSON
        try:
            # Clean up markdown code blocks if present
            clean_text = final_response_text.replace("```json", "").replace("```", "").strip()
            result_json = json.loads(clean_text)
            logger.info(f"[{self.patient_id}] Pipeline Complete. Status: {result_json.get('overall_status')}")
            return result_json
        except Exception as e:
            logger.error(f"Failed to parse final agent output: {e}")
            # Return string representation to avoid JSON serialization errors
            return {"status": "ERROR", "raw_output": str(final_response_text)}

# --- Quick Test ---
if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    
    async def main():
        if not os.getenv("GOOGLE_API_KEY"):
            print("❌ Error: GOOGLE_API_KEY not found.")
            return

        print("Testing Parallel CaseAgent for Patient 789...")
        agent = CaseAgent("789", "2025-11-18")
        result = await agent.run_check()
        print(json.dumps(result, indent=2))
    
    asyncio.run(main())