"""
CoordinatorAgent - Main orchestrator for C.O.R.E. system (Google ADK)

This agent uses Google's Agent Development Kit (ADK) to:
1. Read the MDT roster to identify patients needing case preparation
2. Spawn autonomous CaseAgents (one per patient) using ADK's LlmAgent
3. Monitor progress via A2A protocol
4. Generate final MDT readiness dashboard with action items
5. Provide observability via tracing

Author: Faith Ogundimu
Created: November 2025
"""

import json
import logging
import os
import uuid
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

try:
    # When running from test_system.py (root)
    from agents.case_agent import CaseAgent
except ImportError:
    # Fallback if running inside the folder
    from case_agent import CaseAgent

import asyncio

# Load environment variables from .env file
load_dotenv()

# Configure logging based on environment variable
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
    """
    Load the MDT roster from JSON file.

    Use this tool when you need to know which patients require MDT case preparation.

    Args:
        tool_context: ADK tool context (automatically provided)
        roster_path: Path to the MDT roster JSON file

    Returns:
        dict with:
          - status: 'success' or 'error'
          - mdt_info: MDT-level metadata (if success)
          - patients: list of patient dicts (if success)
          - error: error message (if error)
    """
    try:
        roster_file = Path(roster_path)
        if not roster_file.exists():
            error_msg = f"MDT roster file not found at {roster_file}"
            logger.error(error_msg)
            return {"status": "error", "error": error_msg}

        with roster_file.open("r") as f:
            data = json.load(f)

        mdt_info = data.get("mdt_info", {})
        patients = data.get("patients", [])

        logger.info(
            "Roster loaded via tool: %s patients, MDT date=%s",
            len(patients),
            mdt_info.get("meeting_date"),
        )

        # Save into session state so the agent can reuse it
        tool_context.state["session:mdt_info"] = mdt_info
        tool_context.state["session:patients"] = patients

        return {"status": "success", "mdt_info": mdt_info, "patients": patients}
    except Exception as e:
        error_msg = f"Error loading MDT roster: {e}"
        logger.exception(error_msg)
        return {"status": "error", "error": error_msg}


def save_dashboard(
    tool_context: ToolContext,
    dashboard_json: str,
    output_path: str = "output/mdt_dashboard.json",
) -> dict:
    """
    Save the MDT readiness dashboard JSON to a file.

    Use this tool when the agent has produced a final readiness dashboard and you
    want to persist it to disk for downstream visualisation or review.

    Args:
        tool_context: ADK tool context (automatically provided)
        dashboard_json: JSON string with the dashboard contents
        output_path: Path to write the dashboard JSON

    Returns:
        dict with:
          - status: 'success' or 'error'
          - message / error: string description
    """
    try:
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        # Validate JSON
        dashboard_data = json.loads(dashboard_json)

        with output_file.open("w") as f:
            json.dump(dashboard_data, f, indent=2)

        logger.info("Dashboard saved via tool to %s", output_file)
        return {
            "status": "success",
            "message": f"Dashboard saved to {output_file}",
        }
    except Exception as e:
        error_msg = f"Error saving dashboard: {e}"
        logger.exception(error_msg)
        return {"status": "error", "error": error_msg}


def get_case_agent_status(
    tool_context: ToolContext,
    patient_id: str,
) -> dict:
    """
    Get the status of a specific CaseAgent.

    This is currently a stub and returns PENDING, since CaseAgents are not yet
    fully implemented.

    Args:
        tool_context: ADK tool context
        patient_id: Patient ID to check

    Returns:
        dict:
          - patient_id
          - status: 'PENDING'
          - message
    """
    logger.info("get_case_agent_status tool called for patient %s", patient_id)
    return {
        "patient_id": patient_id,
        "status": "PENDING",
        "message": "CaseAgent not yet implemented",
    }


# ==================== COORDINATOR AGENT ====================


class CoordinatorAgent:
    """
    CoordinatorAgent orchestrates MDT case preparation using Google ADK.

    Uses LlmAgent with Gemini 2.x Flash to spawn and coordinate CaseAgents.
    """

    def __init__(
        self,
        mdt_roster_path: str = "mock_db/mdt_roster_2025-11-18.json",
        model_name: str = "gemini-2.5-flash-lite",
    ):
        """
        Initialize the CoordinatorAgent.

        Args:
            mdt_roster_path: Path to MDT roster JSON file
            model_name: Gemini model name to use with ADK
        """
        self.mdt_roster_path = mdt_roster_path
        self.model_name = model_name

        # Environment
        self.api_key = os.getenv("GOOGLE_API_KEY")
        if not self.api_key or self.api_key == "your_google_ai_api_key_here":
            raise RuntimeError(
                "GOOGLE_API_KEY is not configured. Check your .env file."
            )

        self.environment = os.getenv("ENVIRONMENT", "development")
        self.max_concurrent_cases = int(os.getenv("MAX_CONCURRENT_CASES", "20"))
        self.evaluation_mode = (
            os.getenv("EVALUATION_MODE", "false").lower() == "true"
        )

        # Session management
        self.session_id = str(uuid.uuid4())
        self.session_service = InMemorySessionService()

        # Local state (pure Python, no ADK)
        self.patients: List[Dict] = []
        self.mdt_info: Dict = {}
        self.case_agents: Dict[str, LlmAgent] = {}
        self.results: Dict[str, Dict] = {}

        # Create the ADK agent (LlmAgent) for high-level coordination
        self.agent = self._create_coordinator_agent()
        self.runner = Runner(
            app_name="core_mdt_coordinator",
            agent=self.agent,
            session_service=self.session_service,
        )

        logger.info("=" * 80)
        logger.info("CoordinatorAgent Initialized (Google ADK)")
        logger.info("  Session ID: %s", self.session_id)
        logger.info("  Model: %s", self.model_name)
        logger.info("  Environment: %s", self.environment)
        logger.info("=" * 80)

    def _create_coordinator_agent(self) -> LlmAgent:
        """
        Create the CoordinatorAgent using Google ADK's LlmAgent.

        Returns:
            Configured LlmAgent instance
        """
        # Create Gemini model. ADK's Gemini wrapper reads GOOGLE_API_KEY from env.
        model = Gemini(model=self.model_name)

        # Define coordinator tools using FunctionTool.
        # NOTE: FunctionTool takes only the callable. The function name and
        # docstring are used by ADK to expose the tool schema to the model.
        coordinator_tools = [
            FunctionTool(func=load_mdt_roster),
            FunctionTool(func=save_dashboard),
            FunctionTool(func=get_case_agent_status),
        ]

        # Create the LlmAgent
        agent = LlmAgent(
            name="CoordinatorAgent",
            model=model,
            description=(
                "Orchestrates MDT case preparation by spawning CaseAgents "
                "and generating readiness dashboards."
            ),
            instruction=self._get_coordinator_instruction(),
            tools=coordinator_tools,
        )

        logger.info("CoordinatorAgent (LlmAgent) created successfully")
        return agent

    def _get_coordinator_instruction(self) -> str:
        """
        Get the system instruction for the CoordinatorAgent.

        Returns:
            Instruction string
        """
        return (
            "You are the CoordinatorAgent for C.O.R.E. (Coordinated Oncology "
            "Readiness Engine).\n\n"
            "ROLE: Orchestrate MDT (Multidisciplinary Team) case preparation "
            "for cancer patients.\n\n"
            "You have access to tools to:\n"
            "  - load_mdt_roster: load the MDT roster JSON into session state\n"
            "  - save_dashboard: save final readiness dashboards to disk\n"
            "  - get_case_agent_status: query status of individual CaseAgents\n\n"
            "Workflow:\n"
            " 1. Always start by loading the MDT roster using load_mdt_roster.\n"
            " 2. For each patient, reason about case preparation requirements.\n"
            " 3. Once cases are prepared (or pending), aggregate into a "
            "    readiness dashboard.\n"
            " 4. Use save_dashboard to persist the dashboard.\n\n"
            "Return concise, structured summaries and never leak raw PII "
            "beyond what is necessary for MDT planning."
        )

    # ============= Local (non-ADK) helper methods for smoke tests =============

    def load_roster(self) -> bool:
        """
        Local helper to load MDT roster directly from JSON.

        This is used by test_coordinator.py to avoid invoking the ADK tools
        pipeline. It simply reads the JSON file and populates self.mdt_info and
        self.patients.

        Returns:
            True if load succeeded, False otherwise.
        """
        try:
            roster_file = Path(self.mdt_roster_path)
            if not roster_file.exists():
                logger.error("Roster file not found at %s", roster_file)
                return False

            with roster_file.open("r") as f:
                data = json.load(f)

            self.mdt_info = data.get("mdt_info", {})
            self.patients = data.get("patients", [])

            logger.info(
                "Roster loaded (local): %s patients, MDT date=%s",
                len(self.patients),
                self.mdt_info.get("meeting_date"),
            )
            return True
        except Exception as e:
            logger.exception("Error loading roster: %s", e)
            return False

    def spawn_case_agents(self) -> bool:
        try:
            if not self.patients:
                logger.warning("No patients loaded.")
                return False

            for patient in self.patients:
                pid = patient.get("patient_id")
                if not pid: continue

                # Instantiate the real CaseAgent
                self.case_agents[pid] = CaseAgent(
                    patient_id=pid,
                    mdt_date=self.mdt_info.get("meeting_date", "Unknown")
                )

            logger.info(f"Spawned {len(self.case_agents)} CaseAgents.")
            return True
        except Exception as e:
            logger.exception(f"Error spawning agents: {e}")
            return False

    async def run_case_preparation_async(self): 
        results = {}
        for pid, agent in self.case_agents.items():
            if agent:
                # Run the agent's logic
                state = await agent.run_check()
                results[pid] = state
        return results


# ==================== CLI entry-point for manual debugging ====================


def main() -> None:
    """
    Minimal CLI entry point for manual debugging.

    This will:
      1. Create a CoordinatorAgent
      2. Load the MDT roster
      3. Spawn case agents (stub)
      4. Run case preparation (stub)
      5. Print a tiny dashboard summary
    """
    try:
        project_root = Path(__file__).parent
        roster_path = project_root / "mock_db" / "mdt_roster_2025-11-18.json"

        coord = CoordinatorAgent(
            mdt_roster_path=str(roster_path),
            model_name=os.getenv("COORDINATOR_MODEL", "gemini-2.5-flash-lite"),
        )

        if not coord.load_roster():
            print("Failed to load MDT roster.")
            return

        print("Loaded MDT roster:")
        print(f"  MDT date: {coord.mdt_info.get('meeting_date')}")
        print(f"  Location: {coord.mdt_info.get('location')}")
        print(f"  Patients: {len(coord.patients)}")

        if not coord.spawn_case_agents():
            print("Failed to spawn CaseAgents (stub).")
            return

        results = coord.run_case_preparation()
        print("\nCase preparation (stub) results:")
        for pid, res in results.items():
            print(f"  {pid}: status={res['status']}, readiness={res['readiness_percentage']}%")

        # Very small inline dashboard
        dashboard = {
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "mdt_info": coord.mdt_info,
            "summary": {
                "patient_count": len(coord.patients),
                "ready_count": sum(
                    1 for r in results.values() if r["status"] == "READY"
                ),
                "blocked_count": sum(
                    1 for r in results.values() if r["status"] == "BLOCKED"
                ),
            },
        }

        print("\nInline dashboard summary:")
        print(f"Patients: {dashboard['summary']['patient_count']}")
        print(f"Ready: {dashboard['summary']['ready_count']}")
        print(f"Blocked: {dashboard['summary']['blocked_count']}")
    except Exception as e:
        logger.error("Fatal error in CLI main: %s", e)
        import traceback

        traceback.print_exc()
        raise


if __name__ == "__main__":
    main()
