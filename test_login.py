import sys
import os
import tempfile
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, '/usr/local/lib/python3.14/site-packages')

from app import app
import database.db
from werkzeug.security import generate_password_hash

def test_login_valid_credentials():
    # Use a temporary database file for isolated testing
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

                # Test valid login
                login_response = client.post('/login', data=dict(
                    username='testuser',
                    password='testpass123'
                ), follow_redirects=True)
                # Should redirect to expenses page after login
                assert login_response.status_code == 200
                assert b'Expenses' in login_response.data  # We land on expenses page after login
                # Check that we are logged in by accessing profile
                profile_response = client.get('/profile')
                assert profile_response.status_code == 200
                assert b'Test User' in profile_response.data or b'testuser' in profile_response.data

    finally:
        os.close(db_fd)
        os.unlink(db_path)
        database.db.DATABASE = original_database

def test_login_invalid_credentials():
    # Use a temporary database file for isolated testing
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
                db.execute(
                    "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                    ('testuser', 'test@example.com', password_hash)
                )
                db.commit()

                # Test invalid password
                login_response = client.post('/login', data=dict(
                    username='testuser',
                    password='wrongpass'
                ), follow_redirects=False)
                # Should stay on login page (redirect to login page again? Actually, after failed login, it re-renders login page with flash)
                # The login route returns the login template on GET, but on POST with failure, it returns the login template with flash message.
                # We expect status code 200 (since it re-renders the login page) and the flash error message.
                assert login_response.status_code == 200
                assert b'Invalid username or password' in login_response.data

                # Test non-existent user
                login_response2 = client.post('/login', data=dict(
                    username='nonexistent',
                    password='anything'
                ), follow_redirects=False)
                assert login_response2.status_code == 200
                assert b'Invalid username or password' in login_response2.data

    finally:
        os.close(db_fd)
        os.unlink(db_path)
        database.db.DATABASE = original_database

if __name__ == '__main__':
    test_login_valid_credentials()
    test_login_invalid_credentials()
    print('All login tests passed!')