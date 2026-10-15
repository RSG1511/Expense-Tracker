import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
# Add the system site-packages where flask is installed
sys.path.insert(0, '/usr/local/lib/python3.14/site-packages')

from app import app
import database.db
from werkzeug.security import generate_password_hash

def test_profile_summary_stats():
    # Backup original database path
    original_database = database.db.DATABASE
    # Use an in-memory database with shared cache for isolated testing
    database.db.DATABASE = "file::memory:?cache=shared"
    try:
        with app.test_client() as client:
            with app.app_context():
                from database.db import get_db, init_db
                init_db()
                db = get_db()
                # Create test user: sampleuser / sample123
                password_hash = generate_password_hash('sample123')
                cursor = db.execute(
                    "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                    ('sampleuser', 'sample@example.com', password_hash)
                )
                user_id = cursor.lastrowid
                # Create three Food expenses totaling 117.49
                sample_expenses = [
                    (user_id, 'Expense 1', 50.00, 'Food', '2024-01-15', 'First expense'),
                    (user_id, 'Expense 2', 30.00, 'Food', '2024-01-16', 'Second expense'),
                    (user_id, 'Expense 3', 37.49, 'Food', '2024-01-17', 'Third expense'),
                ]
                db.executemany(
                    '''INSERT INTO expenses (user_id, title, amount, category, date, description)
                       VALUES (?, ?, ?, ?, ?, ?)''',
                    sample_expenses
                )
                db.commit()

                # Log in as sample user
                login_response = client.post('/login', data=dict(
                    username='sampleuser',
                    password='sample123'
                ), follow_redirects=True)
                # Ensure login succeeded
                assert login_response.status_code == 200
                assert b'Expenses' in login_response.data  # We land on expenses page after login

                # Access the profile page
                profile_response = client.get('/profile')
                assert profile_response.status_code == 200

                # Debug: print profile response data
                print(f"Profile response data (first 500 bytes): {profile_response.data[:500]}")

                # Check for expected summary stats
                # Expected total: 117.49, transaction count: 3, top category: Food
                assert b'Total Spent' in profile_response.data
                assert '₹117.49'.encode('utf-8') in profile_response.data
                assert b'Transactions' in profile_response.data
                assert b'3' in profile_response.data
                assert b'Top Category' in profile_response.data
                assert b'Food' in profile_response.data

    finally:
        # Restore original database path
        database.db.DATABASE = original_database

if __name__ == '__main__':
    test_profile_summary_stats()