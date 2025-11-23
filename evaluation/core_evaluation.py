"""
core_evaluation.py

Behavioural evaluation for C.O.R.E. CaseAgent.

- Runs CaseAgent on a labelled test set (evaluation/mdt_eval_labels.json)
- Compares predicted readiness + blockers to expected labels
- Computes simple metrics and writes them to evaluation/core_eval_metrics.json

Author: Faith Ogundimu
"""

import asyncio
import json
import time
from pathlib import Path
from typing import Dict, Any, List, Set, Tuple

from dotenv import load_dotenv

load_dotenv()

# Try to import CaseAgent from different layouts (repo vs flat)
try:
    from agents.case_agent import CaseAgent
except ImportError:
    import sys
    sys.path.append(str(Path(__file__).resolve().parents[1]))
    try:
        from case_agent import CaseAgent
    except ImportError:
        sys.path.append(str(Path(__file__).resolve().parents[1] / "agents"))
        from case_agent import CaseAgent


ROOT_DIR = Path(__file__).resolve().parents[1]
EVAL_DIR = ROOT_DIR / "evaluation"
LABEL_PATH = EVAL_DIR / "mdt_eval_labels.json"
METRICS_PATH = EVAL_DIR / "core_eval_metrics.json"


def load_labels(path: Path = LABEL_PATH) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Label file not found at {path}")
    with path.open("r") as f:
        return json.load(f)


def normalise_status(status: str) -> str:
    """Normalise arbitrary LLM status strings into coarse categories."""
    if not status:
        return "ERROR"
    s = status.strip().upper()
    if "READY" in s:
        return "READY"
    if "BLOCK" in s:
        return "BLOCKED"
    if "PROGRESS" in s:
        return "IN_PROGRESS"
    if "ERROR" in s:
        return "ERROR"
    return s or "UNKNOWN"


def extract_blockers_from_checklist(checklist: Dict[str, Any]) -> Set[str]:
    """
    Very simple heuristic: treat any checklist value containing 'BLOCKER'
    or 'NOT COMPLETED' as a blocker for that category.
    """
    blockers: Set[str] = set()
    for category, summary in checklist.items():
        text = str(summary).upper()
        if "BLOCKER" in text or "NOT COMPLETED" in text or "MISSING" in text:
            blockers.add(category.upper())
    return blockers


async def evaluate_case(
    patient_id: str,
    meeting_date: str = "2025-11-18",
) -> Tuple[float, Dict[str, Any]]:
    """Run CaseAgent for a single patient and measure latency."""
    start = time.time()
    agent = CaseAgent(patient_id=patient_id, mdt_date=meeting_date)
    result = await agent.run_check()
    elapsed = time.time() - start
    return elapsed, result


async def run_behaviour_evaluation() -> Dict[str, Any]:
    """Run behavioural evaluation over the labelled test set."""
    labels = load_labels(LABEL_PATH)
    meeting_date = labels.get("meeting_date", "2025-11-18")

    expected_entries: List[Dict[str, Any]] = labels.get("patients", [])
    if not expected_entries:
        raise ValueError("No patients found in label file")

    total_cases = len(expected_entries)
    status_matches = 0
    status_mismatches: List[Dict[str, Any]] = []

    blocker_hits = 0
    blocker_misses = 0
    blocker_false_positives = 0

    json_errors = 0
    total_time = 0.0

    detailed_results: Dict[str, Any] = {}

    print("=" * 80)
    print("C.O.R.E. BEHAVIOURAL EVALUATION")
    print("=" * 80)
    print(f"\nUsing labels from: {LABEL_PATH}")
    print(f"Total labelled patients: {total_cases}\n")

    for entry in expected_entries:
        pid = str(entry["patient_id"])
        exp_status = entry["expected_status"].upper()
        exp_blockers = {b.upper() for b in entry.get("expected_blockers", [])}

        print("-" * 80)
        print(f"Evaluating patient {pid}")
        print("-" * 80)

        elapsed, result = await evaluate_case(pid, meeting_date=meeting_date)
        total_time += elapsed

        overall_status = normalise_status(result.get("overall_status", ""))
        checklist = result.get("checklist", {})
        pred_blockers = extract_blockers_from_checklist(checklist)

        # Status metrics
        if overall_status == exp_status:
            status_matches += 1
            print(f"  ✓ Status match: {overall_status}")
        else:
            print(f"  ✗ Status mismatch: expected {exp_status}, got {overall_status}")
            status_mismatches.append(
                {
                    "patient_id": pid,
                    "expected_status": exp_status,
                    "predicted_status": overall_status,
                }
            )

        # Blocker metrics
        hits = exp_blockers & pred_blockers
        misses = exp_blockers - pred_blockers
        false_positives = pred_blockers - exp_blockers

        blocker_hits += len(hits)
        blocker_misses += len(misses)
        blocker_false_positives += len(false_positives)

        if hits:
            print(f"  ✓ Correct blockers: {', '.join(sorted(hits))}")
        if misses:
            print(f"  ✗ Missed blockers: {', '.join(sorted(misses))}")
        if false_positives:
            print(f"  ⚠ Extra blockers (FP): {', '.join(sorted(false_positives))}")

        # JSON / schema robustness
        if overall_status == "ERROR" or not checklist:
            json_errors += 1

        detailed_results[pid] = {
            "elapsed_sec": round(elapsed, 3),
            "expected_status": exp_status,
            "predicted_status": overall_status,
            "expected_blockers": sorted(list(exp_blockers)),
            "predicted_blockers": sorted(list(pred_blockers)),
        }

        print(f"  ⏱ Time: {elapsed:.2f}s\n")

    avg_time = total_time / total_cases if total_cases else 0.0
    status_accuracy = status_matches / total_cases if total_cases else 0.0

    metrics: Dict[str, Any] = {
        "total_cases": total_cases,
        "status_matches": status_matches,
        "status_accuracy": round(status_accuracy, 3),
        "blocker_hits": blocker_hits,
        "blocker_misses": blocker_misses,
        "blocker_false_positives": blocker_false_positives,
        "json_error_cases": json_errors,
        "total_time_sec": round(total_time, 2),
        "avg_time_per_case_sec": round(avg_time, 2),
        "status_mismatches": status_mismatches,
        "per_patient": detailed_results,
    }

    # Ensure eval directory exists
    EVAL_DIR.mkdir(exist_ok=True, parents=True)
    with METRICS_PATH.open("w") as f:
        json.dump(metrics, f, indent=2)

    print("=" * 80)
    print("EVALUATION SUMMARY")
    print("=" * 80)
    print(f"\nStatus accuracy: {metrics['status_accuracy'] * 100:.1f}%")
    print(f"Blocker hits: {blocker_hits}")
    print(f"Blocker misses: {blocker_misses}")
    print(f"Blocker false positives: {blocker_false_positives}")
    print(f"JSON/schema error cases: {json_errors}")
    print(f"\nTotal time: {metrics['total_time_sec']:.2f}s")
    print(f"Average time per case: {metrics['avg_time_per_case_sec']:.2f}s")
    print(f"\nMetrics written to: {METRICS_PATH}\n")

    if status_mismatches:
        print("Status mismatches:")
        for mm in status_mismatches:
            print(
                f"  - Patient {mm['patient_id']}: "
                f"expected {mm['expected_status']}, "
                f"got {mm['predicted_status']}"
            )

    return metrics


if __name__ == "__main__":
    try:
        asyncio.run(run_behaviour_evaluation())
    except KeyboardInterrupt:
        print("\nEvaluation interrupted by user.")
    except Exception as e:
        print(f"\n❌ Error during evaluation: {e}")
        import traceback
        traceback.print_exc()
