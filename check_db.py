import sqlite3
conn = sqlite3.connect('knowledge_base.db')
c = conn.cursor()
c.execute("SELECT id, username FROM users")
print("=== users ===")
for r in c.fetchall():
    print(r)
conn.close()
