"""
Миграция: добавление полей для хранения результата парсинга.
"""
import sys
import os
import io

# Установка кодировки UTF-8 для Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Если запущено в Docker, используем путь из переменной окружения
if os.getenv('DB_PATH'):
    os.environ['DB_PATH'] = os.getenv('DB_PATH')

from app.models.database import engine, SessionLocal
import sqlalchemy

DB_PATH = os.getenv("DB_PATH", "sessions.db")

def migrate():
    """Добавление новых полей в таблицу client_sessions."""
    print(f"[MIGRATION] Adding parsing fields to database: {DB_PATH}")
    
    with engine.connect() as conn:
        # Проверяем, существуют ли уже поля
        inspector = sqlalchemy.inspect(engine)
        columns = [col['name'] for col in inspector.get_columns('client_sessions')]
        
        print(f"[MIGRATION] Existing columns: {columns}")
        
        # Добавляем parsed_text, если его нет
        if 'parsed_text' not in columns:
            print("[MIGRATION] Adding column: parsed_text")
            conn.execute(sqlalchemy.text("ALTER TABLE client_sessions ADD COLUMN parsed_text TEXT DEFAULT ''"))
            conn.commit()
        else:
            print("[MIGRATION] Column parsed_text already exists")
        
        # Добавляем parsed_intermediate, если его нет
        if 'parsed_intermediate' not in columns:
            print("[MIGRATION] Adding column: parsed_intermediate")
            conn.execute(sqlalchemy.text("ALTER TABLE client_sessions ADD COLUMN parsed_intermediate TEXT DEFAULT ''"))
            conn.commit()
        else:
            print("[MIGRATION] Column parsed_intermediate already exists")
    
    print("[MIGRATION] Migration completed successfully!")

if __name__ == "__main__":
    try:
        migrate()
        sys.exit(0)
    except Exception as e:
        print(f"[MIGRATION ERROR] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

