"""
Unit tests for the Scheduler lifecycle and diagnostics.
"""
from backend.core.scheduler import (
    get_scheduler,
    start_scheduler,
    shutdown_scheduler,
    get_scheduler_status,
)


def test_scheduler_lifecycle():
    """Verify scheduler starts, handles duplicate calls, and shuts down cleanly."""
    # Ensure fresh state
    shutdown_scheduler()

    # Start
    start_scheduler()
    scheduler = get_scheduler()
    assert scheduler.running is True

    # Duplicate start call should be safely ignored
    start_scheduler()
    assert scheduler.running is True

    # Check diagnostic status
    status = get_scheduler_status()
    assert status["running"] is True
    assert status["job_store"] == "in-memory"
    assert "persistence_notice" in status

    # Shutdown
    shutdown_scheduler()
    status_after = get_scheduler_status()
    assert status_after["running"] is False
