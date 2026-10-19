import sqlite3

DATABASE_NAME = "planner.db"

def get_db():
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()

    # 1. Users Table (with reset_token for Forgot Password SMTP)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        reset_token TEXT
    );
    """)

    # 2. Tasks Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        subject TEXT NOT NULL,
        task_type TEXT NOT NULL,
        deadline TEXT NOT NULL,
        estimated_hours REAL NOT NULL,
        priority INTEGER NOT NULL,
        specific_meta TEXT,
        color_tag TEXT,
        is_completed INTEGER DEFAULT 0,
        FOREIGN KEY (user_id) REFERENCES users (id)
    );
    """)

    # 3. Free Slots Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS free_slots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        day_of_week INTEGER NOT NULL,
        start_hour INTEGER NOT NULL,
        duration_hours REAL NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users (id)
    );
    """)

    # 4. Schedule Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS schedule (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        task_id INTEGER NOT NULL,
        task_title TEXT NOT NULL,
        subject TEXT NOT NULL,
        color_tag TEXT NOT NULL,
        session_date TEXT NOT NULL,
        start_time TEXT NOT NULL,
        end_time TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users (id),
        FOREIGN KEY (task_id) REFERENCES tasks (id)
    );
    """)

    # 5. Habits Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS habits (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        streak INTEGER DEFAULT 0,
        last_completed TEXT,
        FOREIGN KEY (user_id) REFERENCES users (id)
    );
    """)

    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully!")
