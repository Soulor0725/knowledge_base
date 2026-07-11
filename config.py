"""配置常量集中管理"""
import os
import threading

# ── 登录频率限制 ──
MAX_LOGIN_ATTEMPT_ENTRIES = 10000
LOGIN_LOCK = threading.Lock()
RATE_LIMIT_WINDOW = 300  # 5分钟窗口
RATE_LIMIT_MAX = 10      # 窗口内最大尝试次数

# ── 缓存配置 ──
CACHE_TTL = 300          # 缓存有效期 5 分钟
CACHE_MAX_SIZE = 1000    # 最多缓存 1000 个用户
CACHE_EXPIRED = object()
cache_lock = threading.Lock()

# ── 密码策略 ──
PASSWORD_MIN_LENGTH = 8
USERNAME_MIN_LENGTH = 3

# ── 登录尝试记录（IP → [时间戳列表]） ──
login_attempts = {}

# ── 数据库路径 ──
DATABASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'knowledge_base.db')

# ── 文件上传配置 ──
UPLOAD_FOLDER = os.path.join('static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
ALLOWED_MIME_TYPES = {'image/png', 'image/jpeg', 'image/gif', 'image/webp'}

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ── 记账分类白名单 ──
EXPENSE_CATEGORIES = ['燃气费', '电费', '话费', '网费', '暖气费', '香烟', '菜肉米面油', '交通', '物业费', '水果', '其他']
