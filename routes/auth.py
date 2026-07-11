"""认证路由模块"""
import re
import time
import sqlite3
import logging
from passlib.hash import pbkdf2_sha256
from flask import request, jsonify, g
from routes import auth_bp
from config import (USERNAME_MIN_LENGTH, PASSWORD_MIN_LENGTH, LOGIN_LOCK,
                    RATE_LIMIT_WINDOW, RATE_LIMIT_MAX, MAX_LOGIN_ATTEMPT_ENTRIES,
                    login_attempts)
from db import get_db
from utils import safe_get_json, safe_commit
from auth_utils import generate_token, login_required

logger = logging.getLogger(__name__)


@auth_bp.route('/register', methods=['POST'])
def register():
    """用户注册"""
    data, err = safe_get_json()
    if err:
        return err
    if not data:
        return jsonify({'error': '请提供用户名、密码和中文名'}), 400
    username = (data.get('username') or '').strip()
    password = data.get('password')
    name = (data.get('name') or '').strip()

    if not username or not password:
        return jsonify({'error': '用户名和密码不能为空'}), 400
    
    if len(username) < USERNAME_MIN_LENGTH or len(password) < PASSWORD_MIN_LENGTH:
        return jsonify({'error': '用户名至少3个字符，密码至少8位，且需包含大小写字母和数字'}), 400
    if not re.search(r'[A-Z]', password) or not re.search(r'[a-z]', password) or not re.search(r'\d', password):
        return jsonify({'error': '密码必须同时包含大写字母、小写字母和数字'}), 400
    
    db = get_db()
    cursor = db.cursor()
    
    try:
        hashed_password = pbkdf2_sha256.hash(password)
        cursor.execute('INSERT INTO users (username, password, name) VALUES (?, ?, ?)', (username, hashed_password, name))
        user_id = cursor.lastrowid
        err = safe_commit(db)
        if err:
            return err
        
        token = generate_token(user_id, token_version=0)
        return jsonify({'id': user_id, 'username': username, 'name': name, 'token': token, 'message': '注册成功'}), 201
    except sqlite3.IntegrityError:
        return jsonify({'error': '用户名已存在'}), 400


@auth_bp.route('/login', methods=['POST'])
def login():
    """用户登录"""
    remote_ip = request.remote_addr or 'unknown'
    with LOGIN_LOCK:
        now = time.time()
        attempts = login_attempts.get(remote_ip, [])
        attempts = [t for t in attempts if now - t < RATE_LIMIT_WINDOW]
        login_attempts[remote_ip] = attempts
        if len(login_attempts[remote_ip]) >= RATE_LIMIT_MAX:
            return jsonify({'error': '登录尝试过于频繁，请5分钟后再试'}), 429
        login_attempts[remote_ip].append(now)
        # 限制总IP数量防止DoS（超过则删除最旧的50%）
        if len(login_attempts) > MAX_LOGIN_ATTEMPT_ENTRIES:
            sorted_ips = sorted(login_attempts, key=lambda ip: login_attempts[ip][-1] if login_attempts[ip] else 0)
            for _ip in sorted_ips[:len(sorted_ips)//2]:
                del login_attempts[_ip]

    data, err = safe_get_json()
    if err:
        return err
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
    
    # 递增 token_version 踢掉之前的所有登录
    cursor.execute('UPDATE users SET token_version = token_version + 1 WHERE id = ?', (user['id'],))
    cursor.execute('SELECT token_version FROM users WHERE id = ?', (user['id'],))
    new_ver = cursor.fetchone()[0]
    safe_commit(db)
    token = generate_token(user['id'], token_version=new_ver)
    # 检查 user 中是否有对应的列
    name = user['name'] if 'name' in user.keys() else ''
    avatar = user['avatar'] if 'avatar' in user.keys() else ''
    return jsonify({'id': user['id'], 'username': user['username'], 'name': name, 'avatar': avatar, 'token': token, 'message': '登录成功'})


@auth_bp.route('/me', methods=['GET', 'PUT'])
@login_required
def get_current_user():
    """获取或更新当前用户信息"""
    if request.method == 'GET':
        db = get_db()
        cursor = db.cursor()
        cursor.execute('SELECT id, username, name, avatar, created_at FROM users WHERE id = ?', (g.user_id,))
        user = cursor.fetchone()
        if not user:
            return jsonify({'error': '用户不存在'}), 404
        return jsonify(dict(user))
    elif request.method == 'PUT':
        data, err = safe_get_json()
        if err:
            return err
        name = data.get('name', '').strip()
        avatar = data.get('avatar', '')
        
        # 校验 avatar URL 格式
        if avatar and not avatar.startswith(('http://', 'https://', 'data:image/')):
            return jsonify({'error': '头像URL格式无效'}), 400
        
        db = get_db()
        cursor = db.cursor()
        
        try:
            cursor.execute('UPDATE users SET name = ?, avatar = ? WHERE id = ?', (name, avatar, g.user_id))
            err = safe_commit(db)
            if err:
                return err
            
            # 返回更新后的用户信息
            cursor.execute('SELECT id, username, name, avatar, created_at FROM users WHERE id = ?', (g.user_id,))
            user = cursor.fetchone()
            return jsonify(dict(user))
        except Exception as e:
            logger.warning('update_user failed: %s', e)
            return jsonify({'error': '更新用户信息失败'}), 500


@auth_bp.route('/change-password', methods=['POST'])
@login_required
def change_password():
    """修改密码"""
    data, err = safe_get_json()
    if err:
        return err
    if not data:
        return jsonify({'error': '请提供原密码和新密码'}), 400

    old_password = data.get('old_password', '')
    new_password = data.get('new_password', '')

    if not old_password or not new_password:
        return jsonify({'error': '原密码和新密码不能为空'}), 400

    if len(new_password) < PASSWORD_MIN_LENGTH:
        return jsonify({'error': f'新密码长度不能少于 {PASSWORD_MIN_LENGTH} 个字符，且需包含大小写字母和数字'}), 400
    if not re.search(r'[A-Z]', new_password) or not re.search(r'[a-z]', new_password) or not re.search(r'\d', new_password):
        return jsonify({'error': '新密码必须同时包含大写字母、小写字母和数字'}), 400

    if old_password == new_password:
        return jsonify({'error': '新密码不能与原密码相同'}), 400

    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT password FROM users WHERE id = ?", (g.user_id,))
    row = cursor.fetchone()
    if not row:
        return jsonify({'error': '用户不存在'}), 404

    if not pbkdf2_sha256.verify(old_password, row['password']):
        return jsonify({'error': '原密码错误'}), 401

    hashed_password = pbkdf2_sha256.hash(new_password)
    cursor.execute("UPDATE users SET password = ? WHERE id = ?", (hashed_password, g.user_id))
    safe_commit(db)

    logger.info('user %d changed password', g.user_id)
    return jsonify({'message': '密码修改成功'}), 200
