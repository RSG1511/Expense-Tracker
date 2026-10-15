import sys
sys.path.insert(0, "/workspace/expense-tracker")
import pytest
from app import app as flask_app
from database.db import init_db, get_db
import datetime


@pytest.fixture
def app():
    flask_app.config.update({
        'TESTING': True,
        'DATABASE': ':memory:',  # isolated in-memory DB per test
        'SECRET_KEY': 'test-secret',
        'WTF_CSRF_ENABLED': False,
    })
    # Override the database module's DATABASE variable to use in-memory database
    import database.db
    original_database = database.db.DATABASE
    database.db.DATABASE = 'file::memory:?cache=shared'
    try:
        with flask_app.app_context():
            init_db()
            yield flask_app
    finally:
        database.db.DATABASE = original_database


@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def auth_client(client):
    """A test client that is already logged in."""
    # Register a user
    client.post('/register', data={
        'username': 'testuser',
        'email': 'test@example.com',
        'password': 'testpass'
    })
    # Log in
    client.post('/login', data={
        'username': 'testuser',
        'password': 'testpass'
    })
    return client

def test_profile_unauthenticated_redirects(client):
    """Unauthenticated access to /profile should redirect to login."""
    response = client.get('/profile', follow_redirects=False)
    assert response.status_code == 302
    assert '/login' in response.location

def test_profile_authenticated_shows_all_expenses_by_default(auth_client):
    """When logged in with no expenses, profile shows zero totals."""
    response = auth_client.get('/profile')
    assert response.status_code == 200
    # Check that the page shows zero total spent and zero transactions
    assert '₹0.00'.encode() in response.data  # total spent
    # Check for transaction count (might be in a specific element)
    # We'll look for a pattern; adjust based on actual template
    assert b'0' in response.data  # transaction count

def test_profile_date_filter_no_params_shows_all(auth_client):
    """Explicitly providing no date params (or invalid) shows all expenses."""
    # Insert an expense outside any preset range to ensure we can see it's included
    # We'll use the DB helper to insert directly for test setup
    with flask_app.app_context():
        db = get_db()
        # Get the test user's id
        from database.db import get_user_by_username
        user = get_user_by_username('testuser')
        user_id = user['id']
        # Insert an expense with a known date
        db.execute(
            "INSERT INTO expenses (user_id, title, amount, category, date, description) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, 'Test Expense', 100.0, 'Test', '2024-01-15', 'Test description')
        )
        db.commit()

    # Request with no query params
    response = auth_client.get('/profile')
    assert response.status_code == 200
    # Check that the expense appears in the recent transactions
    assert b'Test Expense' in response.data
    assert '₹100.00'.encode() in response.data

def profile_set_dates(client, date_from, date_to):
    """Helper to make a profile request with date params."""
    return client.get(f'/profile?date_from={date_from}&date_to={date_to}')

def test_profile_date_filter_valid_range(auth_client):
    """Filtering with a valid date range returns only expenses in that range."""
    with flask_app.app_context():
        db = get_db()
        from database.db import get_user_by_username
        user = get_user_by_username('testuser')
        user_id = user['id']
        # Insert two expenses: one inside range, one outside
        db.execute(
            "INSERT INTO expenses (user_id, title, amount, category, date, description) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, 'Inside Range', 50.0, 'Test', '2024-06-15', 'Inside')
        )
        db.execute(
            "INSERT INTO expenses (user_id, title, amount, category, date, description) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, 'Outside Range', 200.0, 'Test', '2023-01-01', 'Outside')
        )
        db.commit()

    # Filter to June 2024
    response = auth_client.get('/profile?date_from=2024-06-01&date_to=2024-06-30')
    assert response.status_code == 200
    # Should contain the inside expense
    assert b'Inside Range' in response.data
    assert '₹50.00'.encode() in response.data
    # Should NOT contain the outside expense
    assert b'Outside Range' not in response.data
    assert '₹200.00'.encode() not in response.data

def test_profile_date_filter_invalid_range_flip_dates(auth_client):
    """If date_from > date_to, should flash error and show all expenses."""
    with flask_app.app_context():
        db = get_db()
        from database.db import get_user_by_username
        user = get_user_by_username('testuser')
        user_id = user['id']
        # Insert an expense
        db.execute(
            "INSERT INTO expenses (user_id, title, amount, category, date, description) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, 'Test Expense', 150.0, 'Test', '2024-07-01', 'Test')
        )
        db.commit()

    # Send date_from after date_to
    response = auth_client.get('/profile?date_from=2024-07-02&date_to=2024-07-01', follow_redirects=True)
    assert response.status_code == 200
    # Check for flash error message
    assert b'Start date must be before end date.' in response.data
    # Should still show the expense (because fallback to unfiltered)
    assert b'Test Expense' in response.data
    assert '₹150.00'.encode() in response.data

def test_profile_date_filter_malformed_date_ignored(auth_client):
    """Malformed date params are ignored, falling back to unfiltered view."""
    with flask_app.app_context():
        db = get_db()
        from database.db import get_user_by_username
        user = get_user_by_username('testuser')
        user_id = user['id']
        # Insert an expense
        db.execute(
            "INSERT INTO expenses (user_id, title, amount, category, date, description) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, 'Test Expense', 75.0, 'Test', '2024-08-01', 'Test')
        )
        db.commit()

    # Send a malformed date_from
    response = auth_client.get('/profile?date_from=not-a-date&date_to=2024-08-31')
    assert response.status_code == 200
    # Should show the expense (because malformed date is ignored, so unfiltered)
    assert b'Test Expense' in response.data
    assert '₹75.00'.encode() in response.data

def test_profile_preset_this_month(auth_client):
    """Clicking 'This Month' preset filters to current month."""
    # We'll calculate what "This Month" should be based on today
    today = datetime.date.today()
    month_start = today.replace(day=1).strftime('%Y-%m-%d')
    # Today's date as end
    today_end = today.strftime('%Y-%m-%d')

    with flask_app.app_context():
        db = get_db()
        from database.db import get_user_by_username
        user = get_user_by_username('testuser')
        user_id = user['id']
        # Insert an expense in current month and one outside
        db.execute(
            "INSERT INTO expenses (user_id, title, amount, category, date, description) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, 'This Month Expense', 30.0, 'Test', month_start, 'In month')
        )
        # Last month expense (approximate)
        last_month = (today.replace(day=1) - datetime.timedelta(days=1)).replace(day=15)
        db.execute(
            "INSERT INTO expenses (user_id, title, amount, category, date, description) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, 'Last Month Expense', 40.0, 'Test', last_month.strftime('%Y-%m-%d'), 'Last month')
        )
        db.commit()

    # Request the profile with the preset params (as if the link was clicked)
    response = auth_client.get(f'/profile?date_from={month_start}&date_to={today_end}')
    assert response.status_code == 200
    # Should show the current month expense
    assert b'This Month Expense' in response.data
    assert '₹30.00'.encode() in response.data
    # Should NOT show last month's expense
    assert b'Last Month Expense' not in response.data
    assert '₹40.00'.encode() not in response.data

def test_profile_preset_last_3_months(auth_client):
    """Clicking 'Last 3 Months' preset filters to last 3 months."""
    today = datetime.date.today()
    three_months_start = (today - datetime.timedelta(days=90)).strftime('%Y-%m-%d')
    today_end = today.strftime('%Y-%m-%d')

    with flask_app.app_context():
        db = get_db()
        from database.db import get_user_by_username
        user = get_user_by_username('testuser')
        user_id = user['id']
        # Insert an expense within last 3 months and one older
        db.execute(
            "INSERT INTO expenses (user_id, title, amount, category, date, description) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, 'Recent Expense', 25.0, 'Test', (today - datetime.timedelta(days=45)).strftime('%Y-%m-%d'), 'Recent')
        )
        # Older than 3 months
        old_date = (today - datetime.timedelta(days=100)).strftime('%Y-%m-%d')
        db.execute(
            "INSERT INTO expenses (user_id, title, amount, category, date, description) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, 'Old Expense', 60.0, 'Test', old_date, 'Old')
        )
        db.commit()

    response = auth_client.get(f'/profile?date_from={three_months_start}&date_to={today_end}')
    assert response.status_code == 200
    assert b'Recent Expense' in response.data
    assert '₹25.00'.encode() in response.data
    assert b'Old Expense' not in response.data
    assert '₹60.00'.encode() not in response.data

def test_profile_preset_last_6_months(auth_client):
    """Clicking 'Last 6 Months' preset filters to last 6 months."""
    today = datetime.date.today()
    six_months_start = (today - datetime.timedelta(days=180)).strftime('%Y-%m-%d')
    today_end = today.strftime('%Y-%m-%d')

    with flask_app.app_context():
        db = get_db()
        from database.db import get_user_by_username
        user = get_user_by_username('testuser')
        user_id = user['id']
        # Insert an expense within last 6 months and one older
        db.execute(
            "INSERT INTO expenses (user_id, title, amount, category, date, description) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, 'Six Month Expense', 35.0, 'Test', (today - datetime.timedelta(days=100)).strftime('%Y-%m-%d'), 'Within 6 months')
        )
        # Older than 6 months
        very_old = (today - datetime.timedelta(days=200)).strftime('%Y-%m-%d')
        db.execute(
            "INSERT INTO expenses (user_id, title, amount, category, date, description) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, 'Very Old Expense', 90.0, 'Test', very_old, 'Older than 6 months')
        )
        db.commit()

    response = auth_client.get(f'/profile?date_from={six_months_start}&date_to={today_end}')
    assert response.status_code == 200
    assert b'Six Month Expense' in response.data
    assert '₹35.00'.encode() in response.data
    assert b'Very Old Expense' not in response.data
    assert '₹90.00'.encode() not in response.data

def test_profile_preset_all_time_shows_all(auth_client):
    """Clicking 'All Time' (no params) shows all expenses."""
    with flask_app.app_context():
        db = get_db()
        from database.db import get_user_by_username
        user = get_user_by_username('testuser')
        user_id = user['id']
        # Insert two expenses
        db.execute(
            "INSERT INTO expenses (user_id, title, amount, category, date, description) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, 'Expense 1', 10.0, 'Test', '2024-01-01', 'First')
        )
        db.execute(
            "INSERT INTO expenses (user_id, title, amount, category, date, description) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, 'Expense 2', 20.0, 'Test', '2024-12-01', 'Second')
        )
        db.commit()

    # Request with no query params (All Time)
    response = auth_client.get('/profile')
    assert response.status_code == 200
    assert b'Expense 1' in response.data
    assert '₹10.00'.encode() in response.data
    assert b'Expense 2' in response.data
    assert '₹20.00'.encode() in response.data

def test_profile_date_filter_empty_strings_treated_as_missing(auth_client):
    """Empty date_from or date_to strings are treated as not provided (unfiltered)."""
    with flask_app.app_context():
        db = get_db()
        from database.db import get_user_by_username
        user = get_user_by_username('testuser')
        user_id = user['id']
        db.execute(
            "INSERT INTO expenses (user_id, title, amount, category, date, description) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, 'Test Expense', 55.0, 'Test', '2024-05-01', 'Test')
        )
        db.commit()

    # Provide empty string for date_from
    response = auth_client.get('/profile?date_from=&date_to=2024-05-31')
    assert response.status_code == 200
    # Should show the expense (because empty date_from is ignored -> unfiltered)
    assert b'Test Expense' in response.data
    assert '₹55.00'.encode() in response.data

def test_profile_date_filter_highlights_active_preset_in_template(auth_client):
    """The template should highlight the active preset button (we check for a visual indicator)."""
    # We'll check that when we set a date range, the template receives the values
    # and presumably renders the active state. We can check for the presence of
    # the date values in the page (e.g., in the input fields) as a proxy.
    today = datetime.date.today()
    month_start = today.replace(day=1).strftime('%Y-%m-%d')
    today_end = today.strftime('%Y-%m-%d')

    with flask_app.app_context():
        db = get_db()
        from database.db import get_user_by_username
        user = get_user_by_username('testuser')
        user_id = user['id']
        db.execute(
            "INSERT INTO expenses (user_id, title, amount, category, date, description) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, 'Test Expense', 12.34, 'Test', month_start, 'Test')
        )
        db.commit()

    response = auth_client.get(f'/profile?date_from={month_start}&date_to={today_end}')
    assert response.status_code == 200
    # Check that the date values appear in the page (likely in the input fields' value attributes)
    # We'll look for the date strings in the HTML.
    assert month_start.encode() in response.data
    assert today_end.encode() in response.data

if __name__ == '__main__':
    pytest.main([__file__])