# 智慧管理中心 (Echo) — 单用户 Flask + 原生JS SPA，SQLite

## 命令
python app.py              # :5001
pip install -r requirements.txt
pytest -m p0 -q            # P0 smoke（需服务运行中，最快反馈）
pytest tests/test_overtime.py -q  # 单模块回归
pytest -q --cov --cov-report=term-missing  # 全量 + 覆盖率（发版前）

## 关键约束（违反则故障）
- 端口 5001（非 5000）
- SQLite 占位符 ?（非 %s）
- CSV 导出必须 GBK + UTF-8 BOM，Content-Type: text/csv; charset=gbk
- init_db() 只接受 ALTER TABLE ADD COLUMN，禁止改已有 CREATE TABLE；仅 __main__ 时运行
- JWT 7天过期；路由 @login_required；所有查询必加 WHERE user_id=?
- 上传文件存 static/uploads/，扩展名白名单 png/jpg/jpeg/gif/webp

## 业务规则
- 加班计算：工作日 19:00-23:59 起算；周末 09:00-23:00 自动扣午休 2h（12:00-14:00）；同日唯一约束

## 前后端入口
- 后端 app.py（单文件 38 路由，get_db() 存 g，rows = sqlite3.Row）
- 前端 static/index.html（单文件 SPA，API_URL='/api'，token 存 localStorage key=token，REPORT_PAGE_SIZE=10）

## 搜索入口
init_db, generate_token, login_required, UPLOAD_FOLDER, REPORT_PAGE_SIZE, calculate_overtime_duration, getAuthHeaders

## 设计文档
- `docs/BUG_FIX_LESSONS.md` — Bug 修复经验沉淀（v2.1→v2.5.4 全部修复）
- `docs/TOKEN_OPTIMIZATION.md` — Claude Code token 优化指南（CLAUDE.md 瘦身、提示词规范、工具调度、工作流瘦身）
- `docs/TEST_TOKEN_OPTIMIZATION.md` — 测试架构师 token 优化（测试文件架构、测试提示词模板、调试循环优化、手工用例管理）
- `docs/TEST_OPTIMIZATION_MASTER.md` — 测试优化权威指南（资产清理、架构重构、配置标准化、覆盖度补齐、执行策略、UI测试、数据工厂、CI集成）
- `docs/ARCHITECTURE.md` — 架构图集
- `docs/PRD.md` — 产品需求
- `docs/INTERACTION_DESIGN.md` — 交互设计
