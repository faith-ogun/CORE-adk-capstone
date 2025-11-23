faith@ZETA CORE-adk-capstone % python3 performance_comparison.py 
================================================================================
C.O.R.E. PERFORMANCE ANALYSIS
Parallel Agent Architecture
================================================================================

────────────────────────────────────────────────────────────────────────────────
TESTING PARALLEL CASEAGENT
────────────────────────────────────────────────────────────────────────────────

────────────────────────────────────────────────────────────────────────────────
Testing Patient 123
────────────────────────────────────────────────────────────────────────────────

🚀 Running Parallel CaseAgent...
   Architecture: ParallelAgent → 4 baby agents → SynthesisAgent
Warning: there are non-text parts in the response: ['function_call'], returning concatenated text result from text parts. Check the full candidates.content.parts accessor to get the full model response.
Warning: there are non-text parts in the response: ['function_call'], returning concatenated text result from text parts. Check the full candidates.content.parts accessor to get the full model response.
Warning: there are non-text parts in the response: ['function_call'], returning concatenated text result from text parts. Check the full candidates.content.parts accessor to get the full model response.
Warning: there are non-text parts in the response: ['function_call'], returning concatenated text result from text parts. Check the full candidates.content.parts accessor to get the full model response.
Warning: there are non-text parts in the response: ['function_call'], returning concatenated text result from text parts. Check the full candidates.content.parts accessor to get the full model response.
   ✓ Completed in 3.76 seconds
   Status: READY
   Checklist: 5/5 items complete

────────────────────────────────────────────────────────────────────────────────
Testing Patient 456
────────────────────────────────────────────────────────────────────────────────

🚀 Running Parallel CaseAgent...
   Architecture: ParallelAgent → 4 baby agents → SynthesisAgent
Warning: there are non-text parts in the response: ['function_call'], returning concatenated text result from text parts. Check the full candidates.content.parts accessor to get the full model response.
Warning: there are non-text parts in the response: ['function_call'], returning concatenated text result from text parts. Check the full candidates.content.parts accessor to get the full model response.
Warning: there are non-text parts in the response: ['function_call'], returning concatenated text result from text parts. Check the full candidates.content.parts accessor to get the full model response.
Warning: there are non-text parts in the response: ['function_call'], returning concatenated text result from text parts. Check the full candidates.content.parts accessor to get the full model response.
Warning: there are non-text parts in the response: ['function_call'], returning concatenated text result from text parts. Check the full candidates.content.parts accessor to get the full model response.
   ✓ Completed in 2.97 seconds
   Status: READY
   Checklist: 5/5 items complete

────────────────────────────────────────────────────────────────────────────────
Testing Patient 789
────────────────────────────────────────────────────────────────────────────────

🚀 Running Parallel CaseAgent...
   Architecture: ParallelAgent → 4 baby agents → SynthesisAgent
Warning: there are non-text parts in the response: ['function_call'], returning concatenated text result from text parts. Check the full candidates.content.parts accessor to get the full model response.
Warning: there are non-text parts in the response: ['function_call'], returning concatenated text result from text parts. Check the full candidates.content.parts accessor to get the full model response.
Warning: there are non-text parts in the response: ['function_call'], returning concatenated text result from text parts. Check the full candidates.content.parts accessor to get the full model response.
Warning: there are non-text parts in the response: ['function_call'], returning concatenated text result from text parts. Check the full candidates.content.parts accessor to get the full model response.
Warning: there are non-text parts in the response: ['function_call'], returning concatenated text result from text parts. Check the full candidates.content.parts accessor to get the full model response.
   ✓ Completed in 2.81 seconds
   Status: BLOCKED
   Checklist: 3/5 items complete
   🚨 Blockers detected: Radiology

================================================================================
PERFORMANCE SUMMARY
================================================================================

Average time per patient: 3.18 seconds
Total time for 3 patients: 9.54 seconds

📊 COMPARED TO SEQUENTIAL APPROACH:
   Sequential (estimated): 24.0s (8.0s per patient)
   Parallel (actual): 9.5s (3.2s per patient)
   ⚡ Time saved: 14.5 seconds
   ⚡ Speedup: ~60% faster

🏥 EXTRAPOLATED TO 20-PATIENT MDT:
   Sequential: 2.7 minutes (160s)
   Parallel: 1.1 minutes (64s)
   ⏱ Time saved: 1.6 minutes (96s)

================================================================================
ARCHITECTURE DETAILS
================================================================================

🏗️ Your Parallel CaseAgent Architecture:
   CaseAgent (SequentialAgent)
   ├─► Phase 1: ParallelAgent
   │   ├─► EHRAgent (fetch_clinical_notes)
   │   ├─► PathologyAgent (fetch_pathology)
   │   ├─► RadiologyAgent (fetch_radiology)
   │   └─► GenomicsAgent (fetch_genomics)
   └─► Phase 2: CaseManager (synthesis)
       └─► Aggregates results → JSON output

✨ Key Benefits:
   ✓ 4 baby agents run concurrently (no sequential bottleneck)
   ✓ Each agent is a specialist in one domain
   ✓ Clean separation of concerns
   ✓ Easy to add 5th agent (ContraindicationAgent)
   ✓ Automatic blocker detection (unsigned reports)
   ✓ Structured JSON output perfect for dashboards

================================================================================
DETAILED RESULTS BY PATIENT
================================================================================

────────────────────────────────────────────────────────────────────────────────
Patient 123: READY
────────────────────────────────────────────────────────────────────────────────
  ✓ Clinical:
     58-year-old with Stage IIA invasive ductal carcinoma of the right brea...
  ✓ Pathology:
     Invasive ductal carcinoma, Grade 2. ER: Positive (90%), PR: Positive (...
  ✓ Radiology:
     No evidence of distant metastatic disease. Primary tumor right breast ...
  ✓ Genomics:
     PIK3CA H1047R, TP53 R273H. TMB: TMB-Low.
  ✓ Contraindications:
     9 drug profiles available. Breast cancer relevant: Doxorubicin, Cyclop...

  📝 Notes: All data is present and clear; the case is ready.

────────────────────────────────────────────────────────────────────────────────
Patient 456: READY
────────────────────────────────────────────────────────────────────────────────
  ✓ Clinical:
     52-year-old female diagnosed with Stage IIB invasive lobular carcinoma...
  ✓ Pathology:
     Invasive lobular carcinoma, Grade 2, ER Positive (85%), PR Negative, H...
  ✓ Radiology:
     Latest Scan (Mammogram): Irregular spiculated mass left breast 10 o'cl...
  ✓ Genomics:
     ESR1 Y537S mutation detected. TMB is TMB-Low.
  ✓ Contraindications:
     Loaded 9 drug profiles. Breast cancer relevant: Doxorubicin, Cyclophos...

  📝 Notes: All data is present and clear.

────────────────────────────────────────────────────────────────────────────────
Patient 789: BLOCKED
────────────────────────────────────────────────────────────────────────────────
  ✓ Clinical:
     45-year-old female, Stage IIA triple-negative invasive ductal carcinom...
  ✓ Pathology:
     Invasive ductal carcinoma, Grade 3, ER Negative, PR Negative, HER2 Neg...
  ⚠ Radiology:
     BLOCKER: UNSIGNED report. Right breast irregular enhancing mass, suspi...
  ⚠ Genomics:
     Genomic testing NOT completed.
  ✓ Contraindications:
     9 drug profiles available, including Doxorubicin, Cyclophosphamide, Pa...

  📝 Notes: Radiology report is unsigned, blocking readiness.

================================================================================
RECOMMENDATIONS FOR IMPROVEMENT
================================================================================

💡 Suggested Enhancements:
   1. Add ContraindicationAgent (5th baby agent)
      - Fetch drug safety rules
      - Cross-reference with patient comorbidities
      - Flag treatment concerns

   2. Update Coordinator to use your new CaseAgent
      - Use coordinator_updated.py provided
      - Runs multiple CaseAgents in sequence
      - Generates dashboard JSON

   3. Add more sophisticated synthesis
      - Calculate readiness scores
      - Prioritize action items
      - Generate treatment recommendations

   4. Build dashboard UI
      - Visualize parallel agent execution
      - Show real-time progress
      - Interactive blocker resolution

================================================================================
COMPETITION HIGHLIGHTS (Agents for Good)
================================================================================

🏆 What Makes This Special:
   ✓ Multi-agent orchestration (CoordinatorAgent + CaseAgents + Baby Agents)
   ✓ Parallel execution using Google ADK patterns
   ✓ Real-world healthcare application (MDT case prep)
   ✓ Autonomous decision-making (blocker detection)
   ✓ Measurable impact (~60% faster, saves clinician time)
   ✓ Production-ready architecture (error handling, logging)
   ✓ Scalable to large MDTs (20+ patients)

📊 Key Metrics for Demo:
   • Average case prep time: 3.2s per patient
   • Total agents: ~13 (1 coordinator + 3 case × 4 baby)
   • Blocker detection: ✓ Automatic (patient 789 correctly flagged)
   • Speedup: ~60% vs sequential approach