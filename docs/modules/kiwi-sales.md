# 猕猴桃销售模块

## 概述
管理猕猴桃销售订单，包括 CRUD、报表统计和数据导出。

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/kiwi-sales` | 获取订单列表 |
| POST | `/api/kiwi-sales` | 创建订单 |
| PUT | `/api/kiwi-sales/:id` | 更新订单 |
| DELETE | `/api/kiwi-sales/:id` | 删除订单 |
| POST | `/api/kiwi-sales/batch-delete` | 批量删除 |
| GET | `/api/kiwi-sales-report` | 报表统计 |
| GET | `/api/kiwi-sales/export` | 导出 CSV |

## 请求/响应示例

### 创建订单
**请求**
```json
POST /api/kiwi-sales
{
  "customer_name": "张三",
  "phone": "13800138000",
  "address": "北京市朝阳区xxx",
  "order_date": "2026-07-11",
  "quantity": 10,
  "payment_amount": 500.00,
  "status": "未发货",
  "remark": "红心猕猴桃"
}
```
**响应** (201)
```json
{
  "message": "添加成功",
  "id": 1
}
```

### 报表统计
**请求**
```
GET /api/kiwi-sales-report?page=1&page_size=10&year=2026
```
**响应** (200)
```json
{
  "report": [
    {
      "customer_name": "张三",
      "remark": "红心",
      "total_quantity": 50,
      "total_amount": 2500.00
    }
  ],
  "page": 1,
  "page_size": 10,
  "total_customers": 20,
  "total_pages": 2,
  "summary": {
    "红心": {"quantity": 100, "amount": 5000.00},
    "黄心": {"quantity": 80, "amount": 3200.00},
    "total_quantity": 180,
    "total_amount": 8200.00
  }
}
```

## 业务规则

### 订单校验
| 字段 | 规则 |
|------|------|
| customer_name | 必填，最多 50 字符 |
| phone | 必填，11 位手机号（纯数字） |
| address | 必填，最多 200 字符 |
| order_date | 必填，YYYY-MM-DD 格式 |
| quantity | 非负整数 |
| payment_amount | 非负数，保留 2 位小数 |
| status | "已发货" 或 "未发货" |
| tracking_number | 可选，最多 50 字符 |
| remark | 可选，最多 50 字符 |

### 报表
- 按客户名 + 规格分组统计
- 支持年份筛选
- 分页显示（按客户分组）
- 汇总：按规格统计数量和金额

### 导出
- CSV 格式（GBK 编码，支持 Excel 打开）
- 支持按客户、电话、年份筛选
- 最多导出 10000 条

## 查询参数

### GET /api/kiwi-sales
| 参数 | 类型 | 说明 |
|------|------|------|
| page | int | 页码 |
| page_size | int | 每页数量 |
| customer | string | 客户名模糊搜索 |
| phone | string | 电话模糊搜索 |
| year | string | 年份筛选 |

### GET /api/kiwi-sales-report
| 参数 | 类型 | 说明 |
|------|------|------|
| page | int | 页码 |
| page_size | int | 每页数量 |
| year | string | 年份筛选 |

### GET /api/kiwi-sales/export
| 参数 | 类型 | 说明 |
|------|------|------|
| customer | string | 客户名筛选 |
| phone | string | 电话筛选 |
| year | string | 年份筛选 |

## 数据模型

```sql
CREATE TABLE kiwi_sales (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_name TEXT NOT NULL,
    phone TEXT NOT NULL,
    address TEXT NOT NULL,
    order_date TEXT NOT NULL,
    status TEXT DEFAULT '未发货',
    tracking_number TEXT,
    remark TEXT,
    quantity INTEGER DEFAULT 0,
    payment_amount REAL DEFAULT 0.00,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    user_id INTEGER,
    FOREIGN KEY (user_id) REFERENCES users (id)
);
```

## 索引
```sql
CREATE INDEX idx_kiwi_sales_user_id ON kiwi_sales(user_id);
CREATE INDEX idx_kiwi_sales_user_created ON kiwi_sales(user_id, created_at DESC);
```

## 导出字段

| 列名 | 说明 |
|------|------|
| 序号 | 自增序号 |
| 客户名 | customer_name |
| 电话 | phone |
| 地址 | address |
| 接单日期 | order_date |
| 状态 | status |
| 运单号 | tracking_number |
| 备注 | remark |
| 数量 | quantity |
| 支付金额 | payment_amount |

## 相关文件
- `routes/kiwi_sales.py` - 路由实现 (305行)
