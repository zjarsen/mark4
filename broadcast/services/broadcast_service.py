"""Core broadcast service for sending messages to Telegram users."""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

logger = logging.getLogger('broadcast_service')


class BroadcastService:
    """Service for broadcasting messages to Telegram users."""

    def __init__(self, database_path: str):
        """
        Initialize broadcast service.

        Args:
            database_path: Path to SQLite database
        """
        self.database_path = database_path
        self.history_file = Path('broadcast/data/history.json')
        self.drafts_file = Path('broadcast/data/drafts.json')

        # Ensure data directory exists
        self.history_file.parent.mkdir(parents=True, exist_ok=True)

        # Initialize JSON files if they don't exist
        if not self.history_file.exists():
            self.history_file.write_text('[]')
        if not self.drafts_file.exists():
            self.drafts_file.write_text('[]')

    async def get_target_users(self, filters: Optional[Dict] = None) -> List[int]:
        """
        Query database for user IDs based on filters.

        Args:
            filters: Dictionary with filter criteria:
                - vip_tiers: List of VIP tiers ['none', 'vip', 'black_gold']
                - min_balance: Minimum credit balance
                - max_balance: Maximum credit balance
                - last_active_after: Date string (YYYY-MM-DD)
                - last_active_before: Date string (YYYY-MM-DD)
                - has_purchased: Boolean (True for paid users, False for free, None for all)

        Returns:
            List of user_ids matching criteria
        """
        import sqlite3

        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()

        query = "SELECT user_id FROM users WHERE 1=1"
        params = []

        if filters:
            # VIP tier filter
            if filters.get('vip_tiers'):
                placeholders = ','.join('?' * len(filters['vip_tiers']))
                query += f" AND vip_tier IN ({placeholders})"
                params.extend(filters['vip_tiers'])

            # Credit balance filters
            if filters.get('min_balance') is not None:
                query += " AND credit_balance >= ?"
                params.append(filters['min_balance'])

            if filters.get('max_balance') is not None:
                query += " AND credit_balance <= ?"
                params.append(filters['max_balance'])

            # Last activity date filters
            if filters.get('last_active_after'):
                query += " AND last_interaction_date >= ?"
                params.append(filters['last_active_after'])

            if filters.get('last_active_before'):
                query += " AND last_interaction_date <= ?"
                params.append(filters['last_active_before'])

            # Purchase history filter
            if filters.get('has_purchased') is not None:
                if filters['has_purchased']:
                    query += " AND total_spent > 0"
                else:
                    query += " AND (total_spent = 0 OR total_spent IS NULL)"

        cursor.execute(query, params)
        user_ids = [row[0] for row in cursor.fetchall()]

        conn.close()
        return user_ids

    async def send_broadcast(
        self,
        bot,
        user_ids: List[int],
        message: str,
        parse_mode: str = 'Markdown',
        buttons: Optional[List[List[Dict]]] = None
    ) -> Dict:
        """
        Send broadcast message to list of users with rate limiting.

        Args:
            bot: Telegram Bot instance
            user_ids: List of user IDs to send to
            message: Message text
            parse_mode: 'Markdown' or 'HTML'
            buttons: Optional inline keyboard buttons

        Returns:
            Dictionary with success/failure counts and failed user IDs
        """
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup

        successful = 0
        failed = 0
        failed_users = []

        # Create inline keyboard if buttons provided
        reply_markup = None
        if buttons:
            keyboard = [[InlineKeyboardButton(btn['text'], url=btn['url']) for btn in row] for row in buttons]
            reply_markup = InlineKeyboardMarkup(keyboard)

        for user_id in user_ids:
            try:
                await bot.send_message(
                    chat_id=user_id,
                    text=message,
                    parse_mode=parse_mode,
                    reply_markup=reply_markup
                )
                successful += 1

                # Rate limiting: 30 messages/second = 33ms delay
                await asyncio.sleep(0.035)

            except Exception as e:
                logger.error(f"Failed to send to {user_id}: {str(e)}")
                failed += 1
                failed_users.append(user_id)

        return {
            'successful': successful,
            'failed': failed,
            'failed_users': failed_users
        }

    def save_to_history(self, broadcast_data: Dict):
        """Save broadcast to history JSON file."""
        history = json.loads(self.history_file.read_text())
        broadcast_data['sent_at'] = datetime.now().isoformat()
        history.insert(0, broadcast_data)  # Add to beginning

        # Keep only last 100 broadcasts
        history = history[:100]

        self.history_file.write_text(json.dumps(history, ensure_ascii=False, indent=2))

    def get_history(self) -> List[Dict]:
        """Get broadcast history."""
        return json.loads(self.history_file.read_text())

    def save_draft(self, draft_data: Dict):
        """Save message draft."""
        drafts = json.loads(self.drafts_file.read_text())
        draft_data['id'] = datetime.now().timestamp()
        draft_data['saved_at'] = datetime.now().isoformat()
        drafts.append(draft_data)

        self.drafts_file.write_text(json.dumps(drafts, ensure_ascii=False, indent=2))

    def get_drafts(self) -> List[Dict]:
        """Get all drafts."""
        return json.loads(self.drafts_file.read_text())

    def delete_draft(self, draft_id: float):
        """Delete a draft by ID."""
        drafts = json.loads(self.drafts_file.read_text())
        drafts = [d for d in drafts if d.get('id') != draft_id]
        self.drafts_file.write_text(json.dumps(drafts, ensure_ascii=False, indent=2))
