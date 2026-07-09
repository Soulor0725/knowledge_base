"""
P0 Smoke Test — 全模块核心冒烟
运行：pytest tests/test_smoke.py -q
覆盖：注册 → 文章/分类/标签/统计/消费/销售/加班 → 鉴权

本文件同时作为新测试架构的示范：
- 使用 conftest.py 的 auth/client fixtures（无需自行注册）
- 使用 temp_* fixtures 自动清理测试数据
- 标记 @pytest.mark.p0 以便选择性执行
"""
import pytest

BASE = '/api'


@pytest.mark.p0
@pytest.mark.smoke
class TestAuthSmoke:
    """认证模块冒烟（前置：已在 conftest.py 的 auth fixture 中完成注册+登录）"""

    def test_auth_header_present(self, auth):
        """auth fixture 返回有效 headers"""
        assert 'Authorization' in auth
        assert auth['Authorization'].startswith('Bearer ')


@pytest.mark.p0
@pytest.mark.smoke
class TestArticlesSmoke:
    """知识库模块冒烟"""

    def test_list_articles(self, auth, client):
        r = client.get(f'{BASE}/articles', headers=auth)
        assert r.status_code == 200

    def test_create_article(self, auth, client):
        r = client.post(f'{BASE}/articles', headers=auth, json={
            'title': 'Smoke', 'content': 'Smoke content', 'category': '技术'
        })
        assert r.status_code == 201
        assert 'id' in r.json()

    def test_get_article_detail(self, auth, client, temp_article):
        r = client.get(f'{BASE}/articles/{temp_article}', headers=auth)
        assert r.status_code == 200

    def test_update_article(self, auth, client, temp_article):
        r = client.put(f'{BASE}/articles/{temp_article}', headers=auth, json={
            'title': 'Updated', 'content': 'Updated content'
        })
        assert r.status_code == 200

    def test_delete_article(self, auth, client, temp_article):
        r = client.delete(f'{BASE}/articles/{temp_article}', headers=auth)
        assert r.status_code == 200

    def test_list_categories(self, auth, client):
        r = client.get(f'{BASE}/categories', headers=auth)
        assert r.status_code == 200 and isinstance(r.json(), list)

    def test_list_tags(self, auth, client):
        r = client.get(f'{BASE}/tags', headers=auth)
        assert r.status_code == 200

    def test_stats(self, auth, client):
        r = client.get(f'{BASE}/stats', headers=auth)
        assert r.status_code == 200


@pytest.mark.p0
@pytest.mark.smoke
class TestExpensesSmoke:
    """消费记账模块冒烟"""

    def test_create_expense(self, auth, client):
        r = client.post(f'{BASE}/expenses', headers=auth, json={
            'category': '交通', 'amount': 99.9, 'remark': 'smoke', 'date': '2026-07-08'
        })
        assert r.status_code == 201

    def test_list_expenses(self, auth, client):
        r = client.get(f'{BASE}/expenses', headers=auth)
        assert r.status_code == 200

    def test_expense_stats(self, auth, client):
        r = client.get(f'{BASE}/expenses/stats?year=2026', headers=auth)
        assert r.status_code == 200

    def test_delete_expense(self, auth, client, temp_expense):
        r = client.delete(f'{BASE}/expenses/{temp_expense}', headers=auth)
        assert r.status_code == 200


@pytest.mark.p0
@pytest.mark.smoke
class TestKiwiSalesSmoke:
    """猕猴桃销售模块冒烟"""

    def test_create_kiwi(self, auth, client):
        r = client.post(f'{BASE}/kiwi-sales', headers=auth, json={
            'customer_name': 'SmokeCust', 'phone': '13800138000',
            'address': 'SmokeAddr', 'order_date': '2026-07-08',
            'quantity': 10, 'payment_amount': 500, 'status': '未发货'
        })
        assert r.status_code == 201

    def test_list_kiwi(self, auth, client):
        r = client.get(f'{BASE}/kiwi-sales', headers=auth)
        assert r.status_code == 200

    def test_kiwi_report(self, auth, client):
        r = client.get(f'{BASE}/kiwi-sales/report', headers=auth)
        assert r.status_code == 200

    def test_delete_kiwi(self, auth, client, temp_kiwi):
        r = client.delete(f'{BASE}/kiwi-sales/{temp_kiwi}', headers=auth)
        assert r.status_code == 200


@pytest.mark.p0
@pytest.mark.smoke
class TestOvertimeSmoke:
    """加班记录模块冒烟"""

    def test_create_weekday(self, auth, client):
        r = client.post(f'{BASE}/overtime', headers=auth, json={
            'overtime_type': 'weekday', 'date': '2026-07-08',
            'start_time': '19:00', 'end_time': '21:00', 'remark': 'smoke'
        })
        assert r.status_code == 201

    def test_create_weekend(self, auth, client):
        r = client.post(f'{BASE}/overtime', headers=auth, json={
            'overtime_type': 'weekend', 'date': '2026-07-12',
            'start_time': '09:00', 'end_time': '17:00', 'remark': 'smoke'
        })
        assert r.status_code == 201

    def test_list_overtime(self, auth, client):
        r = client.get(f'{BASE}/overtime', headers=auth)
        assert r.status_code == 200

    def test_overtime_stats(self, auth, client):
        r = client.get(f'{BASE}/overtime/stats', headers=auth)
        assert r.status_code == 200

    def test_delete_overtime(self, auth, client, temp_overtime):
        r = client.delete(f'{BASE}/overtime/{temp_overtime}', headers=auth)
        assert r.status_code == 200


@pytest.mark.p0
@pytest.mark.smoke
class TestAuthEdgeCases:
    """鉴权边界（不依赖 auth fixture）"""

    def test_no_token_401(self, client):
        r = client.get(f'{BASE}/articles')
        assert r.status_code == 401

    def test_invalid_token_401(self, client):
        r = client.get(f'{BASE}/articles',
                       headers={'Authorization': 'Bearer invalid.token'})
        assert r.status_code == 401

    def test_404_json(self, client):
        r = client.get(f'{BASE}/nonexist')
        assert r.status_code == 404 and 'error' in r.json()
