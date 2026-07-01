#!/bin/bash
# ============================================
#  Echo 智慧管理中心 - 一键部署脚本
#  用法: sudo bash deploy.sh
# ============================================

set -e

# ---- 配置区（按需修改）----
APP_NAME="echo"
APP_DIR="/opt/knowledge_base"
APP_USER="www-data"
APP_PORT=5001
GUNICORN_WORKERS=4
DOMAIN=""  # 留空则用 IP 访问，填域名则自动申请 HTTPS

# ---- 颜色输出 ----
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

info()  { echo -e "${GREEN}[INFO]${NC} $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

# ---- 检查 root ----
if [ "$EUID" -ne 0 ]; then
    error "请使用 sudo 运行此脚本: sudo bash deploy.sh"
fi

# ---- 1. 系统依赖 ----
info "=== 步骤 1/7: 安装系统依赖 ==="
apt-get update -qq
apt-get install -y -qq python3 python3-pip python3-venv nginx curl > /dev/null

# ---- 2. 创建应用目录和用户 ----
info "=== 步骤 2/7: 准备应用目录 ==="
id -u "$APP_USER" &>/dev/null || useradd -r -s /bin/false "$APP_USER"
mkdir -p "$APP_DIR"
mkdir -p "$APP_DIR/static/uploads"

# ---- 3. 部署代码（如果当前目录有 app.py 则复制，否则从 Git 拉取）----
info "=== 步骤 3/7: 部署应用代码 ==="
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
if [ -f "$SCRIPT_DIR/app.py" ]; then
    info "从当前目录复制代码..."
    cp -r "$SCRIPT_DIR"/app.py "$APP_DIR/"
    cp -r "$SCRIPT_DIR"/requirements.txt "$APP_DIR/"
    cp -r "$SCRIPT_DIR"/static "$APP_DIR/"
else
    info "从 GitHub 拉取代码..."
    apt-get install -y -qq git > /dev/null
    if [ -d "$APP_DIR/.git" ]; then
        cd "$APP_DIR" && git pull
    else
        rm -rf "$APP_DIR"
        git clone https://github.com/Soulor0725/knowledge_base.git "$APP_DIR"
    fi
fi
chown -R "$APP_USER:$APP_USER" "$APP_DIR"

# ---- 4. Python 虚拟环境 + 依赖 ----
info "=== 步骤 4/7: 安装 Python 依赖 ==="
sudo -u "$APP_USER" python3 -m venv "$APP_DIR/venv"
sudo -u "$APP_USER" "$APP_DIR/venv/bin/pip" install --upgrade pip -q
sudo -u "$APP_USER" "$APP_DIR/venv/bin/pip" install -q \
    flask flask-cors pyjwt passlib gunicorn

# ---- 5. 生成 SECRET_KEY ----
info "=== 步骤 5/7: 生成密钥 ==="
ENV_FILE="$APP_DIR/.env"
if [ ! -f "$ENV_FILE" ]; then
    SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    echo "SECRET_KEY=$SECRET" > "$ENV_FILE"
    chmod 600 "$ENV_FILE"
    info "已生成密钥并写入 $ENV_FILE"
else
    info "密钥文件已存在，跳过生成"
fi

# ---- 6. systemd 服务 ----
info "=== 步骤 6/7: 配置 systemd 服务 ==="
cat > /etc/systemd/system/${APP_NAME}.service << EOF
[Unit]
Description=Echo Management Center
After=network.target

[Service]
User=$APP_USER
Group=$APP_USER
WorkingDirectory=$APP_DIR
EnvironmentFile=$APP_DIR/.env
ExecStart=$APP_DIR/venv/bin/gunicorn \\
    -w $GUNICORN_WORKERS \\
    -b 127.0.0.1:$APP_PORT \\
    --access-logfile $APP_DIR/access.log \\
    --error-logfile $APP_DIR/error.log \\
    app:app
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable ${APP_NAME}
systemctl restart ${APP_NAME}
info "服务已启动: systemctl status ${APP_NAME}"

# ---- 7. Nginx 配置 ----
info "=== 步骤 7/7: 配置 Nginx ==="
if [ -n "$DOMAIN" ]; then
    # 有域名：配置 HTTPS
    info "检测到域名 $DOMAIN，配置 HTTPS..."
    apt-get install -y -qq certbot python3-certbot-nginx > /dev/null

    cat > /etc/nginx/sites-available/${APP_NAME} << EOF
server {
    listen 80;
    server_name $DOMAIN;
    return 301 https://\$host\$request_uri;
}
EOF

    nginx -t && systemctl reload nginx

    # 申请证书
    certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos -m "admin@$DOMAIN"

else
    # 无域名：HTTP 直连
    info "未配置域名，使用 IP 直接访问..."
    cat > /etc/nginx/sites-available/${APP_NAME} << EOF
server {
    listen 80 default_server;
    server_name _;

    client_max_body_size 16M;

    location / {
        proxy_pass http://127.0.0.1:$APP_PORT;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location /static/ {
        alias $APP_DIR/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
EOF
fi

ln -sf /etc/nginx/sites-available/${APP_NAME} /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx

# ---- 完成 ----
SERVER_IP=$(curl -s ifconfig.me 2>/dev/null || echo "你的服务器IP")
echo ""
echo "============================================="
info "  部署完成！"
echo "============================================="
echo ""
if [ -n "$DOMAIN" ]; then
    echo "  访问地址: https://$DOMAIN"
else
    echo "  访问地址: http://$SERVER_IP"
fi
echo ""
echo "  管理命令:"
echo "    查看状态: systemctl status $APP_NAME"
echo "    重启服务: systemctl restart $APP_NAME"
echo "    查看日志: journalctl -u $APP_NAME -f"
echo "    查看错误: tail -f $APP_DIR/error.log"
echo ""
echo "  数据库位置: $APP_DIR/knowledge_base.db"
echo "  密钥文件:   $APP_DIR/.env"
echo ""
echo "  ⚠️  首次访问请先注册账号"
echo "============================================="
