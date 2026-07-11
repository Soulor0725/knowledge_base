"""通用工具函数模块"""
import sqlite3
import time
from datetime import datetime
from flask import request, jsonify


def sanitize_csv_field(value):
    """清洗 CSV 字段，防止注入"""
    if value and isinstance(value, str) and value[0] in ('=', '+', '-', '@'):
        return "'" + value
    return value


def safe_get_json():
    """安全解析请求JSON，返回 (data, error_tuple_or_None)"""
    try:
        data = request.get_json(silent=True)
        if data is None:
            if not request.data or request.data.strip() == b'':
                return {}, None
            return None, (jsonify({'error': '请求体必须是合法JSON'}), 400)
        if not isinstance(data, dict):
            return None, (jsonify({'error': '请求体必须是JSON对象'}), 400)
        return data, None
    except Exception:
        return None, (jsonify({'error': '请求体解析失败'}), 400)


def safe_commit(db, max_retries=2):
    """安全提交，失败时回滚并返回 (error_tuple_or_None)。暂时性锁冲突自动重试。"""
    for attempt in range(max_retries + 1):
        try:
            db.commit()
            return None
        except sqlite3.OperationalError as e:
            if "locked" in str(e) and attempt < max_retries:
                time.sleep(0.03 * (attempt + 1))
                continue
            try:
                db.rollback()
            except Exception:
                pass
            return (jsonify({'error': '数据库操作失败'}), 500)
        except sqlite3.Error:
            try:
                db.rollback()
            except Exception:
                pass
            return (jsonify({'error': '数据库操作失败'}), 500)
        except Exception:
            try:
                db.rollback()
            except Exception:
                pass
            return (jsonify({'error': '服务器内部错误'}), 500)


def validate_date(date_str, field='日期'):
    """验证 YYYY-MM-DD 格式"""
    if not date_str:
        return None
    try:
        datetime.strptime(date_str, '%Y-%m-%d')
        return None
    except (ValueError, TypeError):
        return (jsonify({'error': f'{field}格式错误，请使用YYYY-MM-DD'}), 400)


def clamp_pagination(page, page_size, max_size=50):
    """安全化分页参数，每页条数限制为 5/10/15 三档"""
    CHOICES = (5, 10, 15)
    try:
        page = max(1, int(page))
    except (ValueError, TypeError):
        page = 1
    try:
        ps = int(page_size)
    except (ValueError, TypeError):
        ps = 5
    if ps in CHOICES:
        page_size = ps
    else:
        page_size = min(CHOICES, key=lambda c: abs(c - ps))
        if page_size < 1:
            page_size = 5
    return page, page_size


def month_to_range(month_str):
    """将 YYYY-MM 转换为日期范围"""
    try:
        y, m = int(month_str[:4]), int(month_str[5:7])
        start = f'{y:04d}-{m:02d}-01'
        end = f'{y+1:04d}-01-01' if m == 12 else f'{y:04d}-{m+1:02d}-01'
        return start, end
    except (ValueError, TypeError, IndexError):
        return None, None


def year_to_range(year_str):
    """将 YYYY 转换为日期范围"""
    try:
        y = int(year_str)
        return f'{y:04d}-01-01', f'{y+1:04d}-01-01'
    except (ValueError, TypeError):
        return None, None


def fetchall_dicts(cursor):
    """将 cursor 结果转为字典列表"""
    cols = [d[0] for d in cursor.description] if cursor.description else []
    return [dict(zip(cols, row)) for row in cursor.fetchall()]
