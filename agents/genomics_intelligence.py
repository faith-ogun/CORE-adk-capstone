"""
GenomicsIntelligenceAgent - Advanced genomic analysis with clinical trial matching

This agent performs deep analysis on genomic data:
1. Interprets clinical significance of mutations (using Google Search)
2. Searches for matching clinical trials (ClinicalTrials.gov API)
3. Finds supporting evidence from PubMed (NCBI E-utilities API)
4. Synthesizes treatment recommendations

Author: Faith Ogundimu
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
import asyncio
import os

from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.models.google_llm import Gemini
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools.function_tool import FunctionTool
from google.adk.tools import google_search
from google.genai import types

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GenomicsIntelligenceAgent:
    """
    High-level orchestrator for genomic intelligence analysis.
    
    This runs AFTER CaseAgent completes, providing deep genomic insights
    for patients with mutation data.
    """
    
    def __init__(
        self,
        patient_id: str,
        genomic_data: Dict[str, Any],
        clinical_context: Dict[str, Any],
        model_name: str = "gemini-2.0-flash"
    ):
        """
        Initialize the genomics intelligence agent.
        
        Args:
            patient_id: Patient identifier
            genomic_data: Full genomic data from genomics_data.json
            clinical_context: Clinical info (diagnosis, stage, receptor status)
            model_name: Gemini model to use
        """
        self.patient_id = patient_id
        self.genomic_data = genomic_data
        self.clinical_context = clinical_context
        self.model_name = model_name
        
        self.app_name = f"genomics_intelligence_{patient_id}"
        self.user_id = "core_system"
        self.session_id = f"gi_{patient_id}"
        
        # Build the agent pipeline
        self.agent = self._build_intelligence_pipeline()
        self.session_service = InMemorySessionService()
        self.runner = Runner(
            agent=self.agent,
            app_name=self.app_name,
            session_service=self.session_service
        )
    
    def _build_intelligence_pipeline(self) -> SequentialAgent:
        """
        Builds the sequential genomic intelligence pipeline.
        
        Pipeline:
        1. MutationInterpreterAgent - Analyzes mutation significance (Google Search)
        2. ClinicalTrialMatcherAgent - Finds relevant trials (ClinicalTrials.gov)
        3. EvidenceSearchAgent - Searches PubMed for supporting evidence
        4. SynthesisAgent - Combines everything into structured recommendations
        """
        
        # Import tools
        import sys
        sys.path.append(str(Path(__file__).parent.parent))
        
        from tools.clinical_trials_api import search_clinical_trials
        from tools.pubmed_api import search_pubmed_literature
        
        # --- Agent 1: Mutation Interpreter (Google Search) ---
        mutation_interpreter = LlmAgent(
            name="MutationInterpreter",
            model=Gemini(model=self.model_name),
            instruction=self._get_interpreter_instruction(),
            tools=[google_search],
            output_key="mutation_analysis"
        )
        
        # --- Agent 2: Clinical Trial Matcher ---
        trial_matcher = LlmAgent(
            name="ClinicalTrialMatcher",
            model=Gemini(model=self.model_name),
            instruction=self._get_trial_matcher_instruction(),
            tools=[FunctionTool(search_clinical_trials)],
            output_key="clinical_trials"
        )
        
        # --- Agent 3: Evidence Search Agent ---
        evidence_searcher = LlmAgent(
            name="EvidenceSearcher",
            model=Gemini(model=self.model_name),
            instruction=self._get_evidence_searcher_instruction(),
            tools=[FunctionTool(search_pubmed_literature)],
            output_key="evidence_summary"
        )
        
        # --- Agent 4: Synthesis Agent ---
        synthesizer = LlmAgent(
            name="GenomicsSynthesizer",
            model=Gemini(model=self.model_name),
            instruction=self._get_synthesis_instruction(),
            output_key="final_report"
        )
        
        # --- Sequential Pipeline ---
        pipeline = SequentialAgent(
            name=f"GenomicsIntelligencePipeline_{self.patient_id}",
            sub_agents=[
                mutation_interpreter,
                trial_matcher,
                evidence_searcher,
                synthesizer
            ],
            description="Sequential genomic intelligence analysis pipeline"
        )
        
        return pipeline
    
    # ============= Agent Instructions =============
    
    def _get_interpreter_instruction(self) -> str:
        """
        Instructions for the mutation interpreter agent.
        Uses Google Search for real-time mutation interpretation.
        """
        mutations_str = json.dumps(self.genomic_data.get("mutations", []), indent=2)
        clinical_str = json.dumps(self.clinical_context, indent=2)
        
        return f"""You are a clinical genomics expert analyzing mutations for Patient {self.patient_id}.

        **Patient Clinical Context:**
        {clinical_str}

        **Detected Mutations:**
        {mutations_str}

        **Your Task:**
        For EACH mutation detected, use Google Search to find:
        1. **Clinical Significance**: Search "[gene] [variant] pathogenic clinical significance"
        2. **Mechanism**: Search "[gene] [variant] mechanism of action pathway"
        3. **Actionability**: Search "[gene] [variant] FDA approved therapy targeted treatment"
        4. **Prevalence**: Search "[gene] [variant] prevalence [cancer type]"

        **Search Strategy:**
        - For PIK3CA H1047R: Search "PIK3CA H1047R breast cancer clinical significance"
        - For TP53 R273H: Search "TP53 R273H pathogenic mechanism"
        - Focus on: OncoKB, COSMIC, cBioPortal, ClinVar

        **Output Format (JSON):**
        {{
            "mutations_analyzed": [
                {{
                    "gene": "PIK3CA",
                    "variant": "H1047R",
                    "significance": "Pathogenic",
                    "mechanism": "Brief description of mechanism",
                    "actionability": "FDA-approved: Drug name if available",
                    "prevalence": "Percentage in cancer type",
                    "sources_consulted": ["Source1", "Source2"]
                }}
            ]
        }}

        **CRITICAL:** Use google_search tool for EACH mutation. Search before answering!"""
    
    def _get_trial_matcher_instruction(self) -> str:
        """Instructions for clinical trial matcher agent."""
        return f"""You are a clinical trial matching specialist for Patient {self.patient_id}.

        **Previous Analysis:**
        {{mutation_analysis}}

        **Your Task:**
        Use the search_clinical_trials tool to find relevant trials for actionable mutations.

        For EACH actionable mutation:
        1. Call: search_clinical_trials(genes=["GENE"], mutation="VARIANT", cancer_type="breast cancer", status=["RECRUITING"])

        **Output Format (JSON):**
        {{
            "clinical_trials": [
                {{
                    "nct_id": "NCT12345678",
                    "title": "Trial title",
                    "phase": "Phase 2",
                    "status": "Recruiting",
                    "target_mutation": "PIK3CA",
                    "eligibility_match": "High - reason",
                    "url": "https://clinicaltrials.gov/study/NCT12345678"
                }}
            ]
        }}

        Return top 3-5 most relevant trials."""
    
    def _get_evidence_searcher_instruction(self) -> str:
        """Instructions for evidence search agent."""
        return f"""You are a medical literature analyst for Patient {self.patient_id}.

        **Previous Analysis:**
        Mutations: {{mutation_analysis}}
        Trials: {{clinical_trials}}

        **Your Task:**
        Use search_pubmed_literature to find key evidence.

        For each mutation + drug combination:
        1. Call: search_pubmed_literature("GENE VARIANT DRUG breast cancer", max_results=5, search_type="clinical_trial")

        **Output Format (JSON):**
        {{
            "evidence": [
                {{
                    "pmid": "12345678",
                    "title": "Paper title",
                    "authors": "Author et al.",
                    "journal": "Journal Name",
                    "year": "2019",
                    "key_findings": "Brief summary",
                    "study_type": "Clinical Trial"
                }}
            ]
        }}

        Focus on Phase 3 RCTs and high-impact journals."""
    
    def _get_synthesis_instruction(self) -> str:
        """Instructions for final synthesis agent."""
        return f"""You are synthesizing a genomic intelligence report for Patient {self.patient_id}.

        **All Available Data:**
        - Mutation Analysis: {{mutation_analysis}}
        - Clinical Trials: {{clinical_trials}}
        - Evidence: {{evidence_summary}}
        
        **Your Task:**
        Create a structured clinical report for MDT discussion.
        
        **Output Format (JSON):**
        {{
            "patient_id": "{self.patient_id}",
            "executive_summary": "2-3 sentence summary of key findings",
            "mutations": [
                {{
                    "gene": "PIK3CA",
                    "variant": "H1047R",
                    "significance": "Pathogenic activating mutation",
                    "actionability": "FDA-approved therapy available",
                    "recommended_treatment": "Alpelisib + fulvestrant"
                }}
            ],
            "treatment_recommendations": [
                {{
                    "priority": 1,
                    "therapy": "Drug name",
                    "indication": "Specific indication",
                    "evidence_level": "Level 1",
                    "key_trial": "SOLAR-1",
                    "pmid": "31091374"
                }}
            ],
            "clinical_trials": [
                {{
                    "nct_id": "NCT12345678",
                    "title": "Trial title",
                    "phase": "Phase 2",
                    "eligibility_match": "High"
                }}
            ],
            "next_steps": "Specific clinical actions recommended"
        }}
        
        **CRITICAL:** 
        - All claims must have sources (PMID or NCT ID)
        - Be specific and actionable
        - Focus on FDA-approved options first"""
    
    # ============= Main Execution =============
    
    async def run_analysis(self) -> Dict[str, Any]:
        """
        Run the complete genomic intelligence analysis.
        
        Returns:
            Structured genomic intelligence report (JSON)
        """
        logger.info(f"[{self.patient_id}] Starting Genomic Intelligence Analysis...")
        logger.info(f"[{self.patient_id}] Pipeline: Google Search → ClinicalTrials.gov → PubMed → Synthesis")
        
        # Create session
        try:
            await self.session_service.create_session(
                app_name=self.app_name,
                user_id=self.user_id,
                session_id=self.session_id
            )
        except Exception as e:
            logger.debug(f"Session creation note: {e}")
        
        # Trigger message
        trigger_msg = types.Content(
            role="user",
            parts=[types.Part(text="Begin genomic intelligence analysis.")]
        )
        
        final_response_text = ""
        
        # Run pipeline
        async for event in self.runner.run_async(
            new_message=trigger_msg,
            user_id=self.user_id,
            session_id=self.session_id
        ):
            if hasattr(event, "content") and event.content:
                raw_content = event.content
                
                # Extract text safely
                if isinstance(raw_content, str):
                    text_extraction = raw_content
                elif hasattr(raw_content, "parts"):
                    parts_text = []
                    for part in raw_content.parts:
                        if hasattr(part, "text") and part.text:
                            parts_text.append(part.text)
                    text_extraction = "".join(parts_text)
                else:
                    continue
                
                if text_extraction.strip():
                    final_response_text = text_extraction
        
        # Parse JSON output
        try:
            clean_text = final_response_text.replace("```json", "").replace("```", "").strip()
            result = json.loads(clean_text)
            logger.info(f"[{self.patient_id}] Genomic Intelligence Analysis Complete ✓")
            return result
        except Exception as e:
            logger.error(f"Failed to parse genomic intelligence output: {e}")
            return {
                "status": "ERROR",
                "patient_id": self.patient_id,
                "error": str(e),
                "raw_output": final_response_text[:500]
            }


# ============= Quick Test =============

async def test_genomics_intelligence():
    """Test the genomics intelligence agent with Patient 123."""
    
    from dotenv import load_dotenv
    load_dotenv()
    
    if not os.getenv("GOOGLE_API_KEY"):
        print("❌ Error: GOOGLE_API_KEY not found")
        return
    
    # Load genomic data
    genomics_path = Path(__file__).parent.parent / "mock_db" / "genomics_data.json"
    
    if not genomics_path.exists():
        print(f"❌ Error: genomics_data.json not found at {genomics_path}")
        return
    
    with open(genomics_path, 'r') as f:
        all_genomics = json.load(f)
    
    patient_genomics = all_genomics.get("patient_123", {})
    
    # Clinical context
    clinical_context = {
        "diagnosis": "Invasive ductal carcinoma, right breast",
        "stage": "IIA (T2N1aM0)",
        "receptors": "ER+/PR+/HER2-",
        "grade": "2"
    }
    
    print("="*80)
    print("🧬 TESTING GENOMICS INTELLIGENCE AGENT - PATIENT 123")
    print("="*80)
    print(f"\n📋 Clinical Context:")
    print(f"   Diagnosis: {clinical_context['diagnosis']}")
    print(f"   Receptors: {clinical_context['receptors']}")
    print(f"   Stage: {clinical_context['stage']}")
    
    mutations = patient_genomics.get('mutations', [])
    print(f"\n🔬 Detected Mutations: {len(mutations)}")
    for mut in mutations:
        print(f"   • {mut['gene']} {mut['variant']} ({mut['interpretation']})")
    
    print("\n" + "-"*80)
    print("🚀 Starting Multi-Agent Pipeline...")
    print("-"*80)
    print("Agent 1: MutationInterpreter (Google Search)")
    print("Agent 2: ClinicalTrialMatcher (ClinicalTrials.gov API)")
    print("Agent 3: EvidenceSearcher (PubMed API)")
    print("Agent 4: GenomicsSynthesizer (Final Report)")
    print("-"*80 + "\n")
    
    agent = GenomicsIntelligenceAgent(
        patient_id="123",
        genomic_data=patient_genomics,
        clinical_context=clinical_context
    )
    
    result = await agent.run_analysis()
    
    print("\n" + "="*80)
    print("📊 GENOMIC INTELLIGENCE REPORT")
    print("="*80)
    
    if result.get("status") == "ERROR":
        print(f"\n❌ Error: {result.get('error')}")
        print(f"\nRaw output preview: {result.get('raw_output', '')[:300]}...")
    else:
        print(json.dumps(result, indent=2))
        
        # Summary
        print("\n" + "="*80)
        print("📝 SUMMARY")
        print("="*80)
        
        if "executive_summary" in result:
            print(f"\n{result['executive_summary']}")
        
        if "mutations" in result:
            print(f"\n🔬 Mutations Analyzed: {len(result['mutations'])}")
        
        if "treatment_recommendations" in result:
            print(f"💊 Treatment Options: {len(result['treatment_recommendations'])}")
        
        if "clinical_trials" in result:
            print(f"🏥 Clinical Trials Found: {len(result['clinical_trials'])}")


if __name__ == "__main__":
    asyncio.run(test_genomics_intelligence())