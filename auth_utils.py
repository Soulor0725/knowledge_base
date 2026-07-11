"""认证工具模块"""
from datetime import datetime, timedelta, timezone
from functools import wraps
from flask import request, jsonify, g, current_app
import jwt
from db import get_db


def generate_token(user_id, token_version=0):
    """生成JWT token，包含 token_version 用于踢掉旧登录"""
    payload = {
        'user_id': user_id,
        'ver': token_version,
        'exp': datetime.now(timezone.utc) + timedelta(days=7)  # 7天过期
    }
    return jwt.encode(payload, current_app.config['SECRET_KEY'], algorithm='HS256')


def decode_token(token):
    """解码JWT token，返回 payload 或 None（不抛出异常）"""
    try:
        return jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None


def verify_token(token):
    """验证JWT token（兼容旧调用），返回 user_id 或 None"""
    payload = decode_token(token)
    if payload is None:
        return None
    return payload.get('user_id')


def login_required(f):
    """登录装饰器，同时校验 token_version 防止旧 token 继续使用"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'error': '未提供认证token'}), 401

        token = token.replace('Bearer ', '')
        payload = decode_token(token)
        if not payload:
            return jsonify({'error': '无效或过期的token'}), 401

        user_id = payload.get('user_id')
        token_ver = payload.get('ver', 0)

        # 校验 token_version 是否匹配当前用户版本
        db = get_db()
        cursor = db.cursor()
        cursor.execute('SELECT token_version FROM users WHERE id = ?', (user_id,))
        row = cursor.fetchone()
        if not row:
            return jsonify({'error': '用户不存在'}), 401
        if row[0] != token_ver:
            return jsonify({'error': '登录已在其他地方失效，请重新登录'}), 401

        g.user_id = user_id
        return f(*args, **kwargs)
    return decorated_function
