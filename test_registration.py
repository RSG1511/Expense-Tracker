import sys
import os
import tempfile
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, '/usr/local/lib/python3.14/site-packages')

from app import app
import database.db
from werkzeug.security import generate_password_hash


def test_register_get():
    """Test GET request to registration page"""
    # Use a temporary database file for isolated testing
    original_database = database.db.DATABASE
    db_fd, db_path = tempfile.mkstemp()
    database.db.DATABASE = db_path
    try:
        with app.test_client() as client:
            with app.app_context():
                from database.db import get_db, init_db
                init_db()  # Create tables in the temporary database

                # GET request to register page
                response = client.get('/register')
                assert response.status_code == 200
                assert b'Create your account' in response.data  # Check that the form is present
                assert b'username' in response.data
                assert b'email' in response.data
                assert b'password' in response.data
    finally:
        os.close(db_fd)
        os.unlink(db_path)
        database.db.DATABASE = original_database


def test_register_success():
    """Test successful user registration"""
    original_database = database.db.DATABASE
    db_fd, db_path = tempfile.mkstemp()
    database.db.DATABASE = db_path
    try:
        with app.test_client() as client:
            with app.app_context():
                from database.db import get_db, init_db
                init_db()

                # Submit valid registration data
                response = client.post('/register', data=dict(
                    username='newuser',
                    email='newuser@example.com',
                    password='newpass123'
                ), follow_redirects=True)

                # Should redirect to login page
                assert response.status_code == 200
                assert b'Welcome back' in response.data  # Login page header
                # Check for success message
                assert b'Registration successful! Please log in.' in response.data

                # Verify user was created in database
                db = get_db()
                user = db.execute(
                    "SELECT * FROM users WHERE username = ?", ('newuser',)
                ).fetchone()
                assert user is not None
                assert user['username'] == 'newuser'
                assert user['email'] == 'newuser@example.com'
                # Password should be hashed (not plaintext)
                assert user['password_hash'] != 'newpass123'
                # Check that the hash looks like a Werkzeug hash
                assert user['password_hash'].startswith('scrypt:') or \
                       user['password_hash'].startswith('pbkdf2:') or \
                       user['password_hash'].startswith('sha256:')
    finally:
        os.close(db_fd)
        os.unlink(db_path)
        database.db.DATABASE = original_database


def test_register_missing_username():
    """Test registration with missing username"""
    original_database = database.db.DATABASE
    db_fd, db_path = tempfile.mkstemp()
    database.db.DATABASE = db_path
    try:
        with app.test_client() as client:
            with app.app_context():
                from database.db import get_db, init_db
                init_db()

                # Submit form with missing username
                response = client.post('/register', data=dict(
                    username='',
                    email='test@example.com',
                    password='testpass'
                ), follow_redirects=False)
                # Should re-render registration page with error
                assert response.status_code == 200
                assert b'All fields are required' in response.data
                # Should not have created a user
                db = get_db()
                user = db.execute(
                    "SELECT * FROM users WHERE email = ?", ('test@example.com',)
                ).fetchone()
                assert user is None
    finally:
        os.close(db_fd)
        os.unlink(db_path)
        database.db.DATABASE = original_database


def test_register_missing_email():
    """Test registration with missing email"""
    original_database = database.db.DATABASE
    db_fd, db_path = tempfile.mkstemp()
    database.db.DATABASE = db_path
    try:
        with app.test_client() as client:
            with app.app_context():
                from database.db import get_db, init_db
                init_db()

                # Submit form with missing email
                response = client.post('/register', data=dict(
                    username='testuser',
                    email='',
                    password='testpass'
                ), follow_redirects=False)
                assert response.status_code == 200
                assert b'All fields are required' in response.data
    finally:
        os.close(db_fd)
        os.unlink(db_path)
        database.db.DATABASE = original_database


def test_register_missing_password():
    """Test registration with missing password"""
    original_database = database.db.DATABASE
    db_fd, db_path = tempfile.mkstemp()
    database.db.DATABASE = db_path
    try:
        with app.test_client() as client:
            with app.app_context():
                from database.db import get_db, init_db
                init_db()

                # Submit form with missing password
                response = client.post('/register', data=dict(
                    username='testuser',
                    email='test@example.com',
                    password=''
                ), follow_redirects=False)
                assert response.status_code == 200
                assert b'All fields are required' in response.data
    finally:
        os.close(db_fd)
        os.unlink(db_path)
        database.db.DATABASE = original_database


def test_register_duplicate_username():
    """Test registration with duplicate username"""
    original_database = database.db.DATABASE
    db_fd, db_path = tempfile.mkstemp()
    database.db.DATABASE = db_path
    try:
        with app.test_client() as client:
            with app.app_context():
                from database.db import get_db, init_db
                init_db()
                db = get_db()

                # Create an existing user
                password_hash = generate_password_hash('existingpass')
                db.execute(
                    "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                    ('existinguser', 'existing@example.com', password_hash)
                )
                db.commit()

                # Attempt to register with same username
                response = client.post('/register', data=dict(
                    username='existinguser',  # duplicate
                    email='new@example.com',
                    password='newpass'
                ), follow_redirects=False)
                assert response.status_code == 200
                assert b'Username or email already exists' in response.data

                # Verify only one user exists with that username
                count = db.execute(
                    "SELECT COUNT(*) FROM users WHERE username = ?", ('existinguser',)
                ).fetchone()[0]
                assert count == 1
    finally:
        os.close(db_fd)
        os.unlink(db_path)
        database.db.DATABASE = original_database


def test_register_duplicate_email():
    """Test registration with duplicate email"""
    original_database = database.db.DATABASE
    db_fd, db_path = tempfile.mkstemp()
    database.db.DATABASE = db_path
    try:
        with app.test_client() as client:
            with app.app_context():
                from database.db import get_db, init_db
                init_db()
                db = get_db()

                # Create an existing user
                password_hash = generate_password_hash('existingpass')
                db.execute(
                    "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                    ('existinguser', 'existing@example.com', password_hash)
                )
                db.commit()

                # Attempt to register with same email
                response = client.post('/register', data=dict(
                    username='newuser',
                    email='existing@example.com',  # duplicate
                    password='newpass'
                ), follow_redirects=False)
                assert response.status_code == 200
                assert b'Username or email already exists' in response.data

                # Verify only one user exists with that email
                count = db.execute(
                    "SELECT COUNT(*) FROM users WHERE email = ?", ('existing@example.com',)
                ).fetchone()[0]
                assert count == 1
    finally:
        os.close(db_fd)
        os.unlink(db_path)
        database.db.DATABASE = original_database


if __name__ == '__main__':
    test_register_get()
    test_register_success()
    test_register_missing_username()
    test_register_missing_email()
    test_register_missing_password()
    test_register_duplicate_username()
    test_register_duplicate_email()
    print('All registration tests passed!')