import sqlite3
from flask import g

DATABASE = 'expense_tracker.db'

def get_db():
    """Returns a SQLite connection with row_factory and foreign keys enabled"""
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
    return db

def init_db():
    """Creates all tables using CREATE TABLE IF NOT EXISTS"""
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        # Users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        # Expenses table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                amount REAL NOT NULL,
                category TEXT NOT NULL,
                date DATE NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        ''')
        conn.commit()

def seed_db():
    """Inserts sample data for development"""
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        # Check if we already have a user
        cursor.execute("SELECT COUNT(*) FROM users")
        if cursor.fetchone()[0] == 0:
            # Hash a sample password
            from werkzeug.security import generate_password_hash
            password_hash = generate_password_hash('sample123')
            cursor.execute(
                "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                ('sampleuser', 'sample@example.com', password_hash)
            )
            user_id = cursor.lastrowid
            # Sample expenses
            sample_expenses = [
                (user_id, 'Groceries', 56.50, 'Food', '2024-01-15', 'Weekly shopping'),
                (user_id, 'Gasoline', 45.00, 'Transport', '2024-01-16', 'Fill up tank'),
                (user_id, 'Netflix', 15.99, 'Entertainment', '2024-01-10', 'Monthly subscription'),
            ]
            cursor.executemany(
                '''INSERT INTO expenses (user_id, title, amount, category, date, description)
                   VALUES (?, ?, ?, ?, ?, ?)''',
                sample_expenses
            )
            conn.commit()
