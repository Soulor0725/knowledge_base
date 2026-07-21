# 阿里云轻量应用服务器部署教程

## 一、购买服务器

### 1. 进入控制台

1. 打开 [阿里云官网](https://www.aliyun.com/)
2. 登录/注册阿里云账号
3. 搜索 **「轻量应用服务器」**，点击进入

### 2. 选择配置

| 配置项 | 推荐选择 |
|--------|---------|
| 地域 | 离你最近的（杭州/上海/北京） |
| 镜像 | **Ubuntu 22.04 64位**（或 Ubuntu 20.04） |
| 实例规格 | 2核2G 足够（新人价约 60-90 元/年） |
| 系统盘 | 40GB SSD（默认） |
| 带宽 | 3-5Mbps（默认） |

> 新人首次购买有优惠，续费较贵。第二年可以换新账号重新买。

### 3. 完成购买

- 设置 root 密码（**务必记住**，后面要用）
- 购买成功后，在控制台能看到公网 IP

### 4. 开放端口

在轻量应用服务器控制台 → **防火墙** → **添加规则**：

| 协议 | 端口 | 说明 |
|------|------|------|
| TCP | 22 | SSH 远程登录 |
| TCP | 80 | HTTP（Nginx） |
| TCP | 443 | HTTPS（如需） |

> 默认已有 22 端口，确保 80 端口开放即可。

---

## 二、连接服务器

### Windows（推荐用 PowerShell）

```powershell
ssh root@你的公网IP
```

输入密码回车即可。

### 或者用 Xshell / FinalShell

- 下载 [FinalShell](http://www.hostbuf.com/t/1001.html)（免费）
- 新建连接 → 填入 IP、端口 22、用户名 root、密码

---

## 三、一键部署

### 1. 上传项目代码

**方式 A：用 Git 拉取（推荐）**

服务器上直接克隆：

```bash
cd /opt
git clone https://github.com/Soulor0725/knowledge_base.git
```

**方式 B：本地打包上传**

在本地项目目录执行：

```bash
# 本地压缩
tar -czf knowledge_base.tar.gz --exclude=.git --exclude=__pycache__ --exclude=*.db .

# 上传到服务器（在本地 PowerShell 执行）
scp knowledge_base.tar.gz root@你的公网IP:/tmp/

# 在服务器上解压
ssh root@你的公网IP
mkdir -p /opt/knowledge_base
tar -xzf /tmp/knowledge_base.tar.gz -C /opt/knowledge_base
```

### 2. 运行部署脚本

```bash
cd /opt/knowledge_base
sudo bash deploy.sh
```

脚本会自动完成：

1. 安装 Python3、Nginx 等系统依赖
2. 创建 Python 虚拟环境
3. 安装 Flask、gunicorn 等依赖
4. 随机生成 SECRET_KEY
5. 配置 systemd 服务（开机自启+崩溃重启）
6. 配置 Nginx 反向代理

整个过程约 2-5 分钟。

### 3. 验证部署

```bash
# 查看服务状态
systemctl status echo

# 应看到 Active: active (running)
```

浏览器打开 `http://你的公网IP`，看到登录页面即部署成功。

---

## 四、后续更新

每次代码有更新，在服务器上执行：

```bash
cd /opt/knowledge_base
sudo bash update.sh
```

自动：备份数据库 → 拉取最新代码 → 重启服务。

---

## 五、常用管理命令

```bash
# 查看服务状态
systemctl status echo

# 重启服务
systemctl restart echo

# 停止服务
systemctl stop echo

# 查看实时日志
journalctl -u echo -f

# 查看错误日志
tail -f /opt/knowledge_base/error.log

# 查看访问日志
tail -f /opt/knowledge_base/access.log
```

---

## 六、数据备份

数据库文件在 `/opt/knowledge_base/knowledge_base.db`，建议定期备份：

### 手动备份

```bash
cp /opt/knowledge_base/knowledge_base.db /opt/knowledge_base/knowledge_base.db.bak
```

### 自动备份（每天凌晨3点）

```bash
# 创建备份脚本
cat > /opt/knowledge_base/backup.sh << 'EOF'
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
cp /opt/knowledge_base/knowledge_base.db /opt/knowledge_base/backup/knowledge_base_$DATE.db
# 只保留最近30天的备份
find /opt/knowledge_base/backup -name "*.db" -mtime +30 -delete
EOF

mkdir -p /opt/knowledge_base/backup
chmod +x /opt/knowledge_base/backup.sh

# 添加定时任务
echo "0 3 * * * /opt/knowledge_base/backup.sh" | crontab -
```

---

## 七、配置域名 + HTTPS（可选）

### 1. 域名备案

国内服务器用域名必须备案：
- 阿里云控制台 → 备案 → 按提示填写资料
- 备案约 7-20 个工作日

### 2. 域名解析

阿里云控制台 → 域名 → 解析 → 添加记录：

| 记录类型 | 主机记录 | 记录值 |
|---------|---------|--------|
| A | @ | 你的公网IP |

### 3. 部署时指定域名

```bash
# 编辑 deploy.sh，设置 DOMAIN
DOMAIN="你的域名.com"

# 重新运行
sudo bash deploy.sh
```

脚本会自动通过 Let's Encrypt 申请免费 HTTPS 证书。

---

## 八、常见问题

### Q: 部署后访问不了？

```bash
# 1. 检查服务是否运行
systemctl status echo

# 2. 检查端口是否监听
ss -tlnp | grep 5001

# 3. 检查防火墙（阿里云控制台）是否开放 80 端口

# 4. 检查 Nginx 配置
nginx -t
systemctl status nginx
```

### Q: 能访问但样式/图片加载不了？

Nginx 的静态文件配置可能有问题，检查 `/etc/nginx/sites-available/echo` 中 static 路径是否正确。

### Q: 数据库被锁（database is locked）？

```bash
# 重启服务即可
systemctl restart echo
```

### Q: 如何查看内存/磁盘使用？

```bash
# 内存
free -h

# 磁盘
df -h

# 进程
top -u www-data
```

---

## 九、费用总结

| 项目 | 费用 |
|------|------|
| 云服务器（2核2G） | 60-90 元/年（新人价） |
| 域名（.com） | 30-60 元/年（可选） |
| HTTPS 证书 | 免费（Let's Encrypt） |
| **合计** | **最低 60 元/年** |

## 相关链接
- [[architecture/overview]] - 系统架构总览
- [[guides/deployment]] - 部署流程
- [[guides/setup]] - 环境搭建
