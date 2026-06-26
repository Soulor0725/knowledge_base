import sqlite3
db = sqlite3.connect('knowledge_base.db')
cur = db.cursor()
cur.execute("SELECT user_id, date, category, amount FROM expenses ORDER BY date")
print("All data:")
for r in cur.fetchall():
    print(f"  {r[0]} | {r[1]} | {r[2]} | {r[3]}")

print()
print("Filter: year=2026, month 01-03:")
cur.execute("SELECT category, SUM(amount) as total FROM expenses WHERE user_id=1 AND strftime('%Y', date)='2026' AND strftime('%m', date)>='01' AND strftime('%m', date)<='03' GROUP BY category")
rows = cur.fetchall()
print(f"  rows: {rows}")
cur.execute("SELECT SUM(amount) FROM expenses WHERE user_id=1 AND strftime('%Y', date)='2026' AND strftime('%m', date)>='01' AND strftime('%m', date)<='03'")
print(f"  total: {cur.fetchone()[0]}")
db.close()
