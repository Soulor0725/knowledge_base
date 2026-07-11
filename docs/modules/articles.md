# 文章模块

## 概述
知识库核心模块，管理文章的 CRUD、分类、标签、统计和文件上传。

## API 接口

### 文章
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/articles` | 获取文章列表 |
| POST | `/api/articles` | 创建文章 |
| GET | `/api/articles/:id` | 获取文章详情 |
| PUT | `/api/articles/:id` | 更新文章 |
| DELETE | `/api/articles/:id` | 删除文章 |
| POST | `/api/articles/:id/favorite` | 切换收藏 |
| POST | `/api/articles/batch-delete` | 批量删除 |
| GET | `/api/articles/navigate` | 文章导航 |

### 分类
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/categories` | 获取分类列表 |
| POST | `/api/categories` | 创建分类 |
| DELETE | `/api/categories/:id` | 删除分类 |

### 统计
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/stats` | 文章统计 |
| GET | `/api/tags` | 标签列表 |

### 上传
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/upload` | 上传文件 |

## 请求/响应示例

### 获取文章列表
**请求**
```
GET /api/articles?page=1&page_size=10&category=技术&search=Python
```
**响应** (200)
```json
{
  "articles": [
    {
      "id": 1,
      "title": "Python 入门",
      "category": "技术",
      "tags": "python,入门",
      "created_at": "2026-07-11T10:00:00",
      "updated_at": "2026-07-11T10:00:00",
      "views": 42,
      "is_favorite": 0,
      "is_draft": 0
    }
  ],
  "total": 100,
  "page": 1,
  "page_size": 10
}
```

### 创建文章
**请求**
```json
POST /api/articles
{
  "title": "Python 入门",
  "content": "# Python 入门\n\n这是内容...",
  "category": "技术",
  "tags": "python,入门",
  "is_draft": 0
}
```
**响应** (201)
```json
{
  "id": 1,
  "message": "创建成功"
}
```

### 批量删除
**请求**
```json
POST /api/articles/batch-delete
{
  "ids": [1, 2, 3]
}
```
**响应** (200)
```json
{
  "message": "成功删除 3 条记录",
  "deleted": 3
}
```

### 文章统计
**响应** (200)
```json
{
  "total_articles": 100,
  "favorites": 15,
  "total_views": 5000,
  "categories_used": 5
}
```

## 业务规则

### 文章
- 标题：最多 200 字符
- 内容：最多 65535 字符
- 标签：最多 500 字符，逗号分隔
- 分类：必须存在于用户分类列表
- 草稿模式：标题和内容非必填
- 浏览量：每次查看详情自动 +1

### 分类
- 名称：必填，最多 50 字符
- 不能包含 `<>"'&` 等特殊字符
- 删除分类时，该分类下的文章自动归为"未分类"

### 上传
- 支持格式：PNG、JPG、JPEG、GIF、WebP
- 最大 16MB
- 校验 magic bytes（防止伪造扩展名）
- 文件名：`时间戳_原文件名`

### 缓存
- 统计数据缓存 5 分钟
- 标签数据缓存 5 分钟
- 创建/更新/删除文章时自动清除缓存

## 查询参数

### GET /api/articles
| 参数 | 类型 | 说明 |
|------|------|------|
| page | int | 页码，默认 1 |
| page_size | int | 每页数量，可选 5/10/15 |
| category | string | 按分类筛选 |
| tag | string | 按标签筛选 |
| search | string | 搜索标题和内容 |
| favorite | string | "true" 仅显示收藏 |

### GET /api/articles/navigate
| 参数 | 类型 | 说明 |
|------|------|------|
| current_id | int | 当前文章 ID |
| direction | string | "prev" 或 "next" |

## 数据模型

```sql
CREATE TABLE articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    category TEXT DEFAULT '未分类',
    tags TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    views INTEGER DEFAULT 0,
    is_favorite INTEGER DEFAULT 0,
    is_draft INTEGER DEFAULT 0,
    user_id INTEGER,
    FOREIGN KEY (user_id) REFERENCES users (id)
);

CREATE TABLE categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    color TEXT DEFAULT '#667eea',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    user_id INTEGER
);
```

## 索引
```sql
CREATE INDEX idx_articles_user_id ON articles(user_id);
CREATE INDEX idx_articles_updated_at ON articles(updated_at);
CREATE INDEX idx_articles_user_category ON articles(user_id, category);
CREATE INDEX idx_articles_user_updated ON articles(user_id, updated_at DESC);
```

## 相关文件
- `routes/articles.py` - 路由实现 (420行)
- `cache.py` - 缓存管理
