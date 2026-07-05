# Copilot instructions for this repository

This file gives targeted guidance to future Copilot sessions working on this repo. It incorporates the README and docs and focuses on concrete, actionable commands and repository-specific conventions.

## 1) Build / run / test / lint (project-specific)

- Install dependencies (repo root):
  - python -m pip install -r requirements.txt

- Run (development):
  - Direct (recommended for quick edits):
    - Windows (cmd): set SECRET_KEY=your_secret_here & python app.py
    - PowerShell: $env:SECRET_KEY='your_secret_here'; python app.py
    - Or: python app.py  # app.py reads SECRET_KEY from app.config — replace with env for production
  - Quick start (Windows): double-click start.bat or run auto_start.bat (these set UTF-8 & start the app).

- Run in production:
  - Serve via a WSGI server (gunicorn/uvicorn) behind a reverse proxy. Ensure SECRET_KEY is provided via environment variable.

- Database:
  - SQLite file: knowledge_base.db (repo root). init_db() will create/ALTER tables on startup. Backup before destructive changes.

- Tests:
  - Integration smoke test: start the server (http://localhost:5001) then run:
    - python test_api.py
  - (No pytest suite currently) If pytest is later added, run a single test with:
    - python -m pytest path/to/test_file.py::test_name

- Linting:
  - No linter or lint scripts configured. If adding linting, prefer ruff/flake8/black. Add commands to CI and to this doc when present.

## 2) High-level architecture (big picture)

- Entrypoint: app.py — a single-file Flask app that serves:
  - JSON REST endpoints under /api/*
  - Static site from static/ (index.html + assets)

- Major domains (all implemented inside app.py):
  - Authentication (JWT)
  - Articles / Knowledge base (CRUD, drafts, favorites, search)
  - Categories and tags
  - File uploads (static/uploads/)
  - Kiwi sales (orders, CSV export, reporting)
  - Overtime / Expenses (time/expense records)
  - Reporting & export endpoints

- Persistence & runtime behavior:
  - SQLite used directly via sqlite3 (no ORM). init_db() creates tables and runs simple ALTERs if columns are missing — treat it as the canonical schema-updater. It's idempotent but inspect SQL before running against production DB.
  - UPLOAD_FOLDER = static/uploads; file names are secured with werkzeug.utils.secure_filename.
  - CSV exports are encoded for Excel compatibility (GBK) in some endpoints — tests or exports should account for encoding.

- Authentication:
  - JWT tokens issued by generate_token() and expected in Authorization: Bearer <token> headers.
  - Use the login_required decorator for protected endpoints.

- Frontend coupling:
  - Many UI behaviors and constants live in static/index.html (e.g., REPORT_PAGE_SIZE, pagination defaults). Changing UI behavior often requires editing static files rather than Python code.

## 3) Key repository conventions and gotchas (targeted)

- Secret handling: app.config['SECRET_KEY'] is hardcoded in app.py. Do not commit secrets. For deployments, set SECRET_KEY via environment variable and update app.py to read it from os.environ.

- Database lifecycle & schema changes:
  - init_db() runs at startup and will create missing tables and add missing columns. Still: backup knowledge_base.db before making schema changes or running migrations on production data.

- Single-file app pattern:
  - app.py contains multiple logical modules. When adding features, prefer extracting code into modules (e.g., app/auth.py, app/articles.py) to keep single-change diffs small and safe.

- Authorization header:
  - Authorization token is expected as 'Authorization: Bearer <token>'. login_required strips the 'Bearer ' prefix.

- File uploads & serving:
  - Uploaded files are saved to static/uploads/ and served by Flask's static route. Ensure correct filesystem permissions.

- Exports & encoding:
  - CSV export endpoints target Excel compatibility and may use GBK/encoded output. Tests that assert CSV content should be aware of encoding.

- Tests:
  - test_api.py is an integration smoke test that assumes a running server at localhost:5001. It does not run the server itself.

- Windows-first helpers:
  - start.bat, auto_start.bat, and setup_autostart.ps1 exist and configure UTF-8 console encoding (chcp 65001). Use them when working on Windows to avoid encoding issues.

## 4) Where to look (quick pointers for Copilot)

- Primary files to inspect first:
  - app.py (entrypoint + all REST routes and init_db)
  - static/index.html (UI behavior, constants)
  - test_api.py (integration smoke test)
  - docs/ARCHITECTURE.md, docs/PRD.md, docs/INTERACTION_DESIGN.md — product and design context

- Helpful searches:
  - Search for `init_db`, `generate_token`, `login_required`, `UPLOAD_FOLDER`, `REPORT_PAGE_SIZE` to find behavior touching DB, auth, uploads, and UI paging.

- Tools available in environment: git, curl. Running commands will be Windows-style (backslashes in paths).

## 5) AI / Assistant integration notes

- Existing assistant configs: none found (CLAUDE.md, AGENTS.md, .cursorrules, .windsurfrules, CONVENTIONS.md are absent). This doc should be the canonical Copilot guidance for this repo.

- When making changes that affect runtime (port, DB schema, SECRET_KEY), include a short verification step (start server & run a single endpoint check with curl or python requests) so Copilot sessions can validate behavior.

---

Actionable suggestions (for maintainers; Copilot can help implement these):
- Move large logical sections out of app.py into modules (app/auth.py, app/articles.py, app/kiwi_sales.py). This makes automated edits and tests safer.
- Replace inline SECRET_KEY with os.environ.get('SECRET_KEY') and document required env vars in README and CI.
- Add a minimal pytest-based test suite and a GitHub Actions workflow (CI) to run the tests on push/PR. Include a small fixture that spins up the app or uses the integration script pattern.

Created/updated: `.github/copilot-instructions.md` — consolidated README/docs info, added explicit run/test instructions, and highlighted repo-specific conventions for future Copilot sessions.

Would you like me to:
- extract app.py into smaller modules (I can create a safe refactor plan), or
- add a minimal pytest smoke test and a GitHub Actions workflow that runs it?

> Playwright configuration: a GitHub Actions workflow was added at .github/workflows/playwright.yml and local setup instructions at docs/PLAYWRIGHT_SETUP.md.
