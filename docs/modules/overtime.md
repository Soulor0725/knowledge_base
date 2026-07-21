# 加班记录模块

## 概述
管理加班记录，支持平时加班和周末加班，自动计算时长，提供月度统计。

## 前端组件

### 自定义时间选择器
- 使用下拉框选择小时（08-23）和分钟（00-59）
- 显示格式：`🕐 19 - 00`（横线分隔）
- 存储格式：`19:00`（冒号分隔，兼容后端）
- 图标：Font Awesome 时钟图标，主题色蓝色

### 样式类
- `.time-picker` - 容器样式
- `.time-picker-icon` - 时钟图标
- `.time-hour` / `.time-minute` - 下拉选择框
- `.time-picker-separator` - 分隔符

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/overtime` | 获取记录列表 |
| POST | `/api/overtime` | 添加记录 |
| PUT | `/api/overtime/:id` | 更新记录 |
| DELETE | `/api/overtime/:id` | 删除记录 |
| POST | `/api/overtime/batch-delete` | 批量删除 |
| GET | `/api/overtime/stats` | 月度统计 |
| GET | `/api/overtime/stats/monthly` | 周期统计 |

## 请求/响应示例

### 添加记录
**请求**
```json
POST /api/overtime
{
  "overtime_type": "weekday",
  "date": "2026-07-11",
  "start_time": "19:00",
  "end_time": "22:00",
  "remark": "赶项目"
}
```
**响应** (201)
```json
{
  "message": "添加成功",
  "id": 1,
  "duration": 3.0
}
```

### 月度统计
**请求**
```
GET /api/overtime/stats?month=2026-07
```
**响应** (200)
```json
{
  "weekday_total": 25.5,
  "weekend_total": 8.0,
  "total_hours": 33.5,
  "total_count": 12
}
```

### 周期统计
**请求**
```
GET /api/overtime/stats/monthly?month=2026-07
```
**响应** (200)
```json
{
  "period_start": "2026-06-21",
  "period_end": "2026-07-20",
  "weekday_total": 20.0,
  "weekend_total": 6.0,
  "total_hours": 26.0,
  "total_count": 10,
  "month": "2026-07"
}
```

## 业务规则

### 加班类型
| 类型 | 值 | 时间范围 | 计算规则 |
|------|-----|----------|----------|
| 平时加班 | weekday | 结束时间 19:00-23:59 | 统一从 19:00 开始计算 |
| 周末加班 | weekend | 08:30-23:59 | 从 start_time 开始，自动扣除 12:00-14:00 午餐 |

### 时长计算
- **平时加班**：无论 start_time 是多少，都从 19:00 开始计算
- **周末加班**：如果跨越 12:00-14:00，自动扣除午餐时间（最多 2 小时）

### 限制
- 同一天只能有一条加班记录（`UNIQUE INDEX`）
- 时间格式：HH:MM（24小时制）
- 结束时间必须晚于开始时间
- 支持手动指定时长（覆盖自动计算）

### 统计周期
- **月度统计**：自然月（1日-月末）
- **周期统计**：上月 21 日 - 本月 20 日（含）

## 查询参数

### GET /api/overtime
| 参数 | 类型 | 说明 |
|------|------|------|
| page | int | 页码 |
| page_size | int | 每页数量 |
| month | string | 月份筛选 YYYY-MM |

### GET /api/overtime/stats
| 参数 | 类型 | 说明 |
|------|------|------|
| month | string | 月份筛选 YYYY-MM（可选，不传则统计全部） |

### GET /api/overtime/stats/monthly
| 参数 | 类型 | 说明 |
|------|------|------|
| month | string | 必填，YYYY-MM 格式 |

## 数据模型

```sql
CREATE TABLE overtime_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    overtime_type TEXT NOT NULL,      -- 'weekday' 或 'weekend'
    date TEXT NOT NULL,               -- YYYY-MM-DD
    start_time TEXT NOT NULL,         -- HH:MM
    end_time TEXT NOT NULL,           -- HH:MM
    duration REAL NOT NULL,           -- 小时数
    remark TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    user_id INTEGER,
    FOREIGN KEY (user_id) REFERENCES users (id)
);

CREATE UNIQUE INDEX idx_overtime_user_date 
ON overtime_records(user_id, date);
```

## 索引
```sql
CREATE INDEX idx_overtime_user_id ON overtime_records(user_id);
CREATE INDEX idx_overtime_date ON overtime_records(date);
CREATE UNIQUE INDEX idx_overtime_user_date ON overtime_records(user_id, date);
```

## 错误码

| HTTP 状态码 | 错误信息 |
|-------------|----------|
| 400 | 加班类型必须是 平时加班 或 周末加班 |
| 400 | 平时加班结束时间需在 19:00-23:59 范围内 |
| 400 | 周末加班时间范围为 08:30-23:59 |
| 400 | 该日期已存在加班记录 |
| 400 | 结束时间必须晚于开始时间 |

## 相关文件
- `routes/overtime.py` - 路由实现 (280行)
- `static/index.html` - 前端组件（时间选择器、表单、列表）

## 相关链接
- [[architecture/overview]] - 系统架构总览
- [[modules/auth]] - 认证模块（用户隔离）
- [[modules/articles]] - 文章模块
- [[modules/kiwi-sales]] - 猕猴桃销售模块
- [[modules/expenses]] - 记账模块
- [[BUG_FIX_LESSONS]] - Bug 修复经验（含加班相关）
- [[INTERACTION_DESIGN]] - 交互设计（含时间选择器）
