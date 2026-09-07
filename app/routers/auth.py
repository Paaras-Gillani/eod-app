from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse
from app.database import get_connection
from app.security import verify_password

router = APIRouter()


@router.post("/login")
def login(request: Request, username: str = Form(...), password: str = Form(...)):
    conn = get_connection()
    try:
        user = conn.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()
    finally:
        conn.close()

    if not user or not verify_password(password, user["password_hash"], user["salt"]):
        return RedirectResponse(url="/login?error=1", status_code=303)

    request.session["user_id"] = user["id"]
    request.session["username"] = user["username"]
    request.session["role"] = user["role"]
    return RedirectResponse(url="/", status_code=303)


@router.post("/logout")
@router.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)
