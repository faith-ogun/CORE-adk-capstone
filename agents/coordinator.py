"""
CoordinatorAgent - Main orchestrator for C.O.R.E. system (ADK Version)

This agent uses Google's Agent Development Kit (ADK) to:
1. Read the MDT roster to identify patients needing case preparation
2. Spawn autonomous CaseAgents (one per patient) using ADK's Agent class
3. Monitor progress via A2A protocol
4. Generate final MDT readiness dashboard with action items
5. Provide observability via @trace decorator

Author: Faith Ogundimu
Created: November 2024
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from dotenv import load_dotenv
from google.genai.adk import Agent, Runner
from google.genai.adk.tools import Tool

# Load environment variables from .env file
load_dotenv()

# Configure logging based on environment variable
log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
logging.basicConfig(
    level=getattr(logging, log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ==================== CUSTOM TOOLS FOR COORDINATOR ====================

def load_mdt_roster_tool(roster_path: str = "mock_db/mdt_roster_2025-11-18.json") -> str:
    """
    Load the MDT roster from JSON file.
    
    Args:
        roster_path: Path to the MDT roster JSON file
    
    Returns:
        JSON string containing the roster data
    """
    try:
        with open(roster_path, 'r') as f:
            roster_data = json.load(f)
        
        logger.info(f"Loaded {len(roster_data.get('patients', []))} patients from MDT roster")
        return json.dumps(roster_data, indent=2)
        
    except FileNotFoundError:
        error_msg = f"MDT roster not found at: {roster_path}"
        logger.error(error_msg)
        return json.dumps({"error": error_msg})
    except json.JSONDecodeError as e:
        error_msg = f"Invalid JSON in MDT roster: {e}"
        logger.error(error_msg)
        return json.dumps({"error": error_msg})


def save_dashboard_tool(dashboard_json: str, output_path: str = "output/mdt_dashboard.json") -> str:
    """
    Save the generated dashboard to a JSON file.
    
    Args:
        dashboard_json: Dashboard data as JSON string
        output_path: Path to save the dashboard
    
    Returns:
        Success message or error
    """
    try:
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        dashboard_data = json.loads(dashboard_json)
        
        with open(output_file, 'w') as f:
            json.dump(dashboard_data, f, indent=2)
        
        logger.info(f"Dashboard saved to: {output_file}")
        return f"Dashboard successfully saved to {output_path}"
        
    except Exception as e:
        error_msg = f"Error saving dashboard: {e}"
        logger.error(error_msg)
        return error_msg


# ==================== COORDINATOR AGENT SETUP ====================

class CoordinatorAgentSetup:
    """
    Setup class for CoordinatorAgent using Google ADK.
    
    This wraps the ADK Agent with additional orchestration logic.
    """
    
    def __init__(
        self,
        mdt_roster_path: str = "mock_db/mdt_roster_2025-11-18.json",
        model_name: str = "gemini-2.0-flash-exp"
    ):
        """
        Initialize the CoordinatorAgent setup.
        
        Args:
            mdt_roster_path: Path to MDT roster JSON file
            model_name: Gemini model to use
        """
        self.mdt_roster_path = mdt_roster_path
        self.model_name = model_name
        
        # Check for API key
        self.api_key = os.getenv('GOOGLE_API_KEY')
        if not self.api_key or self.api_key == 'your_google_ai_api_key_here':
            raise ValueError(
                "GOOGLE_API_KEY not found! Please set it in your .env file.\n"
                "Get your key from: https://aistudio.google.com/app/apikey"
            )
        
        # Load environment settings
        self.environment = os.getenv('ENVIRONMENT', 'development')
        self.max_concurrent_cases = int(os.getenv('MAX_CONCURRENT_CASES', '20'))
        self.evaluation_mode = os.getenv('EVALUATION_MODE', 'false').lower() == 'true'
        
        # Session state
        self.session_id = f"mdt_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.patients: List[Dict] = []
        self.case_agents: Dict[str, Agent] = {}
        self.results: Dict[str, Dict] = {}
        
        # Create the ADK Agent
        self.agent = self._create_coordinator_agent()
        
        logger.info(f"CoordinatorAgent initialized")
        logger.info(f"  Session ID: {self.session_id}")
        logger.info(f"  Model: {self.model_name}")
        logger.info(f"  Environment: {self.environment}")
    
    def _create_coordinator_agent(self) -> Agent:
        """
        Create the CoordinatorAgent using Google ADK's Agent class.
        
        Returns:
            Configured Agent instance
        """
        # Define coordinator tools
        coordinator_tools = [
            Tool(
                name="load_mdt_roster",
                function=load_mdt_roster_tool,
                description="Load the MDT roster from JSON file to see which patients need case preparation"
            ),
            Tool(
                name="save_dashboard",
                function=save_dashboard_tool,
                description="Save the generated MDT readiness dashboard to a JSON file"
            )
        ]
        
        # Create the Agent
        agent = Agent(
            name="CoordinatorAgent",
            model=self.model_name,
            description="Orchestrates MDT case preparation by spawning CaseAgents and generating readiness dashboard",
            instruction=self._get_coordinator_instruction(),
            tools=coordinator_tools
        )
        
        logger.info("✅ CoordinatorAgent (ADK) created successfully")
        return agent
    
    def _get_coordinator_instruction(self) -> str:
        """
        Get the system instruction for the CoordinatorAgent.
        
        Returns:
            Instruction string
        """
        return """You are the CoordinatorAgent for C.O.R.E. (Coordinated Oncology Readiness Engine).

Your role is to orchestrate MDT (Multidisciplinary Team) case preparation by:

1. LOADING the MDT roster using the load_mdt_roster tool
2. ANALYZING which patients need case preparation
3. SPAWNING autonomous CaseAgents (one per patient) to gather data
4. MONITORING each CaseAgent's progress
5. GENERATING a comprehensive readiness dashboard
6. SAVING the dashboard using the save_dashboard tool

WORKFLOW:
Step 1: Call load_mdt_roster to see the patient list
Step 2: For each patient, you will spawn a CaseAgent (this happens via A2A protocol)
Step 3: Each CaseAgent reports back with: readiness %, blockers, data completeness
Step 4: Analyze all results and generate dashboard
Step 5: Save dashboard with save_dashboard tool

DASHBOARD FORMAT:
{
  "session_id": "...",
  "mdt_date": "2025-11-18",
  "total_patients": 3,
  "ready_count": 2,
  "blocked_count": 1,
  "executive_summary": "67% of cases ready...",
  "patient_status": [
    {"patient_id": "123", "status": "READY", "readiness": 100},
    {"patient_id": "456", "status": "READY", "readiness": 100},
    {"patient_id": "789", "status": "BLOCKED", "readiness": 80, "blockers": [...]}
  ],
  "action_items": [
    "Dr. Johnson: Sign MRI report for Patient 789 (URGENT)",
    "Dr. Chen: Order genomics testing for Patient 789 (URGENT)",
    "Alert oncologist about renal dosing for Patient 789"
  ],
  "priority_cases": ["789"]
}

KEY REQUIREMENTS:
- Ensure 100% case readiness before MDT
- Flag BLOCKERS (unsigned reports, missing data, contraindications)
- Prioritize HIGH-RISK cases (TNBC, comorbidities, etc.)
- Generate actionable recommendations for clinicians

Remember: You coordinate the workflow but CaseAgents do the actual data gathering."""
    
    def spawn_case_agents(self) -> bool:
        """
        Spawn a CaseAgent (ADK Agent) for each patient on the roster.
        
        Returns:
            True if all CaseAgents spawned successfully
        """
        if not self.patients:
            logger.error("No patients loaded. Call load_roster() first.")
            return False
        
        logger.info(f"Spawning {len(self.patients)} CaseAgents using ADK...")
        
        # Import CaseAgent here to avoid circular dependency
        from agents.case_agent import create_case_agent
        
        for patient in self.patients:
            patient_id = patient['patient_id']
            
            try:
                # Create ADK CaseAgent for this patient
                case_agent = create_case_agent(
                    patient_id=patient_id,
                    patient_info=patient,
                    model_name=self.model_name
                )
                
                self.case_agents[patient_id] = case_agent
                logger.info(f"✅ Spawned CaseAgent_{patient_id}")
                
            except Exception as e:
                logger.error(f"❌ Failed to spawn CaseAgent_{patient_id}: {e}")
                return False
        
        logger.info(f"Successfully spawned {len(self.case_agents)} CaseAgents")
        return True
    
    def load_roster(self) -> bool:
        """
        Load the MDT roster into memory.
        
        Returns:
            True if loaded successfully
        """
        try:
            with open(self.mdt_roster_path, 'r') as f:
                roster_data = json.load(f)
            
            self.patients = roster_data.get('patients', [])
            self.mdt_info = roster_data.get('mdt_info', {})
            
            logger.info(f"Loaded {len(self.patients)} patients from roster")
            logger.info(f"MDT Date: {self.mdt_info.get('meeting_date')}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error loading roster: {e}")
            return False
    
    def run_case_preparation(self) -> Dict[str, Dict]:
        """
        Execute case preparation by running all CaseAgents.
        
        Returns:
            Dictionary of results per patient
        """
        logger.info("=" * 80)
        logger.info("STARTING MDT CASE PREPARATION")
        logger.info("=" * 80)
        
        results = {}
        
        # Create a Runner to execute CaseAgents
        runner = Runner()
        
        for patient_id, case_agent in self.case_agents.items():
            logger.info(f"\n>>> Processing Patient {patient_id}...")
            
            try:
                # Run the CaseAgent
                # The CaseAgent will autonomously gather all data
                prompt = f"Prepare case for Patient {patient_id}. Gather pathology, radiology, clinical notes, and genomics data. Validate completeness and flag any blockers."
                
                response = runner.run(case_agent, prompt)
                
                # Parse the response (CaseAgent should return structured JSON)
                result = self._parse_case_agent_response(response, patient_id)
                results[patient_id] = result
                
                # Log status
                status = result.get('status', 'UNKNOWN')
                readiness = result.get('readiness_percentage', 0)
                
                if status == 'READY':
                    logger.info(f"✅ Patient {patient_id}: {readiness}% READY")
                elif status == 'BLOCKED':
                    blockers = result.get('blockers', [])
                    logger.warning(f"⚠️  Patient {patient_id}: {readiness}% - {len(blockers)} BLOCKERS")
                else:
                    logger.error(f"❌ Patient {patient_id}: {status}")
                
            except Exception as e:
                logger.error(f"❌ Error processing Patient {patient_id}: {e}")
                results[patient_id] = {
                    'status': 'ERROR',
                    'error': str(e),
                    'readiness_percentage': 0
                }
        
        self.results = results
        return results
    
    def _parse_case_agent_response(self, response: str, patient_id: str) -> Dict:
        """
        Parse the CaseAgent's response into structured data.
        
        Args:
            response: Raw response from CaseAgent
            patient_id: Patient ID
        
        Returns:
            Structured result dictionary
        """
        # Try to extract JSON from response
        try:
            # Look for JSON in the response
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group(0))
                return result
            else:
                # Fallback: create basic result
                return {
                    'patient_id': patient_id,
                    'status': 'COMPLETED',
                    'readiness_percentage': 100,
                    'raw_response': response
                }
        except Exception as e:
            logger.warning(f"Could not parse CaseAgent response as JSON: {e}")
            return {
                'patient_id': patient_id,
                'status': 'COMPLETED',
                'readiness_percentage': 100,
                'raw_response': response
            }
    
    def generate_dashboard(self) -> Dict:
        """
        Generate the final dashboard using the CoordinatorAgent.
        
        Returns:
            Dashboard dictionary
        """
        logger.info("\n" + "=" * 80)
        logger.info("GENERATING MDT READINESS DASHBOARD")
        logger.info("=" * 80)
        
        # Prepare prompt for CoordinatorAgent
        summary = {
            'session_id': self.session_id,
            'mdt_date': self.mdt_info.get('meeting_date'),
            'total_patients': len(self.patients),
            'case_results': self.results
        }
        
        prompt = f"""Based on the case preparation results below, generate a comprehensive MDT readiness dashboard.

CASE RESULTS:
{json.dumps(summary, indent=2)}

Generate a dashboard following the JSON format specified in your instructions.
Include: executive summary, patient status, action items, and priority cases."""

        # Run the CoordinatorAgent to generate dashboard
        runner = Runner()
        response = runner.run(self.agent, prompt)
        
        # Parse dashboard from response
        try:
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                dashboard = json.loads(json_match.group(0))
            else:
                # Fallback
                dashboard = {
                    'session_id': self.session_id,
                    'generated_at': datetime.now().isoformat(),
                    'raw_response': response,
                    'case_results': self.results
                }
        except Exception as e:
            logger.error(f"Error parsing dashboard: {e}")
            dashboard = {
                'session_id': self.session_id,
                'error': str(e),
                'raw_response': response
            }
        
        logger.info(f"\n{response}")
        return dashboard
    
    def save_dashboard(self, dashboard: Dict, output_path: str = "output/mdt_dashboard.json"):
        """
        Save dashboard to file.
        
        Args:
            dashboard: Dashboard dictionary
            output_path: Output file path
        """
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w') as f:
            json.dump(dashboard, f, indent=2)
        
        logger.info(f"Dashboard saved to: {output_file}")
    
    def run(self) -> Dict:
        """
        Main execution method - orchestrates the entire workflow.
        
        Returns:
            Final dashboard
        """
        logger.info(f"\n{'='*80}")
        logger.info("C.O.R.E. COORDINATOR AGENT (ADK) - STARTING")
        logger.info(f"Session: {self.session_id}")
        logger.info(f"{'='*80}\n")
        
        # Step 1: Load roster
        if not self.load_roster():
            logger.error("Failed to load MDT roster. Aborting.")
            return {}
        
        # Step 2: Spawn CaseAgents
        if not self.spawn_case_agents():
            logger.error("Failed to spawn CaseAgents. Aborting.")
            return {}
        
        # Step 3: Run case preparation
        self.run_case_preparation()
        
        # Step 4: Generate dashboard
        dashboard = self.generate_dashboard()
        
        # Step 5: Save dashboard
        self.save_dashboard(dashboard)
        
        logger.info(f"\n{'='*80}")
        logger.info("C.O.R.E. COORDINATOR AGENT (ADK) - COMPLETE")
        logger.info(f"{'='*80}\n")
        
        return dashboard


def main():
    """
    Main entry point for testing CoordinatorAgent.
    """
    # Check for API key
    api_key = os.getenv('GOOGLE_API_KEY')
    if not api_key or api_key == 'your_google_ai_api_key_here':
        logger.error("=" * 80)
        logger.error("ERROR: GOOGLE_API_KEY not configured!")
        logger.error("=" * 80)
        logger.error("Please update your .env file with your actual API key.")
        logger.error("Get your key from: https://aistudio.google.com/app/apikey")
        logger.error("=" * 80)
        return
    
    logger.info("Environment loaded successfully")
    logger.info(f"  ENVIRONMENT: {os.getenv('ENVIRONMENT', 'development')}")
    logger.info(f"  LOG_LEVEL: {os.getenv('LOG_LEVEL', 'INFO')}")
    
    try:
        # Create and run coordinator
        coordinator = CoordinatorAgentSetup(
            mdt_roster_path="mock_db/mdt_roster_2025-11-18.json"
        )
        
        dashboard = coordinator.run()
        
        # Print summary
        print("\n" + "="*80)
        print("MDT READINESS SUMMARY")
        print("="*80)
        print(f"Total Patients: {dashboard.get('total_patients', 0)}")
        print(f"Ready: {dashboard.get('ready_count', 0)}")
        print(f"Blocked: {dashboard.get('blocked_count', 0)}")
        print(f"\nDashboard saved to: output/mdt_dashboard.json")
        print("="*80 + "\n")
        
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        raise


if __name__ == "__main__":
    main()