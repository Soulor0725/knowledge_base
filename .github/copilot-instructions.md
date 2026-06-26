# Copilot instructions for this repository

This file gives targeted guidance to future Copilot sessions working on this repo.

## 1) Build / run / test / lint (project-specific)
- Install Python deps: `python -m pip install -r requirements.txt` (uses the repo-root requirements.txt).
- Run locally (development):
  - Quick start (Windows): double-click `start.bat` or run `auto_start.bat` to set encoding and run the app.
  - Direct: `python app.py` (app listens on port 5001 by default). The app prints the local URL on startup.
- Run in production: use a WSGI server (gunicorn/uvicorn) behind a reverse proxy. Update `app.config['SECRET_KEY']` via environment variable before exposing to the public.
- Database: the app auto-creates an SQLite DB file `knowledge_base.db` at the repo root on first run. Back up before destructive operations.
- Tests:
  - There is a small integration-style script `test_api.py` that expects a running server at http://localhost:5001. Run it with `python test_api.py` after starting the app.
  - If pytest is added later, run a single test using: `python -m pytest path/to/test_file.py::test_name`.
- Linting: no linter or lint scripts are configured. Add tools (flake8/ruff/black) and CI if desired.

## 2) High-level architecture (big picture)
- Entrypoint: `app.py` — a single-file Flask application that both serves JSON API endpoints under `/api/*` and static front-end assets from `static/`.
- Frontend: static files are under `static/` (key file: `static/index.html`). The frontend is not a separate build; editing static files directly changes site behavior.
- Modules (all implemented in `app.py`):
  - User auth (JWT tokens)
  - Articles/knowledge base (CRUD, search, tags, categories)
  - Categories API
  - File uploads (saved to `static/uploads/`)
  - Kiwi sales (orders CRUD and reporting)
  - Overtime & expenses modules (time tracking, accounting endpoints)
  - Reporting/stats endpoints
- Persistence: SQLite (`knowledge_base.db`) used directly via sqlite3 (no ORM). Schema creation and migrations are handled at runtime inside `init_db()`.
- Static uploads: saved to `static/uploads/`; `UPLOAD_FOLDER` is relative to repo root.
- Platform: repository includes Windows helper scripts (`start.bat`, `auto_start.bat`, `setup_autostart.ps1`) — recommended when running on Windows.

## 3) Key repository conventions and gotchas
- Secret management: `app.config['SECRET_KEY']` is set inline in `app.py`. For deployment, set a secure secret via environment variable and replace the hardcoded string.
- Port & host: default host/port are set in `app.py` (host '0.0.0.0', port 5001). Change there for containerization or CI tests.
- DB lifecycle & migrations: `init_db()` runs on startup and creates/ALTERs tables as needed. It is idempotent but inspect schema changes before running on production data.
- Static+backend coupling: front-end behavior (UI, pagination constants, reporting page size) is controlled in `static/index.html`. Small changes to that file affect the site without touching Python code.
- Tests: `test_api.py` is not a unit test — it's an integration smoke-test script that issues HTTP requests to a running server. Start server first.
- Multiple functional domains live in one file: `app.py` contains many logically separate domains (auth, articles, sales, overtime, expenses). When modifying, favor organizing new code into modules if it grows.
- Uploads and paths: uploaded files are saved under `static/uploads/` and served by Flask's static route — ensure write permissions and back up uploads if needed.
- Windows specifics: PowerShell/Batch scripts assume UTF-8 console encoding adjustments (chcp 65001).

## 4) Where to look (quick pointers)
- App entrypoint and runtime behavior: `app.py` (search for `init_db`, `if __name__ == '__main__'`, and route decorators).
- Fast checks and examples: `test_api.py` (integration test script)
- Docs: `docs/ARCHITECTURE.md`, `docs/PRD.md`, `RELEASE_NOTES.md`
- Frontend/UI: `static/index.html`, `static/` (uploads, assets)
- Setup/start scripts: `start.bat`, `auto_start.bat`, `setup_autostart.ps1`
- Sample or prototype data: `prototype.html`

## 5) AI / Assistant integration notes
- No other assistant config files were found (CLAUDE.md, AGENTS.md, .cursorrules, .windsurfrules, CONVENTIONS.md). No special assistant tooling is configured.
- When adding tests/CI, include runnable commands (e.g., `pytest`, `make test`) so Copilot can run them.

---

Suggested improvements (actionable):
- Move long app logic out of `app.py` into package modules (e.g., `app/auth.py`, `app/articles.py`) to make automated code edits safer.
- Replace the hardcoded SECRET_KEY with reading from an environment variable (e.g., `os.environ.get('SECRET_KEY')`) and document required env vars in README.
- Add a minimal pytest-based test suite and a GitHub Actions workflow that runs the tests on push/PR.

Created/updated: `.github/copilot-instructions.md` — updated with explicit run/test instructions, architecture summary, and repository-specific conventions.

Would you like help: 
- moving app sections into modules, or
- creating a small pytest smoke test and a GitHub Actions workflow to run it?
