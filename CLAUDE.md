# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This is a Flask web application for tracking personal expenses. Users can register, log in, add/edit/delete expenses, and view their expense history. The application uses SQLite for data storage and features session-based authentication.

## Project Structure

- `app.py` - Main Flask application containing all routes and application logic
- `database/db.py` - Database helper functions for initialization, connection, and seeding
- `templates/` - HTML templates for server-side rendering (base layout, landing, auth, expense pages)
- `static/` - Static assets (CSS and JavaScript)
  - `static/css/style.css` - Main stylesheet
  - `static/js/main.js` - JavaScript functionality
- `expense_tracker.db` - SQLite database file (gitignored)
- `requirements.txt` - Python dependencies (Flask, Werkzeug, pytest, pytest-flask)
- `venv/` - Virtual environment (gitignored)

## Key Components

### Application Flow
1. Users access the landing page (`/`) which redirects to expenses if logged in
2. Authentication routes: `/register`, `/login`, `/logout`
3. Expense management: 
   - View expenses: `/expenses` (login required)
   - Add expense: `/expenses/add` (login required)
   - Edit expense: `/expenses/<int:id>/edit` (login required)
   - Delete expense: `/expenses/<int:id>/delete` (login required, POST only)
4. Static pages: `/terms`, `/privacy`

### Database
- Users table: id, username, email, password_hash, created_at
- Expenses table: id, user_id (FK), title, amount, category, date, description, created_at
- Initialized via `init_db()` and seeded with sample data via `seed_db()` on app startup

### Authentication
- Session-based using Flask's `session`
- Passwords hashed with Werkzeug's `generate_password_hash`/`check_password_hash`
- `login_required` decorator protects routes

## Development Commands

### Setup
1. Create virtual environment: `python -m venv venv`
2. Activate: `source venv/bin/activate` (Linux/Mac) or `venv\Scripts\activate` (Windows)
3. Install dependencies: `pip install -r requirements.txt`

### Running the Application
```bash
# Method 1: Direct execution
python app.py

# Method 2: Using Flask CLI
export FLASK_APP=app.py
export FLASK_ENV=development  # enables debug mode
flask run --host=0.0.0.0 --port=5006
```

The application will be available at http://localhost:5006

### Running Tests
While no test files currently exist, the project includes pytest and pytest-flask dependencies. To run tests:
```bash
pytest
```
Tests should be placed in a `tests/` directory or named `test_*.py` for discovery.

### Database Management
- The database is initialized automatically on app startup via `init_db()`
- Sample data is populated via `seed_db()` if no users exist
- To reset: delete `expense_tracker.db` and restart the application

### Linting/Formatting
No specific linting tools are configured, but you can add:
- Flake8: `pip install flake8` then `flake8 .`
- Black: `pip install black` then `black .`

## Architecture Notes

### Separation of Concerns
- **Presentation**: HTML templates in `templates/` with base template inheritance
- **Application Logic**: Routes and route handlers in `app.py`
- **Data Access**: Database functions in `database/db.py`
- **Static Assets**: CSS in `static/css/`, JavaScript in `static/js/`

### Extensibility
For larger applications, consider:
- Splitting routes into Flask blueprints
- Moving database models to separate models.py
- Using application factories pattern
- Adding form validation with WTForms or similar

### Security Considerations
- Secret key is hardcoded (should be moved to environment variable in production)
- Debug mode enabled (should be disabled in production)
- Consider adding CSRF protection
- Use HTTPS in production