from flask import Flask, request, jsonify, send_from_directory, g, make_response
import io
import csv
import urllib.parse
import codecs
from flask_cors import CORS
import sqlite3
from datetime import datetime, timedelta, timezone
import os
import re
from werkzeug.utils import secure_filename
import jwt
from passlib.hash import pbkdf2_sha256
from functools import wraps

# 调试启动信息
print("="*50)
print("正在启动 Echo...")
print(f"当前文件: {__file__}")
print(f"工作目录: {os.getcwd()}")
print("="*50)

app = Flask(__name__, static_folder='static')
CORS(app, origins=['http://localhost:5001', 'http://127.0.0.1:5001'])
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or os.urandom(32).hex()
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB 上传大小限制

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(app.static_folder, 'favicon.ico', mimetype='image/x-icon')

DATABASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'knowledge_base.db')
UPLOAD_FOLDER = os.path.join('static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def sanitize_csv_field(value):
    if value and isinstance(value, str) and value and value[0] in ('=', '+', '-', '@'):
        return "'" + value
    return value

def get_db():
    """获取数据库连接"""
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(e=None):
    """关闭数据库连接"""
    db = g.pop('db', None)
    if db is not None:
        db.close()

def generate_token(user_id):
    """生成JWT token"""
    payload = {
        'user_id': user_id,
        'exp': datetime.now(timezone.utc) + timedelta(days=7)  # 7天过期
    }
    return jwt.encode(payload, app.config['SECRET_KEY'], algorithm='HS256')

def verify_token(token):
    """验证JWT token"""
    try:
        payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
        return payload['user_id']
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def login_required(f):
    """登录装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'error': '未提供认证token'}), 401
        
        token = token.replace('Bearer ', '')
        user_id = verify_token(token)
        if not user_id:
            return jsonify({'error': '无效或过期的token'}), 401
        
        g.user_id = user_id
        return f(*args, **kwargs)
    return decorated_function

def init_db():
    """初始化数据库"""
    conn = sqlite3.connect(DATABASE)
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

    # 检查是否已有分类，如果没有则插入默认分类
    cursor.execute('SELECT COUNT(*) FROM categories')
    count = cursor.fetchone()[0]
    if count == 0:
        # 只在数据库为空时插入默认分类
        cursor.execute("INSERT INTO categories (name, color) VALUES ('技术', '#667eea')")
        cursor.execute("INSERT INTO categories (name, color) VALUES ('生活', '#764ba2')")
        cursor.execute("INSERT INTO categories (name, color) VALUES ('学习', '#f093fb')")
        cursor.execute("INSERT INTO categories (name, color) VALUES ('工作', '#4facfe')")

    conn.commit()
    conn.close()

@app.route('/api/auth/register', methods=['POST'])
def register():
    """用户注册"""
    data = request.get_json()
    if not data:
        return jsonify({'error': '请提供用户名、密码和中文名'}), 400
    username = (data.get('username') or '').strip()
    password = data.get('password')
    name = (data.get('name') or '').strip()

    if not username or not password:
        return jsonify({'error': '用户名和密码不能为空'}), 400
    
    if len(username) < 3 or len(password) < 6:
        return jsonify({'error': '用户名至少3个字符，密码至少6个字符，且需包含字母和数字'}), 400
    if not re.search(r'[A-Za-z]', password) or not re.search(r'\d', password):
        return jsonify({'error': '密码必须同时包含字母和数字'}), 400
    
    db = get_db()
    cursor = db.cursor()
    
    try:
        hashed_password = pbkdf2_sha256.hash(password)
        cursor.execute('INSERT INTO users (username, password, name) VALUES (?, ?, ?)', (username, hashed_password, name))
        user_id = cursor.lastrowid
        db.commit()
        
        token = generate_token(user_id)
        return jsonify({'id': user_id, 'username': username, 'name': name, 'token': token, 'message': '注册成功'}), 201
    except sqlite3.IntegrityError:
        return jsonify({'error': '用户名已存在'}), 400

@app.route('/api/auth/login', methods=['POST'])
def login():
    """用户登录"""
    data = request.get_json()
    if not data:
        return jsonify({'error': '请提供用户名和密码'}), 400
    username = (data.get('username') or '').strip()
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'error': '用户名和密码不能为空'}), 400
    
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
    user = cursor.fetchone()
    
    if not user or not pbkdf2_sha256.verify(password, user['password']):
        return jsonify({'error': '用户名或密码错误'}), 401
    
    token = generate_token(user['id'])
    # 检查 user 中是否有对应的列
    name = user['name'] if 'name' in user.keys() else ''
    avatar = user['avatar'] if 'avatar' in user.keys() else ''
    return jsonify({'id': user['id'], 'username': user['username'], 'name': name, 'avatar': avatar, 'token': token, 'message': '登录成功'})

@app.route('/')
def index():
    """返回首页"""
    return send_from_directory('static', 'index.html')

@app.route('/api/auth/me', methods=['GET', 'PUT'])
@login_required
def get_current_user():
    """获取或更新当前用户信息"""
    if request.method == 'GET':
        db = get_db()
        cursor = db.cursor()
        cursor.execute('SELECT id, username, name, avatar, created_at FROM users WHERE id = ?', (g.user_id,))
        user = cursor.fetchone()
        return jsonify(dict(user))
    elif request.method == 'PUT':
        data = request.get_json()
        name = data.get('name', '').strip()
        avatar = data.get('avatar', '')
        
        db = get_db()
        cursor = db.cursor()
        
        try:
            cursor.execute('UPDATE users SET name = ?, avatar = ? WHERE id = ?', (name, avatar, g.user_id))
            db.commit()
            
            # 返回更新后的用户信息
            cursor.execute('SELECT id, username, name, avatar, created_at FROM users WHERE id = ?', (g.user_id,))
            user = cursor.fetchone()
            return jsonify(dict(user))
        except Exception as e:
            return jsonify({'error': '更新用户信息失败'}), 500

@app.route('/api/articles', methods=['GET'])
@login_required
def get_articles():
    db = get_db()
    cursor = db.cursor()
    category = request.args.get('category')
    tag = request.args.get('tag')
    search = request.args.get('search')
    favorite = request.args.get('favorite')
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 5, type=int)

    base_query = 'SELECT * FROM articles WHERE user_id = ?'
    count_query = 'SELECT COUNT(*) FROM articles WHERE user_id = ?'
    params = [g.user_id]

    if category:
        base_query += ' AND category = ?'
        count_query += ' AND category = ?'
        params.append(category)
    if tag:
        base_query += ' AND tags LIKE ?'
        count_query += ' AND tags LIKE ?'
        params.append(f'%{tag}%')
    if search:
        base_query += ' AND (title LIKE ? OR content LIKE ?)'
        count_query += ' AND (title LIKE ? OR content LIKE ?)'
        params.extend([f'%{search}%', f'%{search}%'])
    if favorite == 'true':
        base_query += ' AND is_favorite = 1'
        count_query += ' AND is_favorite = 1'

    cursor.execute(count_query, params)
    total = cursor.fetchone()[0]

    offset = (page - 1) * page_size
    base_query += ' ORDER BY updated_at DESC LIMIT ? OFFSET ?'
    params.extend([page_size, offset])

    cursor.execute(base_query, params)
    articles = [dict(row) for row in cursor.fetchall()]

    return jsonify({
        'articles': articles,
        'total': total,
        'page': page,
        'page_size': page_size
    })

@app.route('/api/articles/batch-delete', methods=['POST'])
@login_required
def batch_delete_articles():
    data = request.get_json()
    ids = data.get('ids', [])
    if not ids or not isinstance(ids, list):
        return jsonify({'error': '请提供要删除的文章ID列表'}), 400
    if len(ids) > 100:
        return jsonify({'error': '单次删除不能超过100篇文章'}), 400
    db = get_db()
    cursor = db.cursor()
    placeholders = ','.join(['?'] * len(ids))
    cursor.execute(f'DELETE FROM articles WHERE id IN ({placeholders}) AND user_id=?', ids + [g.user_id])
    deleted = cursor.rowcount
    db.commit()
    return jsonify({'message': f'成功删除 {deleted} 条记录', 'deleted': deleted})

@app.route('/api/articles/navigate', methods=['GET'])
@login_required
def get_navigate_article():
    current_id = request.args.get('current_id', type=int)
    direction = request.args.get('direction', 'next')
    
    if not current_id:
        return jsonify({'error': '缺少参数'}), 400
    
    user_id = g.user_id
    
    try:
        db = get_db()
        cursor = db.cursor()
        
        if direction == 'prev':
            query = 'SELECT * FROM articles WHERE id < ? AND user_id = ? ORDER BY id DESC LIMIT 1'
        else:
            query = 'SELECT * FROM articles WHERE id > ? AND user_id = ? ORDER BY id ASC LIMIT 1'
        
        cursor.execute(query, (current_id, user_id))
        article = cursor.fetchone()
        
        if article:
            article_dict = dict(article)
            article_dict['is_top'] = 0
            return jsonify({'article': article_dict})
        else:
            return jsonify({'error': '没有更多文章'}), 404
    except Exception as e:
        return jsonify({'error': '获取导航文章失败'}), 500

@app.route('/api/articles/<int:article_id>', methods=['GET'])
@login_required
def get_article(article_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT * FROM articles WHERE id = ? AND user_id = ?', (article_id, g.user_id))
    article = cursor.fetchone()
    if article:
        cursor.execute('UPDATE articles SET views = views + 1 WHERE id = ?', (article_id,))
        db.commit()
        return jsonify(dict(article))
    return jsonify({'error': '文章不存在'}), 404

@app.route('/api/articles', methods=['POST'])
@login_required
def create_article():
    data = request.get_json()
    title = data.get('title')
    content = data.get('content')
    category = data.get('category', '未分类')
    tags = data.get('tags', '')
    is_draft = data.get('is_draft', 0)

    if not is_draft:
        if not title:
            return jsonify({'error': '标题不能为空'}), 400
        if not content:
            return jsonify({'error': '内容不能为空'}), 400

    db = get_db()
    cursor = db.cursor()
    cursor.execute('INSERT INTO articles (title, content, category, tags, is_draft, user_id) VALUES (?, ?, ?, ?, ?, ?)',
                  (title, content, category, tags, int(is_draft), g.user_id))
    article_id = cursor.lastrowid
    db.commit()
    return jsonify({'id': article_id, 'message': '创建成功'}), 201

@app.route('/api/articles/<int:article_id>', methods=['PUT'])
@login_required
def update_article(article_id):
    data = request.get_json()
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT id FROM articles WHERE id = ? AND user_id = ?', (article_id, g.user_id))
    if not cursor.fetchone():
        return jsonify({'error': '文章不存在'}), 404

    updates = []
    params = []
    if 'title' in data:
        updates.append('title = ?')
        params.append(data['title'])
    if 'content' in data:
        updates.append('content = ?')
        params.append(data['content'])
    if 'category' in data:
        updates.append('category = ?')
        params.append(data['category'])
    if 'tags' in data:
        updates.append('tags = ?')
        params.append(data['tags'])
    if 'is_favorite' in data:
        updates.append('is_favorite = ?')
        params.append(int(data['is_favorite']))
    if 'is_draft' in data:
        updates.append('is_draft = ?')
        params.append(int(data['is_draft']))

    updates.append('updated_at = ?')
    params.append(datetime.now())
    params.append(article_id)
    params.append(g.user_id)

    cursor.execute(f"UPDATE articles SET {', '.join(updates)} WHERE id = ? AND user_id = ?", params)
    db.commit()
    return jsonify({'message': '更新成功'})

@app.route('/api/articles/<int:article_id>', methods=['DELETE'])
@login_required
def delete_article(article_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute('DELETE FROM articles WHERE id = ? AND user_id = ?', (article_id, g.user_id))
    if cursor.rowcount == 0:
        return jsonify({'error': '文章不存在'}), 404
    db.commit()
    return jsonify({'message': '删除成功'})

@app.route('/api/articles/<int:article_id>/favorite', methods=['POST'])
@login_required
def toggle_favorite(article_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute('UPDATE articles SET is_favorite = NOT is_favorite WHERE id = ? AND user_id = ?', (article_id, g.user_id))
    if cursor.rowcount == 0:
        return jsonify({'error': '文章不存在'}), 404
    cursor.execute('SELECT is_favorite FROM articles WHERE id = ? AND user_id = ?', (article_id, g.user_id))
    is_favorite = cursor.fetchone()[0]
    db.commit()
    return jsonify({'is_favorite': bool(is_favorite)})

@app.route('/api/categories', methods=['GET'])
@login_required
def get_categories():
    db = get_db()
    cursor = db.cursor()
    cursor.execute('''
        SELECT c.*, COUNT(a.id) as article_count
        FROM categories c
        LEFT JOIN articles a ON c.name = a.category AND a.user_id = ?
        GROUP BY c.id
        ORDER BY c.created_at
    ''', (g.user_id,))
    categories = [dict(row) for row in cursor.fetchall()]
    return jsonify(categories)

@app.route('/api/categories', methods=['POST'])
@login_required
def create_category():
    data = request.get_json()
    name = data.get('name', '').strip()
    color = data.get('color', '#667eea')
    if not name:
        return jsonify({'error': '分类名称不能为空'}), 400
    if len(name) > 50:
        return jsonify({'error': '分类名称不能超过50个字符'}), 400
    if re.search(r'[<>"\'&]', name):
        return jsonify({'error': '分类名称不能包含特殊字符'}), 400
    db = get_db()
    cursor = db.cursor()
    try:
        cursor.execute('INSERT INTO categories (name, color) VALUES (?, ?)', (name, color))
        category_id = cursor.lastrowid
        db.commit()
        return jsonify({'id': category_id, 'message': '创建成功'}), 201
    except sqlite3.IntegrityError:
        return jsonify({'error': '分类已存在'}), 400

@app.route('/api/categories/<category_id>', methods=['DELETE'])
@login_required
def delete_category(category_id):
    db = get_db()
    cursor = db.cursor()
    
    # 先检查是否是纯数字，如果是纯数字则按名称删除，避免误删
    is_numeric = isinstance(category_id, str) and category_id.isdigit()
    
    if not is_numeric:
        # 不是纯数字，尝试按ID删除
        try:
            cursor.execute('SELECT name FROM categories WHERE id = ? AND user_id = ?', (int(category_id), g.user_id))
            row = cursor.fetchone()
            if row:
                cat_name = row['name']
                cursor.execute('DELETE FROM categories WHERE id = ? AND user_id = ?', (int(category_id), g.user_id))
                cursor.execute("UPDATE articles SET category = '未分类' WHERE category = ? AND user_id = ?", (cat_name, g.user_id))
                db.commit()
                return jsonify({'message': '删除成功'})
        except (ValueError, TypeError):
            pass
    
    # 按名称删除
    category_name = str(category_id)
    cursor.execute('DELETE FROM categories WHERE name = ? AND user_id = ?', (category_name, g.user_id))
    if cursor.rowcount > 0:
        # 将引用该分类的文章设为"未分类"
        cursor.execute("UPDATE articles SET category = '未分类' WHERE category = ? AND user_id = ?", (category_name, g.user_id))
        db.commit()
        return jsonify({'message': '删除成功'})
    
    # 没有找到记录
    db.commit()
    return jsonify({'message': '删除失败，分类不存在'}), 404

@app.route('/api/stats', methods=['GET'])
@login_required
def get_stats():
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT COUNT(*) FROM articles WHERE user_id = ?', (g.user_id,))
    total_articles = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM articles WHERE is_favorite = 1 AND user_id = ?', (g.user_id,))
    favorites = cursor.fetchone()[0]
    cursor.execute('SELECT SUM(views) FROM articles WHERE user_id = ?', (g.user_id,))
    total_views = cursor.fetchone()[0] or 0
    cursor.execute('SELECT COUNT(DISTINCT category) FROM articles WHERE user_id = ?', (g.user_id,))
    categories_used = cursor.fetchone()[0]
    return jsonify({
        'total_articles': total_articles,
        'favorites': favorites,
        'total_views': total_views,
        'categories_used': categories_used
    })

@app.route('/api/tags', methods=['GET'])
@login_required
def get_all_tags():
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT tags FROM articles WHERE tags != "" AND user_id = ?', (g.user_id,))
    all_tags = []
    for row in cursor.fetchall():
        if row[0]:
            tags = [t.strip() for t in row[0].split(',') if t.strip()]
            all_tags.extend(tags)
    tag_counts = {}
    for tag in all_tags:
        tag_counts[tag] = tag_counts.get(tag, 0) + 1
    sorted_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)
    return jsonify([{'name': tag, 'count': count} for tag, count in sorted_tags])

@app.route('/api/upload', methods=['POST'])
@login_required
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': '没有文件上传'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': '没有选择文件'}), 400
    if file and '.' in file.filename and file.filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS:
        filename = secure_filename(file.filename)
        # 生成唯一文件名
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{timestamp}_{filename}"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)
        # 返回相对路径
        url = f"/static/uploads/{filename}"
        return jsonify({'url': url, 'filename': filename})
    return jsonify({'error': '不支持的文件类型'}), 400

# 获取猕猴桃销售列表
@app.route('/api/kiwi-sales', methods=['GET'])
@login_required
def get_kiwi_sales():
    db = get_db()
    cursor = db.cursor()
    
    # 分页参数
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 5, type=int)
    offset = (page - 1) * page_size
    
    # 搜索参数
    customer = request.args.get('customer', '', type=str)
    phone = request.args.get('phone', '', type=str)
    year = request.args.get('year', '', type=str)
    
    # 构建查询
    conditions = ['user_id = ?']
    params = [g.user_id]
    
    if customer:
        conditions.append('customer_name LIKE ?')
        params.append(f'%{customer}%')
    
    if phone:
        conditions.append('phone LIKE ?')
        params.append(f'%{phone}%')
    
    if year:
        conditions.append("strftime('%Y', order_date) = ?")
        params.append(year)
    
    where_clause = 'WHERE ' + ' AND '.join(conditions)
    
    # 获取总数
    count_query = f'SELECT COUNT(*) FROM kiwi_sales {where_clause}'
    cursor.execute(count_query, params)
    total = cursor.fetchone()[0]
    
    # 获取数据
    data_query = f'''SELECT * FROM kiwi_sales {where_clause} ORDER BY created_at DESC LIMIT ? OFFSET ?'''
    params.extend([page_size, offset])
    cursor.execute(data_query, params)
    
    sales = [dict(row) for row in cursor.fetchall()]
    
    return jsonify({
        'sales': sales,
        'total': total,
        'page': page,
        'page_size': page_size
    })

# 添加猕猴桃销售记录
@app.route('/api/kiwi-sales', methods=['POST'])
@login_required
def add_kiwi_sale():
    data = request.get_json()
    
    if not data:
        return jsonify({'error': '请提供订单信息（客户名、电话、地址、接单日期等）'}), 400
    
    customer_name = data.get('customer_name', '').strip()
    if not customer_name:
        return jsonify({'error': '客户名不能为空'}), 400
    if len(customer_name) > 50:
        return jsonify({'error': '客户名不能超过50个字符'}), 400
    
    # 电话校验
    phone = data.get('phone', '').strip()
    if not phone:
        return jsonify({'error': '电话号码不能为空'}), 400
    if not phone.isdigit() or len(phone) != 11:
        return jsonify({'error': '请输入有效的11位手机号码'}), 400
    
    # 地址校验
    address = data.get('address', '').strip()
    if not address:
        return jsonify({'error': '收货地址不能为空'}), 400
    if len(address) > 200:
        return jsonify({'error': '地址不能超过200个字符'}), 400
    
    # 接单日期校验
    order_date = data.get('order_date')
    if not order_date:
        return jsonify({'error': '接单日期不能为空'}), 400
    
    # 发货日期校验
    ship_date = data.get('ship_date', '')
    if ship_date and ship_date < order_date:
        return jsonify({'error': '发货日期不能早于接单日期'}), 400
    
    # 运单号校验
    tracking_number = data.get('tracking_number', '').strip()
    if tracking_number and len(tracking_number) > 50:
        return jsonify({'error': '运单号不能超过50个字符'}), 400
    
    # 备注校验
    remark = data.get('remark', '').strip()
    if remark and len(remark) > 50:
        return jsonify({'error': '备注不能超过50个字符'}), 400

    # 数量校验
    quantity = data.get('quantity', 0)
    if not isinstance(quantity, int) or quantity < 0:
        return jsonify({'error': '数量必须是正整数'}), 400

    # 支付金额校验
    payment_amount = data.get('payment_amount', 0.00)
    try:
        payment_amount = float(payment_amount)
        if payment_amount < 0:
            return jsonify({'error': '支付金额不能为负数'}), 400
        payment_amount = round(payment_amount, 2)
    except (ValueError, TypeError):
        return jsonify({'error': '支付金额必须是数字'}), 400

    # 状态校验
    status = data.get('status', '未发货')
    if status not in ['已发货', '未发货']:
        return jsonify({'error': '状态必须是已发货或未发货'}), 400

    # 数据库操作
    db = get_db()
    cursor = db.cursor()
    cursor.execute('''
        INSERT INTO kiwi_sales (customer_name, phone, address, order_date, status, tracking_number, remark, quantity, payment_amount, user_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (customer_name, phone, address, order_date, status, tracking_number, remark, quantity, payment_amount, g.user_id))
    db.commit()

    return jsonify({'message': '添加成功', 'id': cursor.lastrowid}), 201

# 更新猕猴桃销售记录
@app.route('/api/kiwi-sales/<int:sale_id>', methods=['PUT'])
@login_required
def update_kiwi_sale(sale_id):
    data = request.get_json()
    
    if not data:
        return jsonify({'error': '请提供订单信息（客户名、电话、地址、接单日期等）'}), 400
    
    customer_name = data.get('customer_name', '').strip()
    if not customer_name:
        return jsonify({'error': '客户名不能为空'}), 400
    if len(customer_name) > 50:
        return jsonify({'error': '客户名不能超过50个字符'}), 400
    
    # 电话校验
    phone = data.get('phone', '').strip()
    if not phone:
        return jsonify({'error': '电话号码不能为空'}), 400
    if not phone.isdigit() or len(phone) != 11:
        return jsonify({'error': '请输入有效的11位手机号码'}), 400
    
    # 地址校验
    address = data.get('address', '').strip()
    if not address:
        return jsonify({'error': '收货地址不能为空'}), 400
    if len(address) > 200:
        return jsonify({'error': '地址不能超过200个字符'}), 400
    
    # 接单日期校验
    order_date = data.get('order_date')
    if not order_date:
        return jsonify({'error': '接单日期不能为空'}), 400
    
    # 发货日期校验
    ship_date = data.get('ship_date', '')
    if ship_date and ship_date < order_date:
        return jsonify({'error': '发货日期不能早于接单日期'}), 400
    
    # 运单号校验
    tracking_number = data.get('tracking_number', '').strip()
    if tracking_number and len(tracking_number) > 50:
        return jsonify({'error': '运单号不能超过50个字符'}), 400
    
    # 备注校验
    remark = data.get('remark', '').strip()
    if remark and len(remark) > 50:
        return jsonify({'error': '备注不能超过50个字符'}), 400

    # 数量校验
    quantity = data.get('quantity', 0)
    if not isinstance(quantity, int) or quantity < 0:
        return jsonify({'error': '数量必须是正整数'}), 400

    # 支付金额校验
    payment_amount = data.get('payment_amount', 0.00)
    try:
        payment_amount = float(payment_amount)
        if payment_amount < 0:
            return jsonify({'error': '支付金额不能为负数'}), 400
        payment_amount = round(payment_amount, 2)
    except (ValueError, TypeError):
        return jsonify({'error': '支付金额必须是数字'}), 400

    # 状态校验
    status = data.get('status', '未发货')
    if status not in ['已发货', '未发货']:
        return jsonify({'error': '状态必须是已发货或未发货'}), 400

    # 数据库操作
    db = get_db()
    cursor = db.cursor()
    cursor.execute('''
        UPDATE kiwi_sales SET customer_name=?, phone=?, address=?, order_date=?, status=?, tracking_number=?, remark=?, quantity=?, payment_amount=?
        WHERE id=? AND user_id=?
    ''', (customer_name, phone, address, order_date, status, tracking_number, remark, quantity, payment_amount, sale_id, g.user_id))
    if cursor.rowcount == 0:
        return jsonify({'error': '记录不存在'}), 404
    db.commit()
    return jsonify({'message': '更新成功'})

# 删除猕猴桃销售记录
@app.route('/api/kiwi-sales/<int:sale_id>', methods=['DELETE'])
@login_required
def delete_kiwi_sale(sale_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute('DELETE FROM kiwi_sales WHERE id=? AND user_id=?', (sale_id, g.user_id))
    if cursor.rowcount == 0:
        return jsonify({'error': '记录不存在'}), 404
    db.commit()
    return jsonify({'message': '删除成功'})

# 批量删除猕猴桃销售记录
@app.route('/api/kiwi-sales/batch-delete', methods=['POST'])
@login_required
def batch_delete_kiwi_sales():
    data = request.get_json()
    ids = data.get('ids', [])
    if not ids or not isinstance(ids, list):
        return jsonify({'error': '请提供要删除的记录ID列表'}), 400
    db = get_db()
    cursor = db.cursor()
    placeholders = ','.join(['?'] * len(ids))
    cursor.execute(f'DELETE FROM kiwi_sales WHERE id IN ({placeholders}) AND user_id=?', ids + [g.user_id])
    deleted = cursor.rowcount
    db.commit()
    return jsonify({'message': f'成功删除 {deleted} 条记录', 'deleted': deleted})

# 猕猴桃销售报表统计
@app.route('/api/kiwi-sales-report', methods=['GET'])
@login_required
def get_kiwi_sales_report():
    db = get_db()
    cursor = db.cursor()
    
    # 获取分页参数
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 5, type=int)
    
    # 获取年份筛选参数
    year = request.args.get('year', '', type=str)
    
    # 构建年份筛选条件
    year_filter = ''
    year_params = []
    if year:
        year_filter = "AND strftime('%Y', order_date) = ?"
        year_params = [year]
    
    # 先获取所有客户数据进行分组计算
    cursor.execute(f'''
        SELECT customer_name, remark, SUM(quantity) as total_quantity, SUM(payment_amount) as total_amount
        FROM kiwi_sales
        WHERE user_id = ? AND customer_name IS NOT NULL AND customer_name != '' {year_filter}
        GROUP BY customer_name, remark
        ORDER BY customer_name, remark
    ''', (g.user_id,) + tuple(year_params))
    
    all_results = [dict(row) for row in cursor.fetchall()]
    
    # 按客户名分组
    grouped_data = {}
    for row in all_results:
        customer = row['customer_name']
        if customer not in grouped_data:
            grouped_data[customer] = {
                'customer_name': customer,
                'items': [],
                'total_quantity': 0,
                'total_amount': 0
            }
        grouped_data[customer]['items'].append(row)
        grouped_data[customer]['total_quantity'] += row['total_quantity']
        grouped_data[customer]['total_amount'] += row['total_amount']
    
    # 转换为列表并计算分页
    customers_list = list(grouped_data.values())
    total_customers = len(customers_list)
    total_pages = (total_customers + page_size - 1) // page_size
    
    # 获取当前页数据
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    page_customers = customers_list[start_idx:end_idx]
    
    # 展平数据用于前端显示
    report_data = []
    for customer in page_customers:
        report_data.extend(customer['items'])

    # 汇总统计：按规格（remark）分组统计数量和金额
    cursor.execute(f'''
        SELECT remark, SUM(quantity) as total_quantity, SUM(payment_amount) as total_amount
        FROM kiwi_sales
        WHERE user_id = ? {year_filter}
        GROUP BY remark
    ''', (g.user_id,) + tuple(year_params))
    summary_rows = cursor.fetchall()
    summary = {}
    total_quantity = 0
    total_amount = 0
    for row in summary_rows:
        remark = row['remark'] or '其他'
        qty = row['total_quantity'] or 0
        amt = row['total_amount'] or 0
        total_quantity += qty
        total_amount += amt
        if remark not in summary:
            summary[remark] = {'quantity': 0, 'amount': 0}
        summary[remark]['quantity'] += qty
        summary[remark]['amount'] += amt

    summary_output = {k: {'quantity': v['quantity'], 'amount': round(v['amount'], 2)} for k, v in summary.items()}

    return jsonify({
        'report': report_data,
        'page': page,
        'page_size': page_size,
        'total_customers': total_customers,
        'total_pages': total_pages,
        'summary': {
            **summary_output,
            'total_quantity': total_quantity,
            'total_amount': round(total_amount, 2)
        }
    })

# 加班记录 - 计算时长
def calculate_overtime_duration(overtime_type, start_time, end_time):
    """根据加班类型和时间计算加班时长"""
    end = datetime.strptime(end_time, '%H:%M')
    if overtime_type == 'weekday':
        # 平时加班统一从19:00开始计算，无论用户输入的开始时间
        start = datetime.strptime('19:00', '%H:%M')
    else:
        start = datetime.strptime(start_time, '%H:%M')
    diff_minutes = (end - start).seconds // 60
    if overtime_type == 'weekend':
        # 周末加班自动扣除12:00-14:00午餐时间（2小时=120分钟）
        lunch_start = datetime.strptime('12:00', '%H:%M')
        lunch_end = datetime.strptime('14:00', '%H:%M')
        if start < lunch_end and end > lunch_start:
            overlap_start = max(start, lunch_start)
            overlap_end = min(end, lunch_end)
            lunch_minutes = (overlap_end - overlap_start).seconds // 60
            diff_minutes -= lunch_minutes
    return round(diff_minutes / 60, 1)

# 获取加班记录列表
@app.route('/api/overtime', methods=['GET'])
@login_required
def get_overtime_records():
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 5, type=int)
    month = request.args.get('month', '', type=str)
    offset = (page - 1) * page_size

    conditions = ['user_id = ?']
    params = [g.user_id]

    if month:
        conditions.append("strftime('%Y-%m', date) = ?")
        params.append(month)

    where_clause = ' AND '.join(conditions)

    db = get_db()
    cursor = db.cursor()

    cursor.execute(f'SELECT COUNT(*) FROM overtime_records WHERE {where_clause}', params)
    total = cursor.fetchone()[0]

    cursor.execute(f'SELECT * FROM overtime_records WHERE {where_clause} ORDER BY date DESC, start_time DESC LIMIT ? OFFSET ?',
                   params + [page_size, offset])
    records = [dict(row) for row in cursor.fetchall()]

    return jsonify({
        'records': records,
        'total': total,
        'page': page,
        'page_size': page_size
    })

# 添加加班记录
@app.route('/api/overtime', methods=['POST'])
@login_required
def add_overtime_record():
    data = request.get_json()
    overtime_type = data.get('overtime_type', '')
    date = data.get('date', '').strip()
    start_time = data.get('start_time', '').strip()
    end_time = data.get('end_time', '').strip()
    remark = data.get('remark', '').strip()

    if overtime_type not in ['weekday', 'weekend']:
        return jsonify({'error': '加班类型必须是 平时加班 或 周末加班'}), 400
    if not date:
        return jsonify({'error': '日期不能为空'}), 400
    if not start_time or not end_time:
        return jsonify({'error': '开始时间和结束时间不能为空'}), 400

    try:
        datetime.strptime(start_time, '%H:%M')
        datetime.strptime(end_time, '%H:%M')
    except ValueError:
        return jsonify({'error': '时间格式错误，请使用 HH:MM 格式'}), 400

    if start_time >= end_time:
        return jsonify({'error': '结束时间必须晚于开始时间'}), 400

    # 平时加班：结束时间需在19:00-23:59范围内
    if overtime_type == 'weekday':
        if end_time < '19:00' or end_time > '23:59':
            return jsonify({'error': '平时加班结束时间需在 19:00-23:59 范围内'}), 400

    # 周末加班时间范围校验
    if overtime_type == 'weekend':
        if start_time < '08:30' or end_time > '23:59':
            return jsonify({'error': '周末加班时间范围为 08:30-23:59'}), 400

    # 检查同一天是否已有加班记录
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT id FROM overtime_records WHERE user_id = ? AND date = ?', (g.user_id, date))
    if cursor.fetchone():
        return jsonify({'error': '该日期已存在加班记录，请删除后再添加'}), 400

    manual_duration = data.get('duration')
    if manual_duration is not None:
        try:
            duration = float(manual_duration)
            if duration <= 0:
                return jsonify({'error': '时长必须大于0'}), 400
        except (ValueError, TypeError):
            return jsonify({'error': '时长格式错误'}), 400
    else:
        duration = calculate_overtime_duration(overtime_type, start_time, end_time)

    cursor.execute('INSERT INTO overtime_records (overtime_type, date, start_time, end_time, duration, remark, user_id) VALUES (?, ?, ?, ?, ?, ?, ?)',
                   (overtime_type, date, start_time, end_time, duration, remark, g.user_id))
    db.commit()

    return jsonify({'message': '添加成功', 'id': cursor.lastrowid, 'duration': duration}), 201

# 更新加班记录
@app.route('/api/overtime/<int:record_id>', methods=['PUT'])
@login_required
def update_overtime_record(record_id):
    data = request.get_json()
    overtime_type = data.get('overtime_type', '')
    date = data.get('date', '').strip()
    start_time = data.get('start_time', '').strip()
    end_time = data.get('end_time', '').strip()
    remark = data.get('remark', '').strip()

    if overtime_type not in ['weekday', 'weekend']:
        return jsonify({'error': '加班类型必须是 平时加班 或 周末加班'}), 400
    if not date:
        return jsonify({'error': '日期不能为空'}), 400
    if not start_time or not end_time:
        return jsonify({'error': '开始时间和结束时间不能为空'}), 400

    try:
        datetime.strptime(start_time, '%H:%M')
        datetime.strptime(end_time, '%H:%M')
    except ValueError:
        return jsonify({'error': '时间格式错误，请使用 HH:MM 格式'}), 400

    if start_time >= end_time:
        return jsonify({'error': '结束时间必须晚于开始时间'}), 400

    if overtime_type == 'weekday':
        if end_time < '19:00' or end_time > '23:59':
            return jsonify({'error': '平时加班结束时间需在 19:00-23:59 范围内'}), 400

    if overtime_type == 'weekend':
        if start_time < '08:30' or end_time > '23:59':
            return jsonify({'error': '周末加班时间范围为 08:30-23:59'}), 400

    manual_duration = data.get('duration')
    if manual_duration is not None:
        try:
            duration = float(manual_duration)
            if duration <= 0:
                return jsonify({'error': '时长必须大于0'}), 400
        except (ValueError, TypeError):
            return jsonify({'error': '时长格式错误'}), 400
    else:
        duration = calculate_overtime_duration(overtime_type, start_time, end_time)

    db = get_db()
    cursor = db.cursor()

    # 检查同一天是否已有其他加班记录（排除自身）
    cursor.execute('SELECT id FROM overtime_records WHERE user_id = ? AND date = ? AND id != ?', (g.user_id, date, record_id))
    if cursor.fetchone():
        return jsonify({'error': '该日期已存在加班记录，请删除后再添加'}), 400

    cursor.execute('UPDATE overtime_records SET overtime_type=?, date=?, start_time=?, end_time=?, duration=?, remark=? WHERE id=? AND user_id=?',
                   (overtime_type, date, start_time, end_time, duration, remark, record_id, g.user_id))
    if cursor.rowcount == 0:
        return jsonify({'error': '记录不存在'}), 404
    db.commit()

    return jsonify({'message': '更新成功', 'duration': duration})

# 删除加班记录（单条）
@app.route('/api/overtime/<int:record_id>', methods=['DELETE'])
@login_required
def delete_overtime_record(record_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute('DELETE FROM overtime_records WHERE id=? AND user_id=?', (record_id, g.user_id))
    if cursor.rowcount == 0:
        return jsonify({'error': '记录不存在'}), 404
    db.commit()
    return jsonify({'message': '删除成功'})

# 批量删除加班记录
@app.route('/api/overtime/batch-delete', methods=['POST'])
@login_required
def batch_delete_overtime_records():
    data = request.get_json()
    ids = data.get('ids', [])
    if not ids or not isinstance(ids, list):
        return jsonify({'error': '请提供要删除的记录ID列表'}), 400
    db = get_db()
    cursor = db.cursor()
    placeholders = ','.join(['?'] * len(ids))
    cursor.execute(f'DELETE FROM overtime_records WHERE id IN ({placeholders}) AND user_id=?', ids + [g.user_id])
    deleted = cursor.rowcount
    db.commit()
    return jsonify({'message': f'成功删除 {deleted} 条记录', 'deleted': deleted})



# 加班月度统计
@app.route('/api/overtime/stats', methods=['GET'])
@login_required
def get_overtime_stats():
    month = request.args.get('month', '', type=str)
    db = get_db()
    cursor = db.cursor()

    if month:
        cursor.execute("SELECT SUM(duration) FROM overtime_records WHERE user_id = ? AND overtime_type = 'weekday' AND strftime('%Y-%m', date) = ?", (g.user_id, month))
        weekday_total = cursor.fetchone()[0] or 0
        cursor.execute("SELECT SUM(duration) FROM overtime_records WHERE user_id = ? AND overtime_type = 'weekend' AND strftime('%Y-%m', date) = ?", (g.user_id, month))
        weekend_total = cursor.fetchone()[0] or 0
        cursor.execute("SELECT COUNT(*) FROM overtime_records WHERE user_id = ? AND strftime('%Y-%m', date) = ?", (g.user_id, month))
        total_count = cursor.fetchone()[0]
    else:
        cursor.execute("SELECT SUM(duration) FROM overtime_records WHERE user_id = ? AND overtime_type = 'weekday'", (g.user_id,))
        weekday_total = cursor.fetchone()[0] or 0
        cursor.execute("SELECT SUM(duration) FROM overtime_records WHERE user_id = ? AND overtime_type = 'weekend'", (g.user_id,))
        weekend_total = cursor.fetchone()[0] or 0
        cursor.execute("SELECT COUNT(*) FROM overtime_records WHERE user_id = ?", (g.user_id,))
        total_count = cursor.fetchone()[0]

    return jsonify({
        'weekday_total': round(weekday_total, 1),
        'weekend_total': round(weekend_total, 1),
        'total_hours': round(weekday_total + weekend_total, 1),
        'total_count': total_count
    })

# 加班月度统计（按上月21日到本月20日周期）
@app.route('/api/overtime/stats/monthly', methods=['GET'])
@login_required
def get_overtime_monthly_stats():
    month = request.args.get('month', '', type=str)
    if not month:
        return jsonify({'error': '请提供month参数 (YYYY-MM)'}), 400

    try:
        target = datetime.strptime(month, '%Y-%m')
    except ValueError:
        return jsonify({'error': '月份格式错误，请使用 YYYY-MM'}), 400

    # 统计周期：上月21日 到 本月20日（含）
    period_start_month = target.month - 1 if target.month > 1 else 12
    period_start_year = target.year if target.month > 1 else target.year - 1
    period_start = f"{period_start_year}-{period_start_month:02d}-21"
    period_end = f"{target.year}-{target.month:02d}-20"

    db = get_db()
    cursor = db.cursor()

    cursor.execute(
        "SELECT SUM(duration) FROM overtime_records WHERE user_id = ? AND overtime_type = 'weekday' AND date >= ? AND date <= ?",
        (g.user_id, period_start, period_end)
    )
    weekday_total = cursor.fetchone()[0] or 0

    cursor.execute(
        "SELECT SUM(duration) FROM overtime_records WHERE user_id = ? AND overtime_type = 'weekend' AND date >= ? AND date <= ?",
        (g.user_id, period_start, period_end)
    )
    weekend_total = cursor.fetchone()[0] or 0

    cursor.execute(
        "SELECT COUNT(*) FROM overtime_records WHERE user_id = ? AND date >= ? AND date <= ?",
        (g.user_id, period_start, period_end)
    )
    total_count = cursor.fetchone()[0]

    return jsonify({
        'period_start': period_start,
        'period_end': period_end,
        'weekday_total': round(weekday_total, 1),
        'weekend_total': round(weekend_total, 1),
        'total_hours': round(weekday_total + weekend_total, 1),
        'total_count': total_count,
        'month': month
    })

# ===== 记账模块 API =====
EXPENSE_CATEGORIES = ['燃气费', '电费', '话费', '网费', '香烟', '菜肉米面油', '交通', '物业费', '水果', '其他']

@app.route('/api/expenses', methods=['GET'])
@login_required
def get_expenses():
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 10, type=int)
    month = request.args.get('month', '', type=str)
    category = request.args.get('category', '', type=str)
    offset = (page - 1) * page_size

    conditions = ['user_id = ?']
    params = [g.user_id]
    if month:
        conditions.append("strftime('%Y-%m', date) = ?")
        params.append(month)
    if category:
        conditions.append('category = ?')
        params.append(category)

    where_clause = ' AND '.join(conditions)
    db = get_db()
    cursor = db.cursor()

    cursor.execute(f'SELECT COUNT(*) FROM expenses WHERE {where_clause}', params)
    total = cursor.fetchone()[0]

    cursor.execute(f'SELECT * FROM expenses WHERE {where_clause} ORDER BY date DESC, id DESC LIMIT ? OFFSET ?',
                   params + [page_size, offset])
    records = [dict(row) for row in cursor.fetchall()]

    return jsonify({'records': records, 'total': total, 'page': page, 'page_size': page_size})


@app.route('/api/expenses/export', methods=['GET', 'POST'])
@login_required
def export_expenses():
    """导出消费记录为 CSV：
    - POST JSON {ids: [1,2,3]} 导出指定 id 列表（仅导出属于当前用户的记录）
    - GET 使用查询参数 month=YYYY-MM 或 category=分类 导出匹配的全部记录
    如果都不提供，则导出当前用户所有消费记录。
    """
    try:
        db = get_db()
        cursor = db.cursor()

        if request.method == 'POST':
            data = request.get_json() or {}
            ids = data.get('ids', [])
            if not ids:
                return jsonify({'error': 'ids不能为空'}), 400
            placeholders = ','.join(['?'] * len(ids))
            params = list(ids) + [g.user_id]
            cursor.execute(f"SELECT id, category, amount, remark, date FROM expenses WHERE id IN ({placeholders}) AND user_id = ? ORDER BY date DESC", params)
            rows = cursor.fetchall()
        else:
            month = request.args.get('month', '')
            category = request.args.get('category', '')
            conditions = ['user_id = ?']
            params = [g.user_id]
            if month:
                conditions.append("strftime('%Y-%m', date) = ?")
                params.append(month)
            if category:
                conditions.append('category = ?')
                params.append(category)
            where_clause = ' AND '.join(conditions)
            cursor.execute(f"SELECT id, category, amount, remark, date FROM expenses WHERE {where_clause} ORDER BY date DESC", params)
            rows = cursor.fetchall()

        if not rows:
            return jsonify({'error': '没有数据可导出'}), 400

        output = io.BytesIO()
        # 使用 GBK 编码（Windows中文Excel原生支持，无需BOM）
        stream_writer = codecs.getwriter('gbk')(output)
        writer = csv.writer(stream_writer, lineterminator='\n')
        writer.writerow(['ID', '分类', '金额', '日期', '备注'])
        for r in rows:
            writer.writerow([r['id'], r['category'], float(r['amount']), r['date'], r['remark'] or ''])

        csv_data = output.getvalue()
        output.close()

        response = make_response(csv_data)
        response.headers['Content-Type'] = 'text/csv;charset=gbk'
        safe_filename = f"expense_record_{datetime.utcnow().strftime('%Y%m%d')}.csv"
        response.headers['Content-Disposition'] = f"attachment; filename=\"{safe_filename}\""
        return response
    except Exception as e:
        return jsonify({'error': '导出消费记录失败'}), 500

# 猕猴桃销售订单导出
@app.route('/api/kiwi-sales/export', methods=['GET'])
@login_required
def export_kiwi_sales():
    try:
        db = get_db()
        cursor = db.cursor()
        
        # 搜索参数
        customer = request.args.get('customer', '', type=str)
        phone = request.args.get('phone', '', type=str)
        year = request.args.get('year', '', type=str)
        
        # 构建查询
        conditions = ['user_id = ?']
        params = [g.user_id]
        
        if customer:
            conditions.append('customer_name LIKE ?')
            params.append(f'%{customer}%')
        
        if phone:
            conditions.append('phone LIKE ?')
            params.append(f'%{phone}%')
        
        if year:
            conditions.append("strftime('%Y', order_date) = ?")
            params.append(year)
        
        where_clause = 'WHERE ' + ' AND '.join(conditions)
        
        cursor.execute(f'''SELECT id, customer_name, phone, address, order_date, status, tracking_number, remark, quantity, payment_amount 
                          FROM kiwi_sales {where_clause} ORDER BY created_at DESC''', params)
        rows = cursor.fetchall()
        
        if not rows:
            return jsonify({'error': '没有数据可导出'}), 400
        
        output = io.BytesIO()
        stream_writer = codecs.getwriter('gbk')(output)
        writer = csv.writer(stream_writer, lineterminator='\n')
        writer.writerow(['序号', '客户名', '电话', '地址', '接单日期', '状态', '运单号', '备注', '数量', '支付金额'])
        
        for idx, r in enumerate(rows):
            writer.writerow([
                idx + 1,
                r['customer_name'],
                r['phone'],
                r['address'],
                r['order_date'] or '',
                r['status'] or '未发货',
                r['tracking_number'] or '',
                r['remark'] or '',
                r['quantity'] or 0,
                (r['payment_amount'] or 0)
            ])
        
        csv_data = output.getvalue()
        output.close()
        
        response = make_response(csv_data)
        response.headers['Content-Type'] = 'text/csv;charset=gbk'
        safe_filename = f"kiwi_sales_{datetime.utcnow().strftime('%Y%m%d')}.csv"
        response.headers['Content-Disposition'] = f"attachment; filename=\"{safe_filename}\""
        return response
    except Exception as e:
        return jsonify({'error': '导出猕猴桃销售记录失败'}), 500

@app.route('/api/expenses', methods=['POST'])
@login_required
def add_expense():
    data = request.get_json()
    category = data.get('category', '').strip()
    amount = data.get('amount')
    remark = data.get('remark', '').strip()
    date = data.get('date', '').strip()

    if not category:
        return jsonify({'error': '请选择分类'}), 400
    if category not in EXPENSE_CATEGORIES:
        return jsonify({'error': f'无效的分类: {category}'}), 400
    if amount is None:
        return jsonify({'error': '请输入金额'}), 400
    try:
        amount = float(amount)
        if amount <= 0:
            return jsonify({'error': '金额必须大于0'}), 400
        amount = round(amount, 2)
    except (ValueError, TypeError):
        return jsonify({'error': '金额格式错误'}), 400
    if not date:
        return jsonify({'error': '请选择日期'}), 400

    db = get_db()
    cursor = db.cursor()
    cursor.execute('INSERT INTO expenses (category, amount, remark, date, user_id) VALUES (?, ?, ?, ?, ?)',
                   (category, amount, remark, date, g.user_id))
    db.commit()
    return jsonify({'message': '添加成功', 'id': cursor.lastrowid}), 201


@app.route('/api/expenses/<int:expense_id>', methods=['PUT'])
@login_required
def update_expense(expense_id):
    data = request.get_json()
    category = data.get('category', '').strip()
    amount = data.get('amount')
    remark = data.get('remark', '').strip()
    date = data.get('date', '').strip()

    if not category or category not in EXPENSE_CATEGORIES:
        return jsonify({'error': '无效的分类'}), 400
    try:
        amount = float(amount)
        if amount <= 0:
            return jsonify({'error': '金额必须大于0'}), 400
        amount = round(amount, 2)
    except (ValueError, TypeError):
        return jsonify({'error': '金额格式错误'}), 400
    if not date:
        return jsonify({'error': '请选择日期'}), 400

    db = get_db()
    cursor = db.cursor()
    cursor.execute('UPDATE expenses SET category=?, amount=?, remark=?, date=? WHERE id=? AND user_id=?',
                   (category, amount, remark, date, expense_id, g.user_id))
    if cursor.rowcount == 0:
        return jsonify({'error': '记录不存在'}), 404
    db.commit()
    return jsonify({'message': '更新成功'})


@app.route('/api/expenses/<int:expense_id>', methods=['DELETE'])
@login_required
def delete_expense(expense_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute('DELETE FROM expenses WHERE id=? AND user_id=?', (expense_id, g.user_id))
    if cursor.rowcount == 0:
        return jsonify({'error': '记录不存在'}), 404
    db.commit()
    return jsonify({'message': '删除成功'})


@app.route('/api/expenses/batch-delete', methods=['POST'])
@login_required
def batch_delete_expenses():
    data = request.get_json()
    ids = data.get('ids', [])
    if not ids or not isinstance(ids, list):
        return jsonify({'error': '请提供要删除的记录ID列表'}), 400
    db = get_db()
    cursor = db.cursor()
    placeholders = ','.join(['?'] * len(ids))
    cursor.execute(f'DELETE FROM expenses WHERE id IN ({placeholders}) AND user_id=?', ids + [g.user_id])
    deleted = cursor.rowcount
    db.commit()
    return jsonify({'message': f'成功删除 {deleted} 条记录', 'deleted': deleted})


@app.route('/api/expenses/stats', methods=['GET'])
@login_required
def get_expenses_stats():
    year = request.args.get('year', '', type=str)
    start_month = request.args.get('start_month', '', type=str)
    end_month = request.args.get('end_month', '', type=str)
    month = request.args.get('month', '', type=str)

    db = get_db()
    cursor = db.cursor()

    if month:
        conditions = ['user_id = ?', "strftime('%Y-%m', date) = ?"]
        params = [g.user_id, month]
    elif year:
        if start_month and end_month:
            conditions = ['user_id = ?', "strftime('%Y', date) = ?", "strftime('%m', date) >= ?", "strftime('%m', date) <= ?"]
            params = [g.user_id, year, start_month, end_month]
        elif start_month:
            conditions = ['user_id = ?', "strftime('%Y', date) = ?", "strftime('%m', date) >= ?"]
            params = [g.user_id, year, start_month]
        elif end_month:
            conditions = ['user_id = ?', "strftime('%Y', date) = ?", "strftime('%m', date) <= ?"]
            params = [g.user_id, year, end_month]
        else:
            conditions = ['user_id = ?', "strftime('%Y', date) = ?"]
            params = [g.user_id, year]
    else:
        conditions = ['user_id = ?']
        params = [g.user_id]

    where_clause = ' AND '.join(conditions)

    cursor.execute(f"SELECT category, SUM(amount) as total FROM expenses WHERE {where_clause} GROUP BY category ORDER BY total DESC", params)
    rows = cursor.fetchall()
    cursor.execute(f"SELECT SUM(amount) FROM expenses WHERE {where_clause}", params)
    grand_total = cursor.fetchone()[0] or 0

    categories = []
    for row in rows:
        total = row['total'] or 0
        pct = round(total / grand_total * 100, 1) if grand_total > 0 else 0
        categories.append({'category': row['category'], 'amount': round(total, 2), 'percentage': pct})

    return jsonify({'categories': categories, 'grand_total': round(grand_total, 2)})


@app.route('/api/expenses/stats/monthly', methods=['GET'])
@login_required
def get_expenses_stats_monthly():
    year = request.args.get('year', '', type=str)
    start_month = request.args.get('start_month', '', type=str)
    end_month = request.args.get('end_month', '', type=str)

    db = get_db()
    cursor = db.cursor()

    conditions = ['user_id = ?']
    params = [g.user_id]

    if year:
        conditions.append("strftime('%Y', date) = ?")
        params.append(year)
    if start_month:
        conditions.append("strftime('%m', date) >= ?")
        params.append(start_month)
    if end_month:
        conditions.append("strftime('%m', date) <= ?")
        params.append(end_month)

    where_clause = ' AND '.join(conditions)

    cursor.execute(
        f"SELECT strftime('%m', date) as month, SUM(amount) as total "
        f"FROM expenses WHERE {where_clause} GROUP BY month ORDER BY month",
        params
    )
    rows = cursor.fetchall()

    months = []
    for row in rows:
        months.append({'month': row['month'], 'total': round(row['total'] or 0, 2)})

    return jsonify({'months': months})


if __name__ == '__main__':
    init_db()
    print("=" * 60)
    print("  Echo 已启动！")
    print("  访问地址: http://localhost:5001")
    print("  按 Ctrl+C 停止服务")
    print("=" * 60)
    app.run(host='0.0.0.0', port=5001, debug=False)
