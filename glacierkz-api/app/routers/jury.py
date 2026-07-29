from fastapi import APIRouter

from app.services.jury_evidence_service import jury_evidence

router = APIRouter(prefix="/api/jury", tags=["jury"])


@router.get("/evidence")
def evidence() -> dict:
    """A concise, read-only summary of what the local release can prove."""
    return jury_evidence()
