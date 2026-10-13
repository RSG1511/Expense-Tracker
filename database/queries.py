from database.db import get_db
from datetime import datetime
from flask import g


def get_user_by_id(user_id):
    """Get user information by ID."""
    db = get_db()
    try:
        row = db.execute(
            '''SELECT username as name, email, created_at
               FROM users
               WHERE id = ?''',
            (user_id,)
        ).fetchone()
        if not row:
            return None
        # Format member_since as "Month YYYY"
        created_at = datetime.strptime(row['created_at'], '%Y-%m-%d %H:%M:%S')
        member_since = created_at.strftime('%B %Y')
        return {
            'name': row['name'],
            'email': row['email'],
            'member_since': member_since
        }
    finally:
        db.close()
        g._database = None


def get_summary_stats(user_id):
    """Get summary statistics for a user's expenses."""
    db = get_db()
    try:
        row = db.execute(
            '''SELECT
                   COALESCE(SUM(amount), 0) as total_spent,
                   COUNT(*) as transaction_count
               FROM expenses
               WHERE user_id = ?''',
            (user_id,)
        ).fetchone()
        total_spent = row['total_spent']
        transaction_count = row['transaction_count']

        # Get top category
        top_category_row = db.execute(
            '''SELECT category, SUM(amount) as cat_total
               FROM expenses
               WHERE user_id = ?
               GROUP BY category
               ORDER BY cat_total DESC
               LIMIT 1''',
            (user_id,)
        ).fetchone()
        top_category = top_category_row['category'] if top_category_row and total_spent > 0 else "—"

        return {
            'total_spent': total_spent,
            'transaction_count': transaction_count,
            'top_category': top_category
        }
    finally:
        db.close()
        g._database = None


def get_recent_transactions(user_id, limit=10):
    """Get recent transactions for a user."""
    db = get_db()
    try:
        rows = db.execute(
            '''SELECT date, description, category, amount
               FROM expenses
               WHERE user_id = ?
               ORDER BY date DESC
               LIMIT ?''',
            (user_id, limit)
        ).fetchall()
        # Convert rows to list of dicts
        return [dict(row) for row in rows]
    finally:
        db.close()
        g._database = None


def get_category_breakdown(user_id):
    """Get category breakdown for a user's expenses."""
    db = get_db()
    try:
        rows = db.execute(
            '''SELECT category, SUM(amount) as total
               FROM expenses
               WHERE user_id = ?
               GROUP BY category''',
            (user_id,)
        ).fetchall()

        if not rows:
            return []

        # Calculate total spent
        total_spent = sum(row['total'] for row in rows)
        if total_spent == 0:
            return []

        # Build list with percentages
        result = []
        for row in rows:
            pct = round((row['total'] / total_spent) * 100)
            result.append({
                'name': row['category'],
                'amount': row['total'],
                'pct': pct
            })

        # Sort by amount descending
        result.sort(key=lambda x: x['amount'], reverse=True)

        # Adjust percentages to sum to 100
        total_pct = sum(item['pct'] for item in result)
        if total_pct != 100 and result:
            diff = 100 - total_pct
            # Add difference to the largest category (first item)
            result[0]['pct'] += diff

        return result
    finally:
        db.close()
        g._database = None