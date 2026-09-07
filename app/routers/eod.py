from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.database import get_connection
from app.deps import get_current_user

router = APIRouter(prefix="/api/eod", tags=["eod"])


class BreakdownItem(BaseModel):
    method: str
    amount: float


class EODSubmission(BaseModel):
    page_id: int
    report_date: Optional[str] = None  # defaults to today

    redeem_processed_count: int
    redeem_paid_count: int
    redeem_pending_count: int

    redeem_paid_amount: float
    redeem_pending_amount: float
    grand_total_deposit: float

    deposit_breakdown: list[BreakdownItem] = []
    redeem_breakdown: list[BreakdownItem] = []

    screenshot_path: Optional[str] = None


@router.post("")
def create_eod(payload: EODSubmission, user=Depends(get_current_user)):
    report_date = payload.report_date or date.today().isoformat()

    conn = get_connection()
    try:
        page = conn.execute(
            "SELECT id FROM pages WHERE id = ?", (payload.page_id,)
        ).fetchone()
        if not page:
            raise HTTPException(status_code=404, detail="Page not found.")

        cur = conn.execute(
            """
            INSERT INTO eod_reports (
                page_id, user_id, report_date,
                redeem_processed_count, redeem_paid_count, redeem_pending_count,
                redeem_paid_amount, redeem_pending_amount, grand_total_deposit,
                screenshot_path
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload.page_id,
                user["id"],
                report_date,
                payload.redeem_processed_count,
                payload.redeem_paid_count,
                payload.redeem_pending_count,
                payload.redeem_paid_amount,
                payload.redeem_pending_amount,
                payload.grand_total_deposit,
                payload.screenshot_path,
            ),
        )
        eod_id = cur.lastrowid

        conn.executemany(
            "INSERT INTO deposit_breakdown (eod_id, method, amount) VALUES (?, ?, ?)",
            [(eod_id, i.method, i.amount) for i in payload.deposit_breakdown],
        )
        conn.executemany(
            "INSERT INTO redeem_breakdown (eod_id, method, amount) VALUES (?, ?, ?)",
            [(eod_id, i.method, i.amount) for i in payload.redeem_breakdown],
        )
        conn.commit()
    finally:
        conn.close()

    return {"id": eod_id, "report_date": report_date}


@router.get("")
def list_eod(
    page_id: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    user=Depends(get_current_user),
):
    query = """
        SELECT e.*, p.name AS page_name, u.username
        FROM eod_reports e
        JOIN pages p ON p.id = e.page_id
        JOIN users u ON u.id = e.user_id
        WHERE 1=1
    """
    params: list = []
    if page_id:
        query += " AND e.page_id = ?"
        params.append(page_id)
    if start_date:
        query += " AND e.report_date >= ?"
        params.append(start_date)
    if end_date:
        query += " AND e.report_date <= ?"
        params.append(end_date)
    query += " ORDER BY e.report_date DESC, e.created_at DESC LIMIT 200"

    conn = get_connection()
    try:
        rows = conn.execute(query, params).fetchall()
    finally:
        conn.close()
    return [dict(r) for r in rows]


@router.get("/{eod_id}")
def get_eod(eod_id: int, user=Depends(get_current_user)):
    conn = get_connection()
    try:
        report = conn.execute(
            """
            SELECT e.*, p.name AS page_name, u.username
            FROM eod_reports e
            JOIN pages p ON p.id = e.page_id
            JOIN users u ON u.id = e.user_id
            WHERE e.id = ?
            """,
            (eod_id,),
        ).fetchone()
        if not report:
            raise HTTPException(status_code=404, detail="Report not found.")

        deposits = conn.execute(
            "SELECT method, amount FROM deposit_breakdown WHERE eod_id = ?",
            (eod_id,),
        ).fetchall()
        redeems = conn.execute(
            "SELECT method, amount FROM redeem_breakdown WHERE eod_id = ?",
            (eod_id,),
        ).fetchall()
    finally:
        conn.close()

    result = dict(report)
    result["deposit_breakdown"] = [dict(r) for r in deposits]
    result["redeem_breakdown"] = [dict(r) for r in redeems]
    return result
