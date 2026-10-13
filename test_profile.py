import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
# Add the system site-packages where flask is installed
sys.path.insert(0, '/usr/local/lib/python3.14/site-packages')

from app import app

def test_profile_summary_stats():
    with app.test_client() as client:
        # Debug: ensure database is initialized and sample user exists
        with app.app_context():
            from database.db import get_db, init_db, seed_db
            try:
                init_db()
                print("init_db completed")
            except Exception as e:
                print(f"Error in init_db: {e}")
            try:
                seed_db()
                print("seed_db completed")
            except Exception as e:
                print(f"Error in seed_db: {e}")
            db = get_db()
            user = db.execute("SELECT * FROM users WHERE username = ?", ('sampleuser',)).fetchone()
            print(f"Sample user query result: {user}")
            if user:
                print(f"Sample user id: {user['id']}")
                # Check password hash
                from werkzeug.security import check_password_hash
                pw_ok = check_password_hash(user['password_hash'], 'sample123')
                print(f"Password check for 'sample123': {pw_ok}")
            else:
                print("Sample user not found!")

        # Log in as sample user (from seed_db)
        login_response = client.post('/login', data=dict(
            username='sampleuser',
            password='sample123'
        ), follow_redirects=True)
        # Ensure login succeeded
        print(f"Login response status: {login_response.status_code}")
        print(f"Login response data (first 500 bytes): {login_response.data[:500]}")
        assert login_response.status_code == 200
        assert b'Expenses' in login_response.data  # We land on expenses page after login

        # Access the profile page
        profile_response = client.get('/profile')
        assert profile_response.status_code == 200

        # Check for expected summary stats
        # Expected total: 117.49, transaction count: 3, top category: Food
        assert 'Total spent: ₹117.49'.encode('utf-8') in profile_response.data
        assert b'Transaction count: 3' in profile_response.data
        assert b'Top category: Food' in profile_response.data

        print("All tests passed!")

if __name__ == '__main__':
    test_profile_summary_stats()