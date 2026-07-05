# Repository Guidelines

## Project Structure & Module Organization

This is a **single-file monolith** Flask web app (智慧管理中心/Echo, v2.3.0).

- `app.py` — Backend entrypoint: all REST routes, auth, DB init, and domain logic (~1630 lines). No blueprints or modules.
- `static/index.html` — Complete frontend: UI, client-side routing, and API calls (~5940 lines). Vanilla JS, no build step.
- `static/uploads/` — User-uploaded images (gitignored).
- `knowledge_base.db` — SQLite database (gitignored). Schema managed by `init_db()`.
- `docs/` — Architecture diagrams, PRD, interaction design specs, Playwright setup.
- `Test_Team/` — Manual test cases and PRD documents (gitignored).
- `requirements.txt` — Python dependencies: `flask`, `flask-cors`, `pyjwt`, `passlib`.

## Build, Test, and Development Commands

```bash
pip install -r requirements.txt   # Install dependencies
python app.py                     # Start dev server on http://0.0.0.0:5001
start.bat                         # Windows quick-start (sets UTF-8, installs deps, runs app)
python test_api.py                # Integration smoke test (requires running server)
```

- **Port is 5001**, not 5000.
- **Windows PowerShell**: use `;` not `&&` to chain commands (e.g., `python app.py; if ($?) { ... }`).
- No linter or formatter is configured. Prefer `ruff` / `flake8` / `black` if adding one.
- CI exists: `.github/workflows/playwright.yml` for Playwright E2E tests.

## Coding Style & Naming Conventions

- **Python**: 4-space indentation, PEP 8 style.
- **Frontend**: Vanilla JS with `fetch()`. API calls use `API_URL = '/api'` and `getAuthHeaders()` for Bearer tokens.
- **SQLite**: Raw `sqlite3` (no ORM). Placeholder is `?`, not `%s`. Rows returned as `sqlite3.Row`.
- **Schema changes**: Do NOT edit existing `CREATE TABLE` statements in `init_db()`. Append `ALTER TABLE` blocks instead (idempotent).
- **CSV exports**: Use GBK encoding (no BOM) for Windows Excel compatibility. Do NOT switch to plain UTF-8.

## Testing Guidelines

- `test_api.py` is an integration smoke test. Start the server at `localhost:5001` before running it.
- No pytest suite exists. If adding tests, use `python -m pytest path/to/test_file.py::test_name`.
- Helper scripts (`check_db.py`, `list_tables.py`, `query_tables.py`) are for manual DB inspection — run from repo root.
- CI: `.github/workflows/playwright.yml` runs Playwright E2E tests on push/PR.

## Commit & Pull Request Guidelines

Commit messages follow two patterns:

- **Version bumps**: `v2.2.0: UI全面美化、工作日报文案适配、数据库连接泄漏修复`
- **Imperative**: `Bump version to v2.2.1`, `Remove CODEBUDDY.md from repo and ignore it`

When submitting PRs:

- Include a description of changes and affected modules.
- Update `VERSION.md` for user-facing changes.
- Back up `knowledge_base.db` before schema-altering changes.

## Architecture Notes

- **Auth**: JWT tokens (7-day expiry) via `pyjwt`. The `@login_required` decorator reads `Authorization: Bearer <token>` and sets `g.user_id`. All data queries filter by `g.user_id`.
- **Overtime rules**: Weekday starts from 19:00; weekend 09:00–23:00 with 2-hour lunch deduction. Same-day uniqueness enforced. Monthly stats use 20th-to-20th period (e.g., July = June 20 – July 20).
- **Secret handling**: `SECRET_KEY` is read from `os.environ` with random fallback. Do not hardcode.
- **File uploads**: Saved to `static/uploads/`, sanitized via `werkzeug.utils.secure_filename`. Allowed: png, jpg, jpeg, gif, webp. 16MB limit.
- **DB connection lifecycle**: `close_db` registered via `@app.teardown_appcontext`. Do not manually open/close connections outside `get_db()`.
- **Domain modules** (all in `app.py`): Auth, Articles/Knowledge base, Kiwi sales, Overtime, Expenses, Upload.
