"""
Coordinator - Orchestrates MDT case preparation using CaseAgents.

This is now a deterministic coordinator, not an LLM-driven agent.
All agentic behaviour lives inside CaseAgent and its specialist baby agents.

Author: Faith Ogundimu
Updated: November 2025
"""

import json
import logging
import os
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from dotenv import load_dotenv

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


class CoordinatorAgent:
    """
    CoordinatorAgent orchestrates MDT case preparation in a deterministic way.

    Responsibilities:
      - Load the MDT roster from JSON.
      - Spawn one CaseAgent per patient.
      - Run CaseAgents (each of which runs 5 baby agents in parallel).
      - Aggregate results into an MDT readiness dashboard.
    """

    def __init__(
        self,
        mdt_roster_path: str = "mock_db/mdt_roster_2025-11-18.json",
        model_name: str = "gemini-2.0-flash",
    ):
        self.mdt_roster_path = mdt_roster_path
        self.model_name = model_name

        # Environment (needed for CaseAgent / Gemini, but not used directly here)
        self.api_key = os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise RuntimeError("GOOGLE_API_KEY not configured")

        self.environment = os.getenv("ENVIRONMENT", "development")
        self.max_concurrent_cases = int(os.getenv("MAX_CONCURRENT_CASES", "20"))

        # State
        self.patients: List[Dict] = []
        self.mdt_info: Dict = {}
        self.case_agents: Dict[str, CaseAgent] = {}
        self.results: Dict[str, Dict] = {}

        logger.info("=" * 80)
        logger.info("Coordinator initialized (deterministic orchestrator)")
        logger.info("  MDT roster path: %s", self.mdt_roster_path)
        logger.info("  CaseAgent model: %s", self.model_name)
        logger.info("=" * 80)

    # ============= Helper methods =============

    def load_roster(self) -> bool:
        """Load MDT roster from JSON into coordinator state."""
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
        """Instantiate a CaseAgent for each patient in the roster."""
        try:
            if not self.patients:
                logger.warning("No patients to spawn agents for")
                return False

            meeting_date = self.mdt_info.get("meeting_date", "Unknown")

            for patient in self.patients:
                pid = patient.get("patient_id")
                if not pid:
                    continue

                # Create CaseAgent with parallel architecture and chosen model
                self.case_agents[pid] = CaseAgent(
                    patient_id=pid,
                    mdt_date=meeting_date,
                    model_name=self.model_name,
                )

            logger.info(
                "Spawned %s CaseAgents (each with parallel baby agents)",
                len(self.case_agents),
            )
            return True
        except Exception as e:
            logger.exception("Error spawning CaseAgents: %s", e)
            return False

    async def run_case_preparation_async(self) -> Dict[str, Dict]:
        """
        Run case preparation for all patients.

        Currently runs CaseAgents sequentially; each CaseAgent internally
        uses ParallelAgent + SequentialAgent to parallelise specialist work.
        """
        results: Dict[str, Dict] = {}

        if not self.case_agents:
            logger.warning("No CaseAgents available; did you call spawn_case_agents()?")
            return results

        logger.info("Running case preparation for %s patients...", len(self.case_agents))

        for pid, agent in self.case_agents.items():
            if not agent:
                continue

            logger.info("[%s] Starting CaseAgent...", pid)
            try:
                state = await agent.run_check()
                results[pid] = state
                status = state.get("overall_status", "UNKNOWN")
                logger.info("[%s] Complete. Status: %s", pid, status)
            except Exception as e:
                logger.error("[%s] Error during case preparation: %s", pid, e)
                results[pid] = {
                    "patient_id": pid,
                    "overall_status": "ERROR",
                    "error": str(e),
                }

        self.results = results
        return results

    def generate_dashboard(self) -> dict:
        """Generate MDT readiness dashboard from CaseAgent results."""
        if not self.results:
            logger.warning("No results to generate dashboard from")
            return {}

        # Status counts
        ready_count = sum(
            1 for r in self.results.values() if r.get("overall_status") == "READY"
        )
        blocked_count = sum(
            1 for r in self.results.values() if r.get("overall_status") == "BLOCKED"
        )
        in_progress_count = sum(
            1 for r in self.results.values() if r.get("overall_status") == "IN_PROGRESS"
        )
        error_count = sum(
            1 for r in self.results.values() if r.get("overall_status") == "ERROR"
        )

        # Aggregate blockers from each checklist
        all_blockers = []
        for pid, result in self.results.items():
            checklist = result.get("checklist", {})
            for category, summary in checklist.items():
                text = str(summary)
                if "BLOCKER" in text.upper():
                    all_blockers.append(
                        {
                            "patient_id": pid,
                            "category": category,
                            "issue": summary,
                        }
                    )

        total_patients = len(self.patients) or len(self.results)
        readiness_pct = (
            round((ready_count / total_patients) * 100, 1) if total_patients else 0
        )

        dashboard = {
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "mdt_info": self.mdt_info,
            "summary": {
                "total_patients": total_patients,
                "ready": ready_count,
                "in_progress": in_progress_count,
                "blocked": blocked_count,
                "errors": error_count,
                "readiness_percentage": readiness_pct,
            },
            "blockers": all_blockers,
            "patient_details": [],
        }

        # Add patient-level details
        for pid, result in self.results.items():
            patient_info = next(
                (p for p in self.patients if p.get("patient_id") == pid), {}
            )

            dashboard["patient_details"].append(
                {
                    "patient_id": pid,
                    "mrn": patient_info.get("mrn"),
                    "case_priority": patient_info.get("case_priority"),
                    "overall_status": result.get("overall_status"),
                    "checklist": result.get("checklist", {}),
                    "notes": result.get("notes", ""),
                }
            )

        return dashboard


# ==================== CLI ENTRY POINT ====================


async def main_async():
    """Async CLI entry point for running the full MDT workflow end-to-end."""
    try:
        # Try to locate roster file in a few common paths
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

        print("\n" + "=" * 80)
        print("MDT ROSTER LOADED")
        print("=" * 80)
        print(f"MDT Date: {coord.mdt_info.get('meeting_date')}")
        print(f"Location: {coord.mdt_info.get('location')}")
        print(f"Patients: {len(coord.patients)}")

        # Spawn case agents
        if not coord.spawn_case_agents():
            print("❌ Failed to spawn CaseAgents")
            return

        print(f"\n✓ Spawned {len(coord.case_agents)} CaseAgents")
        print("  (Each CaseAgent runs 5 baby agents in parallel)")

        # Run case preparation
        print("\n" + "=" * 80)
        print("RUNNING CASE PREPARATION (PARALLEL BABY AGENTS PER CASE)")
        print("=" * 80)

        results = await coord.run_case_preparation_async()

        print("\n" + "=" * 80)
        print("CASE PREPARATION COMPLETE")
        print("=" * 80)

        for pid, result in results.items():
            print(f"\nPatient {pid}:")
            print(f"  Status: {result.get('overall_status')}")
            print(f"  Checklist:")
            for category, data in result.get("checklist", {}).items():
                text = str(data).upper()
                has_blocker = "BLOCKER" in text or "NOT" in text
                status_emoji = "✓" if not has_blocker else "⚠"
                snippet = str(data)
                if len(snippet) > 60:
                    snippet = snippet[:60] + "..."
                print(f"    {status_emoji} {category}: {snippet}")
            if result.get("notes"):
                print(f"  Notes: {result['notes']}")

        # Generate dashboard
        dashboard = coord.generate_dashboard()

        print("\n" + "=" * 80)
        print("MDT READINESS DASHBOARD")
        print("=" * 80)
        summary = dashboard.get("summary", {})
        print(f"Total Patients: {summary.get('total_patients', 0)}")
        print(f"Ready: {summary.get('ready', 0)}")
        print(f"In Progress: {summary.get('in_progress', 0)}")
        print(f"Blocked: {summary.get('blocked', 0)}")
        print(f"Errors: {summary.get('errors', 0)}")
        print(f"Readiness: {summary.get('readiness_percentage', 0)}%")

        blockers = dashboard.get("blockers", [])
        if blockers:
            print(f"\n⚠ Total Blockers: {len(blockers)}")
            for blocker in blockers:
                issue = str(blocker["issue"])
                if len(issue) > 60:
                    issue = issue[:60] + "..."
                print(
                    f"  - Patient {blocker['patient_id']} "
                    f"({blocker['category']}): {issue}"
                )

        # Save dashboard
        output_path = Path("output/mdt_dashboard.json")
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with output_path.open("w") as f:
            json.dump(dashboard, f, indent=2)

        print(f"\n✓ Dashboard saved to {output_path}")

    except Exception as e:
        logger.error("Fatal error in coordinator main_async: %s", e)
        import traceback

        traceback.print_exc()
        raise


def main():
    """Sync wrapper for CLI."""
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
