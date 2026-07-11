"""文章路由模块"""
import re
import os
import sqlite3
import logging
from datetime import datetime, timezone
from werkzeug.utils import secure_filename
from flask import request, jsonify, g
from routes import articles_bp
from config import ALLOWED_EXTENSIONS, ALLOWED_MIME_TYPES, UPLOAD_FOLDER
from db import get_db
from utils import safe_get_json, safe_commit, clamp_pagination
from auth_utils import login_required
from cache import (get_cached, set_cached, invalidate_stats, invalidate_tags,
                   _stats_cache, _stats_cache_time, _tags_cache, _tags_cache_time,
                   CACHE_EXPIRED)

logger = logging.getLogger(__name__)


@articles_bp.route('/articles', methods=['GET'])
@login_required
def get_articles():
    db = get_db()
    cursor = db.cursor()
    category = request.args.get('category')
    tag = request.args.get('tag')
    search = request.args.get('search')
    favorite = request.args.get('favorite')
    page, page_size = clamp_pagination(
        request.args.get('page', 1, type=int),
        request.args.get('page_size', 5, type=int))

    base_query = 'SELECT id, title, category, tags, created_at, updated_at, views, is_favorite, is_draft FROM articles WHERE user_id = ?'
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


@articles_bp.route('/articles/batch-delete', methods=['POST'])
@login_required
def batch_delete_articles():
    data, err = safe_get_json()
    if err:
        return err
    ids = data.get('ids', [])
    if not ids or not isinstance(ids, list):
        return jsonify({'error': '请提供要删除的文章ID列表'}), 400
    if len(ids) > 100:
        return jsonify({'error': '单次删除不能超过100篇文章'}), 400
    db = get_db()
    cursor = db.cursor()
    if not all(isinstance(i, int) for i in ids):
        return jsonify({'error': 'ID列表必须全部为整数'}), 400
    placeholders = ','.join(['?'] * len(ids))
    cursor.execute(f'DELETE FROM articles WHERE id IN ({placeholders}) AND user_id=?', ids + [g.user_id])
    deleted = cursor.rowcount
    err = safe_commit(db)
    if err:
        return err
    invalidate_tags(g.user_id)
    invalidate_stats(g.user_id)
    return jsonify({'message': f'成功删除 {deleted} 条记录', 'deleted': deleted})


@articles_bp.route('/articles/navigate', methods=['GET'])
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
            query = 'SELECT id, title, category, tags, created_at, updated_at, views, is_favorite, is_draft FROM articles WHERE id < ? AND user_id = ? ORDER BY id DESC LIMIT 1'
        else:
            query = 'SELECT id, title, category, tags, created_at, updated_at, views, is_favorite, is_draft FROM articles WHERE id > ? AND user_id = ? ORDER BY id ASC LIMIT 1'
        
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


@articles_bp.route('/articles/<int:article_id>', methods=['GET'])
@login_required
def get_article(article_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT * FROM articles WHERE id = ? AND user_id = ?', (article_id, g.user_id))
    article = cursor.fetchone()
    if article:
        try:
            db.execute('UPDATE articles SET views = views + 1 WHERE id = ?', (article_id,))
            safe_commit(db)
        except Exception as e:
            logger.warning('views increment failed: %s', e)
        return jsonify(dict(article))
    return jsonify({'error': '文章不存在'}), 404


@articles_bp.route('/articles', methods=['POST'])
@login_required
def create_article():
    data, err = safe_get_json()
    if err:
        return err
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
    if title and len(title) > 200:
        return jsonify({'error': '标题不能超过200个字符'}), 400
    if content and len(content) > 65535:
        return jsonify({'error': '内容不能超过65535个字符'}), 400
    if tags and len(tags) > 500:
        return jsonify({'error': '标签不能超过500个字符'}), 400

    # 校验分类是否存在于用户分类列表中
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT name FROM categories WHERE (user_id = ? OR user_id = 0) AND name = ?', (g.user_id, category))
    if not cursor.fetchone():
        return jsonify({'error': f'分类不存在: {category}'}), 400
    cursor = db.cursor()
    cursor.execute('INSERT INTO articles (title, content, category, tags, is_draft, user_id) VALUES (?, ?, ?, ?, ?, ?)',
                  (title, content, category, tags, int(is_draft), g.user_id))
    article_id = cursor.lastrowid
    err = safe_commit(db)
    if err:
        return err
    invalidate_tags(g.user_id)
    invalidate_stats(g.user_id)
    return jsonify({'id': article_id, 'message': '创建成功'}), 201


@articles_bp.route('/articles/<int:article_id>', methods=['PUT'])
@login_required
def update_article(article_id):
    data, err = safe_get_json()
    if err:
        return err
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT id FROM articles WHERE id = ? AND user_id = ?', (article_id, g.user_id))
    if not cursor.fetchone():
        return jsonify({'error': '文章不存在'}), 404

    if 'title' in data and data['title'] and len(data['title']) > 200:
        return jsonify({'error': '标题不能超过200个字符'}), 400
    if 'content' in data and data['content'] and len(data['content']) > 65535:
        return jsonify({'error': '内容不能超过65535个字符'}), 400
    if 'tags' in data and data['tags'] and len(data['tags']) > 500:
        return jsonify({'error': '标签不能超过500个字符'}), 400

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
    params.append(datetime.now(timezone.utc))
    params.append(article_id)
    params.append(g.user_id)

    cursor.execute(f"UPDATE articles SET {', '.join(updates)} WHERE id = ? AND user_id = ?", params)
    err = safe_commit(db)
    if err:
        return err
    invalidate_tags(g.user_id)
    invalidate_stats(g.user_id)
    return jsonify({'message': '更新成功'})


@articles_bp.route('/articles/<int:article_id>', methods=['DELETE'])
@login_required
def delete_article(article_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute('DELETE FROM articles WHERE id = ? AND user_id = ?', (article_id, g.user_id))
    if cursor.rowcount == 0:
        return jsonify({'error': '文章不存在'}), 404
    err = safe_commit(db)
    if err:
        return err
    invalidate_tags(g.user_id)
    invalidate_stats(g.user_id)
    return jsonify({'message': '删除成功'})


@articles_bp.route('/articles/<int:article_id>/favorite', methods=['POST'])
@login_required
def toggle_favorite(article_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute('UPDATE articles SET is_favorite = NOT is_favorite WHERE id = ? AND user_id = ? RETURNING is_favorite', (article_id, g.user_id))
    row = cursor.fetchone()
    if row is None:
        return jsonify({'error': '文章不存在'}), 404
    is_favorite = row[0]
    err = safe_commit(db)
    if err:
        return err
    return jsonify({'is_favorite': bool(is_favorite)})


@articles_bp.route('/categories', methods=['GET'])
@login_required
def get_categories():
    db = get_db()
    cursor = db.cursor()
    cursor.execute('''
        SELECT c.*, COUNT(a.id) as article_count
        FROM categories c
        LEFT JOIN articles a ON c.name = a.category AND a.user_id = ?
        WHERE c.user_id = ? OR c.user_id = 0
        GROUP BY c.id
        ORDER BY c.created_at
    ''', (g.user_id, g.user_id))
    categories = [dict(row) for row in cursor.fetchall()]
    return jsonify(categories)


@articles_bp.route('/categories', methods=['POST'])
@login_required
def create_category():
    data, err = safe_get_json()
    if err:
        return err
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
        cursor.execute('INSERT INTO categories (name, color, user_id) VALUES (?, ?, ?)', (name, color, g.user_id))
        category_id = cursor.lastrowid
        err = safe_commit(db)
        if err:
            return err
        return jsonify({'id': category_id, 'message': '创建成功'}), 201
    except sqlite3.IntegrityError:
        return jsonify({'error': '分类已存在'}), 400


@articles_bp.route('/categories/<int:category_id>', methods=['DELETE'])
@login_required
def delete_category(category_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT name FROM categories WHERE id = ? AND (user_id = ? OR user_id = 0)', (category_id, g.user_id))
    row = cursor.fetchone()
    if not row:
        return jsonify({'error': '分类不存在'}), 404
    cat_name = row['name']
    try:
        cursor.execute('DELETE FROM categories WHERE id = ? AND (user_id = ? OR user_id = 0)', (category_id, g.user_id))
        cursor.execute("UPDATE articles SET category = '未分类' WHERE category = ? AND user_id = ?", (cat_name, g.user_id))
        err = safe_commit(db)
        if err:
            return err
        return jsonify({'message': '删除成功'})
    except Exception as e:
        logger.warning('delete_category failed: %s', e)
        db.rollback()
        return jsonify({'error': '删除失败'}), 500


@articles_bp.route('/stats', methods=['GET'])
@login_required
def get_stats():
    cache_key = g.user_id
    cached = get_cached(_stats_cache, _stats_cache_time, cache_key)
    if cached is not CACHE_EXPIRED and cached is not None:
        return jsonify(cached)

    cursor = get_db().execute('''
        SELECT
            COUNT(*) AS total_articles,
            SUM(CASE WHEN is_favorite = 1 THEN 1 ELSE 0 END) AS favorites,
            COALESCE(SUM(views), 0) AS total_views,
            COUNT(DISTINCT category) AS categories_used
        FROM articles WHERE user_id = ?
    ''', (g.user_id,))
    row = cursor.fetchone()
    result = {
        'total_articles': row['total_articles'],
        'favorites': row['favorites'],
        'total_views': row['total_views'],
        'categories_used': row['categories_used']
    }
    set_cached(_stats_cache, _stats_cache_time, cache_key, result)
    return jsonify(result)


@articles_bp.route('/tags', methods=['GET'])
@login_required
def get_all_tags():
    cache_key = g.user_id
    cached = get_cached(_tags_cache, _tags_cache_time, cache_key)
    if cached is not CACHE_EXPIRED and cached is not None:
        return jsonify(cached)

    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT tags FROM articles WHERE tags != "" AND user_id = ?', (g.user_id,))
    tag_counts = {}
    for row in cursor.fetchall():
        for tag in row[0].split(','):
            tag = tag.strip()
            if tag:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
    sorted_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)
    result = [{'name': tag, 'count': count} for tag, count in sorted_tags]
    set_cached(_tags_cache, _tags_cache_time, cache_key, result)
    return jsonify(result)


@articles_bp.route('/upload', methods=['POST'])
@login_required
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': '没有文件上传'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': '没有选择文件'}), 400
    if not (file and '.' in file.filename and file.filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS):
        return jsonify({'error': '不支持的文件类型'}), 400
    if file.content_type not in ALLOWED_MIME_TYPES:
        return jsonify({'error': '文件内容类型不合法'}), 400
    file.seek(0, os.SEEK_END)
    if file.tell() == 0:
        return jsonify({'error': '文件内容为空'}), 400
    file.seek(0)
    header = file.read(8)
    file.seek(0)
    _ALLOWED_MAGIC = (b'\x89PNG', b'\xff\xd8\xff', b'GIF8', b'RIFF')
    if not any(header.startswith(m) for m in _ALLOWED_MAGIC):
        return jsonify({'error': '文件类型校验失败'}), 400
    filename = secure_filename(file.filename)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"{timestamp}_{filename}"
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)
    url = f"/static/uploads/{filename}"
    return jsonify({'url': url, 'filename': filename})
