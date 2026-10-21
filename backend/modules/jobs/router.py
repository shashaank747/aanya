"""
Jobs router - Lightweight boundary placeholder.
Planned: Job application logging, timeline tracking, and interview follow-ups.
"""
from fastapi import APIRouter
from backend.schemas import StandardResponse, ModulePlaceholderResponse

router = APIRouter(prefix="/jobs", tags=["Jobs (Planned)"])


@router.get("", response_model=StandardResponse[ModulePlaceholderResponse])
def get_jobs_module_info():
    """Information endpoint describing planned job tracking capabilities."""
    return StandardResponse(
        success=True,
        data=ModulePlaceholderResponse(
            module="jobs",
            status="planned",
            message="Job tracking module placeholder. Business logic to be implemented in subsequent phases.",
            capabilities_planned=[
                "Track job applications, companies, roles, and status",
                "Log interview stages, feedback, and scheduled callbacks",
                "Store notes and resume revisions per application",
            ],
        ),
    )
