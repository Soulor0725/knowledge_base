# 部署指南

## 部署方式

### 1. 开发环境（内置服务器）

```bash
python app.py
# 服务运行在 http://localhost:5001
```

### 2. 生产环境（Gunicorn）

```bash
# 安装 gunicorn
pip install gunicorn

# 启动服务
gunicorn -w 4 -b 0.0.0.0:5001 app:app

# 后台运行
nohup gunicorn -w 4 -b 0.0.0.0:5001 app:app > gunicorn.log 2>&1 &
```

### 3. Windows 服务

使用 `nssm` 注册为 Windows 服务：
```bash
nssm install Echo "C:\Python\python.exe" "E:\trae_projects\knowledge_base\app.py"
nssm start Echo
```

## 配置

### 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| SECRET_KEY | JWT 密钥 | 随机生成 |
| FLASK_ENV | 环境 | production |
| PORT | 端口 | 5001 |

### 生产配置

```bash
# 设置密钥（重启不会使 token 失效）
export SECRET_KEY="your-secret-key-here"

# 启动
python app.py
```

## 反向代理（Nginx）

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static/ {
        alias /path/to/knowledge_base/static/;
        expires 1d;
    }
}
```

## 数据备份

### 自动备份脚本

```bash
#!/bin/bash
# backup.sh
DATE=$(date +%Y%m%d_%H%M%S)
cp knowledge_base.db "backups/knowledge_base_${DATE}.db"
# 保留最近 7 天的备份
find backups/ -name "*.db" -mtime +7 -delete
```

### 定时任务

```bash
# 每天凌晨 2 点备份
0 2 * * * /path/to/backup.sh
```

## 监控

### 健康检查

```bash
curl http://localhost:5001/api/health
# 返回 {"status": "ok", "db": "connected"}
```

### 日志查看

```bash
# 实时日志
tail -f app.log

# Gunicorn 日志
tail -f gunicorn.log
```

## 常见问题

### 数据库锁定
- 原因：并发写入冲突
- 解决：SQLite WAL 模式 + busy_timeout=5000

### Token 失效
- 原因：SECRET_KEY 变化
- 解决：设置固定 SECRET_KEY 环境变量

### 文件上传失败
- 原因：目录权限
- 解决：确保 `static/uploads/` 可写

## 部署检查清单

- [ ] 设置 SECRET_KEY 环境变量
- [ ] 配置反向代理
- [ ] 启用 HTTPS
- [ ] 设置自动备份
- [ ] 配置日志轮转
- [ ] 测试健康检查端点

## 相关链接
- [[architecture/overview]] - 系统架构总览
- [[guides/setup]] - 环境搭建
- [[guides/coding-standards]] - 编码规范
- [[ALIYUN_DEPLOY]] - 阿里云部署指南
