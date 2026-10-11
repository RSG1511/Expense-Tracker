import sqlite3
from flask import g
from werkzeug.security import generate_password_hash

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
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
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
                date TEXT NOT NULL,
                description TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
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
            password_hash = generate_password_hash('demo123')
            cursor.execute(
                "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
                ('Demo User', 'demo@spendly.com', password_hash)
            )
            user_id = cursor.lastrowid
            # Sample expenses - 8 expenses across all categories
            sample_expenses = [
                (user_id, 'Groceries', 56.50, 'Food', '2024-01-15', 'Weekly shopping'),
                (user_id, 'Gasoline', 45.00, 'Transport', '2024-01-16', 'Fill up tank'),
                (user_id, 'Electric Bill', 89.99, 'Bills', '2024-01-14', 'Monthly electricity'),
                (user_id, 'Gym Membership', 29.99, 'Health', '2024-01-10', 'Monthly subscription'),
                (user_id, 'Movie Night', 22.50, 'Entertainment', '2024-01-12', 'Weekend movie'),
                (user_id, 'New Shirt', 34.99, 'Shopping', '2024-01-13', 'Online purchase'),
                (user_id, 'Internet Bill', 69.99, 'Bills', '2024-01-13', 'Monthly internet'),
                (user_id, 'Bank Fee', 12.50, 'Other', '2024-01-11', 'Monthly service charge'),
            ]
            cursor.executemany(
                '''INSERT INTO expenses (user_id, title, amount, category, date, description)
                   VALUES (?, ?, ?, ?, ?, ?)''',
                sample_expenses
            )
            conn.commit()