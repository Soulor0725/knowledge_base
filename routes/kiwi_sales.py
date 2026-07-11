"""猕猴桃销售路由模块"""
import io
import csv
import logging
from datetime import datetime, timezone
from flask import request, jsonify, g, Response, stream_with_context
from routes import kiwi_sales_bp
from db import get_db
from utils import safe_get_json, safe_commit, clamp_pagination, validate_date, year_to_range, fetchall_dicts, sanitize_csv_field
from auth_utils import login_required

logger = logging.getLogger(__name__)


def _validate_kiwi_sale_data(data):
    """Validate kiwi sale input. Returns (error_tuple_or_None, validated_fields_or_None)."""
    customer_name = data.get('customer_name', '').strip()
    if not customer_name:
        return (jsonify({'error': '客户名不能为空'}), 400), None
    if len(customer_name) > 50:
        return (jsonify({'error': '客户名不能超过50个字符'}), 400), None

    # 电话校验
    phone = data.get('phone', '').strip()
    if not phone:
        return (jsonify({'error': '电话号码不能为空'}), 400), None
    if not phone.isdigit() or len(phone) != 11:
        return (jsonify({'error': '请输入有效的11位手机号码'}), 400), None

    # 地址校验
    address = data.get('address', '').strip()
    if not address:
        return (jsonify({'error': '收货地址不能为空'}), 400), None
    if len(address) > 200:
        return (jsonify({'error': '地址不能超过200个字符'}), 400), None

    # 接单日期校验
    order_date = data.get('order_date')
    if not order_date:
        return (jsonify({'error': '接单日期不能为空'}), 400), None
    date_err = validate_date(order_date, '接单日期')
    if date_err:
        return date_err

    # 发货日期校验
    ship_date = data.get('ship_date', '')
    if ship_date and ship_date < order_date:
        return (jsonify({'error': '发货日期不能早于接单日期'}), 400), None

    # 运单号校验
    tracking_number = data.get('tracking_number', '').strip()
    if tracking_number and len(tracking_number) > 50:
        return (jsonify({'error': '运单号不能超过50个字符'}), 400), None

    # 备注校验
    remark = data.get('remark', '').strip()
    if remark and len(remark) > 50:
        return (jsonify({'error': '备注不能超过50个字符'}), 400), None

    # 数量校验
    quantity = data.get('quantity', 0)
    if not isinstance(quantity, int) or quantity < 0:
        return (jsonify({'error': '数量必须是正整数'}), 400), None

    # 支付金额校验
    payment_amount = data.get('payment_amount', 0.00)
    try:
        payment_amount = float(payment_amount)
        if payment_amount < 0:
            return (jsonify({'error': '支付金额不能为负数'}), 400), None
        payment_amount = round(payment_amount, 2)
    except (ValueError, TypeError):
        return (jsonify({'error': '支付金额必须是数字'}), 400), None

    # 状态校验
    status = data.get('status', '未发货')
    if status not in ['已发货', '未发货']:
        return (jsonify({'error': '状态必须是已发货或未发货'}), 400), None

    return None, {
        'customer_name': customer_name,
        'phone': phone,
        'address': address,
        'order_date': order_date,
        'tracking_number': tracking_number,
        'remark': remark,
        'quantity': quantity,
        'payment_amount': payment_amount,
        'status': status,
    }


@kiwi_sales_bp.route('/kiwi-sales', methods=['GET'])
@login_required
def get_kiwi_sales():
    db = get_db()
    cursor = db.cursor()
    
    # 分页参数
    page, page_size = clamp_pagination(
        request.args.get('page', 1, type=int),
        request.args.get('page_size', 5, type=int))
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
        yr_start, yr_end = year_to_range(year)
        if yr_start and yr_end:
            conditions.append("order_date >= ? AND order_date < ?")
            params.extend([yr_start, yr_end])
    
    where_clause = 'WHERE ' + ' AND '.join(conditions)
    
    # 获取总数
    count_query = f'SELECT COUNT(*) FROM kiwi_sales {where_clause}'
    cursor.execute(count_query, params)
    total = cursor.fetchone()[0]
    
    # 获取数据
    data_query = f'''SELECT id, customer_name, phone, address, order_date, status, tracking_number, remark, quantity, payment_amount, created_at FROM kiwi_sales {where_clause} ORDER BY created_at DESC LIMIT ? OFFSET ?'''
    params.extend([page_size, offset])
    cursor.execute(data_query, params)
    
    sales = [dict(row) for row in cursor.fetchall()]
    
    return jsonify({
        'sales': sales,
        'total': total,
        'page': page,
        'page_size': page_size
    })


@kiwi_sales_bp.route('/kiwi-sales', methods=['POST'])
@login_required
def add_kiwi_sale():
    data, err = safe_get_json()
    if err:
        return err
    if not data:
        return jsonify({'error': '请提供订单信息（客户名、电话、地址、接单日期等）'}), 400
    
    err, validated = _validate_kiwi_sale_data(data)
    if err:
        return err

    # 数据库操作
    db = get_db()
    cursor = db.cursor()
    cursor.execute('''
        INSERT INTO kiwi_sales (customer_name, phone, address, order_date, status, tracking_number, remark, quantity, payment_amount, user_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (validated['customer_name'], validated['phone'], validated['address'],
          validated['order_date'], validated['status'], validated['tracking_number'],
          validated['remark'], validated['quantity'], validated['payment_amount'], g.user_id))
    err = safe_commit(db)
    if err:
        return err

    return jsonify({'message': '添加成功', 'id': cursor.lastrowid}), 201


@kiwi_sales_bp.route('/kiwi-sales/<int:sale_id>', methods=['PUT'])
@login_required
def update_kiwi_sale(sale_id):
    data, err = safe_get_json()
    if err:
        return err
    if not data:
        return jsonify({'error': '请提供订单信息（客户名、电话、地址、接单日期等）'}), 400
    
    err, validated = _validate_kiwi_sale_data(data)
    if err:
        return err

    # 数据库操作
    db = get_db()
    cursor = db.cursor()
    cursor.execute('''
        UPDATE kiwi_sales SET customer_name=?, phone=?, address=?, order_date=?, status=?, tracking_number=?, remark=?, quantity=?, payment_amount=?
        WHERE id=? AND user_id=?
    ''', (validated['customer_name'], validated['phone'], validated['address'],
          validated['order_date'], validated['status'], validated['tracking_number'],
          validated['remark'], validated['quantity'], validated['payment_amount'], sale_id, g.user_id))
    if cursor.rowcount == 0:
        return jsonify({'error': '记录不存在'}), 404
    err = safe_commit(db)
    if err:
        return err
    return jsonify({'message': '更新成功'})


@kiwi_sales_bp.route('/kiwi-sales/<int:sale_id>', methods=['DELETE'])
@login_required
def delete_kiwi_sale(sale_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute('DELETE FROM kiwi_sales WHERE id=? AND user_id=?', (sale_id, g.user_id))
    if cursor.rowcount == 0:
        return jsonify({'error': '记录不存在'}), 404
    err = safe_commit(db)
    if err:
        return err
    return jsonify({'message': '删除成功'})


@kiwi_sales_bp.route('/kiwi-sales/batch-delete', methods=['POST'])
@login_required
def batch_delete_kiwi_sales():
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
    cursor.execute(f'DELETE FROM kiwi_sales WHERE id IN ({placeholders}) AND user_id=?', ids + [g.user_id])
    deleted = cursor.rowcount
    err = safe_commit(db)
    if err:
        return err
    return jsonify({'message': f'成功删除 {deleted} 条记录', 'deleted': deleted})


@kiwi_sales_bp.route('/kiwi-sales-report', methods=['GET'])
@login_required
def get_kiwi_sales_report():
    db = get_db()
    cursor = db.cursor()
    
    # 获取分页参数
    page, page_size = clamp_pagination(
        request.args.get('page', 1, type=int),
        request.args.get('page_size', 5, type=int))
    
    # 获取年份筛选参数
    year = request.args.get('year', '', type=str)
    
    # 构建年份筛选条件
    year_filter = ''
    year_params = []
    if year:
        yr_start, yr_end = year_to_range(year)
        if yr_start and yr_end:
            year_filter = 'AND order_date >= ? AND order_date < ?'
            year_params = [yr_start, yr_end]
    
    # 先获取所有客户数据进行分组计算
    cursor.execute(f'''
        SELECT customer_name, remark, SUM(quantity) as total_quantity, SUM(payment_amount) as total_amount
        FROM kiwi_sales
        WHERE user_id = ? AND customer_name IS NOT NULL AND customer_name != '' {year_filter}
        GROUP BY customer_name, remark
        ORDER BY customer_name, remark
        LIMIT 5000
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
        grouped_data[customer]['total_quantity'] += (row['total_quantity'] or 0)
        grouped_data[customer]['total_amount'] += (row['total_amount'] or 0)
    
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


@kiwi_sales_bp.route('/kiwi-sales/export', methods=['GET'])
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
            yr_start, yr_end = year_to_range(year)
            if yr_start and yr_end:
                conditions.append("order_date >= ? AND order_date < ?")
                params.extend([yr_start, yr_end])
        
        where_clause = 'WHERE ' + ' AND '.join(conditions)
        
        cursor.execute(f'''SELECT id, customer_name, phone, address, order_date, status, tracking_number, remark, quantity, payment_amount 
                          FROM kiwi_sales {where_clause} ORDER BY created_at DESC LIMIT 10000''', params)
        rows = fetchall_dicts(cursor)
        
        if not rows:
            return jsonify({'error': '没有数据可导出'}), 404

        def generate_csv():
            output = io.StringIO()
            writer = csv.writer(output, lineterminator='\n')
            writer.writerow(['序号', '客户名', '电话', '地址', '接单日期', '状态', '运单号', '备注', '数量', '支付金额'])
            for idx, r in enumerate(rows):
                line = output.getvalue()
                yield line.encode('gbk')
                output.seek(0)
                output.truncate(0)
                writer.writerow([
                    idx + 1,
                    sanitize_csv_field(r['customer_name']),
                    sanitize_csv_field(r['phone']),
                    sanitize_csv_field(r['address']),
                    sanitize_csv_field(r['order_date'] or ''),
                    sanitize_csv_field(r['status'] or '未发货'),
                    sanitize_csv_field(r['tracking_number'] or ''),
                    sanitize_csv_field(r['remark'] or ''),
                    r['quantity'] or 0,
                    (r['payment_amount'] or 0)
                ])

            final = output.getvalue()
            if final:
                yield final.encode('gbk')

        safe_filename = f"kiwi_sales_{datetime.now(timezone.utc).strftime('%Y%m%d')}.csv"
        response = Response(stream_with_context(generate_csv()), mimetype='text/csv;charset=gbk')
        response.headers['Content-Disposition'] = f"attachment; filename=\"{safe_filename}\""
        return response
    except Exception as e:
        logger.warning('export_kiwi_sales failed: %s', e)
        return jsonify({'error': '导出猕猴桃销售记录失败'}), 500
