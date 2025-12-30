"""
Admin Portal for Mark4 Telegram Bot

A Flask-based web interface for monitoring user activity, transactions, and system metrics.
"""

from flask import Flask, render_template, request, jsonify
import sqlite3
import logging
from datetime import datetime, timedelta
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
    Format timestamp for display, converting UTC to GMT+8.

    Args:
        utc_timestamp_str: Timestamp string in format 'YYYY-MM-DD HH:MM:SS' (in UTC)

    Returns:
        Formatted timestamp string in GMT+8 timezone
    """
    if not utc_timestamp_str:
        return "N/A"

    try:
        # Parse UTC timestamp (database stores UTC)
        dt_utc = datetime.strptime(utc_timestamp_str, '%Y-%m-%d %H:%M:%S')

        # Add UTC timezone info
        dt_utc = pytz.utc.localize(dt_utc)

        # Convert to GMT+8 (Asia/Shanghai)
        gmt8 = pytz.timezone('Asia/Shanghai')
        dt_gmt8 = dt_utc.astimezone(gmt8)

        # Format and return with timezone indicator
        return dt_gmt8.strftime('%Y-%m-%d %H:%M:%S') + ' GMT+8'
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
                COALESCE(spent.total, 0) as total_spent,
                COALESCE(img_count.count, 0) as image_processing_count,
                COALESCE(free_count.count, 0) as free_usage_count,
                COALESCE(vid_count.count, 0) as video_processing_count
            FROM users u
            LEFT JOIN (
                SELECT user_id, SUM(ABS(amount)) as total
                FROM transactions
                WHERE transaction_type = 'deduction' AND amount < 0
                GROUP BY user_id
            ) spent ON u.user_id = spent.user_id
            LEFT JOIN (
                SELECT user_id, COUNT(*) as count
                FROM transactions
                WHERE description LIKE '%image_processing%' AND transaction_type = 'deduction' AND amount < 0
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
                WHERE description LIKE '%video_processing%' AND transaction_type = 'deduction' AND amount < 0
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

    Displays usage statistics, revenue breakdown, and usage trends with moving window controls.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Get window parameters (default: last 7 days)
        window_days = int(request.args.get('days', 7))
        window_offset = int(request.args.get('offset', 0))

        # Clamp values to reasonable ranges
        window_days = max(7, min(365, window_days))  # 7-365 days
        window_offset = max(-1000, min(0, window_offset))  # Max 1000 days back, 0 for current

        # Calculate date range in GMT+8 (database stores local time)
        gmt8 = pytz.timezone('Asia/Shanghai')
        now_gmt8 = datetime.now(gmt8)

        # Use midnight boundaries for clean daily buckets
        # End date: midnight of tomorrow (to include all of today)
        end_date_gmt8 = now_gmt8.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=window_offset + 1)
        start_date_gmt8 = end_date_gmt8 - timedelta(days=window_days)

        # Use GMT+8 datetime strings directly (database stores local time, not UTC)
        start_date_str = start_date_gmt8.strftime('%Y-%m-%d %H:%M:%S')
        end_date_str = end_date_gmt8.strftime('%Y-%m-%d %H:%M:%S')

        # Feature display names and costs
        FEATURE_DISPLAY_NAMES = {
            'image_bra': '📸 粉色蕾丝内衣',
            'image_undress': '📸 脱到精光',
            'video_a': '🎬 脱衣+抖胸',
            'video_b': '🎬 脱衣+下体流精',
            'video_c': '🎬 脱衣+吃吊喝精'
        }

        FEATURE_COSTS = {
            'image_bra': 0,
            'image_undress': 10,
            'video_a': 30,
            'video_b': 30,
            'video_c': 30
        }

        # Get feature usage totals by feature_type
        cursor.execute("""
            SELECT
                feature_type,
                COUNT(*) as usage_count,
                SUM(ABS(amount)) as revenue,
                COUNT(DISTINCT user_id) as unique_users,
                SUM(CASE WHEN amount = 0 THEN 1 ELSE 0 END) as free_usage,
                SUM(CASE WHEN amount < 0 THEN 1 ELSE 0 END) as paid_usage
            FROM transactions
            WHERE transaction_type = 'deduction'
                AND feature_type IS NOT NULL
                AND created_at >= ? AND created_at < ?
            GROUP BY feature_type
            ORDER BY usage_count DESC
        """, (start_date_str, end_date_str))

        feature_stats = cursor.fetchall()

        # Get daily usage trends by feature_type
        cursor.execute("""
            SELECT
                DATE(created_at) as date_gmt8,
                feature_type,
                COUNT(*) as usage_count
            FROM transactions
            WHERE transaction_type = 'deduction'
                AND feature_type IS NOT NULL
                AND created_at >= ? AND created_at < ?
            GROUP BY date_gmt8, feature_type
            ORDER BY date_gmt8 ASC
        """, (start_date_str, end_date_str))

        daily_trends = cursor.fetchall()

        conn.close()

        # Process feature stats into structured format
        features_list = []
        for row in feature_stats:
            feature_type = row['feature_type']
            features_list.append({
                'name': feature_type,
                'display_name': FEATURE_DISPLAY_NAMES.get(feature_type, feature_type),
                'total_usage': row['usage_count'] or 0,
                'paid_usage': row['paid_usage'] or 0,
                'free_usage': row['free_usage'] or 0,
                'revenue': int(row['revenue'] or 0),
                'unique_users': row['unique_users'] or 0,
                'cost': FEATURE_COSTS.get(feature_type, 0)
            })

        # Transform daily trends into date-keyed objects
        daily_usage_map = {}
        for row in daily_trends:
            date = row['date_gmt8']
            feature_type = row['feature_type']
            count = row['usage_count']

            if date not in daily_usage_map:
                daily_usage_map[date] = {
                    'date': date,
                    'image_bra': 0,
                    'image_undress': 0,
                    'video_a': 0,
                    'video_b': 0,
                    'video_c': 0
                }

            daily_usage_map[date][feature_type] = count

        # Convert to sorted list
        daily_usage_list = sorted(daily_usage_map.values(), key=lambda x: x['date'])

        # Format data for template
        analytics_data = {
            'features': features_list,
            'daily_usage': daily_usage_list
        }

        # Window control parameters
        window_params = {
            'days': window_days,
            'offset': window_offset,
            'start_date': start_date_gmt8.strftime('%Y-%m-%d'),
            'end_date': end_date_gmt8.strftime('%Y-%m-%d')
        }

        return render_template('dashboard_features.html',
                             analytics=analytics_data,
                             window=window_params)

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


@app.route('/daily-data')
def dashboard_daily_data():
    """
    Daily data analytics dashboard.

    Displays:
    - Daily active users (any activity in transactions)
    - Daily paying users (completed payments)
    - Daily revenue (CNY from completed payments)
    - Next-day retention rate (users active yesterday who are also active today)

    Supports moving window controls for date range selection.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Get window parameters (default: last 7 days)
        window_days = int(request.args.get('days', 7))
        window_offset = int(request.args.get('offset', 0))

        # Clamp values to reasonable ranges
        window_days = max(7, min(365, window_days))  # 7-365 days
        window_offset = max(-1000, min(0, window_offset))  # Max 1000 days back, 0 for current

        # Calculate date range in GMT+8 (database stores local time)
        gmt8 = pytz.timezone('Asia/Shanghai')
        now_gmt8 = datetime.now(gmt8)

        # Use midnight boundaries for clean daily buckets
        # End date: midnight of tomorrow (to include all of today)
        end_date_gmt8 = now_gmt8.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=window_offset + 1)
        start_date_gmt8 = end_date_gmt8 - timedelta(days=window_days)

        # Use GMT+8 datetime strings directly (database stores local time, not UTC)
        start_date_str = start_date_gmt8.strftime('%Y-%m-%d %H:%M:%S')
        end_date_str = end_date_gmt8.strftime('%Y-%m-%d %H:%M:%S')

        # Query 1: Daily Active Users (any transaction activity)
        cursor.execute("""
            SELECT
                DATE(created_at) as date_gmt8,
                COUNT(DISTINCT user_id) as active_users
            FROM transactions
            WHERE created_at >= ? AND created_at < ?
            GROUP BY DATE(created_at)
            ORDER BY date_gmt8 ASC
        """, (start_date_str, end_date_str))

        active_users_data = cursor.fetchall()

        # Query 2: Daily Paying Users + Revenue (completed payments only)
        cursor.execute("""
            SELECT
                DATE(completed_at) as date_gmt8,
                COUNT(DISTINCT user_id) as paying_users,
                SUM(amount) as revenue_cny
            FROM payments
            WHERE status = 'completed'
                AND completed_at >= ? AND completed_at < ?
            GROUP BY DATE(completed_at)
            ORDER BY date_gmt8 ASC
        """, (start_date_str, end_date_str))

        payment_data = cursor.fetchall()

        # Query 3: Next-Day Retention Rate
        # Need to extend query range by 1 day before start to calculate retention for first day
        extended_start_gmt8 = start_date_gmt8 - timedelta(days=1)
        extended_start_str = extended_start_gmt8.strftime('%Y-%m-%d %H:%M:%S')

        cursor.execute("""
            WITH daily_users AS (
                SELECT DISTINCT
                    DATE(created_at) as date_gmt8,
                    user_id
                FROM transactions
                WHERE created_at >= ? AND created_at < ?
            ),
            yesterday_counts AS (
                -- Count ALL users active on each day (for denominator)
                SELECT
                    date_gmt8,
                    COUNT(DISTINCT user_id) as total_users
                FROM daily_users
                GROUP BY date_gmt8
            ),
            retention_calc AS (
                -- Count users who were active yesterday AND today (for numerator)
                SELECT
                    today.date_gmt8 as date_gmt8,
                    COUNT(DISTINCT today.user_id) as retained_users
                FROM daily_users today
                INNER JOIN daily_users yesterday
                    ON yesterday.date_gmt8 = DATE(today.date_gmt8, '-1 day')
                    AND yesterday.user_id = today.user_id
                WHERE today.date_gmt8 >= ? AND today.date_gmt8 < ?
                GROUP BY today.date_gmt8
            )
            SELECT
                r.date_gmt8,
                COALESCE(y.total_users, 0) as yesterday_active,
                COALESCE(r.retained_users, 0) as retained_users,
                CASE
                    WHEN COALESCE(y.total_users, 0) > 0
                    THEN ROUND(CAST(COALESCE(r.retained_users, 0) AS FLOAT) / y.total_users * 100, 2)
                    ELSE NULL
                END as retention_rate
            FROM retention_calc r
            LEFT JOIN yesterday_counts y
                ON y.date_gmt8 = DATE(r.date_gmt8, '-1 day')
            ORDER BY r.date_gmt8 ASC
        """, (
            extended_start_str,
            end_date_str,
            start_date_gmt8.strftime('%Y-%m-%d'),
            end_date_gmt8.strftime('%Y-%m-%d')
        ))

        retention_data = cursor.fetchall()

        conn.close()

        # Format data for charts
        daily_data = {
            'active_users': [
                {
                    'date': row['date_gmt8'],
                    'count': row['active_users']
                }
                for row in active_users_data
            ],
            'payments': [
                {
                    'date': row['date_gmt8'],
                    'paying_users': row['paying_users'],
                    'revenue': float(row['revenue_cny']) if row['revenue_cny'] else 0.0
                }
                for row in payment_data
            ],
            'retention': [
                {
                    'date': row['date_gmt8'],
                    'yesterday_active': row['yesterday_active'],
                    'retained_users': row['retained_users'],
                    'retention_rate': float(row['retention_rate']) if row['retention_rate'] is not None else None
                }
                for row in retention_data
            ]
        }

        # Window control parameters
        window_params = {
            'days': window_days,
            'offset': window_offset,
            'start_date': start_date_gmt8.strftime('%Y-%m-%d'),
            'end_date': end_date_gmt8.strftime('%Y-%m-%d')
        }

        return render_template('dashboard_daily_data.html',
                             daily_data=daily_data,
                             window=window_params)

    except Exception as e:
        logger.error(f"Error loading daily data dashboard: {str(e)}", exc_info=True)
        return f"Error loading dashboard: {str(e)}", 500


@app.route('/vip-management')
def vip_management():
    """
    VIP management interface.

    Allows admin to search for users by ID and modify their VIP status.
    """
    return render_template('vip_management.html')


@app.route('/api/user/<int:user_id>/info')
def api_user_info(user_id):
    """
    Get user information including VIP status.

    Args:
        user_id: Telegram user ID

    Returns:
        JSON object with user details
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT user_id, telegram_username, vip_tier, credit_balance, created_at
            FROM users
            WHERE user_id = ?
        """, (user_id,))

        user = cursor.fetchone()
        conn.close()

        if not user:
            return jsonify({'error': 'User not found'}), 404

        return jsonify({
            'user_id': user['user_id'],
            'username': user['telegram_username'] or 'N/A',
            'vip_tier': user['vip_tier'],
            'vip_display': get_vip_display_name(user['vip_tier']),
            'credit_balance': int(user['credit_balance']),
            'created_at': format_timestamp_gmt8(user['created_at'])
        })

    except Exception as e:
        logger.error(f"Error getting user info: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/user/<int:user_id>/vip', methods=['POST'])
def api_update_vip(user_id):
    """
    Update user's VIP status.

    Args:
        user_id: Telegram user ID

    Request body:
        {
            "vip_tier": "none" | "vip" | "black_gold"
        }

    Returns:
        JSON response with success status
    """
    try:
        data = request.get_json()
        new_vip_tier = data.get('vip_tier')

        # Validate VIP tier
        valid_tiers = ['none', 'vip', 'black_gold']
        if new_vip_tier not in valid_tiers:
            return jsonify({'error': f'Invalid VIP tier. Must be one of: {", ".join(valid_tiers)}'}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if user exists
        cursor.execute("SELECT user_id, vip_tier FROM users WHERE user_id = ?", (user_id,))
        user = cursor.fetchone()

        if not user:
            conn.close()
            return jsonify({'error': 'User not found'}), 404

        old_vip_tier = user['vip_tier']

        # Update VIP tier
        cursor.execute("""
            UPDATE users
            SET vip_tier = ?
            WHERE user_id = ?
        """, (new_vip_tier, user_id))

        conn.commit()
        conn.close()

        logger.info(f"Admin updated VIP status for user {user_id}: {old_vip_tier} -> {new_vip_tier}")

        return jsonify({
            'success': True,
            'message': f'VIP status updated successfully',
            'old_tier': old_vip_tier,
            'new_tier': new_vip_tier,
            'new_tier_display': get_vip_display_name(new_vip_tier)
        })

    except Exception as e:
        logger.error(f"Error updating VIP status: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/user/<int:user_id>/credits', methods=['POST'])
def api_update_credits(user_id):
    """
    Update user's credit balance.

    Args:
        user_id: Telegram user ID

    Request body:
        {
            "credits": <number> (can be negative)
        }

    Returns:
        JSON response with success status
    """
    try:
        data = request.get_json()
        new_credits = data.get('credits')

        # Validate credits is a number
        try:
            new_credits = float(new_credits)
        except (TypeError, ValueError):
            return jsonify({'error': 'Credits must be a valid number'}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if user exists and get old balance
        cursor.execute("SELECT user_id, credit_balance FROM users WHERE user_id = ?", (user_id,))
        user = cursor.fetchone()

        if not user:
            conn.close()
            return jsonify({'error': 'User not found'}), 404

        old_balance = user['credit_balance']

        # Update credit balance (allows negative values)
        cursor.execute("""
            UPDATE users
            SET credit_balance = ?
            WHERE user_id = ?
        """, (new_credits, user_id))

        conn.commit()
        conn.close()

        logger.info(f"Admin updated credits for user {user_id}: {old_balance} -> {new_credits}")

        return jsonify({
            'success': True,
            'message': f'Credit balance updated successfully',
            'old_balance': float(old_balance),
            'new_balance': float(new_credits)
        })

    except Exception as e:
        logger.error(f"Error updating credits: {str(e)}", exc_info=True)
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
    logger.info(f"Daily Data: http://localhost:{port}/daily-data")
    logger.info(f"VIP Management: http://localhost:{port}/vip-management")

    # Use simple Flask development server
    app.run(host='0.0.0.0', port=port, debug=False)
