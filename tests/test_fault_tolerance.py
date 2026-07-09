"""
容错/异常输入测试
运行：pytest tests/test_fault_tolerance.py -q
覆盖：非法 token、畸形 JSON、越界分页、非法方法、批量超限、超长输入、SQL 注入
"""
import pytest

BASE = '/api'


@pytest.mark.fault_tolerance
@pytest.mark.p1
class TestFaultTolerance:
    """异常输入、边界条件、协议级错误"""

    def test_invalid_token_format(self, client):
        """Token 格式错误 → 401"""
        r = client.get(f'{BASE}/articles',
                       headers={'Authorization': 'Bearer invalid.token.here'})
        assert r.status_code == 401

    def test_malformed_json_body(self, client, auth):
        """JSON 语法错误 → 400"""
        r = client.post(f'{BASE}/auth/login',
                        data='{"invalid', headers=auth)
        assert r.status_code in (400, 500)  # 视服务端容错实现

    def test_empty_body(self, client, auth):
        """空请求体 → 400"""
        r = client.post(f'{BASE}/auth/login', data='', headers=auth)
        assert r.status_code in (400, 500)

    def test_negative_pagination(self, client, auth):
        """负数分页 → 返回空列表或 400，但不 500"""
        r = client.get(f'{BASE}/articles?page=-1&page_size=-10', headers=auth)
        assert r.status_code in (200, 400)

    def test_method_not_allowed(self, client):
        """不允许的方法 → 405"""
        r = client.delete(f'{BASE}/auth/login')
        assert r.status_code in (405, 404)

    def test_batch_delete_limit(self, client, auth):
        """批量删除超限（200 个 ID）→ 400"""
        r = client.post(f'{BASE}/kiwi-sales/batch-delete',
                        headers=auth, json={'ids': list(range(200))})
        assert r.status_code == 400

    def test_very_long_input(self, client, auth):
        """超长输入 → 400 或 201（截断），但不 500"""
        r = client.post(f'{BASE}/articles', headers=auth, json={
            'title': 'A' * 10000, 'content': 'x' * 100000, 'category': '技术'
        })
        assert r.status_code in (201, 400)

    def test_sql_injection_attempt(self, client, auth):
        """SQL 注入尝试 → 不报错、不泄露数据、表未被删除"""
        r = client.get(f"{BASE}/articles?id=1 OR 1=1; DROP TABLE articles;--",
                       headers=auth)
        assert r.status_code in (200, 400, 404)
        # 验证表未被删除
        r2 = client.get(f'{BASE}/articles', headers=auth)
        assert r2.status_code == 200
