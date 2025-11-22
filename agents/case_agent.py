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
                status: 'COMPLETE', 'PARTIAL', 'MISSING', or 'NOT_APPLICABLE'
                summary: A brief summary of the data found.
            """
            if category not in self.readiness_state["checklist"]:
                return {"status": "error", "message": f"Invalid category: {category}"}
            
            self.readiness_state["checklist"][category]["status"] = status
            self.readiness_state["checklist"][category]["data"] = summary
            
            # Auto-update overall status if all complete
            all_complete = all(v["status"] == "COMPLETE" for k,v in self.readiness_state["checklist"].items())
            if all_complete:
                self.readiness_state["overall_status"] = "READY"
                
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
            Simulates A2A request to a Specialist Agent.
            
            Args:
                specialist_type: 'EHR', 'Pathology', 'Radiology', 'Genomics'
                query_details: What you are looking for.
            """
            logger.info(f"[{self.patient_id}] A2A Request -> {specialist_type}: {query_details}")
            
            # --- MOCK DATA RESPONSES (Based on your Project Plan) ---
            if specialist_type == "Genomics":
                return {
                    "source": "GenomicsIntelligenceAgent",
                    "status": "FOUND",
                    "content": {
                        "mutation": "PIK3CA H1047R",
                        "significance": "Actionable",
                        "clinical_trials": ["NCT04305496 (Capivasertib)"],
                        "evidence": "André et al., NEJM 2019"
                    }
                }
            elif specialist_type == "Pathology":
                return {
                    "source": "PathologyAgent",
                    "status": "FOUND",
                    "content": "Invasive ductal carcinoma, Grade 2, ER+/PR+/HER2-"
                }
            elif specialist_type == "EHR":
                return {
                    "source": "EHRAgent",
                    "status": "FOUND",
                    "content": "58F, Hx: Hypertension. Meds: Amlodipine."
                }
            
            # Default mock for others
            return {"status": "FOUND", "content": f"Mock data from {specialist_type}"}

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
        3. When you receive data, ANALYZE it briefly, then call `update_checklist` to mark it COMPLETE.
        4. If `Genomics` returns actionable mutations, explicitly mention them in the summary.
        5. If data is missing/error, call `flag_blocker`.
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