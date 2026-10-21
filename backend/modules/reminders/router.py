"""
Reminders router - Lightweight boundary placeholder.
Planned: Persistent reminders, task alerts, and WebPush browser notifications.
Notice: In this foundation phase, reminders are not yet persistent across restarts,
and push notifications are not yet implemented.
"""
from fastapi import APIRouter
from backend.schemas import StandardResponse, ModulePlaceholderResponse
from backend.core.scheduler import get_scheduler_status

router = APIRouter(prefix="/reminders", tags=["Reminders (Planned)"])


@router.get("", response_model=StandardResponse[ModulePlaceholderResponse])
def get_reminders_module_info():
    """Information endpoint describing planned reminders and current scheduler status."""
    return StandardResponse(
        success=True,
        data=ModulePlaceholderResponse(
            module="reminders",
            status="planned",
            message=(
                "Reminders module placeholder. Reminders require persistent SQLAlchemyJobStore "
                "and WebPush keys before being production-ready."
            ),
            capabilities_planned=[
                "One-time and recurring timed reminders",
                "Browser Web Push notifications on mobile/desktop Chrome",
                "Snooze, acknowledge, and calendar sync",
            ],
        ),
    )


@router.get("/scheduler-status", response_model=StandardResponse[dict])
def get_scheduler_diagnostic():
    """Internal diagnostic endpoint returning scheduler state and persistence notice."""
    return StandardResponse(
        success=True,
        data=get_scheduler_status(),
    )
