# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

"智慧管理中心" (Echo) — a single-user Flask web app combining personal knowledge base, kiwi-sales order management, overtime tracking, and expense accounting. Version v2.2.1, MIT license.

## Commands

### Run the app
```bash
python app.py          # starts on http://0.0.0.0:5001
```
Or on Windows: `start.bat` (sets UTF-8 encoding via `chcp 65001`, installs deps, runs app)

### Install dependencies
```bash
pip install -r requirements.txt
```

### Tests
```bash
python test_api.py     # integration smoke test — requires running server at localhost:5001
```
No pytest suite exists. When adding pytest: `python -m pytest path/to/test_file.py::test_name`

No linter configured. If adding one, prefer ruff/flake8/black.

## Architecture

**Single-file monolith** — the defining pattern of this project:

- **Backend**: `app.py` (~1532 lines) — all 38 routes, auth, DB init, domain logic in one file. No blueprints or modules.
- **Frontend**: `static/index.html` (~5811 lines) — all UI, routing, API calls in one HTML file. No SPA framework, no build step. Vanilla JS with `fetch()`.

### Key backend patterns
- SQLite via raw `sqlite3` (no ORM). `get_db()` stores connection on Flask's `g`; rows returned as `sqlite3.Row`.
- SQLite placeholder is `?` (not `%s`).
- `init_db()` is the schema updater — idempotent, uses `PRAGMA table_info` + `ALTER TABLE ADD COLUMN` for new columns. **Do NOT edit existing `CREATE TABLE` statements**; append `ALTER TABLE` blocks instead.
- `init_db()` only runs inside `if __name__ == '__main__'` — importing app does NOT create tables.
- `close_db` is registered via `@app.teardown_appcontext` (fixed in v2.2.0 — previously missing, caused DB lock errors).

### Key frontend patterns
- `API_URL = '/api'` constant, `getAuthHeaders()` helper for Bearer token.
- Frontend stores JWT token in `localStorage` under key `token`.
- `REPORT_PAGE_SIZE` constant (default 10) for sales-report pagination in `static/index.html`.

### Auth pattern
- JWT tokens (7-day expiry) via `pyjwt`, passwords hashed via `passlib.hash.pbkdf2_sha256`.
- `@login_required` decorator reads `Authorization: Bearer <token>`, sets `g.user_id`.
- All data tables carry `user_id` FK; queries filter by `g.user_id` for user isolation.

### Domain modules (all in app.py)
- Auth: `/api/auth/*`
- Articles/Knowledge base: `/api/articles/*`, `/api/categories/*`, `/api/tags`, `/api/stats`
- Kiwi sales: `/api/kiwi-sales/*`, `/api/kiwi-sales-report`, `/api/kiwi-sales/export`
- Overtime: `/api/overtime/*`, `/api/overtime/stats`
- Expenses: `/api/expenses/*`, `/api/expenses/stats`, `/api/expenses/export`
- Upload: `/api/upload`

## Conventions and Gotchas

- **Port is 5001** — NOT 5000.
- **CSV exports use GBK encoding** with UTF-8 BOM for Windows Excel compatibility. Content-Type is `text/csv; charset=gbk`. Do NOT switch to plain UTF-8 (causes mojibake in Excel).
- **SECRET_KEY is hardcoded** in `app.py`. For production, set via environment variable and update app.py to read `os.environ.get('SECRET_KEY')`.
- **Overtime duration calculation** has domain-specific rules:
  - Weekday overtime: starts from 19:00, end time range 19:00-23:59
  - Weekend overtime: 09:00-23:00, auto-deducts 12:00-14:00 lunch break (2 hours)
  - Same-day uniqueness constraint
- **Uploads**: saved to `static/uploads/`, filenames secured with `werkzeug.utils.secure_filename`. Allowed extensions: png, jpg, jpeg, gif, webp.
- **Default categories seeded** (技术, 生活, 学习, 工作) only when DB is empty.
- **`auto_start.bat` and `setup_autostart.ps1`** have stale hardcoded paths — update before use.
- **Helper scripts** (`list_tables.py`, `query_tables.py`, etc.) use relative DB paths — run from repo root.
- When adding features, prefer extracting code into modules (e.g., `app/auth.py`, `app/articles.py`) to keep diffs small and safe, though the current pattern is single-file.

## Design Docs

- `docs/ARCHITECTURE.md` — auth flow diagrams, module dependency charts, data flow
- `docs/PRD.md` — product requirements
- `docs/INTERACTION_DESIGN.md` — interaction design specs
- `Test_Team/` (gitignored) — 301 manual test cases across 5 modules

## Useful Search Terms

`init_db`, `generate_token`, `login_required`, `UPLOAD_FOLDER`, `REPORT_PAGE_SIZE`, `calculate_overtime_duration`, `getAuthHeaders`
