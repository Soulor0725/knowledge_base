import urllib.request
import json

# Login
data = json.dumps({'username': 'root', 'password': 'root123'}).encode()
req = urllib.request.Request('http://localhost:5001/api/auth/login', data=data, headers={'Content-Type': 'application/json'})
try:
    r = urllib.request.urlopen(req)
    login = json.loads(r.read().decode())
    print("Login OK:", login.get('username'))
    token = login['token']
except Exception as e:
    print("Login failed:", e)
    exit()

# Test overtime
req2 = urllib.request.Request('http://localhost:5001/api/overtime?page=1&page_size=10&month=2026-06', headers={'Authorization': 'Bearer ' + token})
r2 = urllib.request.urlopen(req2)
result = json.loads(r2.read().decode())
print("Overtime records:", result['total'])
for rec in result['records']:
    print(f"  {rec['date']} {rec['overtime_type']} {rec['start_time']}-{rec['end_time']} {rec['duration']}h")

# Test expenses
req3 = urllib.request.Request('http://localhost:5001/api/expenses?page=1&page_size=10', headers={'Authorization': 'Bearer ' + token})
r3 = urllib.request.urlopen(req3)
result3 = json.loads(r3.read().decode())
print("\nExpense records:", result3['total'])
for rec in result3['records']:
    print(f"  {rec['date']} {rec['category']} {rec['amount']}")
