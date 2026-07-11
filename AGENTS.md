# AGENTS.md — Echo v2.5.7

## Architecture
- `app.py` (2145 lines): Flask monolith. Sections have `# ----` markers for grep. **Planned split into 11 files** (see `.mimocode/plans/1783756811019-kind-island.md`).
- `static/index.html` (~5995 lines): Vanilla JS SPA. `fetch()` → `/api`, Bearer JWT in `localStorage.token`.
- `knowledge_base.db`: SQLite, created by `init_db()` (only in `if __name__ == '__main__'`).

## Commands
```bash
pip install -r requirements.txt  # flask, flask-cors, pyjwt, passlib
python app.py                    # port 5001
python test_api.py               # smoke test, server must run on localhost:5001
```
- PowerShell: chain with `;`, not `&&`.

## Line Map (app.py) — grep markers to jump by line
| Section | Marker at | Grep command |
|---------|-----------|-------------|
| Imports + error handlers + cache | L1 | `Select-String -Path app.py -Pattern "def bad_request"` |
| DB + auth utils | L143 | `Select-String "# ---- DB"` |
| init_db (schema) | L230 | `Select-String "# ---- init_db"` |
| Auth (register/login/me) | L382 | `Select-String "# ---- Auth"` |
| Articles + cats + tags | L648 | `Select-String "# ---- Articles"` |
| Upload | L1013 | `Select-String "# ---- Upload"` |
| Kiwi sales | L1042 | `Select-String "# ---- Kiwi"` |
| Overtime | L1394 | `Select-String "# ---- Overtime"` |
| Expenses | L1719 | `Select-String "# ---- Expenses"` |

**Navigate**: `Select-String -Path app.py -Pattern "# ----"` lists all sections.

## SQLite
- Placeholder `?`, not `%s`. Rows → `sqlite3.Row`.
- **Never edit existing `CREATE TABLE`** in `init_db()`. Append `ALTER TABLE ADD COLUMN` guarded by `PRAGMA table_info`.
- Use `get_db()`; `close_db` via `@app.teardown_appcontext`.
- All tables carry `user_id`; `@login_required` filters by `g.user_id` (7-day JWT).

## CSV — **GBK encoding** (UTF-8 BOM). Content-Type `text/csv; charset=gbk`. Never UTF-8.

## Gotchas
- `SECRET_KEY` = `os.environ.get('SECRET_KEY') or os.urandom(32).hex()`. No hardcoded default.
- Default categories seeded only when DB empty (in init_db).
- `auto_start.bat` / `setup_autostart.ps1` have stale paths — update before use.
- `test_*.py` scripts are gitignored.

## Overtime Rules
- Weekday: start 19:00, end 19:00–23:59.
- Weekend: 08:300–23:59, deduct 12:00–14:00. Same-day unique.
- Monthly stats: 20th–20th period.

## Token-Saving Tips
- Read by line range, never full file: `Get-Content app.py | Select-Object -Index 322-546`
- Grep for function: `Select-String -Path app.py -Pattern "def login"`
- For route logic, jump via line map above — avoids reading 2069 lines.
- For schema changes, only read init_db (L170–321).
- **Never read full app.py** — always target the section you need.

## Bug Fix 经验教训（每次修bug后追加）
> **规则**: 每次修复bug后，必须在下方追加一条记录，格式为：`### [日期] 问题简述` → 根因 → 修复方法 → 预防规则。
> **作用**: 下次遇到类似问题时，先读此节，避免重蹈覆辙。

### 2026-07-08 CSS overflow 成对操作
- **现象**: 登录弹窗关闭后 body 无法滚动
- **根因**: `openLoginModal()` 设 `body.style.overflow = 'hidden'`，但 `closeLoginModal()` 未还原
- **修复**: `closeLoginModal()` 中加 `document.body.style.overflow = ''`
- **规则**: 所有 CSS `overflow = 'hidden'` **必须**配对 `overflow = ''` 还原

### 2026-07-08 SQLite 字符串比较不要转 int
- **现象**: `get_expenses_stats()` 1月份数据查不到
- **根因**: `substr(date,6,2)` 返回 `"01"`，但代码用 `int()` 转成 `1`，SQL 比较 `"01" = 1` 不匹配
- **修复**: 移除 `get_expenses_stats()` 中 `int()` 转换，参数保持字符串
- **规则**: SQLite 日期截取结果**永远保持字符串**，不要转 int

### 2026-07-08 PowerShell 不要用 &&
- **现象**: 运行 `pip install && python app.py` 报错
- **根因**: PowerShell 不支持 `&&`，这是 cmd 语法
- **修复**: 改用 `;` 分隔命令：`pip install -r requirements.txt; python app.py`
- **规则**: 所有 PowerShell 命令用 `;`，不用 `&&` 和 `||`

  ### 2026-07-09 escapeHtml() 括号未闭合导致全站 JS 崩溃
  **现象**: 修复 XSS 时 escapeHtml() 调用漏了闭合括号，登录后所有页面无功能
  **根因**: 批量 replace() 仅添加了开括号 ( 而忘记闭合括号 )
  **修复**: 3 个位置添加缺失的闭合括号
  **规则**: 批量修改 HTML/JS 时必须验证括号匹配

  ### 2026-07-09 PowerShell 传含中文 Python 脚本的正确方式
  **现象**: PowerShell 双引号中/Python单引号中转义:${} 被解析为变量
  **根因**: PowerShell 解析 ${} 为变量、单引号中转义冲突
  **修复**: 写入 .py 文件再执行，或使用 chr(39) 构造引号
   **规则**: 永远不要通过 PS 命令行传含中文和模板字符串的 Python 代码

### 2026-07-09 Flask 路由装饰器遗漏导致接口无法访问
- **现象**: 猕猴桃销售列表页数据无法加载，后端 `/api/kiwi-sales` 接口始终无响应
- **根因**: `get_kiwi_sales()` 函数上方缺少 `@app.route("/api/kiwi-sales", methods=["GET"])` 和 `@login_required` 装饰器
- **修复**: 在函数定义前补上两个装饰器
- **规则**: 新增或移动 Flask 路由函数时，**必须**检查 `@app.route()` + `@login_required` 装饰器是否完整；批量重构后运行一次 `test_api.py` 验证所有接口可达

### 2026-07-11 按钮放在 position:relative 容器内导致错位
- **现象**: 工作日报搜索栏的重置按钮位置异常，不在预期的对齐位置
- **根因**: 重置按钮放在 `.search-box`（`position:relative`）内部，而 `.search-box` 的 input 是 `width:100%`，按钮被挤到下方
- **修复**: 将按钮移出 `.search-box`，作为 `.toolbar`（`display:flex`）的直接子元素
- **规则**: 新增按钮/控件时，检查父容器是否 `position:relative`；flex 布局中子元素**必须是 flex 容器的直接子元素**才能正确对齐

### 2026-07-11 敏感文件写入后必须限制权限
- **现象**: `.secret_key` 文件生成后任何系统用户可读取 JWT 签名密钥
- **根因**: `open('file', 'w')` 写入后未调用 `os.chmod`，使用默认权限（通常 0o644）
- **修复**: 写入后立即 `os.chmod(file, 0o600)`
- **规则**: 生成密钥/token/凭据文件后**必须** `os.chmod(path, 0o600)` 限制仅所有者可读

### 2026-07-11 Flask 响应必须添加安全头
- **现象**: HTTP 响应缺少 `X-Content-Type-Options` 和 `X-Frame-Options`，存在 MIME 嗅探和点击劫持风险
- **根因**: `@app.after_request` 中未设置安全响应头
- **修复**: 在 `add_cache_headers` 中添加 `X-Content-Type-Options: nosniff` 和 `X-Frame-Options: DENY`
- **规则**: 所有 HTTP 响应**必须**包含 `X-Content-Type-Options: nosniff` 和 `X-Frame-Options: DENY`

### 2026-07-11 await await 双重等待
- **现象**: 修复 XSS 时批量替换引入了 `await await Promise.all(...)`，语法正确但语义冗余
- **根因**: 批量 replace 操作时未验证 JavaScript 语义
- **修复**: 移除多余的 `await`（3处：L5600/5633/5698）
- **规则**: 批量修改代码后必须验证语法和语义正确性

## 架构风险预警
### 并发安全
- 全局 `dict`（`login_attempts`, `_stats_cache` 等）在 `threaded=True` 下**必须加锁**，否则并发读写会崩溃
- `article.views += 1` 等自增操作需用 SQL 原子 `UPDATE`，不可用 Python 先读后写

### 输入校验
- 批量删除的 `ids` 列表**必须校验全为整数**，否则产生 SQL 语法错误
- 文件上传需校验 magic bytes，不能仅依赖 `content_type`

### 安全
- 前端所有来自后端的字符串拼入 `innerHTML` 前**必须 `escapeHtml()`**
- 错误消息**不要**直接用 `alert()`，应使用统一通知组件

### 错误处理
- 禁止 `except: pass` 静默吞异常，至少用 `logging.warning()` 记录

### 部署
- 生产环境必须设 `SECRET_KEY` 环境变量，否则重启后所有 JWT 失效
- Flask 内置服务器仅限开发，生产用 gunicorn

### 数据迁移
- `ALTER TABLE` 迁移无版本号管理，多人协作时易冲突，后续应引入迁移版本追踪

## Commit & Versioning
- User-facing changes → update `VERSION.md`, back up `knowledge_base.db` before schema changes.

## 语言偏好
- **所有回复使用中文**，包括代码注释、错误说明、进度更新。

## Obsidian 知识库同步
- 文档位于 `docs/` 目录，使用 Obsidian 管理
- **代码变更时**：更新 `docs/modules/` 对应模块文档
- **Bug 修复后**：在 `docs/bugs/` 记录根因和修复
- **架构变更时**：更新 `docs/architecture/`
- **新功能**：更新对应模块文档的 API 接口表
- **配置变更**：更新 `docs/guides/` 相关文档
- 使用 `[[]]` 链接相关文档，保持知识库互联

## 每次改动完成后的流程
1. **同步知识库文档** - 更新 `docs/modules/` 对应文档
2. **更新 README.md** - 同步功能特性和版本说明
3. **升级版本号** - 更新 `VERSION.md` 和 `README.md` 中的版本号
