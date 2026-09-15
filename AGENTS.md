# AGENTS.md — Echo (智慧管理中心)

## Quick Start
```bash
pip install -r requirements.txt
python app.py          # http://localhost:5001
```

## Commands
```bash
pytest -m p0 -q              # P0 冒烟（需服务运行，最快反馈）
pytest tests/test_overtime.py -q  # 单模块回归
pytest -q --cov --cov-report=term-missing  # 全量 + 覆盖率
```

## Critical Constraints (violation = crash)
- **Port 5001** (not 5000)
- **SQLite placeholders: `?`** (not `%s`)
- **CSV exports**: GBK encoding + UTF-8 BOM, `Content-Type: text/csv; charset=gbk`
- **`init_db()`**: only `ALTER TABLE ADD COLUMN`; never modify existing `CREATE TABLE`; only runs when `__main__`
- **JWT**: 7-day expiry; routes use `@login_required`; all queries must include `WHERE user_id=?`
- **Uploads**: stored in `static/uploads/`, whitelist: png/jpg/jpeg/gif/webp

## Architecture
- **Backend**: `app.py` → Blueprint routes in `routes/` (auth, articles, kiwi_sales, overtime, expenses)
- **Frontend**: `static/index.html` — single-file SPA, `API_URL='/api'`, token in `localStorage` key `token`
- **Database**: SQLite (WAL mode), `knowledge_base.db`
- **DB access**: `get_db()` stored in Flask `g`, returns `sqlite3.Row`
- **Auth**: `auth_utils.py` — `generate_token()`, `login_required` decorator, token_version for revocation

## Testing
- Tests hit the **live server** (integration via `requests` library, not Flask test client)
- Shared fixtures in `tests/conftest.py`: `auth`, `client`, `temp_article`, `temp_expense`, `temp_overtime`, `temp_kiwi`
- Markers: `p0`, `p1`, `p2`, `smoke`, `regression`, `security`, `performance`, `fault_tolerance`
- Deprecated: root-level `smoke_test.py` (migrated to `tests/test_smoke.py`)

## Business Rules
- **Overtime**: weekday 19:00–23:59; weekend 09:00–23:00 with 2h lunch break (12:00–14:00); unique per day per user
- **Expenses categories**: whitelist in `config.py` `EXPENSE_CATEGORIES` (17 categories)

## Key Files
| File | Purpose |
|------|---------|
| `app.py` | Flask app factory, Prometheus metrics, error handlers |
| `config.py` | Constants: DB path, upload config, rate limits, expense categories |
| `db.py` | `get_db()`, `init_db()`, monitored DB wrappers |
| `auth_utils.py` | JWT generation, `login_required` decorator |
| `routes/` | Blueprint modules (5 blueprints) |
| `static/index.html` | Entire frontend SPA (~6000 lines) |
| `tests/conftest.py` | Shared test fixtures |
| `CLAUDE.md` | Detailed project constraints |

## Gotchas
- `init_db()` is **only** for schema migration (ALTER TABLE ADD COLUMN), not full setup — table creation uses `CREATE TABLE IF NOT EXISTS`
- SECRET_KEY persisted to `.secret_key` file; regenerated if missing
- Prometheus metrics at `/metrics` endpoint
- CORS allows localhost:5001, localhost:5173
- 16MB upload limit enforced
