# 系统架构

## 整体架构

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend (SPA)                        │
│              static/index.html (6000+ 行)                │
│         Vanilla JS + EasyMDE + highlight.js              │
└─────────────────────────────────────────────────────────┘
                           │
                           │ REST API (JSON)
                           ▼
┌─────────────────────────────────────────────────────────┐
│                    Backend (Flask)                        │
│         app.py (入口) + routes/ (路由模块)                │
├─────────────────────────────────────────────────────────┤
│  routes/auth.py      │ 认证模块 (185行)                  │
│  routes/articles.py  │ 文章+分类+统计+上传 (420行)        │
│  routes/kiwi_sales.py│ 猕猴桃销售 (305行)                │
│  routes/overtime.py  │ 加班记录 (280行)                  │
│  routes/expenses.py  │ 记账模块 (275行)                  │
├─────────────────────────────────────────────────────────┤
│  auth_utils.py       │ JWT token 管理 (55行)             │
│  utils.py            │ 通用工具函数 (110行)               │
│  db.py               │ 数据库连接 (155行)                │
│  cache.py            │ 缓存系统 (48行)                   │
│  config.py           │ 配置常量 (36行)                   │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│                    SQLite Database                        │
│              knowledge_base.db                           │
│         WAL 模式 + 外键约束 + 索引优化                     │
└─────────────────────────────────────────────────────────┘
```

## 模块依赖关系

```
config.py      ← db.py, utils.py, routes/*
db.py          ← routes/*, auth_utils.py
auth_utils.py  ← routes/*
utils.py       ← routes/*
cache.py       ← routes/articles.py
```

**设计原则**：星型拓扑，所有模块 → 共享工具层，无循环依赖。

## 目录结构

```
knowledge_base/
├── app.py              # 入口 (138行)
├── config.py           # 配置常量
├── db.py               # 数据库管理
├── auth_utils.py       # 认证工具
├── utils.py            # 通用工具函数
├── cache.py            # 缓存系统
├── routes/
│   ├── __init__.py     # 蓝图定义
│   ├── auth.py         # 认证路由
│   ├── articles.py     # 文章路由
│   ├── kiwi_sales.py   # 猕猴桃销售路由
│   ├── overtime.py     # 加班记录路由
│   └── expenses.py     # 记账路由
├── static/
│   └── index.html      # 前端 SPA
├── docs/               # Obsidian 知识库
├── tests/              # 测试文件
└── requirements.txt    # 依赖
```

## 数据库设计

### ER 图

```
┌─────────────┐
│    users     │
├─────────────┤
│ id (PK)      │
│ username      │
│ password      │
│ name          │
│ avatar        │
│ token_version │
│ created_at    │
└──────┬──────┘
       │
       │ 1:N
       ▼
┌──────────────────────────────────────────────────────┐
│                    业务表                              │
├──────────────┬──────────────┬──────────────┬─────────┤
│   articles   │  kiwi_sales  │   overtime   │ expenses│
├──────────────┼──────────────┼──────────────┼─────────┤
│ id (PK)      │ id (PK)      │ id (PK)      │ id (PK) │
│ title         │ customer_name│ overtime_type│ category│
│ content       │ phone        │ date         │ amount  │
│ category      │ address      │ start_time   │ remark  │
│ tags          │ order_date   │ end_time     │ date    │
│ views         │ status       │ duration     │         │
│ is_favorite   │ tracking_no  │ remark       │         │
│ is_draft      │ remark       │              │         │
│ user_id (FK)  │ quantity     │ user_id (FK) │user_id  │
│               │ payment_amt  │              │(FK)     │
│               │ user_id (FK) │              │         │
└──────────────┴──────────────┴──────────────┴─────────┘
```

### 索引策略

| 表 | 索引 | 用途 |
|----|------|------|
| articles | user_id, updated_at, (user_id,category) | 列表查询优化 |
| kiwi_sales | user_id, (user_id,created_at) | 列表查询优化 |
| overtime | user_id, date, UNIQUE(user_id,date) | 唯一性约束 |
| expenses | user_id, date, category | 筛选和统计优化 |

## 技术栈

### 后端
- **框架**: Flask 3.0.0
- **数据库**: SQLite 3 (WAL 模式)
- **认证**: JWT (PyJWT 2.9.0+)
- **密码**: pbkdf2-sha256 (passlib)
- **压缩**: flask-compress
- **跨域**: flask-cors

### 前端
- **框架**: Vanilla JavaScript (SPA)
- **编辑器**: EasyMDE (Markdown)
- **高亮**: highlight.js
- **图标**: Font Awesome

## 安全特性

- JWT token + token_version 防重放
- 登录频率限制 (5分钟/10次/IP)
- 密码 pbkdf2-sha256 哈希
- SQL 参数化查询
- XSS 防护 (escapeHtml)
- 文件上传 magic bytes 校验
- CORS 白名单
- 安全响应头 (nosniff, DENY)

## 相关文档
- [[decisions/001-use-flask]] - 选择 Flask
- [[decisions/002-sqlite-choice]] - 选择 SQLite
- [[modules/auth]] - 认证模块
- [[modules/articles]] - 文章模块
