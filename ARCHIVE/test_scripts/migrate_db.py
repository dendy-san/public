import sqlite3
import os

db_path = os.getenv("DB_PATH", "sessions.db")
if not os.path.exists(db_path):
    print(f"Database not found: {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Проверяем существующие колонки
cursor.execute("PRAGMA table_info(client_sessions)")
columns = [row[1] for row in cursor.fetchall()]
print(f"Existing columns: {columns}")

# Добавляем parsed_text, если его нет
if 'parsed_text' not in columns:
    print("Adding column: parsed_text")
    cursor.execute("ALTER TABLE client_sessions ADD COLUMN parsed_text TEXT DEFAULT ''")
else:
    print("Column parsed_text already exists")

# Добавляем parsed_intermediate, если его нет
if 'parsed_intermediate' not in columns:
    print("Adding column: parsed_intermediate")
    cursor.execute("ALTER TABLE client_sessions ADD COLUMN parsed_intermediate TEXT DEFAULT ''")
else:
    print("Column parsed_intermediate already exists")

conn.commit()
print("Migration completed successfully!")
conn.close()

