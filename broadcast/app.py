"""Flask application for broadcast portal."""

from flask import Flask, render_template, request, jsonify
from telegram import Bot
import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import from broadcast.services since we're in the broadcast folder
from broadcast.services.broadcast_service import BroadcastService
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
bot_token = os.getenv('BOT_TOKEN')

# Get database path and make it absolute relative to project root
database_path = os.getenv('DATABASE_PATH', 'data/mark4_bot.db')
if not os.path.isabs(database_path):
    # Make path relative to parent directory (project root)
    project_root = Path(__file__).parent.parent
    database_path = str(project_root / database_path)

broadcast_service = BroadcastService(database_path)
bot = Bot(token=bot_token)


@app.route('/')
def index():
    """Main broadcast dashboard."""
    return render_template('dashboard.html')


@app.route('/history')
def history():
    """View broadcast history."""
    history_data = broadcast_service.get_history()
    return render_template('history.html', history=history_data)


@app.route('/api/users/count', methods=['POST'])
def get_user_count():
    """Get count of users matching filters."""
    filters = request.json.get('filters') if request.json else None

    async def count_users():
        user_ids = await broadcast_service.get_target_users(filters)
        return len(user_ids)

    count = asyncio.run(count_users())
    return jsonify({'count': count})


@app.route('/api/broadcast/test', methods=['POST'])
def test_broadcast():
    """Send test message to admin."""
    data = request.json
    message = data.get('message')
    parse_mode = data.get('parse_mode', 'Markdown')
    buttons = data.get('buttons')
    admin_id = data.get('admin_id')  # Pass from frontend

    async def send_test():
        return await broadcast_service.send_broadcast(
            bot,
            [admin_id],
            message,
            parse_mode,
            buttons
        )

    result = asyncio.run(send_test())
    return jsonify(result)


@app.route('/api/broadcast/send', methods=['POST'])
def send_broadcast():
    """Send broadcast to filtered users."""
    data = request.json
    message = data.get('message')
    parse_mode = data.get('parse_mode', 'Markdown')
    filters = data.get('filters')
    buttons = data.get('buttons')

    async def do_broadcast():
        # Get target users
        user_ids = await broadcast_service.get_target_users(filters)

        # Send broadcast
        result = await broadcast_service.send_broadcast(
            bot,
            user_ids,
            message,
            parse_mode,
            buttons
        )

        # Save to history
        broadcast_service.save_to_history({
            'message': message,
            'parse_mode': parse_mode,
            'filters': filters,
            'buttons': buttons,
            'total_users': len(user_ids),
            'successful': result['successful'],
            'failed': result['failed']
        })

        return result

    result = asyncio.run(do_broadcast())
    return jsonify(result)


@app.route('/api/drafts', methods=['GET'])
def get_drafts():
    """Get all drafts."""
    drafts = broadcast_service.get_drafts()
    return jsonify(drafts)


@app.route('/api/drafts', methods=['POST'])
def save_draft():
    """Save a draft."""
    draft_data = request.json
    broadcast_service.save_draft(draft_data)
    return jsonify({'status': 'success'})


@app.route('/api/drafts/<float:draft_id>', methods=['DELETE'])
def delete_draft(draft_id):
    """Delete a draft."""
    broadcast_service.delete_draft(draft_id)
    return jsonify({'status': 'success'})


if __name__ == '__main__':
    port = int(os.getenv('BROADCAST_PORT', 5002))
    app.run(host='0.0.0.0', port=port, debug=True)
