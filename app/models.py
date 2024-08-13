import sqlite3

DATABASE = 'steamdata.db'

def get_db():
    conn = sqlite3.connect(DATABASE)
    return conn

def create_tables():
    conn = get_db()
    try:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                steam_id TEXT PRIMARY KEY NOT NULL
            );
        ''')
        conn.commit()
    finally:
        conn.close()
