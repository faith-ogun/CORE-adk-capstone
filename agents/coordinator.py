"""
CoordinatorAgent - Updated to work with the new Parallel CaseAgent

This coordinator works with case_agent.py that uses ParallelAgent + SequentialAgent.

Author: Faith Ogundimu
Updated: November 2025
"""

import json
import logging
import os
import uuid
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from dotenv import load_dotenv

# Google ADK imports
from google.genai import types
from google.adk.agents import LlmAgent
from google.adk.models.google_llm import Gemini
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools.function_tool import FunctionTool
from google.adk.tools.tool_context import ToolContext

# Import your CaseAgent
try:
    from agents.case_agent import CaseAgent
except ImportError:
    from case_agent import CaseAgent

# Load environment
load_dotenv()

# Logging
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# ==================== COORDINATOR TOOLS ====================


def load_mdt_roster(
    tool_context: ToolContext,
    roster_path: str = "mock_db/mdt_roster_2025-11-18.json",
) -> dict:
    """Load the MDT roster from JSON file."""
    try:
        roster_file = Path(roster_path)
        if not roster_file.exists():
            error_msg = f"MDT roster not found at {roster_file}"
            logger.error(error_msg)
            return {"status": "error", "error": error_msg}

        with roster_file.open("r") as f:
            data = json.load(f)

        mdt_info = data.get("mdt_info", {})
        patients = data.get("patients", [])

        logger.info(
            "Roster loaded: %s patients, MDT date=%s",
            len(patients),
            mdt_info.get("meeting_date"),
        )

        # Store in session state
        tool_context.state["session:mdt_info"] = mdt_info
        tool_context.state["session:patients"] = patients

        return {"status": "success", "mdt_info": mdt_info, "patients": patients}
    except Exception as e:
        error_msg = f"Error loading roster: {e}"
        logger.exception(error_msg)
        return {"status": "error", "error": error_msg}


def save_dashboard(
    tool_context: ToolContext,
    dashboard_json: str,
    output_path: str = "output/mdt_dashboard.json",
) -> dict:
    """Save the MDT readiness dashboard to file."""
    try:
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        dashboard_data = json.loads(dashboard_json)

        with output_file.open("w") as f:
            json.dump(dashboard_data, f, indent=2)

        logger.info("Dashboard saved to %s", output_file)
        return {
            "status": "success",
            "message": f"Dashboard saved to {output_file}",
        }
    except Exception as e:
        error_msg = f"Error saving dashboard: {e}"
        logger.exception(error_msg)
        return {"status": "error", "error": error_msg}


# ==================== COORDINATOR AGENT ====================


class CoordinatorAgent:
    """
    CoordinatorAgent orchestrates MDT case preparation.
    
    Works with the new parallel CaseAgent architecture.
    """

    def __init__(
        self,
        mdt_roster_path: str = "mock_db/mdt_roster_2025-11-18.json",
        model_name: str = "gemini-2.0-flash",
    ):
        self.mdt_roster_path = mdt_roster_path
        self.model_name = model_name

        # Environment
        self.api_key = os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise RuntimeError("GOOGLE_API_KEY not configured")

        self.environment = os.getenv("ENVIRONMENT", "development")
        self.max_concurrent_cases = int(os.getenv("MAX_CONCURRENT_CASES", "20"))

        # Session management
        self.session_id = str(uuid.uuid4())
        self.session_service = InMemorySessionService()

        # State
        self.patients: List[Dict] = []
        self.mdt_info: Dict = {}
        self.case_agents: Dict[str, CaseAgent] = {}
        self.results: Dict[str, Dict] = {}

        # Create coordinator agent
        self.agent = self._create_coordinator_agent()
        self.runner = Runner(
            app_name="core_mdt_coordinator",
            agent=self.agent,
            session_service=self.session_service,
        )

        logger.info("=" * 80)
        logger.info("CoordinatorAgent Initialized (Parallel Architecture)")
        logger.info("  Session ID: %s", self.session_id)
        logger.info("  Model: %s", self.model_name)
        logger.info("=" * 80)

    def _create_coordinator_agent(self) -> LlmAgent:
        """Create the coordinator LlmAgent."""
        model = Gemini(model=self.model_name)

        coordinator_tools = [
            FunctionTool(func=load_mdt_roster),
            FunctionTool(func=save_dashboard),
        ]

        agent = LlmAgent(
            name="CoordinatorAgent",
            model=model,
            description="Orchestrates MDT case preparation using parallel CaseAgents",
            instruction=self._get_coordinator_instruction(),
            tools=coordinator_tools,
        )

        logger.info("CoordinatorAgent created")
        return agent

    def _get_coordinator_instruction(self) -> str:
        """Get coordinator system instruction."""
        return (
            "You are the CoordinatorAgent for C.O.R.E.\n\n"
            "ROLE: Orchestrate MDT case preparation for cancer patients.\n\n"
            "Workflow:\n"
            " 1. Load MDT roster using load_mdt_roster tool\n"
            " 2. The system will spawn parallel CaseAgents for each patient\n"
            " 3. Aggregate results into a readiness dashboard\n"
            " 4. Save dashboard using save_dashboard tool\n\n"
            "Be concise and focus on MDT readiness status."
        )

    # ============= Helper methods =============

    def load_roster(self) -> bool:
        """Load MDT roster from JSON."""
        try:
            roster_file = Path(self.mdt_roster_path)
            if not roster_file.exists():
                logger.error("Roster not found at %s", roster_file)
                return False

            with roster_file.open("r") as f:
                data = json.load(f)

            self.mdt_info = data.get("mdt_info", {})
            self.patients = data.get("patients", [])

            logger.info(
                "Roster loaded: %s patients, MDT date=%s",
                len(self.patients),
                self.mdt_info.get("meeting_date"),
            )
            return True
        except Exception as e:
            logger.exception("Error loading roster: %s", e)
            return False

    def spawn_case_agents(self) -> bool:
        """Spawn parallel CaseAgents for each patient."""
        try:
            if not self.patients:
                logger.warning("No patients to spawn agents for")
                return False

            for patient in self.patients:
                pid = patient.get("patient_id")
                if not pid:
                    continue

                # Create CaseAgent with parallel architecture
                self.case_agents[pid] = CaseAgent(
                    patient_id=pid,
                    mdt_date=self.mdt_info.get("meeting_date", "Unknown")
                )

            logger.info(
                "Spawned %s CaseAgents (each with parallel baby agents)",
                len(self.case_agents)
            )
            return True
        except Exception as e:
            logger.exception("Error spawning agents: %s", e)
            return False

    async def run_case_preparation_async(self) -> Dict[str, Dict]:
        """Run case preparation for all patients."""
        results = {}

        logger.info("Running case preparation for %s patients...", len(self.case_agents))

        # Run all CaseAgents
        for pid, agent in self.case_agents.items():
            if agent:
                logger.info(f"[{pid}] Starting case agent...")
                try:
                    state = await agent.run_check()
                    results[pid] = state
                    status = state.get('overall_status', 'UNKNOWN')
                    logger.info(f"[{pid}] Complete. Status: {status}")
                except Exception as e:
                    logger.error(f"[{pid}] Error: {e}")
                    results[pid] = {
                        "patient_id": pid,
                        "overall_status": "ERROR",
                        "error": str(e)
                    }

        self.results = results
        return results

    def generate_dashboard(self) -> dict:
        """Generate MDT readiness dashboard from results."""
        if not self.results:
            logger.warning("No results to generate dashboard from")
            return {}

        # Count statuses
        ready_count = sum(
            1 for r in self.results.values()
            if r.get("overall_status") == "READY"
        )
        blocked_count = sum(
            1 for r in self.results.values()
            if r.get("overall_status") == "BLOCKED"
        )
        in_progress_count = sum(
            1 for r in self.results.values()
            if r.get("overall_status") == "IN_PROGRESS"
        )
        error_count = sum(
            1 for r in self.results.values()
            if r.get("overall_status") == "ERROR"
        )

        # Aggregate blockers
        all_blockers = []
        for pid, result in self.results.items():
            checklist = result.get("checklist", {})
            for category, summary in checklist.items():
                if "BLOCKER" in str(summary):
                    all_blockers.append({
                        "patient_id": pid,
                        "category": category,
                        "issue": summary
                    })

        dashboard = {
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "mdt_info": self.mdt_info,
            "summary": {
                "total_patients": len(self.patients),
                "ready": ready_count,
                "in_progress": in_progress_count,
                "blocked": blocked_count,
                "errors": error_count,
                "readiness_percentage": round((ready_count / len(self.results)) * 100, 1)
                if self.results else 0
            },
            "blockers": all_blockers,
            "patient_details": []
        }

        # Add patient-level details
        for pid, result in self.results.items():
            patient_info = next(
                (p for p in self.patients if p.get("patient_id") == pid),
                {}
            )

            dashboard["patient_details"].append({
                "patient_id": pid,
                "mrn": patient_info.get("mrn"),
                "case_priority": patient_info.get("case_priority"),
                "overall_status": result.get("overall_status"),
                "checklist": result.get("checklist", {}),
                "notes": result.get("notes", "")
            })

        return dashboard


# ==================== CLI ENTRY POINT ====================


async def main_async():
    """Async main entry point."""
    try:
        # Find roster path
        script_path = Path(__file__).resolve()
        
        possible_paths = [
            script_path.parent / "mock_db" / "mdt_roster_2025-11-18.json",
            script_path.parent.parent / "mock_db" / "mdt_roster_2025-11-18.json",
            Path("mock_db/mdt_roster_2025-11-18.json"),
        ]
        
        roster_path = None
        for path in possible_paths:
            if path.exists():
                roster_path = str(path)
                break
        
        if not roster_path:
            print("❌ Could not find MDT roster file")
            return
        
        print("Using roster:", roster_path)
        
        # Create coordinator
        coord = CoordinatorAgent(
            mdt_roster_path=roster_path,
            model_name=os.getenv("COORDINATOR_MODEL", "gemini-2.0-flash"),
        )
        
        # Load roster
        if not coord.load_roster():
            print("❌ Failed to load MDT roster")
            return
        
        print("\n" + "="*80)
        print("MDT ROSTER LOADED")
        print("="*80)
        print(f"MDT Date: {coord.mdt_info.get('meeting_date')}")
        print(f"Location: {coord.mdt_info.get('location')}")
        print(f"Patients: {len(coord.patients)}")
        
        # Spawn case agents
        if not coord.spawn_case_agents():
            print("❌ Failed to spawn CaseAgents")
            return
        
        print(f"\n✓ Spawned {len(coord.case_agents)} CaseAgents")
        print("  (Each CaseAgent runs 4 baby agents in parallel)")
        
        # Run case preparation
        print("\n" + "="*80)
        print("RUNNING CASE PREPARATION (PARALLEL AGENTS)")
        print("="*80)
        
        results = await coord.run_case_preparation_async()
        
        print("\n" + "="*80)
        print("CASE PREPARATION COMPLETE")
        print("="*80)
        
        for pid, result in results.items():
            print(f"\nPatient {pid}:")
            print(f"  Status: {result.get('overall_status')}")
            print(f"  Checklist:")
            for category, data in result.get("checklist", {}).items():
                status_emoji = "✓" if "BLOCKER" not in str(data) and "NOT" not in str(data) else "⚠"
                print(f"    {status_emoji} {category}: {data[:60]}...")
            
            if result.get("notes"):
                print(f"  Notes: {result['notes']}")
        
        # Generate dashboard
        dashboard = coord.generate_dashboard()
        
        print("\n" + "="*80)
        print("MDT READINESS DASHBOARD")
        print("="*80)
        print(f"Total Patients: {dashboard['summary']['total_patients']}")
        print(f"Ready: {dashboard['summary']['ready']}")
        print(f"In Progress: {dashboard['summary']['in_progress']}")
        print(f"Blocked: {dashboard['summary']['blocked']}")
        print(f"Errors: {dashboard['summary']['errors']}")
        print(f"Readiness: {dashboard['summary']['readiness_percentage']}%")
        
        if dashboard.get("blockers"):
            print(f"\n⚠ Total Blockers: {len(dashboard['blockers'])}")
            for blocker in dashboard["blockers"]:
                print(f"  - Patient {blocker['patient_id']} ({blocker['category']}): {blocker['issue'][:60]}...")
        
        # Save dashboard
        output_path = Path("output/mdt_dashboard.json")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with output_path.open("w") as f:
            json.dump(dashboard, f, indent=2)
        
        print(f"\n✓ Dashboard saved to {output_path}")
        
    except Exception as e:
        logger.error("Fatal error: %s", e)
        import traceback
        traceback.print_exc()
        raise


def main():
    """Sync wrapper."""
    asyncio.run(main_async())


if __name__ == "__main__":
    main()