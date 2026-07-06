# AGENTS.md — 智慧管理中心 (Echo) v2.5.1

## Architecture

**Single-file monolith Flask app**. All in `app.py` (~1476 lines): REST routes, auth, DB init, 4 domain modules. No blueprints or packages.

- `static/index.html` (~5676 lines) — Vanilla JS SPA, no build step. `fetch()` to `/api`, `getAuthHeaders()` for Bearer token, JWT in `localStorage.token`.
- `knowledge_base.db` — SQLite, auto-created by `init_db()`. Runs only inside `if __name__ == '__main__'` (importing app does NOT create tables).

## Commands

```bash
pip install -r requirements.txt   # deps: flask, flask-cors, pyjwt, passlib
python app.py                     # starts on http://0.0.0.0:5001
start.bat                         # Windows quick-start (chcp 65001, install deps, run)
python test_api.py                # smoke test — needs server running on localhost:5001
```

- **Port is 5001**, not 5000.
- **PowerShell**: `;` not `&&` to chain (e.g., `python app.py; if ($?) { ... }`).
- No linter/formatter configured. Prefer `ruff` / `black` if adding one.

## SQLite Rules

- Placeholder is `?`, not `%s`. Rows returned as `sqlite3.Row`.
- **Never edit existing `CREATE TABLE`** in `init_db()`. Append `ALTER TABLE ADD COLUMN` blocks (idempotent, guarded by `PRAGMA table_info`).
- `close_db` registered via `@app.teardown_appcontext` — use `get_db()` everywhere.
- All tables carry `user_id` FK; queries filter by `g.user_id` (enforced by `@login_required` which reads `Authorization: Bearer <token>`, 7‑day JWT expiry).

## CSV Exports

**GBK encoding** (UTF‑8 BOM) for Windows Excel compatibility. Content-Type `text/csv; charset=gbk`. Do NOT switch to plain UTF-8.

## Domain API Prefixes

| Module | Routes |
|--------|--------|
| Auth | `/api/auth/*` |
| Articles | `/api/articles/*`, `/api/categories/*`, `/api/tags`, `/api/stats` |
| Kiwi sales | `/api/kiwi-sales/*`, `/api/kiwi-sales/export` |
| Overtime | `/api/overtime/*`, `/api/overtime/stats` |
| Expenses | `/api/expenses/*`, `/api/expenses/stats`, `/api/expenses/export` |
| Upload | `/api/upload` (→ `static/uploads/`, 16 MB limit, `werkzeug.utils.secure_filename`) |

## Overtime Rules (domain-specific)

- **Weekday**: start 19:00, end 19:00‑23:59.
- **Weekend**: 09:00‑23:00, auto‑deduct 12:00‑14:00 (2 h lunch). Same‑day unique.
- Monthly stats use **20th‑to‑20th** period (e.g., July = June 20 → July 20).

## Gotchas

- `SECRET_KEY` = `os.environ.get('SECRET_KEY') or os.urandom(32).hex()`. No hardcoded default. Set env var for production.
- Default categories seeded (`技术`, `生活`, `学习`, `工作`) only when DB empty.
- `auto_start.bat` and `setup_autostart.ps1` contain stale hardcoded paths — update before use.
- `test_*.py` scripts (`test_api.py`, `check_js.py`, `test_sql.py`) are **gitignored** — won't appear in repo.
- CI: `.github/workflows/playwright.yml` runs Playwright E2E on push/PR to `main`.

## Commit & Versioning

- For user-facing changes, update `VERSION.md` and back up `knowledge_base.db` before schema-altering changes.
