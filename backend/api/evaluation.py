"""
Evaluation API router.
"""
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database.connection import get_db
from backend.services.evaluation_service import run_evaluation, get_evaluation_summary
from backend.api.deps import require_admin

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin/evaluations", tags=["Evaluation"])


@router.get("")
def get_evaluations(
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    """Return the latest evaluation results summary as a free-form dict."""
    return get_evaluation_summary(db)


@router.post("/run")
def trigger_evaluation(
    db: Session = Depends(get_db),
    current_admin=Depends(require_admin),
):
    """Run the full DeepEval evaluation pipeline synchronously."""
    try:
        result = run_evaluation(db, created_by=current_admin.id)
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Evaluation run failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {str(exc)}")
