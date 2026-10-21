"""
Scheduler lifecycle management using APScheduler.

ARCHITECTURE & PERSISTENCE NOTICE:
----------------------------------
The initial scheduler implementation runs an in-memory BackgroundScheduler.
CRITICAL LIMITATION: In-memory jobs DO NOT survive process or container restarts.

Production Strategy for Reminders:
Before reminders and push notifications are production-ready:
1. APScheduler must be configured with a persistent job store, such as:
   jobstores = {
       'default': SQLAlchemyJobStore(url=settings.DATABASE_URL)
   }
2. A database migration must create the 'apscheduler_jobs' table.
3. Job functions must be standalone top-level functions importable by module path.
4. Push notification triggers (WebPush / FCM) must be integrated and verified.

Do not claim reminders or notifications persist or trigger until the persistent
job store and WebPush integration are fully implemented and tested.
"""
from typing import Dict, Any, Optional
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.executors.pool import ThreadPoolExecutor
from backend.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_scheduler: Optional[BackgroundScheduler] = None


def get_scheduler() -> BackgroundScheduler:
    """
    Get or create the singleton BackgroundScheduler instance.
    Prevents creation of duplicate scheduler instances.
    """
    global _scheduler
    if _scheduler is None:
        executors = {
            "default": ThreadPoolExecutor(max_workers=5)
        }
        job_defaults = {
            "coalesce": True,
            "max_instances": 1,
            "misfire_grace_time": 60,
        }
        _scheduler = BackgroundScheduler(
            executors=executors,
            job_defaults=job_defaults,
            timezone="UTC"
        )
    return _scheduler


def start_scheduler() -> None:
    """
    Safely start the scheduler if enabled and not already running.
    Invoked during FastAPI lifespan startup.
    """
    if not settings.SCHEDULER_AUTOSTART:
        logger.info("Scheduler autostart is disabled via settings.")
        return

    scheduler = get_scheduler()
    if scheduler.running:
        logger.warning("Scheduler is already running; skipping redundant start.")
        return

    try:
        scheduler.start()
        logger.info("APScheduler started successfully (in-memory mode).")
    except Exception as exc:
        logger.error("Failed to start APScheduler: %s", exc)
        raise


def shutdown_scheduler(wait: bool = False) -> None:
    """
    Safely stop the scheduler if running.
    Invoked during FastAPI lifespan shutdown.
    """
    global _scheduler
    if _scheduler is not None and _scheduler.running:
        try:
            _scheduler.shutdown(wait=wait)
            logger.info("APScheduler stopped cleanly.")
        except Exception as exc:
            logger.error("Error shutting down APScheduler: %s", exc)
    _scheduler = None


def get_scheduler_status() -> Dict[str, Any]:
    """
    Returns diagnostic information about the scheduler state and persistence strategy.
    """
    scheduler = get_scheduler()
    is_running = scheduler.running if scheduler else False
    jobs_count = len(scheduler.get_jobs()) if is_running else 0
    jobs_summary = [job.id for job in scheduler.get_jobs()] if is_running else []

    return {
        "running": is_running,
        "jobs_count": jobs_count,
        "active_jobs": jobs_summary,
        "job_store": "in-memory",
        "persistence_notice": (
            "Current job store is in-memory. Jobs do not survive restarts. "
            "A persistent SQLAlchemyJobStore is required for production reminders."
        ),
    }
