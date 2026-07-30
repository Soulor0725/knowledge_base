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
# 顺序：高频日常 → 水电物业 → 其他
EXPENSE_CATEGORIES = [
    '餐饮',       # 日常饮食/外卖/就餐
    '饮品',       # 饮料/饮品/零食饮品
    '水果',       # 水果
    '菜肉米面油', # 买菜/食材/粮油
    '香烟',       # 烟草
    '交通',       # 公交/打车/单车
    '电费',       # 电费
    '燃气费',     # 燃气费
    '水费',       # 水费
    '话费',       # 手机话费
    '网费',       # 宽带网费
    '暖气费',     # 暖气费
    '物业费',     # 物业/房租/房贷
    '日用品',     # 生活用品
    '零食',       # 零食/小吃
    '快递',       # 快递/物流
    '其他',       # 其他未分类
]
