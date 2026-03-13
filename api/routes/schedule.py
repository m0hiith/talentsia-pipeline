"""
API routes for schedule management.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/api/schedule", tags=["Schedule"])


@router.get("/")
async def get_schedule():
    """Get current schedule configuration and status."""
    from agents.scheduler_agent import scheduler
    result = await scheduler.run(action="check")
    return result.get("result", {})


@router.get("/next")
async def next_slot():
    """Get the next available posting slot."""
    from agents.scheduler_agent import scheduler
    result = await scheduler.run(action="next_slot")
    return result.get("result", {})


@router.get("/stats")
async def daily_stats():
    """Get today's publishing stats."""
    from agents.scheduler_agent import scheduler
    result = await scheduler.run(action="stats")
    return result.get("result", {})


@router.get("/scripts")
async def list_scripts(status: str = None, limit: int = 20):
    """List generated scripts."""
    from db.database import get_db
    query = """SELECT s.*, st.title as story_title, st.source
               FROM scripts s
               JOIN stories st ON s.story_id = st.id"""
    params = []

    if status:
        query += " WHERE s.status = ?"
        params.append(status)

    query += f" ORDER BY s.created_at DESC LIMIT {min(limit, 100)}"

    with get_db() as conn:
        rows = conn.execute(query, tuple(params)).fetchall()
        return [dict(r) for r in rows]
