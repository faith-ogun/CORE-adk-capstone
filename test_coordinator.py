"""
Minimal smoke test for CoordinatorAgent (Google ADK)

Assumed project structure:

./
├── .env
├── test_coordinator.py  (this file)
├── agents/
│   └── coordinator.py   (preferred)
└── mock_db/
    └── mdt_roster_2025-11-18.json

If coordinator.py is in the project root instead of agents/, the import
fallback will handle that as well.
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv


def print_header(title: str) -> None:
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def main() -> None:
    # ------------------------------------------------------------------
    # 0. Resolve project paths and Python path
    # ------------------------------------------------------------------
    project_root = Path(__file__).parent.resolve()
    sys.path.insert(0, str(project_root))

    print_header("CoordinatorAgent - Smoke Test")
    print(f"Project root: {project_root}")
    print(f"Python path includes: {project_root}")

    # ------------------------------------------------------------------
    # 1. Load environment
    # ------------------------------------------------------------------
    env_path = project_root / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
        print(f"\nLoaded environment from: {env_path}")
    else:
        print(f"\nWarning: .env file not found at {env_path}")
        print("Continuing, but CoordinatorAgent will fail if GOOGLE_API_KEY is missing.")

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key or api_key == "your_google_ai_api_key_here":
        print("\nERROR: GOOGLE_API_KEY not configured.")
        print("Update your .env file, for example:")
        print("  GOOGLE_API_KEY=your_actual_api_key_here")
        sys.exit(1)

    print("\nEnvironment check:")
    print(f"  GOOGLE_API_KEY: {api_key[:8]}... (redacted)")
    print(f"  ENVIRONMENT: {os.getenv('ENVIRONMENT', 'development')}")
    print(f"  LOG_LEVEL:   {os.getenv('LOG_LEVEL', 'INFO')}")

    # ------------------------------------------------------------------
    # 2. Import CoordinatorAgent
    # ------------------------------------------------------------------
    print_header("Step 1/3: Import CoordinatorAgent")

    CoordinatorAgent = None
    import_error = None

    # Preferred: agents/coordinator.py
    try:
        from agents.coordinator import CoordinatorAgent as CA  # type: ignore
        CoordinatorAgent = CA
        print("Imported CoordinatorAgent from agents.coordinator")
    except Exception as e:
        import_error = e
        print("Could not import from agents.coordinator, trying fallback (coordinator in root)...")

    if CoordinatorAgent is None:
        try:
            from coordinator import CoordinatorAgent as CA  # type: ignore
            CoordinatorAgent = CA
            print("Imported CoordinatorAgent from coordinator")
        except Exception as e2:
            print("\nERROR: Failed to import CoordinatorAgent from both locations.")
            print(f"  First error:  {import_error}")
            print(f"  Second error: {e2}")
            print("\nTroubleshooting:")
            print("  - Ensure coordinator.py exists.")
            print("  - If it is under agents/, make sure agents/__init__.py exists.")
            print("  - Confirm the class is named CoordinatorAgent.")
            sys.exit(1)

    # ------------------------------------------------------------------
    # 3. Instantiate CoordinatorAgent (no ADK calls yet)
    # ------------------------------------------------------------------
    print_header("Step 2/3: Instantiate CoordinatorAgent")

    roster_path = project_root / "mock_db" / "mdt_roster_2025-11-18.json"
    if not roster_path.exists():
        print(f"\nERROR: MDT roster file not found at: {roster_path}")
        print("Create this file or update the path in test_coordinator.py.")
        sys.exit(1)

    print(f"Using MDT roster file: {roster_path}")

    try:
        coordinator = CoordinatorAgent(
            mdt_roster_path=str(roster_path),
            model_name="gemini-2.0-flash-lite",
        )
        print("CoordinatorAgent instantiated successfully.")
        print(f"  Session ID: {coordinator.session_id}")
        print(f"  Model:      {coordinator.model_name}")
        print(f"  Env:        {getattr(coordinator, 'environment', 'N/A')}")
    except Exception as e:
        print("\nERROR: Failed to instantiate CoordinatorAgent.")
        print(f"Details: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # ------------------------------------------------------------------
    # 4. Load roster and run local-only methods
    # ------------------------------------------------------------------
    print_header("Step 3/3: Load roster and run local checks")

    # 4a. Load roster (no ADK, simple JSON read)
    try:
        loaded = coordinator.load_roster()
    except Exception as e:
        print("\nERROR: Exception while calling load_roster().")
        print(f"Details: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    if not loaded:
        print("\nERROR: load_roster() returned False. Check JSON validity and structure.")
        sys.exit(1)

    num_patients = len(coordinator.patients)
    mdt_date = coordinator.mdt_info.get("meeting_date", "Unknown")
    location = coordinator.mdt_info.get("location", "Unknown")

    print("\nRoster loaded successfully.")
    print(f"  Patients: {num_patients}")
    print(f"  MDT date: {mdt_date}")
    print(f"  Location: {location}")

    if num_patients:
        print("\nSample patient IDs from roster:")
        for p in coordinator.patients[:5]:
            pid = p.get("patient_id", "N/A")
            diagnosis = p.get("diagnosis_summary", "N/A")
            if diagnosis and len(diagnosis) > 60:
                diagnosis = diagnosis[:57] + "..."
            print(f"  - {pid}: {diagnosis}")

    # 4b. Spawn CaseAgents (this will gracefully no-op if agents.case_agent is missing)
    print("\nAttempting to spawn CaseAgents (will skip if agents.case_agent is missing)...")
    try:
        spawned = coordinator.spawn_case_agents()
    except Exception as e:
        print("\nERROR: Exception while calling spawn_case_agents().")
        print(f"Details: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    if spawned:
        print(f"spawn_case_agents() completed. CaseAgents created: {len(coordinator.case_agents)}")
    else:
        print("spawn_case_agents() returned False. Check logs for details.")
        sys.exit(1)

    # 4c. Run case preparation in local-only mode
    # If there are no CaseAgents, CoordinatorAgent returns mock PENDING
    # results without calling out to ADK.
    print("\nRunning case preparation (this should not call external APIs if no CaseAgents exist)...")
    try:
        results = coordinator.run_case_preparation()
    except Exception as e:
        print("\nERROR: Exception while calling run_case_preparation().")
        print(f"Details: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    print("\nCase preparation results (summary):")
    for pid, res in results.items():
        status = res.get("status", "UNKNOWN")
        readiness = res.get("readiness_percentage", 0)
        print(f"  Patient {pid}: status={status}, readiness={readiness}%")

    # ------------------------------------------------------------------
    # Final summary
    # ------------------------------------------------------------------
    print_header("ALL SMOKE TESTS COMPLETED")
    print("CoordinatorAgent can be imported, instantiated, and can:")
    print("  1. Load the MDT roster from JSON.")
    print("  2. Optionally spawn CaseAgents (if implemented).")
    print("  3. Run case preparation in a local-only mode without ADK calls if no CaseAgents exist.")


if __name__ == "__main__":
    main()
