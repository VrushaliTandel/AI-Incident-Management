"""
Standalone evaluation runner script.
Run from the AI_Incident_Management directory:
    python evaluation/run_evaluation.py
"""
import sys
import json
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    from backend.database.connection import SessionLocal, init_db
    from backend.database.models import Base  # noqa
    from backend.services.evaluation_service import run_evaluation

    init_db()
    db = SessionLocal()
    try:
        logger.info("Starting DeepEval evaluation...")
        results = run_evaluation(db)
        if "error" in results:
            logger.error("Evaluation error: %s", results["error"])
            return

        print("\n" + "=" * 60)
        print("EVALUATION RESULTS")
        print("=" * 60)
        print(f"Run ID: {results['run_id']}")
        print(f"Total test cases: {results['total_cases']}")
        print("\n--- AVERAGES ---")
        for metric, score in results.get("averages", {}).items():
            if score is not None:
                print(f"  {metric:30s}: {score:.4f}")
            else:
                print(f"  {metric:30s}: N/A")

        print("\n--- PER-CASE RESULTS ---")
        for r in results.get("results", []):
            print(f"\n  Test: {r['test_case_id']}")
            print(f"    Faithfulness:          {r.get('faithfulness', 'N/A')}")
            print(f"    Answer Relevancy:      {r.get('answer_relevancy', 'N/A')}")
            print(f"    Contextual Relevancy:  {r.get('contextual_relevancy', 'N/A')}")
            print(f"    Contextual Precision:  {r.get('contextual_precision', 'N/A')}")
            print(f"    Contextual Recall:     {r.get('contextual_recall', 'N/A')}")
            print(f"    Overall:               {r.get('overall_score', 'N/A')}")

        # Save results to JSON
        output_path = Path(__file__).parent / "last_results.json"
        with open(output_path, "w") as f:
            json.dump(results, f, indent=2, default=str)
        print(f"\nResults saved to: {output_path}")

    finally:
        db.close()


if __name__ == "__main__":
    main()
