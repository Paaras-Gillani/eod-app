from fastapi import Request, HTTPException
from app.database import get_connection


def get_current_user(request: Request):
    """Raises 401 (caught by frontend JS -> redirect to /login) if not logged in."""
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not logged in")
    conn = get_connection()
    try:
        user = conn.execute(
            "SELECT id, username, role FROM users WHERE id = ?", (user_id,)
        ).fetchone()
    finally:
        conn.close()
    if not user:
        raise HTTPException(status_code=401, detail="Not logged in")
    return dict(user)


def require_page_user(request: Request):
    """Same as get_current_user but for page routes (redirect instead of 401 JSON)."""
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    conn = get_connection()
    try:
        user = conn.execute(
            "SELECT id, username, role FROM users WHERE id = ?", (user_id,)
        ).fetchone()
    finally:
        conn.close()
    return dict(user) if user else None
