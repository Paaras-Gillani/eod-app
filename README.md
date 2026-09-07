# EOD Reports

Internal end-of-day reporting tool. Staff pick a gaming page, enter the
redeem counts manually, upload a screenshot of the admin dashboard, and the
AI fills in the deposit/redeem breakdown for review before saving.

## Setup

```bash
cd eod-app
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# edit .env: set SESSION_SECRET and GEMINI_API_KEY
```

### Getting a free Gemini API key

1. Go to https://aistudio.google.com/apikey
2. Sign in with a Google account and click "Create API key" — no credit card needed
3. Paste it into `.env` as `GEMINI_API_KEY`

The app uses `gemini-3.5-flash` by default, which is on Google's free tier
as of July 2026 (daily request quota, no billing required). Google renames
and retires free-tier models fairly often — if you hit a "model no longer
available" error, check https://ai.google.dev/gemini-api/docs/pricing for
the current free-tier model name and update `GEMINI_MODEL` in `.env`.

## Create your first login

There's no public sign-up page on purpose. Create accounts from the server:

```bash
python create_user.py
```

Run it once per staff member (and at least one `admin` for yourself).

## Run it

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Visit http://localhost:8000 — the SQLite database (`data/eod.db`) and the
7 pages (Golden Adventure, Lucky Penny, Sapphire, Lightning Slots, Fishable,
Loot, Jazzy Danny's) are created automatically on first run.

## Deploying for real use

- Put it behind a real domain + HTTPS (e.g. Caddy or nginx as a reverse
  proxy in front of uvicorn, or run with `--host 0.0.0.0` behind your
  existing infra).
- Run with a process manager so it survives reboots/crashes, e.g.:
  `uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2` under
  systemd, pm2, or supervisord.
- `data/eod.db` and `uploads/` are the only stateful folders — back them up.
- Change `SESSION_SECRET` to a real random value in production (see
  `.env.example` for how to generate one) — don't use the dev default.

## How the screenshot extraction works

The whole dashboard screenshot (all pages, all columns) is uploaded once per
EOD. It's sent to Google's Gemini API (free tier), with a prompt telling it
which page name to look for in that screenshot, and asking it to return just
that row as JSON
(deposit breakdown by method, redeem breakdown by method, redeem paid
amount, redeem pending amount, grand total deposit). The extracted numbers
are shown in editable tables — nothing is saved until a human reviews and
hits "Save EOD," so a misread screenshot never silently goes into the
record.

If extraction fails or the page isn't found in the screenshot, staff can
just type the breakdown in manually — the "+ Add method" button works
without ever touching the AI.

## Adding / renaming pages later

Right now pages are seeded once from `DEFAULT_PAGES` in `app/database.py`
on first run. To add or rename a page after that, either:
- edit the `pages` table directly with a SQLite client, or
- ask me to add a small admin screen for it (a few more routes/template —
  happy to build that next if you want it).

## Project layout

```
app/
  main.py           FastAPI app, page routes, startup
  database.py        SQLite schema + seed data
  security.py         password hashing (stdlib, no compiled deps)
  deps.py              login/session helpers
  routers/
    auth.py            login/logout
    pages.py           GET /api/pages
    eod.py              POST/GET /api/eod (save + history + detail)
    vision.py           POST /api/vision/extract (Gemini API call)
static/
  css/style.css
  js/eod_form.js       screenshot upload, editable breakdown tables, save
templates/             server-rendered page shells (data loads via JS)
create_user.py         CLI to create staff/admin logins
```
