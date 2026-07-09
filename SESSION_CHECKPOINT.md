# 会话存档 — 2026-07-08

## 当前进度

### 已完成
1. **AGENTS.md 优化**（中文化 + 行号映射 + 分段导航 + Token节省技巧）
   - 路径: `E:\trae_projects\knowledge_base\AGENTS.md`
   - 内容: 62行，含Line Map表、Bug经验教训区、语言偏好
   
2. **app.py 分段标记**（8个`# ---- Section ----`标记）
   - 位置: L82, L170, L322, L547, L953, L982, L1375, L1676
   - 用途: grep导航，避免全文件读取

3. **全栈性能审计报告**
   - 路径: `E:\trae_projects\knowledge_base\PERFORMANCE_AUDIT.md`
   - 内容: 16个问题（5个🔴高优、6个🟡中优、5个🟢低优）+ 修复方案 + 执行顺序

### 待执行（按优先级）

| 优先级 | 任务 | 预估时间 |
|--------|------|---------|
| 🔴 P0 | SECRET_KEY持久化 | 5分钟 |
| 🔴 P0 | 缓存加线程锁 | 5分钟 |
| 🔴 P0 | login_attempts线程安全+定期清理 | 15分钟 |
| 🟢 P1 | 健康检查端点 /api/health | 5分钟 |
| 🟢 P1 | 请求耗时监控中间件 | 10分钟 |
| 🟡 P2 | kiwi-sales GET无分页 → 加clamp_pagination | 10分钟 |
| 🟡 P2 | CSV流式导出防OOM | 30分钟 |
| 🟡 P2 | locustfile增强断言 | 15分钟 |
| 🟡 P3 | 前端HTML/CSS/JS拆分 | 1-2小时 |

## 项目关键信息

- **端口**: 5001（不是5000）
- **数据库**: knowledge_base.db（SQLite WAL模式）
- **前端**: static/index.html（6038行单文件SPA）
- **Python**: 用`;`不用`&&`
- **CSV编码**: GBK（不是UTF-8）
- **回复语言**: 中文

## 文件结构
```
app.py              → 2069行 Flask单体（含分段标记）
static/index.html   → 6038行 前端SPA
knowledge_base.db   → SQLite数据库
AGENTS.md           → 本会话优化后的agent指引
PERFORMANCE_AUDIT.md → 审计报告（待实施）
locustfile.py       → 已有Locust性能测试脚本
requirements.txt    → flask/cors/pyjwt/passlib/compress
```

## Bug经验教训（已记录在AGENTS.md）
1. CSS overflow必须成对操作（hidden ↔ ''）
2. SQLite字符串比较不转int（substr返回"01"）
3. PowerShell用`;`不用`&&`

## 下次上班继续

打开项目后，建议从🔴P0开始逐个修复。每个修完后，在AGENTS.md的Bug经验教训区追加条目。

## 金句
- 每次读app.py用grep定位，别全读（2069行≈15K token）
- 修bug后必须记录经验教训，下次不犯同样错误
- 所有回复用中文
