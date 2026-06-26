import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), 'knowledge_base.db')
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [t[0] for t in cursor.fetchall()]
print("Tables:", tables)

cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%student%'")
student_tables = [t[0] for t in cursor.fetchall()]
print("Student tables:", student_tables)

for table in student_tables:
    cursor.execute(f"DELETE FROM {table}")
    conn.commit()
    print(f"Deleted all records from {table}")

conn.close()
print("Done!")
