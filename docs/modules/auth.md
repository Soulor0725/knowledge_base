# 认证模块

## 概述
负责用户注册、登录、token 管理、密码修改和个人信息维护。

## API 接口

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| POST | `/api/auth/register` | 用户注册 | 否 |
| POST | `/api/auth/login` | 用户登录 | 否 |
| GET | `/api/auth/me` | 获取当前用户 | 是 |
| PUT | `/api/auth/me` | 更新用户信息 | 是 |
| POST | `/api/auth/change-password` | 修改密码 | 是 |

## 请求/响应示例

### 注册
**请求**
```json
POST /api/auth/register
{
  "username": "root",
  "password": "Root1234",
  "name": "管理员"
}
```
**响应** (201)
```json
{
  "id": 1,
  "username": "root",
  "name": "管理员",
  "token": "eyJ...",
  "message": "注册成功"
}
```

### 登录
**请求**
```json
POST /api/auth/login
{
  "username": "root",
  "password": "Root1234"
}
```
**响应** (200)
```json
{
  "id": 1,
  "username": "root",
  "name": "管理员",
  "avatar": "",
  "token": "eyJ...",
  "message": "登录成功"
}
```

### 修改密码
**请求**
```json
POST /api/auth/change-password
Authorization: Bearer <token>
{
  "old_password": "Root1234",
  "new_password": "NewPass123"
}
```
**响应** (200)
```json
{
  "message": "密码修改成功"
}
```

## 业务规则

### 注册
- 用户名：至少 3 个字符，唯一
- 密码：至少 8 位，必须包含大写字母、小写字母和数字
- 密码使用 pbkdf2-sha256 哈希存储

### 登录
- **频率限制**：5 分钟内最多 10 次/IP
- **DoS 防护**：超过 10000 个 IP 时清理最旧的 50%
- **Token 版本**：登录时递增 `token_version`，踢掉该用户所有旧 token
- JWT token 有效期 7 天

### 修改密码
- 需要提供原密码验证
- 新密码不能与原密码相同
- 密码规则同注册

### Token 验证
- `login_required` 装饰器统一处理
- 校验 `token_version` 防止旧 token 使用
- 头像 URL 必须以 `http://`、`https://` 或 `data:image/` 开头

## 数据模型

```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,        -- pbkdf2-sha256 哈希
    name TEXT DEFAULT '',
    avatar TEXT DEFAULT '',
    token_version INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## 配置常量

| 常量 | 值 | 说明 |
|------|-----|------|
| `USERNAME_MIN_LENGTH` | 3 | 用户名最小长度 |
| `PASSWORD_MIN_LENGTH` | 8 | 密码最小长度 |
| `RATE_LIMIT_WINDOW` | 300 | 限流窗口（秒） |
| `RATE_LIMIT_MAX` | 10 | 窗口内最大尝试次数 |

## 错误码

| HTTP 状态码 | 错误信息 |
|-------------|----------|
| 400 | 用户名至少3个字符，密码至少8位... |
| 400 | 密码必须同时包含大写字母、小写字母和数字 |
| 400 | 用户名已存在 |
| 401 | 用户名或密码错误 |
| 401 | 无效或过期的token |
| 401 | 登录已在其他地方失效，请重新登录 |
| 409 | 登录尝试过于频繁，请5分钟后再试 |

## 相关文件
- `routes/auth.py` - 路由实现 (185行)
- `auth_utils.py` - token 工具函数
- `config.py` - 配置常量
