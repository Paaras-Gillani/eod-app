from fastapi import APIRouter, Depends
from app.database import get_connection
from app.deps import get_current_user

router = APIRouter(prefix="/api/pages", tags=["pages"])


@router.get("")
def list_pages(user=Depends(get_current_user)):
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT id, name FROM pages WHERE active = 1 ORDER BY name"
        ).fetchall()
    finally:
        conn.close()
    return [dict(r) for r in rows]
