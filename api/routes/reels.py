"""
API routes for reels — list, approve, reject, publish.
"""

from fastapi import APIRouter
from db.database import get_db

router = APIRouter(prefix="/api/reels", tags=["Reels"])


@router.get("/")
async def list_reels(status: str = None, limit: int = 20):
    """List reels, optionally filtered by status."""
    query = """SELECT r.*, s.hook, s.body, s.cta, s.full_text, s.caption, s.hashtags,
               s.model_used, st.title as story_title, st.source
               FROM reels r
               JOIN scripts s ON r.script_id = s.id
               JOIN stories st ON s.story_id = st.id"""
    params = []

    if status:
        query += " WHERE r.status = ?"
        params.append(status)

    query += f" ORDER BY r.created_at DESC LIMIT {min(limit, 100)}"

    with get_db() as conn:
        rows = conn.execute(query, tuple(params)).fetchall()
        return [dict(r) for r in rows]


@router.get("/{reel_id}")
async def get_reel(reel_id: str):
    """Get a specific reel with script and story details."""
    with get_db() as conn:
        row = conn.execute(
            """SELECT r.*, s.hook, s.body, s.cta, s.full_text, s.caption, s.hashtags,
               s.model_used, st.title as story_title, st.source
               FROM reels r
               JOIN scripts s ON r.script_id = s.id
               JOIN stories st ON s.story_id = st.id
               WHERE r.id = ?""",
            (reel_id,),
        ).fetchone()
        if not row:
            return {"error": "Reel not found"}
        return dict(row)


@router.post("/{reel_id}/approve")
async def approve_reel(reel_id: str):
    """Approve a reel for publishing."""
    with get_db() as conn:
        conn.execute(
            "UPDATE reels SET status = 'approved' WHERE id = ?", (reel_id,)
        )
    return {"approved": True, "reel_id": reel_id}


@router.post("/{reel_id}/reject")
async def reject_reel(reel_id: str):
    """Reject a reel."""
    with get_db() as conn:
        conn.execute(
            "UPDATE reels SET status = 'rejected' WHERE id = ?", (reel_id,)
        )
    return {"rejected": True, "reel_id": reel_id}


@router.post("/{reel_id}/publish")
async def publish_reel(reel_id: str):
    """Publish a reel to Instagram."""
    from agents.publisher_agent import publisher
    result = await publisher.run(reel_id=reel_id, action="publish")
    return result
