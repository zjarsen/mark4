"""
Admin Portal for Mark4 Telegram Bot

A Flask-based web interface for monitoring user activity, transactions, and system metrics.
"""

from flask import Flask, render_template, request, jsonify
import sqlite3
import logging
from datetime import datetime
from pathlib import Path
import pytz
from typing import Dict, List, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('admin_portal')

# Initialize Flask app
app = Flask(__name__)

# Configuration
DATABASE_PATH = './mark4_bot.db'  # Relative path since we're in data folder


def get_db_connection():
    """
    Get database connection with row factory.

    Returns:
        sqlite3.Connection: Database connection with Row factory
    """
    conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False, timeout=10.0)
    conn.row_factory = sqlite3.Row  # Return rows as dictionaries
    return conn


def format_timestamp_gmt8(utc_timestamp_str: str) -> str:
    """
    Convert UTC timestamp to GMT+8 display format.

    Args:
        utc_timestamp_str: UTC timestamp string in format 'YYYY-MM-DD HH:MM:SS'

    Returns:
        Formatted timestamp string in GMT+8 timezone
    """
    if not utc_timestamp_str:
        return "N/A"

    try:
        # Parse UTC timestamp
        dt = datetime.strptime(utc_timestamp_str, '%Y-%m-%d %H:%M:%S')
        dt_utc = pytz.utc.localize(dt)

        # Convert to GMT+8
        gmt8 = pytz.timezone('Asia/Shanghai')
        dt_gmt8 = dt_utc.astimezone(gmt8)

        return dt_gmt8.strftime('%Y-%m-%d %H:%M:%S')
    except Exception as e:
        logger.error(f"Error formatting timestamp {utc_timestamp_str}: {str(e)}")
        return utc_timestamp_str


def get_vip_display_name(tier: str) -> str:
    """
    Get Chinese display name for VIP tier.

    Args:
        tier: VIP tier code ('none', 'vip', or 'black_gold')

    Returns:
        Chinese display name
    """
    tier_names = {
        'none': '普通用户',
        'vip': '永久VIP',
        'black_gold': '永久黑金VIP'
    }
    return tier_names.get(tier, '普通用户')


@app.route('/')
@app.route('/users')
def dashboard_users():
    """
    User management dashboard.

    Displays user list with usage statistics, VIP status, and credit balance.
    Supports search by user_id or username.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Get search parameters
        search_user_id = request.args.get('user_id', '')
        search_username = request.args.get('username', '')

        # Build query with usage statistics
        query = """
            SELECT
                u.user_id,
                u.telegram_username,
                u.created_at,
                u.vip_tier,
                u.credit_balance,
                u.total_spent,
                COALESCE(img_count.count, 0) as image_processing_count,
                COALESCE(free_count.count, 0) as free_usage_count,
                COALESCE(vid_count.count, 0) as video_processing_count
            FROM users u
            LEFT JOIN (
                SELECT user_id, COUNT(*) as count
                FROM transactions
                WHERE description LIKE '%image_processing%' AND transaction_type = 'deduction'
                GROUP BY user_id
            ) img_count ON u.user_id = img_count.user_id
            LEFT JOIN (
                SELECT user_id, COUNT(*) as count
                FROM transactions
                WHERE amount = 0 AND transaction_type = 'deduction' AND description LIKE '%免费使用%'
                GROUP BY user_id
            ) free_count ON u.user_id = free_count.user_id
            LEFT JOIN (
                SELECT user_id, COUNT(*) as count
                FROM transactions
                WHERE description LIKE '%video_processing%' AND transaction_type = 'deduction'
                GROUP BY user_id
            ) vid_count ON u.user_id = vid_count.user_id
        """

        conditions = []
        params = []

        if search_user_id:
            conditions.append("u.user_id = ?")
            params.append(search_user_id)

        if search_username:
            conditions.append("u.telegram_username LIKE ?")
            params.append(f"%{search_username}%")

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY u.created_at DESC"

        cursor.execute(query, params)
        users = cursor.fetchall()

        # Format data for template
        users_data = []
        for user in users:
            users_data.append({
                'user_id': user['user_id'],
                'username': user['telegram_username'] or 'N/A',
                'created_at': format_timestamp_gmt8(user['created_at']),
                'vip_tier': user['vip_tier'],
                'vip_display': get_vip_display_name(user['vip_tier']),
                'credit_balance': int(user['credit_balance']),
                'total_spent': int(user['total_spent']),
                'image_count': user['image_processing_count'],
                'free_count': user['free_usage_count'],
                'video_count': user['video_processing_count']
            })

        conn.close()

        return render_template('dashboard_users.html',
                             users=users_data,
                             search_user_id=search_user_id,
                             search_username=search_username)

    except Exception as e:
        logger.error(f"Error loading user dashboard: {str(e)}", exc_info=True)
        return f"Error loading dashboard: {str(e)}", 500


@app.route('/transactions')
def dashboard_transactions():
    """
    Transaction ledger dashboard.

    Displays transaction history with pagination, filtering by type and user_id.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Pagination
        page = int(request.args.get('page', 1))
        per_page = 50
        offset = (page - 1) * per_page

        # Filters
        filter_type = request.args.get('type', '')
        search_user_id = request.args.get('user_id', '')

        # Build query
        query = "SELECT * FROM transactions WHERE 1=1"
        params = []

        if filter_type:
            query += " AND transaction_type = ?"
            params.append(filter_type)

        if search_user_id:
            query += " AND user_id = ?"
            params.append(search_user_id)

        # Get total count
        count_query = query.replace("SELECT *", "SELECT COUNT(*)")
        cursor.execute(count_query, params)
        total_count = cursor.fetchone()[0]

        # Get paginated results
        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([per_page, offset])

        cursor.execute(query, params)
        transactions = cursor.fetchall()

        # Format data for template
        transactions_data = []
        for txn in transactions:
            transactions_data.append({
                'id': txn['id'],
                'user_id': txn['user_id'],
                'type': txn['transaction_type'],
                'amount': txn['amount'],
                'balance_after': txn['balance_after'],
                'description': txn['description'] or 'N/A',
                'created_at': format_timestamp_gmt8(txn['created_at'])
            })

        conn.close()

        # Calculate pagination
        total_pages = max(1, (total_count + per_page - 1) // per_page)

        return render_template('dashboard_transactions.html',
                             transactions=transactions_data,
                             page=page,
                             total_pages=total_pages,
                             total_count=total_count,
                             filter_type=filter_type,
                             search_user_id=search_user_id)

    except Exception as e:
        logger.error(f"Error loading transaction dashboard: {str(e)}", exc_info=True)
        return f"Error loading dashboard: {str(e)}", 500


@app.route('/features')
def dashboard_features():
    """
    Feature usage analytics dashboard.

    Displays usage statistics, revenue breakdown, and 30-day usage trends.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Get feature usage totals (separate paid and free)
        cursor.execute("""
            SELECT
                SUM(CASE WHEN description LIKE '%image_processing%' AND amount < 0 THEN 1 ELSE 0 END) as image_paid,
                SUM(CASE WHEN description LIKE '%免费使用%' AND (description LIKE '%image_processing%' OR description LIKE '%粉色蕾丝内衣%') AND amount = 0 THEN 1 ELSE 0 END) as image_free,
                SUM(CASE WHEN description LIKE '%video_processing%' AND amount < 0 THEN 1 ELSE 0 END) as video_paid,
                SUM(CASE WHEN description LIKE '%video_processing%' AND amount = 0 THEN 1 ELSE 0 END) as video_free,
                SUM(CASE WHEN description LIKE '%image_processing%' THEN ABS(amount) ELSE 0 END) as image_revenue,
                SUM(CASE WHEN description LIKE '%video_processing%' THEN ABS(amount) ELSE 0 END) as video_revenue
            FROM transactions
            WHERE transaction_type = 'deduction'
        """)

        stats = cursor.fetchone()

        # Get 30-day usage trends (daily aggregation, separate paid and free)
        cursor.execute("""
            SELECT
                DATE(created_at) as date,
                SUM(CASE WHEN description LIKE '%image_processing%' AND amount < 0 THEN 1 ELSE 0 END) as image_paid,
                SUM(CASE WHEN description LIKE '%免费使用%' AND (description LIKE '%image_processing%' OR description LIKE '%粉色蕾丝内衣%') AND amount = 0 THEN 1 ELSE 0 END) as image_free,
                SUM(CASE WHEN description LIKE '%video_processing%' AND amount < 0 THEN 1 ELSE 0 END) as video_paid,
                SUM(CASE WHEN description LIKE '%video_processing%' AND amount = 0 THEN 1 ELSE 0 END) as video_free
            FROM transactions
            WHERE transaction_type = 'deduction'
                AND created_at >= datetime('now', '-30 days')
            GROUP BY DATE(created_at)
            ORDER BY date ASC
        """)

        daily_usage = cursor.fetchall()

        # Get free trial usage
        cursor.execute("""
            SELECT COUNT(*) as free_trial_users
            FROM users
            WHERE free_image_processing_used = 1
        """)

        free_trial = cursor.fetchone()

        conn.close()

        # Format data for template
        analytics_data = {
            'image_paid': stats['image_paid'] or 0,
            'image_free': stats['image_free'] or 0,
            'image_total': (stats['image_paid'] or 0) + (stats['image_free'] or 0),
            'video_paid': stats['video_paid'] or 0,
            'video_free': stats['video_free'] or 0,
            'video_total': (stats['video_paid'] or 0) + (stats['video_free'] or 0),
            'image_revenue': int(stats['image_revenue'] or 0),
            'video_revenue': int(stats['video_revenue'] or 0),
            'free_trial_users': free_trial['free_trial_users'] or 0,
            'daily_usage': [
                {
                    'date': row['date'],
                    'image_paid': row['image_paid'],
                    'image_free': row['image_free'],
                    'video_paid': row['video_paid'],
                    'video_free': row['video_free']
                }
                for row in daily_usage
            ]
        }

        return render_template('dashboard_features.html',
                             analytics=analytics_data)

    except Exception as e:
        logger.error(f"Error loading feature dashboard: {str(e)}", exc_info=True)
        return f"Error loading dashboard: {str(e)}", 500


@app.route('/api/user/<int:user_id>/transactions')
def api_user_transactions(user_id):
    """
    Get user's detailed transaction history (for modal).

    Args:
        user_id: Telegram user ID

    Returns:
        JSON array of transaction records
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM transactions
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT 50
        """, (user_id,))

        transactions = cursor.fetchall()

        # Format data
        transactions_data = []
        for txn in transactions:
            transactions_data.append({
                'id': txn['id'],
                'type': txn['transaction_type'],
                'amount': txn['amount'],
                'balance_after': txn['balance_after'],
                'description': txn['description'] or 'N/A',
                'created_at': format_timestamp_gmt8(txn['created_at'])
            })

        conn.close()

        return jsonify(transactions_data)

    except Exception as e:
        logger.error(f"Error getting user transactions: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/health')
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'service': 'admin_portal',
        'database': 'mark4_bot.db'
    }), 200


if __name__ == '__main__':
    import sys

    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8081

    logger.info(f"Starting Mark4 Admin Portal on port {port}")
    logger.info(f"User Management: http://localhost:{port}/")
    logger.info(f"Transaction Ledger: http://localhost:{port}/transactions")
    logger.info(f"Feature Analytics: http://localhost:{port}/features")

    # Use simple Flask development server
    app.run(host='0.0.0.0', port=port, debug=False)
