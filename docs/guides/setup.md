# 环境搭建

## 系统要求

- Python 3.8+
- pip
- Git

## 快速开始

### 1. 克隆项目
```bash
git clone <repository-url>
cd knowledge_base
```

### 2. 安装依赖
```bash
pip install -r requirements.txt
```

### 3. 启动服务
```bash
python app.py
```

### 4. 访问应用
- Web 界面: http://localhost:5001
- API 地址: http://localhost:5001/api
- 健康检查: http://localhost:5001/api/health

## 依赖说明

| 包名 | 版本 | 用途 |
|------|------|------|
| Flask | 3.0.0 | Web 框架 |
| Flask-CORS | 4.0.0 | 跨域支持 |
| Flask-Compress | 1.15 | 响应压缩 |
| PyJWT | >=2.9.0 | JWT 认证 |
| passlib | 1.7.4 | 密码哈希 |

## 开发环境

### 运行测试
```bash
# 冒烟测试
python test_api.py

# 完整测试
cd tests
python -m pytest
```

### 数据库重置
```bash
# 删除数据库文件后重启服务
rm knowledge_base.db
python app.py
```

## 常见问题

### 端口被占用
```bash
# Windows
netstat -ano | findstr :5001
taskkill /PID <pid> /F

# Linux/Mac
lsof -i :5001
kill <pid>
```

### 密码忘记
```bash
# 直接操作数据库重置密码
python -c "
import sqlite3
from passlib.hash import pbkdf2_sha256
conn = sqlite3.connect('knowledge_base.db')
new_hash = pbkdf2_sha256.hash('新密码')
conn.execute('UPDATE users SET password = ? WHERE username = ?', (new_hash, 'root'))
conn.commit()
print('密码已重置')
"
```

## IDE 配置

### VS Code
推荐插件:
- Python
- SQLite Viewer
- Obsidian (知识库编辑)

### Obsidian
- 打开项目根目录作为 Vault
- 配置见 `.obsidian/` 目录
