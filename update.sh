#!/bin/bash
# ============================================
#  Echo 更新脚本（拉取最新代码并重启）
#  用法: sudo bash update.sh
# ============================================

set -e

APP_NAME="echo"
APP_DIR="/opt/knowledge_base"
APP_USER="www-data"

GREEN='\033[0;32m'
NC='\033[0m'
info() { echo -e "${GREEN}[INFO]${NC} $1"; }

if [ "$EUID" -ne 0 ]; then
    echo "请使用 sudo 运行: sudo bash update.sh"
    exit 1
fi

# 备份数据库
if [ -f "$APP_DIR/knowledge_base.db" ]; then
    BACKUP="$APP_DIR/knowledge_base.db.bak.$(date +%Y%m%d_%H%M%S)"
    cp "$APP_DIR/knowledge_base.db" "$BACKUP"
    info "数据库已备份: $BACKUP"
fi

# 拉取最新代码
cd "$APP_DIR"
sudo -u "$APP_USER" git pull
chown -R "$APP_USER:$APP_USER" "$APP_DIR"

# 重启服务
systemctl restart "$APP_NAME"
info "更新完成，服务已重启"
systemctl status "$APP_NAME" --no-pager
