#!/usr/bin/env python3
# DEPRECATED: 已迁移到 tests/test_smoke.py。本文件保留作为历史参考，请勿新增用例。
#!/usr/bin/env python3
import sys, requests, json, random, string

BASE = 'http://localhost:5001/api'
PASS = 0; FAIL = 0

def check(name, ok, detail=''):
    global PASS, FAIL
    if ok: PASS += 1
    else: FAIL += 1
    print(f"  [{'OK' if ok else 'XX'}] {name}" + (f" - {detail}" if detail else ""))

h = {}
token = None
def auth_h():
    return {'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'}

u = 'smk_' + ''.join(random.choices(string.ascii_lowercase, k=5))
p = 'SmT' + str(random.randint(1000, 9999))
r = requests.post(BASE + '/auth/register', json={'username': u, 'password': p, 'name': u}, timeout=10)
check('Register', r.status_code == 201)
if r.status_code != 201:
    r = requests.post(BASE + '/auth/login', json={'username': u, 'password': p}, timeout=10)
    check('Login', r.status_code == 200)
if r.status_code in (200, 201):
    token = r.json()['token']
if not token: print("No token"); sys.exit(1)

# Articles
r = requests.get(BASE + '/articles', headers=auth_h(), timeout=10)
check('List articles', r.status_code == 200)
r = requests.post(BASE + '/articles', headers=auth_h(), json={'title': 't1', 'content': 'c1', 'category': '\u6280\u672f'}, timeout=10)
check('Create article', r.status_code == 201)
aid = r.json()['id']
r = requests.get(BASE + f'/articles/{aid}', headers=auth_h(), timeout=10)
check('Get article detail', r.status_code == 200)
r = requests.put(BASE + f'/articles/{aid}', headers=auth_h(), json={'title': 't2', 'content': 'c2'}, timeout=10)
check('Update article', r.status_code == 200)
r = requests.post(BASE + f'/articles/{aid}/favorite', headers=auth_h(), timeout=10)
check('Toggle favorite', r.status_code == 200)

# Categories
r = requests.get(BASE + '/categories', headers=auth_h(), timeout=10)
check('List categories', r.status_code == 200 and isinstance(r.json(), list))

# Tags
r = requests.get(BASE + '/tags', headers=auth_h(), timeout=10)
check('List tags', r.status_code == 200)

# Stats
r = requests.get(BASE + '/stats', headers=auth_h(), timeout=10)
check('Stats', r.status_code == 200)

# Expenses (use valid categories from server)
cats = ['\u71c3\u6c14\u8d39', '\u7535\u8d39', '\u8bdd\u8d39', '\u7f51\u8d39', '\u9999\u70df', '\u83dc\u8089\u7c73\u9762\u6cb9', '\u4ea4\u901a', '\u7269\u4e1a\u8d39', '\u6c34\u679c', '\u5176\u4ed6']
cat = random.choice(cats)
r = requests.post(BASE + '/expenses', headers=auth_h(), json={'category': cat, 'amount': 99.9, 'remark': 't', 'date': '2026-07-07'}, timeout=10)
check('Create expense', r.status_code == 201)
eid = r.json()['id']
r = requests.get(BASE + '/expenses', headers=auth_h(), timeout=10)
check('List expenses', r.status_code == 200)
r = requests.get(BASE + '/expenses/stats?year=2026', headers=auth_h(), timeout=10)
check('Expense stats', r.status_code == 200)
r = requests.put(BASE + f'/expenses/{eid}', headers=auth_h(), json={'category': cat, 'amount': 200, 'remark': 'u', 'date': '2026-07-07'}, timeout=10)
check('Update expense', r.status_code == 200)
r = requests.delete(BASE + f'/expenses/{eid}', headers=auth_h(), timeout=10)
check('Delete expense', r.status_code == 200)

# Kiwi Sales
r = requests.post(BASE + '/kiwi-sales', headers=auth_h(), json={
    'customer_name': 'Cust', 'phone': '13800138000', 'address': 'Addr',
    'order_date': '2026-07-07', 'quantity': 10, 'payment_amount': 500, 'status': '\u672a\u53d1\u8d27'}, timeout=10)
check('Create kiwi', r.status_code == 201)
kid = r.json()['id']
r = requests.get(BASE + '/kiwi-sales', headers=auth_h(), timeout=10)
check('List kiwi', r.status_code == 200)
# Update via PUT (status, all fields)
r = requests.put(BASE + f'/kiwi-sales/{kid}', headers=auth_h(), json={
    'customer_name': 'Cust', 'phone': '13800138000', 'address': 'Addr',
    'order_date': '2026-07-07', 'quantity': 10, 'payment_amount': 500, 'status': '\u5df2\u53d1\u8d27'}, timeout=10)
check('Update kiwi', r.status_code == 200)
r = requests.get(BASE + '/kiwi-sales/report', headers=auth_h(), timeout=10)
check('Kiwi report', r.status_code == 200)
r = requests.delete(BASE + f'/kiwi-sales/{kid}', headers=auth_h(), timeout=10)
check('Delete kiwi', r.status_code == 200)

# Overtime
r = requests.post(BASE + '/overtime', headers=auth_h(), json={
    'overtime_type': 'weekday', 'date': '2026-07-07', 'start_time': '19:00', 'end_time': '21:00', 'remark': 't'}, timeout=10)
check('Create OT weekday', r.status_code == 201)
oid = r.json()['id']
r = requests.post(BASE + '/overtime', headers=auth_h(), json={
    'overtime_type': 'weekend', 'date': '2026-07-11', 'start_time': '09:00', 'end_time': '17:00', 'remark': 't'}, timeout=10)
check('Create OT weekend', r.status_code == 201)
r = requests.get(BASE + '/overtime', headers=auth_h(), timeout=10)
check('List OT', r.status_code == 200)
r = requests.get(BASE + '/overtime/stats', headers=auth_h(), timeout=10)
check('OT stats', r.status_code == 200)
r = requests.delete(BASE + f'/overtime/{oid}', headers=auth_h(), timeout=10)
check('Delete OT', r.status_code == 200)

# Auth edge cases
r = requests.get(BASE + '/articles', timeout=10)
check('No token 401', r.status_code == 401)
r = requests.get(BASE + '/articles', headers={'Authorization': 'Bearer invalid'}, timeout=10)
check('Invalid token 401', r.status_code == 401)
r = requests.get(BASE + '/nonexist', timeout=10)
check('404 JSON', r.status_code == 404 and 'error' in r.json())

print(f"\n=== Results: {PASS} passed, {FAIL} failed ===")
sys.exit(0 if FAIL == 0 else 1)
