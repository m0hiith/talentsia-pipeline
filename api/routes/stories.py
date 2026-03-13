"""
API routes for stories — CRUD, filtering, and stats.
"""

from fastapi import APIRouter
from db.database import get_db

router = APIRouter(prefix="/api/stories", tags=["Stories"])


@router.get("/")
async def list_stories(
    status: str = None,
    source: str = None,
    limit: int = 50,
):
    """List stories, optionally filtered by status and source."""
    query = "SELECT * FROM stories"
    params = []
    conditions = []

    if status:
        conditions.append("status = ?")
        params.append(status)
    if source:
        conditions.append("source = ?")
        params.append(source)

    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY final_score DESC, scraped_at DESC"
    query += f" LIMIT {min(limit, 200)}"

    with get_db() as conn:
        rows = conn.execute(query, tuple(params)).fetchall()
        return [dict(r) for r in rows]


@router.get("/stats")
async def story_stats():
    """Get story statistics by source and status."""
    with get_db() as conn:
        by_source = conn.execute(
            "SELECT source, COUNT(*) as count FROM stories GROUP BY source"
        ).fetchall()
        by_status = conn.execute(
            "SELECT status, COUNT(*) as count FROM stories GROUP BY status"
        ).fetchall()
        total = conn.execute("SELECT COUNT(*) as count FROM stories").fetchone()
        avg_score = conn.execute(
            "SELECT AVG(final_score) as avg FROM stories WHERE final_score > 0"
        ).fetchone()

    return {
        "total": dict(total)["count"] if total else 0,
        "avg_score": round(dict(avg_score)["avg"] or 0, 3) if avg_score else 0,
        "by_source": {dict(r)["source"]: dict(r)["count"] for r in by_source},
        "by_status": {dict(r)["status"]: dict(r)["count"] for r in by_status},
    }


@router.get("/{story_id}")
async def get_story(story_id: str):
    """Get a specific story by ID."""
    with get_db() as conn:
        row = conn.execute("SELECT * FROM stories WHERE id = ?", (story_id,)).fetchone()
        if not row:
            return {"error": "Story not found"}
        return dict(row)


@router.delete("/{story_id}")
async def delete_story(story_id: str):
    """Delete a story."""
    with get_db() as conn:
        conn.execute("DELETE FROM stories WHERE id = ?", (story_id,))
    return {"deleted": True, "id": story_id}
