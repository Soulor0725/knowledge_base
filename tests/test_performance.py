"""
响应时间基线测试（轻量级，非负载测试）
运行：pytest tests/test_performance.py -q
目标：关键接口响应时间 < 阈值，发现性能退化

注意：阈值根据本地 Windows 环境设定，CI 环境可能需要调整。
"""
import pytest
import time

BASE = '/api'


@pytest.mark.performance
@pytest.mark.p2
class TestPerformance:
    """响应时间基线"""

    def test_login_response_time(self, client):
        """登录响应 < 500ms"""
        start = time.time()
        r = client.post(f'{BASE}/auth/login',
                        json={'username': 'root', 'password': 'root123'})
        elapsed_ms = (time.time() - start) * 1000
        assert r.status_code == 200
        assert elapsed_ms < 500, f"Login took {elapsed_ms:.0f}ms (threshold 500ms)"

    def test_list_articles_response_time(self, client, auth):
        """文章列表查询 < 300ms"""
        start = time.time()
        r = client.get(f'{BASE}/articles', headers=auth)
        elapsed_ms = (time.time() - start) * 1000
        assert r.status_code == 200
        assert elapsed_ms < 300, f"List articles took {elapsed_ms:.0f}ms (threshold 300ms)"

    def test_kiwi_report_response_time(self, client, auth):
        """销售报表查询 < 1000ms"""
        start = time.time()
        r = client.get(f'{BASE}/kiwi-sales/report', headers=auth)
        elapsed_ms = (time.time() - start) * 1000
        assert r.status_code == 200
        assert elapsed_ms < 1000, f"Kiwi report took {elapsed_ms:.0f}ms (threshold 1000ms)"

    def test_overtime_stats_response_time(self, client, auth):
        """加班统计查询 < 500ms"""
        start = time.time()
        r = client.get(f'{BASE}/overtime/stats', headers=auth)
        elapsed_ms = (time.time() - start) * 1000
        assert r.status_code == 200
        assert elapsed_ms < 500, f"Overtime stats took {elapsed_ms:.0f}ms (threshold 500ms)"

    def test_expenses_stats_response_time(self, client, auth):
        """消费统计查询 < 500ms"""
        start = time.time()
        r = client.get(f'{BASE}/expenses/stats?year=2026', headers=auth)
        elapsed_ms = (time.time() - start) * 1000
        assert r.status_code == 200
        assert elapsed_ms < 500, f"Expenses stats took {elapsed_ms:.0f}ms (threshold 500ms)"
