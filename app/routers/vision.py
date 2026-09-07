import base64
import json
import os
import uuid
from pathlib import Path

import requests
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException

from app.deps import get_current_user

router = APIRouter(prefix="/api/vision", tags=["vision"])

UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

# The model must return exactly this shape. Keeping it strict makes the
# frontend's rendering code simple and predictable.
EXTRACTION_INSTRUCTIONS = """\
You are reading a screenshot of an internal admin dashboard table. The table \
has one row per gaming page, with columns for total deposit, a breakdown of \
deposit amounts by payment method, total redeem, a breakdown of redeem \
amounts by payment method, and pending redeem amount.

Find the row for the page named "{page_name}" (matching is case-insensitive \
and ignores punctuation/spacing differences). Extract ONLY that row.

Respond with ONLY valid JSON, no markdown fences, no commentary, in exactly \
this shape:

{{
  "found": true,
  "grand_total_deposit": 0.00,
  "deposit_breakdown": [{{"method": "string", "amount": 0.00}}],
  "redeem_paid_amount": 0.00,
  "redeem_breakdown": [{{"method": "string", "amount": 0.00}}],
  "redeem_pending_amount": 0.00
}}

If you cannot find a row matching that page name, respond with:
{{"found": false}}

Rules:
- Amounts are numbers, not strings, with no currency symbols or commas.
- Only include a method in a breakdown if it has a nonzero amount for this page.
- Do not invent methods or amounts that aren't visible in the image.
"""


@router.post("/extract")
async def extract_breakdown(
    page_name: str = Form(...),
    screenshot: UploadFile = File(...),
    user=Depends(get_current_user),
):
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="GEMINI_API_KEY is not configured on the server.",
        )

    contents = await screenshot.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Empty file upload.")

    # Save a copy so the source image is available later for audit.
    ext = Path(screenshot.filename or "screenshot.png").suffix or ".png"
    saved_name = f"{uuid.uuid4().hex}{ext}"
    saved_path = UPLOAD_DIR / saved_name
    saved_path.write_bytes(contents)

    b64_image = base64.b64encode(contents).decode()
    mime = screenshot.content_type or "image/png"

    url = GEMINI_URL.format(model=MODEL)
    body = {
        "contents": [
            {
                "parts": [
                    {"text": EXTRACTION_INSTRUCTIONS.format(page_name=page_name)},
                    {"inline_data": {"mime_type": mime, "data": b64_image}},
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0,
            "maxOutputTokens": 4096,
            "responseMimeType": "application/json",
            # This is a simple extraction task, not something that benefits
            # from the model "thinking" - and thinking tokens eat into
            # maxOutputTokens, which was causing empty responses.
            "thinkingConfig": {"thinkingBudget": 0},
        },
    }

    try:
        resp = requests.post(url, params={"key": api_key}, json=body, timeout=30)
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Couldn't reach Gemini: {e}")

    if resp.status_code != 200:
        # Gemini returns useful error text in the body - surface a trimmed version.
        raise HTTPException(
            status_code=502,
            detail=f"Vision extraction failed ({resp.status_code}): {resp.text[:300]}",
        )

    payload = resp.json()

    # The prompt can be blocked (safety filters) before any candidate is made.
    block_reason = payload.get("promptFeedback", {}).get("blockReason")
    if block_reason:
        raise HTTPException(
            status_code=502,
            detail=f"Gemini blocked this request ({block_reason}). Try a different screenshot or enter the breakdown manually.",
        )

    candidates = payload.get("candidates") or []
    if not candidates:
        raise HTTPException(
            status_code=502,
            detail="Gemini returned no response. Try again or enter the breakdown manually.",
        )

    finish_reason = candidates[0].get("finishReason")
    parts = candidates[0].get("content", {}).get("parts", [])
    raw = "".join(p.get("text", "") for p in parts).strip()

    if not raw:
        raise HTTPException(
            status_code=502,
            detail=f"Gemini returned an empty response (finishReason: {finish_reason}). "
            f"Try again or enter the breakdown manually.",
        )

    try:
        cleaned = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=502,
            detail=f"Gemini's response wasn't valid JSON: {raw[:300]}",
        )

    if not data.get("found"):
        raise HTTPException(
            status_code=404,
            detail=f"Couldn't find a row for '{page_name}' in that screenshot. "
            f"Double check the screenshot or enter the breakdown manually.",
        )

    data["screenshot_path"] = saved_name
    return data
