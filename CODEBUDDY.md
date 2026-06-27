# CODEBUDDY.md

This file provides guidance to CodeBuddy Code when working with code in this repository.

## Project

"智慧管理中心" (Smart Management Center, also branded "Echo") — a Flask + SQLite single-user app combining a personal knowledge base, kiwi-sales order management, overtime tracking, and expense accounting. Frontend is a single static HTML file; backend is a single `app.py`. Current version is tracked in `VERSION.md`.

## Commands

```bash
# Install deps (flask, flask-cors, pyjwt, passlib)
pip install -r requirements.txt

# Run the app — listens on http://localhost:5001 (NOT 5000)
python app.py

# Windows helpers (set console to UTF-8 via chcp 65001, then run app.py)
start.bat            # recommended — uses %~dp0, portable
auto_start.bat       # NOTE: has a stale hardcoded path (C:\Users\Administrator\Documents\trae_projects\test\knowledge_base) — fix before use

# Integration smoke test — REQUIRES a running server on :5001 (logs in as root/root123)
python test_api.py

# DB inspection / maintenance scripts (standalone, not pytest)
python check_db.py          # list users
python list_tables.py       # list sqlite tables
python query_tables.py      # dump table contents
python delete_students.py   # deletes *student* tables — no-op on knowledge_base.db (no such tables); legacy from sibling project

# No linter, no pytest suite, no CI is configured for this sub-project.
```

There is no build step — editing `static/index.html` or `app.py` takes effect on next reload.

## Architecture

### Single-file backend (`app.py`, ~1500 lines)
All routes and domain logic live in `app.py`. There are no blueprints or modules. Domains colocated in one file:
- **Auth** — `/api/auth/{register,login,me}` — JWT (7-day expiry), password hashing via `passlib.hash.pbkdf2_sha256`.
- **Articles** — `/api/articles*` — CRUD, search, favorite toggle, prev/next navigation, view counts, tags.
- **Categories** — `/api/categories` — per-user; seeded with defaults (技术/生活/学习/工作) only when DB is empty.
- **Uploads** — `/api/upload` — saves to `static/uploads/`, uses `werkzeug.utils.secure_filename`, allow-list `{png,jpg,jpeg,gif,webp}`.
- **Kiwi sales** — `/api/kiwi-sales*`, `/api/kiwi-sales-report`, `/api/kiwi-sales/export` — orders + grouped report.
- **Overtime** — `/api/overtime*`, `/api/overtime/stats` — duration auto-computed by `calculate_overtime_duration()`.
- **Expenses** — `/api/expenses*`, `/api/expenses/stats`, `/api/expenses/export`.

### DB lifecycle — important
- `init_db()` is called **only inside `if __name__ == '__main__'`** (app.py:1525). Importing `app` (e.g., from a test) does **not** create tables. Call `init_db()` explicitly if you import the app programmatically.
- Schema creation and migrations are inline in `init_db()`, using `PRAGMA table_info` + `ALTER TABLE ADD COLUMN` checks — idempotent. Add new columns by appending another `if 'col' not in columns: ALTER TABLE ...` block; do not edit the original `CREATE TABLE`.
- No ORM. Raw `sqlite3` via `get_db()` (stored on `g`), rows as `sqlite3.Row`. SQLite placeholder is `?`.
- Most tables carry a `user_id` FK; queries filter by `g.user_id` so data is user-scoped.

### Auth pattern
`@login_required` reads `Authorization: Bearer <token>`, verifies via `verify_token()`, and sets `g.user_id`. Apply it to any new endpoint that should be user-scoped. The frontend stores the token in `localStorage` under key `token` and sends it as `Authorization: Bearer <token>` (see `static/index.html:2062-2063`).

### Frontend (`static/index.html`, ~5700 lines)
No framework, no build. All UI, routing, and API calls are inline. Notable in-file constants:
- `REPORT_PAGE_SIZE` (default 10) — sales-report pagination page size.
- A `getAuthHeaders()` helper (index.html:2062) centralizes the Bearer-token header.

### CSV export convention
Exports (`/api/expenses/export`, `/api/kiwi-sales/export`) use **GBK encoding with a UTF-8 BOM** so Windows Excel renders Chinese correctly. Do not switch them to plain UTF-8 — Excel will show mojibake (this was a real regression fixed in v2.1.0, see `RELEASE_NOTES.md`). Content-Type is `text/csv; charset=gbk`.

## Configuration & gotchas

- **Port**: `5001` — differs from the sibling `student_management/` project (5000) in the same workspace. Don't confuse them.
- **Host**: `0.0.0.0` (LAN-accessible). `debug=False` in `app.run`.
- **SECRET_KEY** is hardcoded in `app.py:24` — known tech debt; externalize to an env var before any real deployment.
- **CORS** is enabled globally (`CORS(app)`).
- **`knowledge_base.db`** is gitignored. Back it up before destructive schema changes.
- **`static/uploads/`** is gitignored — user-uploaded images live here; back up if needed.
- **`auto_start.bat`** references an outdated path — update the `cd /d` line to the current repo location before relying on it.
- Helper scripts (`check_db.py`, `check_js.py`, `list_tables.py`, `query_tables.py`, `delete_students.py`) use a **relative** DB path — run them from the repo root or they will create/read a stray `knowledge_base.db` in the CWD. Prefer passing `os.path.join(os.path.dirname(__file__), 'knowledge_base.db')` if editing them.

## Where to look

- **Entrypoint & routes**: `app.py` — grep for `@app.route` and `init_db`.
- **Frontend**: `static/index.html` (single file).
- **Design docs** (authoritative for intent): `docs/ARCHITECTURE.md`, `docs/PRD.md`, `docs/INTERACTION_DESIGN.md`.
- **Version history**: `VERSION.md`, `RELEASE_NOTES.md`.
- **Prototype markup**: `prototype.html`.
- **Existing AI-assistant guidance** (overlaps with this file): `.github/copilot-instructions.md`.
