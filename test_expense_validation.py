import sys
import os
import tempfile
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, '/usr/local/lib/python3.14/site-packages')

from app import app
import database.db
from werkzeug.security import generate_password_hash

def get_test_client():
    """Return a test client with an isolated temporary database and a logged-in test user."""
    original_database = database.db.DATABASE
    db_fd, db_path = tempfile.mkstemp()
    database.db.DATABASE = db_path
    try:
        with app.test_client() as client:
            with app.app_context():
                from database.db import get_db, init_db
                init_db()
                db = get_db()
                # Create test user
                password_hash = generate_password_hash('testpass123')
                cursor = db.execute(
                    "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                    ('testuser', 'test@example.com', password_hash)
                )
                user_id = cursor.lastrowid
                db.commit()
                # Login
                login_resp = client.post('/login', data=dict(
                    username='testuser',
                    password='testpass123'
                ), follow_redirects=True)
                assert login_resp.status_code == 200
                assert b'Expenses' in login_resp.data
            yield client
    finally:
        os.close(db_fd)
        os.unlink(db_path)
        database.db.DATABASE = original_database

def test_add_expense_valid():
    """Test that a valid amount and date are accepted."""
    for client in get_test_client():
        resp = client.post('/expenses/add', data=dict(
            title='Test Expense',
            amount='10.50',
            category='Food',
            date='2024-01-15',
            description='Test'
        ), follow_redirects=True)
        assert resp.status_code == 200
        # Verify the expense was added
        with app.app_context():
            from database.db import get_db
            db = get_db()
            count = db.execute('SELECT COUNT(*) FROM expenses').fetchone()[0]
            assert count == 1
            row = db.execute('SELECT title, amount, category, date FROM expenses').fetchone()
            assert row[0] == 'Test Expense'
            assert float(row[1]) == 10.50
            assert row[2] == 'Food'
            assert row[3] == '2024-01-15'
        break

def test_add_expense_invalid_amount():
    """Test that invalid amounts are rejected."""
    invalid_amounts = ['abc', '', '0', '-5', 'NaN', 'inf', '-inf', '1.2.3']
    for amt in invalid_amounts:
        for client in get_test_client():
            resp = client.post('/expenses/add', data=dict(
                title='Test Expense',
                amount=amt,
                category='Food',
                date='2024-01-15',
                description='Test'
            ), follow_redirects=False)
            # Should return 200 with error message (form re-rendered)
            assert resp.status_code == 200
            # Check for appropriate error message: required field or amount validation
            assert b'Title, amount, category, and date are required' in resp.data or \
                   b'Amount must be a positive number' in resp.data
            # Ensure no expense was added
            with app.app_context():
                from database.db import get_db
                db = get_db()
                count = db.execute('SELECT COUNT(*) FROM expenses').fetchone()[0]
                assert count == 0
            break

def test_add_expense_invalid_date():
    """Test that invalid dates are rejected."""
    invalid_dates = ['2024-13-01', '2024-02-30', 'not-a-date', '2024/01/15', '']
    for dt in invalid_dates:
        for client in get_test_client():
            resp = client.post('/expenses/add', data=dict(
                title='Test Expense',
                amount='10.00',
                category='Food',
                date=dt,
                description='Test'
            ), follow_redirects=False)
            assert resp.status_code == 200
            # Check for appropriate error message: required field or date validation
            assert b'Title, amount, category, and date are required' in resp.data or \
                   b'Date must be a valid YYYY-MM-DD date' in resp.data
            # Ensure no expense was added
            with app.app_context():
                from database.db import get_db
                db = get_db()
                count = db.execute('SELECT COUNT(*) FROM expenses').fetchone()[0]
                assert count == 0
            break

def test_edit_expense_valid():
    """Test that editing an expense with valid amount and date works."""
    for client in get_test_client():
        with app.app_context():
            from database.db import get_db
            db = get_db()
            # Create an expense for the testuser
            db.execute(
                "INSERT INTO expenses (user_id, title, amount, category, date, description) VALUES (?, ?, ?, ?, ?, ?)",
                (1, 'Original Expense', 20.00, 'Food', '2024-01-01', 'Original desc')
            )
            db.commit()
            expense_id = db.execute('SELECT id FROM expenses WHERE title = ?', ('Original Expense',)).fetchone()[0]
        resp = client.post(f'/expenses/{expense_id}/edit', data=dict(
            title='Updated Expense',
            amount='25.00',
            category='Food',
            date='2024-01-02',
            description='Updated desc'
        ), follow_redirects=True)
        assert resp.status_code == 200
        with app.app_context():
            from database.db import get_db
            db = get_db()
            row = db.execute('SELECT title, amount, category, date, description FROM expenses WHERE id = ?', (expense_id,)).fetchone()
            assert row[0] == 'Updated Expense'
            assert float(row[1]) == 25.00
            assert row[2] == 'Food'
            assert row[3] == '2024-01-02'
            assert row[4] == 'Updated desc'
        break

def test_edit_expense_invalid_amount():
    """Test that invalid amounts during edit are rejected and original expense unchanged."""
    for client in get_test_client():
        with app.app_context():
            from database.db import get_db
            db = get_db()
            db.execute(
                "INSERT INTO expenses (user_id, title, amount, category, date, description) VALUES (?, ?, ?, ?, ?, ?)",
                (1, 'Original Expense', 20.00, 'Food', '2024-01-01', 'Original desc')
            )
            db.commit()
            expense_id = db.execute('SELECT id FROM expenses WHERE title = ?', ('Original Expense',)).fetchone()[0]
            original_amount = db.execute('SELECT amount FROM expenses WHERE id = ?', (expense_id,)).fetchone()[0]
        resp = client.post(f'/expenses/{expense_id}/edit', data=dict(
            title='Updated Expense',
            amount='abc',
            category='Food',
            date='2024-01-02',
            description='Updated desc'
        ), follow_redirects=False)
        assert resp.status_code == 200
        # Check for appropriate error message: required field or amount validation
        assert b'Title, amount, category, and date are required' in resp.data or \
               b'Amount must be a positive number' in resp.data
        with app.app_context():
            from database.db import get_db
            db = get_db()
            amount = db.execute('SELECT amount FROM expenses WHERE id = ?', (expense_id,)).fetchone()[0]
            assert amount == original_amount  # unchanged
        break

def test_edit_expense_invalid_date():
    """Test that invalid dates during edit are rejected and original expense unchanged."""
    for client in get_test_client():
        with app.app_context():
            from database.db import get_db
            db = get_db()
            db.execute(
                "INSERT INTO expenses (user_id, title, amount, category, date, description) VALUES (?, ?, ?, ?, ?, ?)",
                (1, 'Original Expense', 20.00, 'Food', '2024-01-01', 'Original desc')
            )
            db.commit()
            expense_id = db.execute('SELECT id FROM expenses WHERE title = ?', ('Original Expense',)).fetchone()[0]
            original_date = db.execute('SELECT date FROM expenses WHERE id = ?', (expense_id,)).fetchone()[0]
        resp = client.post(f'/expenses/{expense_id}/edit', data=dict(
            title='Updated Expense',
            amount='25.00',
            category='Food',
            date='2024-13-01',
            description='Updated desc'
        ), follow_redirects=False)
        assert resp.status_code == 200
        # Check for appropriate error message: required field or date validation
        assert b'Title, amount, category, and date are required' in resp.data or \
               b'Date must be a valid YYYY-MM-DD date' in resp.data
        with app.app_context():
            from database.db import get_db
            db = get_db()
            date = db.execute('SELECT date FROM expenses WHERE id = ?', (expense_id,)).fetchone()[0]
            assert date == original_date  # unchanged
        break

if __name__ == '__main__':
    # Run tests manually if needed
    import pytest
    pytest.main([__file__, '-v'])