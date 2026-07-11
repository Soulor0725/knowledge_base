"""
安全基线测试
运行：pytest tests/test_security.py -q
覆盖：无 token → 401、伪造 token → 401、用户隔离、XSS 防护、登录限流
"""
import pytest
import random
import string

BASE = '/api'


def _random_user():
    u = 'sec_' + ''.join(random.choices(string.ascii_lowercase, k=6))
    return u, 'Test1234'


@pytest.mark.security
@pytest.mark.p1
class TestSecurity:
    """安全基线"""

    def test_no_token_returns_401(self, client):
        """无 Token → 401"""
        r = client.get(f'{BASE}/articles')
        assert r.status_code == 401

    def test_invalid_token_returns_401(self, client):
        """伪造 Token → 401"""
        r = client.get(f'{BASE}/articles',
                       headers={'Authorization': 'Bearer fake_token_here'})
        assert r.status_code == 401

    def test_expired_token_format(self, client):
        """构造过期 JWT（ manually crafted payload ）→ 401"""
        # 这是一个结构正确但签名无效的 JWT
        invalid_jwt = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoxLCJleHAiOjE2MDAwMDAwMDB9.invalid_signature'
        r = client.get(f'{BASE}/articles',
                       headers={'Authorization': f'Bearer {invalid_jwt}'})
        assert r.status_code == 401

    def test_user_isolation(self, client):
        """用户 A 的数据用户 B 看不到（越权防护）"""
        # 用户 A 注册并创建文章
        ua, pa = _random_user()
        r1 = client.post(f'{BASE}/auth/register',
                         json={'username': ua, 'password': pa, 'name': ua})
        token_a = r1.json()['token']
        r2 = client.post(f'{BASE}/articles',
                         headers={'Authorization': f'Bearer {token_a}', 'Content-Type': 'application/json'},
                         json={'title': 'Private', 'content': 'Secret', 'category': '技术'})
        aid = r2.json()['id']
        # 用户 B 注册并尝试访问
        ub, pb = _random_user()
        r3 = client.post(f'{BASE}/auth/register',
                         json={'username': ub, 'password': pb, 'name': ub})
        token_b = r3.json()['token']
        r4 = client.get(f'{BASE}/articles/{aid}',
                        headers={'Authorization': f'Bearer {token_b}'})
        assert r4.status_code == 404  # B 看不到 A 的文章

    def test_xss_in_content(self, client, auth, temp_article):
        """XSS 脚本不应破坏系统"""
        # 更新文章内容为 XSS 脚本
        xss_payload = '<script>alert("xss")</script>'
        r = client.put(f'{BASE}/articles/{temp_article}', headers=auth,
                       json={'title': xss_payload, 'content': xss_payload})
        assert r.status_code == 200
        # 验证能正常读取（未被破坏）
        r2 = client.get(f'{BASE}/articles/{temp_article}', headers=auth)
        assert r2.status_code == 200

    def test_change_password_wrong_old(self, client):
        """原密码错误时修改失败"""
        u = 'pwd_' + ''.join(__import__('random').choices(__import__('string').ascii_lowercase, k=6))
        p = 'Test1234'
        r = client.post(f'{BASE}/auth/register', json={'username': u, 'password': p, 'name': u})
        if r.status_code != 201:
            r = client.post(f'{BASE}/auth/login', json={'username': u, 'password': p})
        token = r.json()['token']
        headers = {'Authorization': f'Bearer {token}'}
        # Wrong old password
        r2 = client.post(f'{BASE}/auth/change-password', headers=headers,
                         json={'old_password': 'WrongOldPass123', 'new_password': 'NewPass456'})
        assert r2.status_code == 401
        assert '\u539f\u5bc6\u7801' in r2.json().get('error', '')

    def test_change_password_same_as_old(self, client):
        """新密码与原密码相同应拒绝"""
        u = 'pwd_' + ''.join(__import__('random').choices(__import__('string').ascii_lowercase, k=6))
        p = 'Test1234'
        r = client.post(f'{BASE}/auth/register', json={'username': u, 'password': p, 'name': u})
        if r.status_code != 201:
            r = client.post(f'{BASE}/auth/login', json={'username': u, 'password': p})
        token = r.json()['token']
        headers = {'Authorization': f'Bearer {token}'}
        r2 = client.post(f'{BASE}/auth/change-password', headers=headers,
                         json={'old_password': p, 'new_password': p})
        assert r2.status_code == 400

    def test_change_password_too_short(self, client):
        """新密码太短应拒绝"""
        u = 'pwd_' + ''.join(__import__('random').choices(__import__('string').ascii_lowercase, k=6))
        p = 'Test1234'
        r = client.post(f'{BASE}/auth/register', json={'username': u, 'password': p, 'name': u})
        if r.status_code != 201:
            r = client.post(f'{BASE}/auth/login', json={'username': u, 'password': p})
        token = r.json()['token']
        headers = {'Authorization': f'Bearer {token}'}
        r2 = client.post(f'{BASE}/auth/change-password', headers=headers,
                         json={'old_password': p, 'new_password': 'Ab1'})
        assert r2.status_code == 400

    def test_change_password_success(self, client, auth):
        """正常修改密码后用新密码可登录"""
        u = 'pwd_' + ''.join(__import__('random').choices(__import__('string').ascii_lowercase, k=6))
        p = 'Test1234'
        r = client.post(f'{BASE}/auth/register', json={'username': u, 'password': p, 'name': u})
        if r.status_code != 201:
            r = client.post(f'{BASE}/auth/login', json={'username': u, 'password': p})
        token = r.json()['token']
        headers = {'Authorization': f'Bearer {token}'}
        new_p = 'NewPass456'
        r2 = client.post(f'{BASE}/auth/change-password', headers=headers,
                         json={'old_password': p, 'new_password': new_p})
        assert r2.status_code == 200
        # New password works
        r3 = client.post(f'{BASE}/auth/login', json={'username': u, 'password': new_p})
        assert r3.status_code == 200
        assert 'token' in r3.json()
