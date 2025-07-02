import sqlite3

conn = sqlite3.connect('database.db')
c = conn.cursor()

c.execute('''
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('manager', 'worker'))
)
''')
# הוספת עמודה חדשה - רק אם לא קיימת
try:
    c.execute("ALTER TABLE users ADD COLUMN hourly_rate REAL DEFAULT 50")
except:
    pass

c.execute('''
CREATE TABLE IF NOT EXISTS work_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL,
    action TEXT CHECK(action IN ('start', 'end')) NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
)
''')
c.execute('''
CREATE TABLE IF NOT EXISTS inventory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tire_type TEXT NOT NULL,
    quantity INTEGER NOT NULL
)
''')

# הוספת משתמשים לדוגמה
c.execute("INSERT OR IGNORE INTO users (username, password, role) VALUES (?, ?, ?)", ("admin", "1234", "manager"))
c.execute("INSERT OR IGNORE INTO users (username, password, role) VALUES (?, ?, ?)", ("worker1", "1234", "worker"))

conn.commit()
conn.close()
