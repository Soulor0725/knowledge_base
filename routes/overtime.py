"""加班记录路由模块"""
import sqlite3
import logging
from datetime import datetime
from flask import request, jsonify, g
from routes import overtime_bp
from db import get_db
from utils import safe_get_json, safe_commit, clamp_pagination, validate_date, month_to_range
from auth_utils import login_required

logger = logging.getLogger(__name__)


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


@overtime_bp.route('/overtime', methods=['GET'])
@login_required
def get_overtime_records():
    page, page_size = clamp_pagination(
        request.args.get('page', 1, type=int),
        request.args.get('page_size', 5, type=int))
    month = request.args.get('month', '', type=str)
    offset = (page - 1) * page_size

    conditions = ['user_id = ?']
    params = [g.user_id]

    if month:
        m_start, m_end = month_to_range(month)
        if m_start and m_end:
            conditions.append('date >= ? AND date < ?')
            params.extend([m_start, m_end])

    where_clause = ' AND '.join(conditions)

    db = get_db()
    cursor = db.cursor()

    cursor.execute(f'SELECT COUNT(*) FROM overtime_records WHERE {where_clause}', params)
    total = cursor.fetchone()[0]

    cursor.execute(f'SELECT id, overtime_type, date, start_time, end_time, duration, remark FROM overtime_records WHERE {where_clause} ORDER BY date DESC, start_time DESC LIMIT ? OFFSET ?',
                   params + [page_size, offset])
    records = [dict(row) for row in cursor.fetchall()]

    return jsonify({
        'records': records,
        'total': total,
        'page': page,
        'page_size': page_size
    })


@overtime_bp.route('/overtime', methods=['POST'])
@login_required
def add_overtime_record():
    data, err = safe_get_json()
    if err:
        return err
    overtime_type = data.get('overtime_type', '')
    date = data.get('date', '').strip()
    start_time = data.get('start_time', '').strip()
    end_time = data.get('end_time', '').strip()
    remark = data.get('remark', '').strip()

    if overtime_type not in ['weekday', 'weekend']:
        return jsonify({'error': '加班类型必须是 平时加班 或 周末加班'}), 400
    if not date:
        return jsonify({'error': '日期不能为空'}), 400
    date_err = validate_date(date)
    if date_err:
        return date_err
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

    try:
        cursor.execute('INSERT INTO overtime_records (overtime_type, date, start_time, end_time, duration, remark, user_id) VALUES (?, ?, ?, ?, ?, ?, ?)',
                       (overtime_type, date, start_time, end_time, duration, remark, g.user_id))
    except sqlite3.IntegrityError:
        return jsonify({'error': '该日期已存在加班记录'}), 400
    err = safe_commit(db)
    if err:
        return err

    return jsonify({'message': '添加成功', 'id': cursor.lastrowid, 'duration': duration}), 201


@overtime_bp.route('/overtime/<int:record_id>', methods=['PUT'])
@login_required
def update_overtime_record(record_id):
    data, err = safe_get_json()
    if err:
        return err
    overtime_type = data.get('overtime_type', '')
    date = data.get('date', '').strip()
    start_time = data.get('start_time', '').strip()
    end_time = data.get('end_time', '').strip()
    remark = data.get('remark', '').strip()

    if overtime_type not in ['weekday', 'weekend']:
        return jsonify({'error': '加班类型必须是 平时加班 或 周末加班'}), 400
    if not date:
        return jsonify({'error': '日期不能为空'}), 400
    date_err = validate_date(date)
    if date_err:
        return date_err
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
    err = safe_commit(db)
    if err:
        return err

    return jsonify({'message': '更新成功', 'duration': duration})


@overtime_bp.route('/overtime/<int:record_id>', methods=['DELETE'])
@login_required
def delete_overtime_record(record_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute('DELETE FROM overtime_records WHERE id=? AND user_id=?', (record_id, g.user_id))
    if cursor.rowcount == 0:
        return jsonify({'error': '记录不存在'}), 404
    err = safe_commit(db)
    if err:
        return err
    return jsonify({'message': '删除成功'})


@overtime_bp.route('/overtime/batch-delete', methods=['POST'])
@login_required
def batch_delete_overtime_records():
    data, err = safe_get_json()
    if err:
        return err
    ids = data.get('ids', [])
    if not ids or not isinstance(ids, list):
        return jsonify({'error': '请提供要删除的记录ID列表'}), 400
    if len(ids) > 100:
        return jsonify({'error': '单次删除不能超过100条记录'}), 400
    db = get_db()
    cursor = db.cursor()
    if not all(isinstance(i, int) for i in ids):
        return jsonify({'error': 'ID列表必须全部为整数'}), 400
    placeholders = ','.join(['?'] * len(ids))
    cursor.execute(f'DELETE FROM overtime_records WHERE id IN ({placeholders}) AND user_id=?', ids + [g.user_id])
    deleted = cursor.rowcount
    err = safe_commit(db)
    if err:
        return err
    return jsonify({'message': f'成功删除 {deleted} 条记录', 'deleted': deleted})


@overtime_bp.route('/overtime/stats', methods=['GET'])
@login_required
def get_overtime_stats():
    month = request.args.get('month', '', type=str)
    db = get_db()
    cursor = db.cursor()

    if month:
        m_start, m_end = month_to_range(month)
        if m_start and m_end:
            cursor.execute("SELECT SUM(duration) FROM overtime_records WHERE user_id = ? AND overtime_type = 'weekday' AND date >= ? AND date < ?", (g.user_id, m_start, m_end))
            weekday_total = cursor.fetchone()[0] or 0
            cursor.execute("SELECT SUM(duration) FROM overtime_records WHERE user_id = ? AND overtime_type = 'weekend' AND date >= ? AND date < ?", (g.user_id, m_start, m_end))
            weekend_total = cursor.fetchone()[0] or 0
            cursor.execute("SELECT COUNT(*) FROM overtime_records WHERE user_id = ? AND date >= ? AND date < ?", (g.user_id, m_start, m_end))
            total_count = cursor.fetchone()[0]
        else:
            weekday_total = 0
            weekend_total = 0
            total_count = 0
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


@overtime_bp.route('/overtime/stats/monthly', methods=['GET'])
@login_required
def get_overtime_monthly_stats():
    month = request.args.get('month', '', type=str)
    if not month:
        return jsonify({'error': '请提供month参数 (YYYY-MM)'}), 400

    try:
        target = datetime.strptime(month, '%Y-%m')
    except ValueError:
        return jsonify({'error': '月份格式错误，请使用 YYYY-MM'}), 400

    # 工资压一个月：统计周期为前两个月21日 到 前一个月20日（含）
    # 例如：9月对应 7月21日 ~ 8月20日
    period_start_month = target.month - 2
    period_start_year = target.year
    if period_start_month <= 0:
        period_start_month += 12
        period_start_year -= 1
    period_end_month = target.month - 1
    period_end_year = target.year
    if period_end_month <= 0:
        period_end_month += 12
        period_end_year -= 1
    period_start = f"{period_start_year}-{period_start_month:02d}-21"
    period_end = f"{period_end_year}-{period_end_month:02d}-20"

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
