from flask import Flask, render_template, request, redirect, url_for, session, flash, g
from database.db import get_db, init_db, seed_db
from database.queries import get_user_by_id, get_summary_stats, get_recent_transactions, get_category_breakdown
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
from functools import wraps

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # In production, use environment variable

# Database helper
def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect('expense_tracker.db')
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db

@app.teardown_appcontext
def close_db(error):
    db = g.pop('db', None)
    if db is not None:
        db.close()

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    if 'user_id' in session:
        return redirect(url_for('expenses'))
    return render_template("landing.html")

@app.route("/register", methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        if not username or not email or not password:
            flash('All fields are required', 'error')
            return render_template("register.html")

        db = get_db()
        # Check if username or email already exists
        existing = db.execute(
            "SELECT id FROM users WHERE username = ? OR email = ?",
            (username, email)
        ).fetchone()
        if existing:
            flash('Username or email already exists', 'error')
            return render_template("register.html")

        try:
            password_hash = generate_password_hash(password)
            db.execute(
                "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                (username, email, password_hash)
            )
            db.commit()
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Username or email already exists', 'error')

    return render_template("register.html")

@app.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        db = get_db()
        user = db.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()

        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            flash('Login successful!', 'success')
            return redirect(url_for('expenses'))
        else:
            flash('Invalid username or password', 'error')

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('landing'))


@app.route("/profile")
@login_required
def profile():
    user_info = get_user_by_id(session['user_id'])
    if not user_info:
        flash('User not found', 'error')
        return redirect(url_for('landing'))
    summary_stats = get_summary_stats(session['user_id'])
    transactions = get_recent_transactions(session['user_id'])
    category_breakdown = get_category_breakdown(session['user_id'])
    return render_template("profile.html",
                           user_info=user_info,
                           summary_stats=summary_stats,
                           transactions=transactions,
                           category_breakdown=category_breakdown)

@app.route("/expenses")
@login_required
def expenses():
    db = get_db()
    expenses = db.execute(
        "SELECT * FROM expenses WHERE user_id = ? ORDER BY date DESC",
        (session['user_id'],)
    ).fetchall()
    return render_template("expenses.html", expenses=expenses)

@app.route("/expenses/add", methods=['GET', 'POST'])
@login_required
def add_expense():
    if request.method == 'POST':
        title = request.form['title']
        amount = request.form['amount']
        category = request.form['category']
        date = request.form['date']
        description = request.form['description']

        if not title or not amount or not category or not date:
            flash('Title, amount, category, and date are required', 'error')
            return render_template("add_expense.html")

        user_id = session.get('user_id')
        if user_id is None:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('login'))
        db = get_db()
        # Verify user exists
        user = db.execute('SELECT id FROM users WHERE id = ?', (user_id,)).fetchone()
        if user is None:
            session.clear()
            flash('Invalid user session. Please log in again.', 'error')
            return redirect(url_for('login'))

        db.execute(
            "INSERT INTO expenses (user_id, title, amount, category, date, description) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, title, amount, category, date, description)
        )
        db.commit()
        flash('Expense added successfully!', 'success')
        return redirect(url_for('expenses'))

    return render_template("add_expense.html")

@app.route("/expenses/<int:id>/edit", methods=['GET', 'POST'])
@login_required
def edit_expense(id):
    db = get_db()
    expense = db.execute(
        "SELECT * FROM expenses WHERE id = ? AND user_id = ?",
        (id, session['user_id'])
    ).fetchone()

    if not expense:
        flash('Expense not found', 'error')
        return redirect(url_for('expenses'))

    if request.method == 'POST':
        title = request.form['title']
        amount = request.form['amount']
        category = request.form['category']
        date = request.form['date']
        description = request.form['description']

        if not title or not amount or not category or not date:
            flash('Title, amount, category, and date are required', 'error')
            return render_template("edit_expense.html", expense=expense)

        db.execute(
            "UPDATE expenses SET title = ?, amount = ?, category = ?, date = ?, description = ? WHERE id = ? AND user_id = ?",
            (title, amount, category, date, description, id, session['user_id'])
        )
        db.commit()
        flash('Expense updated successfully!', 'success')
        return redirect(url_for('expenses'))

    return render_template("edit_expense.html", expense=expense)

@app.route("/expenses/<int:id>/delete", methods=['POST'])
@login_required
def delete_expense(id):
    db = get_db()
    db.execute(
        "DELETE FROM expenses WHERE id = ? AND user_id = ?",
        (id, session['user_id'])
    )
    db.commit()
    flash('Expense deleted successfully!', 'success')
    return redirect(url_for('expenses'))

# Initialize database
with app.app_context():
    init_db()
    seed_db()

@app.route("/terms")
def terms():
    return render_template("terms.html")
@app.route("/privacy")
def privacy():
    return render_template("privacy.html")
if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5006)