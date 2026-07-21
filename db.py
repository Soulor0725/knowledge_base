"""数据库管理模块"""
import sqlite3
import time
import sys
from flask import g
from config import DATABASE


def _get_db_metrics():
    """延迟加载 Prometheus 指标"""
    # 从已加载的 app 模块中获取，避免循环导入
    # 注意: 直接运行 python app.py 时模块名为 __main__
    for name in ('app', '__main__'):
        mod = sys.modules.get(name)
        if mod and hasattr(mod, 'DB_QUERY_DURATION'):
            return mod.DB_QUERY_DURATION
    # fallback: 返回一个空操作对象
    class _NullMetrics:
        def labels(self, **kwargs):
            return self
        def observe(self, value):
            pass
    return _NullMetrics()


class MonitoredCursor:
    """自动记录耗时的 Cursor 包装器"""
    def __init__(self, cursor):
        self._cursor = cursor

    def execute(self, operation, parameters=()):
        # 排除 PRAGMA 等初始化语句
        if operation.strip().upper().startswith(('PRAGMA', 'BEGIN', 'COMMIT', 'ROLLBACK')):
            return self._cursor.execute(operation, parameters)

        start = time.perf_counter()
        try:
            return self._cursor.execute(operation, parameters)
        finally:
            elapsed = time.perf_counter() - start
            operation_type = operation.strip().split()[0].upper()
            _get_db_metrics().labels(operation=operation_type).observe(elapsed)

    def executemany(self, operation, seq_of_parameters):
        start = time.perf_counter()
        try:
            return self._cursor.executemany(operation, seq_of_parameters)
        finally:
            elapsed = time.perf_counter() - start
            operation_type = operation.strip().split()[0].upper()
            _get_db_metrics().labels(operation=operation_type).observe(elapsed)

    def fetchone(self):
        return self._cursor.fetchone()

    def fetchall(self):
        return self._cursor.fetchall()

    def __getattr__(self, name):
        return getattr(self._cursor, name)


class MonitoredConnection:
    """自动监控 Cursor 的 Connection 包装器"""
    def __init__(self, conn):
        self._conn = conn

    def execute(self, operation, parameters=()):
        start = time.perf_counter()
        try:
            return self._conn.execute(operation, parameters)
        finally:
            elapsed = time.perf_counter() - start
            operation_type = operation.strip().split()[0].upper()
            _get_db_metrics().labels(operation=operation_type).observe(elapsed)

    def cursor(self):
        return MonitoredCursor(self._conn.cursor())

    def commit(self):
        return self._conn.commit()

    def close(self):
        return self._conn.close()

    def __getattr__(self, name):
        return getattr(self._conn, name)


def get_db():
    """获取数据库连接"""
    if 'db' not in g:
        raw_conn = sqlite3.connect(DATABASE, check_same_thread=False)
        raw_conn.row_factory = sqlite3.Row
        raw_conn.execute("PRAGMA foreign_keys = ON")
        raw_conn.execute("PRAGMA journal_mode = WAL")
        raw_conn.execute("PRAGMA busy_timeout = 5000")
        raw_conn.execute("PRAGMA wal_autocheckpoint = 500")
        raw_conn.execute("PRAGMA synchronous = NORMAL")
        g.db = MonitoredConnection(raw_conn)
    return g.db


def close_db(e=None):
    """关闭数据库连接"""
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_db():
    """初始化数据库"""
    conn = sqlite3.connect(DATABASE)
    try:
        cursor = conn.cursor()

        # 创建用户表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                name TEXT DEFAULT '',
                avatar TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # 创建文章表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                category TEXT DEFAULT '未分类',
                tags TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                views INTEGER DEFAULT 0,
                is_favorite INTEGER DEFAULT 0,
                is_draft INTEGER DEFAULT 0,
                user_id INTEGER,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')

        # 创建分类表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                color TEXT DEFAULT '#667eea',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                user_id INTEGER
            )
        ''')

        # 创建猕猴桃销售表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS kiwi_sales (
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
            )
        ''')

        # 检查并添加remark列（用于已存在的表）
        cursor.execute("PRAGMA table_info(kiwi_sales)")
        columns = [col[1] for col in cursor.fetchall()]
        if 'remark' not in columns:
            cursor.execute("ALTER TABLE kiwi_sales ADD COLUMN remark TEXT")

        # 检查并添加quantity列
        if 'quantity' not in columns:
            cursor.execute("ALTER TABLE kiwi_sales ADD COLUMN quantity INTEGER DEFAULT 0")

        # 检查并添加payment_amount列
        if 'payment_amount' not in columns:
            cursor.execute("ALTER TABLE kiwi_sales ADD COLUMN payment_amount REAL DEFAULT 0.00")

        # 检查并添加status列（替换ship_date）
        if 'status' not in columns:
            cursor.execute("ALTER TABLE kiwi_sales ADD COLUMN status TEXT DEFAULT '未发货'")

        # 检查并添加 token_version 列（用于踢掉旧登录）
        cursor.execute("PRAGMA table_info(users)")
        user_columns = [col[1] for col in cursor.fetchall()]
        if 'token_version' not in user_columns:
            cursor.execute("ALTER TABLE users ADD COLUMN token_version INTEGER DEFAULT 0")

        # 创建加班记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS overtime_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                overtime_type TEXT NOT NULL,
                date TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                duration REAL NOT NULL,
                remark TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                user_id INTEGER,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')

        # 创建记账表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                amount REAL NOT NULL,
                remark TEXT DEFAULT '',
                date TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                user_id INTEGER,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')

        # 建索引（放在所有 CREATE TABLE 之后）
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_articles_user_id ON articles(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_articles_updated_at ON articles(updated_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_kiwi_sales_user_id ON kiwi_sales(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_overtime_user_id ON overtime_records(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_overtime_date ON overtime_records(date)")
        cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_overtime_user_date ON overtime_records(user_id, date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_expenses_user_id ON expenses(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_expenses_date ON expenses(date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_expenses_category ON expenses(category)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_articles_user_category ON articles(user_id, category)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_articles_user_updated ON articles(user_id, updated_at DESC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_kiwi_sales_user_created ON kiwi_sales(user_id, created_at DESC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_expenses_user_date_cat ON expenses(user_id, date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_expenses_user_yearmonth ON expenses(user_id, substr(date, 1, 7))")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_expenses_user_month ON expenses(user_id, substr(date, 6, 2))")

        # 检查是否已有分类，如果没有则插入默认分类
        cursor.execute('SELECT COUNT(*) FROM categories')
        count = cursor.fetchone()[0]
        if count == 0:
            # 只在数据库为空时插入默认分类
            cursor.execute("INSERT INTO categories (name, color, user_id) VALUES ('技术', '#667eea', 0)")
            cursor.execute("INSERT INTO categories (name, color, user_id) VALUES ('生活', '#764ba2', 0)")
            cursor.execute("INSERT INTO categories (name, color, user_id) VALUES ('学习', '#f093fb', 0)")
            cursor.execute("INSERT INTO categories (name, color, user_id) VALUES ('工作', '#4facfe', 0)")

        conn.commit()
    finally:
        conn.close()
