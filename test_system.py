import asyncio
import logging
import json

# --- CHANGE THIS IMPORT ---
# Was: from coordinator import CoordinatorAgent
from agents.coordinator import CoordinatorAgent 

# Configure logging...
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

async def run_full_test():
    print("\n========== INITIALIZING C.O.R.E. SYSTEM ==========\n")
    
    # 1. Initialize Coordinator
    # Note: path remains "mock_db/..." because we are running from root
    coord = CoordinatorAgent(
        mdt_roster_path="mock_db/mdt_roster_2025-11-18.json",
        model_name="gemini-2.0-flash-lite"
    )
    
    # 2. Load Roster
    print("--> Loading MDT Roster...")
    if not coord.load_roster():
        print("❌ Failed to load roster.")
        return

    # 3. Spawn Agents
    print(f"--> Spawning Case Agents for {len(coord.patients)} patients...")
    if not coord.spawn_case_agents():
        print("❌ Failed to spawn agents.")
        return

    # 4. Run Parallel Execution
    print("--> STARTING AUTONOMOUS PREPARATION (This may take 10-20 seconds)...")
    print("    Watch for 'A2A Request' logs below:\n")
    
    # We call the async method we added to the class
    results = await coord.run_case_preparation_async()
    
    # 5. Print Final Dashboard
    print("\n========== FINAL READINESS DASHBOARD ==========\n")
    print(json.dumps(results, indent=2))
    
    # Validation check for your specific differentiator
    p123_genomics = results.get("123", {}).get("checklist", {}).get("Genomics_Profile", {})
    if "PIK3CA" in str(p123_genomics):
        print("\n✅ SUCCESS: Patient 123 correctly identified PIK3CA mutation!")
    else:
        print("\n⚠️ WARNING: Genomics data might be missing for Patient 123.")

if __name__ == "__main__":
    asyncio.run(run_full_test())