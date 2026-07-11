"""记账路由模块"""
import io
import csv
import logging
from datetime import datetime, timezone
from flask import request, jsonify, g, Response
from routes import expenses_bp
from config import EXPENSE_CATEGORIES
from db import get_db
from utils import (safe_get_json, safe_commit, clamp_pagination, validate_date,
                   month_to_range, year_to_range, fetchall_dicts, sanitize_csv_field)
from auth_utils import login_required

logger = logging.getLogger(__name__)


@expenses_bp.route('/expenses', methods=['GET'])
@login_required
def get_expenses():
    page, page_size = clamp_pagination(
        request.args.get('page', 1, type=int),
        request.args.get('page_size', 5, type=int))
    date = request.args.get('date', '', type=str)
    category = request.args.get('category', '', type=str)
    offset = (page - 1) * page_size

    conditions = ['user_id = ?']
    params = [g.user_id]
    if date:
        date_err = validate_date(date)
        if date_err:
            return date_err
        conditions.append('date = ?')
        params.append(date)
    if category:
        conditions.append('category = ?')
        params.append(category)

    where_clause = ' AND '.join(conditions)
    db = get_db()
    cursor = db.cursor()

    cursor.execute(f'SELECT COUNT(*) FROM expenses WHERE {where_clause}', params)
    total = cursor.fetchone()[0]

    cursor.execute(f'SELECT id, category, amount, remark, date FROM expenses WHERE {where_clause} ORDER BY date DESC, id DESC LIMIT ? OFFSET ?',
                   params + [page_size, offset])
    records = [dict(row) for row in cursor.fetchall()]

    return jsonify({'records': records, 'total': total, 'page': page, 'page_size': page_size})


@expenses_bp.route('/expenses', methods=['POST'])
@login_required
def add_expense():
    data, err = safe_get_json()
    if err:
        return err
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
    date_err = validate_date(date)
    if date_err:
        return date_err

    db = get_db()
    cursor = db.cursor()
    cursor.execute('INSERT INTO expenses (category, amount, remark, date, user_id) VALUES (?, ?, ?, ?, ?)',
                   (category, amount, remark, date, g.user_id))
    err = safe_commit(db)
    if err:
        return err
    return jsonify({'message': '添加成功', 'id': cursor.lastrowid}), 201


@expenses_bp.route('/expenses/<int:expense_id>', methods=['PUT'])
@login_required
def update_expense(expense_id):
    data, err = safe_get_json()
    if err:
        return err
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
    date_err = validate_date(date)
    if date_err:
        return date_err

    db = get_db()
    cursor = db.cursor()
    cursor.execute('UPDATE expenses SET category=?, amount=?, remark=?, date=? WHERE id=? AND user_id=?',
                   (category, amount, remark, date, expense_id, g.user_id))
    if cursor.rowcount == 0:
        return jsonify({'error': '记录不存在'}), 404
    err = safe_commit(db)
    if err:
        return err
    return jsonify({'message': '更新成功'})


@expenses_bp.route('/expenses/<int:expense_id>', methods=['DELETE'])
@login_required
def delete_expense(expense_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute('DELETE FROM expenses WHERE id=? AND user_id=?', (expense_id, g.user_id))
    if cursor.rowcount == 0:
        return jsonify({'error': '记录不存在'}), 404
    err = safe_commit(db)
    if err:
        return err
    return jsonify({'message': '删除成功'})


@expenses_bp.route('/expenses/batch-delete', methods=['POST'])
@login_required
def batch_delete_expenses():
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
    cursor.execute(f'DELETE FROM expenses WHERE id IN ({placeholders}) AND user_id=?', ids + [g.user_id])
    deleted = cursor.rowcount
    err = safe_commit(db)
    if err:
        return err
    return jsonify({'message': f'成功删除 {deleted} 条记录', 'deleted': deleted})


@expenses_bp.route('/expenses/stats', methods=['GET'])
@login_required
def get_expenses_stats():
    year = request.args.get('year', '', type=str)
    start_month = request.args.get('start_month', '', type=str)
    end_month = request.args.get('end_month', '', type=str)
    month = request.args.get('month', '', type=str)

    db = get_db()
    cursor = db.cursor()

    if month:
        m_start, m_end = month_to_range(month)
        if m_start and m_end:
            conditions = ['user_id = ?', 'date >= ?', 'date < ?']
            params = [g.user_id, m_start, m_end]
        else:
            conditions = ['user_id = ?']
            params = [g.user_id]
    elif year:
        yr_start, yr_end = year_to_range(year)
        if yr_start and yr_end:
            conditions = ['user_id = ?', 'date >= ?', 'date < ?']
            params = [g.user_id, yr_start, yr_end]
            if start_month:
                conditions.append('substr(date, 6, 2) >= ?')
                params.append(start_month)
            if end_month:
                conditions.append('substr(date, 6, 2) <= ?')
                params.append(end_month)
        else:
            conditions = ['user_id = ?']
            params = [g.user_id]
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


@expenses_bp.route('/expenses/today', methods=['GET'])
@login_required
def get_expenses_today():
    """返回指定日期（默认当日）的消费合计。日期由前端传入本地 YYYY-MM-DD。"""
    date = request.args.get('date', '', type=str).strip()
    if not date:
        date = datetime.now().strftime('%Y-%m-%d')
    date_err = validate_date(date)
    if date_err:
        return date_err

    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        'SELECT COUNT(*) as cnt, COALESCE(SUM(amount), 0) as total '
        'FROM expenses WHERE user_id = ? AND date = ?',
        (g.user_id, date)
    )
    row = cursor.fetchone()
    return jsonify({
        'date': date,
        'count': row['cnt'],
        'total': round(row['total'], 2)
    })


@expenses_bp.route('/expenses/stats/monthly', methods=['GET'])
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
        yr_start, yr_end = year_to_range(year)
        if yr_start and yr_end:
            conditions.append('date >= ? AND date < ?')
            params.extend([yr_start, yr_end])
    if start_month:
        conditions.append('substr(date, 6, 2) >= ?')
        params.append(start_month)
    if end_month:
        conditions.append('substr(date, 6, 2) <= ?')
        params.append(end_month)

    where_clause = ' AND '.join(conditions)

    cursor.execute(
        f"SELECT CAST(substr(date, 6, 2) AS INTEGER) as month, SUM(amount) as total "
        f"FROM expenses WHERE {where_clause} GROUP BY month ORDER BY month",
        params
    )
    rows = cursor.fetchall()

    months = []
    for row in rows:
        months.append({'month': row['month'], 'total': round(row['total'] or 0, 2)})

    return jsonify({'months': months})


@expenses_bp.route('/expenses/export', methods=['GET', 'POST'])
@login_required
def export_expenses():
    """导出消费记录为 CSV"""
    try:
        db = get_db()
        cursor = db.cursor()

        if request.method == 'POST':
            data, err = safe_get_json()
            if err:
                return err
            data = data or {}
            ids = data.get('ids', [])
            if not ids:
                return jsonify({'error': 'ids不能为空'}), 400
            if not all(isinstance(i, int) for i in ids):
                return jsonify({'error': 'ids必须为整数列表'}), 400
            placeholders = ','.join(['?'] * len(ids))
            params = list(ids) + [g.user_id]
            cursor.execute(f"SELECT id, category, amount, remark, date FROM expenses WHERE id IN ({placeholders}) AND user_id = ? ORDER BY date DESC", params)
            rows = cursor.fetchall()
        else:
            date = request.args.get('date', '')
            category = request.args.get('category', '')
            conditions = ['user_id = ?']
            params = [g.user_id]
            if date:
                date_err = validate_date(date)
                if date_err:
                    return date_err
                conditions.append('date = ?')
                params.append(date)
            if category:
                conditions.append('category = ?')
                params.append(category)
            where_clause = ' AND '.join(conditions)
            cursor.execute(f"SELECT id, category, amount, remark, date FROM expenses WHERE {where_clause} ORDER BY date DESC LIMIT 10000", params)
            rows = fetchall_dicts(cursor)

        if not rows:
            return jsonify({'error': '没有数据可导出'}), 404

        def generate_csv():
            output = io.StringIO()
            writer = csv.writer(output, lineterminator='\n')
            writer.writerow(['ID', '分类', '金额', '日期', '备注'])
            for r in rows:
                line = output.getvalue()
                yield line.encode('gbk')
                output.seek(0)
                output.truncate(0)
                writer.writerow([sanitize_csv_field(r['id']), sanitize_csv_field(r['category']), float(r['amount']), sanitize_csv_field(r['date']), sanitize_csv_field(r['remark'] or '')])
            final = output.getvalue()
            if final:
                yield final.encode('gbk')

        safe_filename = f"expense_record_{datetime.now(timezone.utc).strftime('%Y%m%d')}.csv"
        response = Response(generate_csv(), mimetype='text/csv;charset=gbk')
        response.headers['Content-Disposition'] = f"attachment; filename=\"{safe_filename}\""
        return response
    except Exception as e:
        logger.warning('export_expenses failed: %s', e)
        return jsonify({'error': '导出消费记录失败'}), 500
