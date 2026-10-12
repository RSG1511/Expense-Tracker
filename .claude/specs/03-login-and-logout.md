---
# Spec: Login and Logout

## Overview
This feature implements user authentication for Spendly. It provides login and logout functionality, allowing users to securely access their expense data. After completing the registration step, users can log in with their credentials and log out when finished. This is essential for personalized expense tracking and sets the foundation for all subsequent expense features.

## Depends on
Step 01 — Database Setup (`users` table must exist)
Step 02 — Registration (users must be able to create accounts)

## Routes
No new routes (login and logout routes already exist at GET/POST `/login` and GET `/logout`; implementation will be completed)

## Database changes
No database changes (the `users` table already contains required fields: `username`, `password_hash`)

## Templates
- **Create:** None
- **Modify:** `templates/login.html` - ensure form uses `username` and `password` fields, includes flash message display, and links to `/register` page

## Files to change
- `app.py` - implement `login()` as GET+POST handler with proper credential validation and session management; implement `logout()` to clear session
- `database/db.py` - add `get_user_by_username(username)` helper function for retrieving user records
- `templates/login.html` - verify form structure and ensure it displays flashed messages

## Files to create
- None

## New dependencies
No new dependencies (application already uses Werkzeug for password hashing)

## Rules for implementation
- No SQLAlchemy or ORMs — use raw `sqlite3` via `get_db()`
- Parameterised queries only — never use f-strings in SQL
- Passwords verified with `werkzeug.security.check_password_hash`
- Session key for the logged-in user must be `session["user_id"]` (integer)
- Use `flask.session` — do not roll a custom session mechanism
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Use `url_for()` for every internal link — never hardcode paths
- On failed login show a generic flash error ("Invalid username or password.") — do not reveal which field was wrong
- After successful login redirect to `url_for("landing")` until a dashboard route exists
- `logout()` must call `session.clear()` then redirect to `url_for("landing")`
- `get_user_by_username` belongs in `database/db.py`, not inline in the route

## Definition of done
- [ ] Visiting `GET /login` renders the login form with username and password fields
- [ ] Submitting the form with valid credentials sets `session["user_id"]` and `session["username"]` and redirects to `/`
- [ ] Submitting with a wrong password shows "Invalid username or password." flash and stays on the login page
- [ ] Submitting with an unregistered username shows the same generic error flash
- [ ] Visiting `GET /logout` clears the session and redirects to `/`
- [ ] After logout, `session["user_id"]` is no longer present
- [ ] The `/logout` route no longer returns the raw stub string
- [ ] Login template uses username field (not email) matching the backend expectation
- [ ] All CSS in login template uses CSS variables, no hardcoded color values
---