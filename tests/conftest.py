"""
Echo 知识库系统 - 共享测试 Fixtures
所有测试文件通过 pytest 的 conftest 机制自动加载本文件中的 fixtures。

使用方式：
    def test_xxx(auth, client):
        r = client.get('/api/articles', headers=auth)
        assert r.status_code == 200
"""
import pytest
import requests
import random
import string

BASE_URL = 'http://localhost:5001/api'


def _random_user():
    """生成随机测试用户名和密码"""
    u = 't_' + ''.join(random.choices(string.ascii_lowercase, k=6))
    return u, 'Test1234'


@pytest.fixture(scope="session")
def client():
    """
    复用单一 requests.Session，避免每测试重建 TCP 连接。
    整个测试会话期间共享一个 session，测试结束后关闭。
    """
    s = requests.Session()
    s.headers.update({'Content-Type': 'application/json'})
    yield s
    s.close()


@pytest.fixture(scope="session")
def auth(client):
    """
    一次注册+登录，全 session 复用 token。
    所有需要鉴权的测试都依赖此 fixture。
    """
    u, p = _random_user()
    r = client.post(f'{BASE_URL}/auth/register', json={
        'username': u, 'password': p, 'name': u
    })
    if r.status_code != 201:  # 用户已存在则直接登录
        r = client.post(f'{BASE_URL}/auth/login', json={
            'username': u, 'password': p
        })
    token = r.json()['token']
    return {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}


@pytest.fixture(scope="session")
def admin_auth(client):
    """
    管理员账号（root/root123）。
    用于需要高权限或预设数据的测试。
    """
    r = client.post(f'{BASE_URL}/auth/login', json={
        'username': 'root', 'password': 'root123'
    })
    if r.status_code != 200:
        pytest.skip('管理员登录失败，跳过需要管理员权限的测试')
    token = r.json()['token']
    return {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}


@pytest.fixture
def temp_article(auth, client):
    """
    创建一篇临时文章，测试结束后自动清理。
    适用于需要"已存在文章"的场景（更新/删除/详情）。
    """
    r = client.post(f'{BASE_URL}/articles', headers=auth, json={
        'title': 'Temp Article', 'content': 'Temp content', 'category': '技术'
    })
    aid = r.json()['id']
    yield aid
    # 测试后清理（忽略删除失败）
    client.delete(f'{BASE_URL}/articles/{aid}', headers=auth)


@pytest.fixture
def temp_expense(auth, client):
    """
    创建一条临时消费记录，测试结束后自动清理。
    """
    r = client.post(f'{BASE_URL}/expenses', headers=auth, json={
        'category': '交通', 'amount': 10.0, 'date': '2026-07-08'
    })
    eid = r.json()['id']
    yield eid
    client.delete(f'{BASE_URL}/expenses/{eid}', headers=auth)


@pytest.fixture
def temp_overtime(auth, client):
    """
    创建一条临时加班记录（工作日），测试结束后自动清理。
    """
    r = client.post(f'{BASE_URL}/overtime', headers=auth, json={
        'overtime_type': 'weekday',
        'date': '2026-07-08',
        'start_time': '19:00',
        'end_time': '21:00',
        'remark': 'test'
    })
    oid = r.json()['id']
    yield oid
    client.delete(f'{BASE_URL}/overtime/{oid}', headers=auth)


@pytest.fixture
def temp_kiwi(auth, client):
    """
    创建一条临时猕猴桃订单，测试结束后自动清理。
    """
    r = client.post(f'{BASE_URL}/kiwi-sales', headers=auth, json={
        'customer_name': 'TestCust',
        'phone': '13800138000',
        'address': 'TestAddr',
        'order_date': '2026-07-08',
        'quantity': 10,
        'payment_amount': 500.0,
        'status': '未发货'
    })
    kid = r.json()['id']
    yield kid
    client.delete(f'{BASE_URL}/kiwi-sales/{kid}', headers=auth)
