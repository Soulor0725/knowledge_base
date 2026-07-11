# 记账模块

## 概述
个人消费记录管理，支持分类统计、月度分析和数据导出。

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/expenses` | 获取记录列表 |
| POST | `/api/expenses` | 添加记录 |
| PUT | `/api/expenses/:id` | 更新记录 |
| DELETE | `/api/expenses/:id` | 删除记录 |
| POST | `/api/expenses/batch-delete` | 批量删除 |
| GET | `/api/expenses/stats` | 分类统计 |
| GET | `/api/expenses/today` | 今日合计 |
| GET | `/api/expenses/stats/monthly` | 月度统计 |
| GET/POST | `/api/expenses/export` | 导出 CSV |

## 请求/响应示例

### 添加记录
**请求**
```json
POST /api/expenses
{
  "category": "电费",
  "amount": 150.50,
  "remark": "7月电费",
  "date": "2026-07-11"
}
```
**响应** (201)
```json
{
  "message": "添加成功",
  "id": 1
}
```

### 分类统计
**请求**
```
GET /api/expenses/stats?year=2026
```
**响应** (200)
```json
{
  "categories": [
    {"category": "电费", "amount": 800.00, "percentage": 35.2},
    {"category": "话费", "amount": 500.00, "percentage": 22.0}
  ],
  "grand_total": 2275.50
}
```

### 今日合计
**请求**
```
GET /api/expenses/today?date=2026-07-11
```
**响应** (200)
```json
{
  "date": "2026-07-11",
  "count": 3,
  "total": 285.50
}
```

### 月度统计
**请求**
```
GET /api/expenses/stats/monthly?year=2026
```
**响应** (200)
```json
{
  "months": [
    {"month": 1, "total": 1200.00},
    {"month": 2, "total": 980.50}
  ]
}
```

## 业务规则

### 分类白名单
```
燃气费、电费、话费、网费、暖气费、香烟、菜肉米面油、交通、物业费、水果、其他
```

### 字段校验
| 字段 | 规则 |
|------|------|
| category | 必填，必须在白名单内 |
| amount | 必填，大于 0，保留 2 位小数 |
| date | 必填，YYYY-MM-DD 格式 |
| remark | 可选，无长度限制 |

### 统计规则
- **分类统计**：按分类汇总金额，计算占比
- **月度统计**：按月份汇总，返回 1-12 月数据
- **今日合计**：指定日期（默认当天）的消费总额和笔数
- 支持按年份、月份范围筛选

### 导出规则
- CSV 格式（GBK 编码，支持 Excel 打开）
- GET：按日期、分类筛选
- POST：指定 ID 列表导出
- 最多导出 10000 条

## 查询参数

### GET /api/expenses
| 参数 | 类型 | 说明 |
|------|------|------|
| page | int | 页码 |
| page_size | int | 每页数量 |
| date | string | 日期筛选 YYYY-MM-DD |
| category | string | 分类筛选 |

### GET /api/expenses/stats
| 参数 | 类型 | 说明 |
|------|------|------|
| year | string | 年份筛选 |
| month | string | 月份筛选 YYYY-MM |
| start_month | string | 起始月份（MM） |
| end_month | string | 结束月份（MM） |

### GET /api/expenses/today
| 参数 | 类型 | 说明 |
|------|------|------|
| date | string | 日期 YYYY-MM-DD（默认当天） |

### GET /api/expenses/stats/monthly
| 参数 | 类型 | 说明 |
|------|------|------|
| year | string | 年份筛选 |
| start_month | string | 起始月份 |
| end_month | string | 结束月份 |

### GET /api/expenses/export
| 参数 | 类型 | 说明 |
|------|------|------|
| date | string | 日期筛选 |
| category | string | 分类筛选 |

## 数据模型

```sql
CREATE TABLE expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT NOT NULL,
    amount REAL NOT NULL,
    remark TEXT DEFAULT '',
    date TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    user_id INTEGER,
    FOREIGN KEY (user_id) REFERENCES users (id)
);
```

## 索引
```sql
CREATE INDEX idx_expenses_user_id ON expenses(user_id);
CREATE INDEX idx_expenses_date ON expenses(date);
CREATE INDEX idx_expenses_category ON expenses(category);
CREATE INDEX idx_expenses_user_date ON expenses(user_id, date);
CREATE INDEX idx_expenses_user_yearmonth ON expenses(user_id, substr(date, 1, 7));
CREATE INDEX idx_expenses_user_month ON expenses(user_id, substr(date, 6, 2));
```

## 导出字段

| 列名 | 说明 |
|------|------|
| ID | 记录 ID |
| 分类 | category |
| 金额 | amount |
| 日期 | date |
| 备注 | remark |

## 相关文件
- `routes/expenses.py` - 路由实现 (275行)
- `config.py` - `EXPENSE_CATEGORIES` 常量
