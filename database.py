"""
============================================================
  JECRC Foundation - College Helpdesk AI Chatbot
  Database Handler - SQLite
  Stores chat history, analytics, feedback, unresolved queries
============================================================
"""

import sqlite3
import datetime
from contextlib import contextmanager


class ChatDatabase:
    """SQLite Database Manager for Chat History & Analytics"""

    def __init__(self, db_path='chat_history.db'):
        self.db_path = db_path
        self._create_tables()
        print(f"✅ Database initialized: {db_path}")

    @contextmanager
    def _get_connection(self):
        """Context manager for safe database connections"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            print(f"❌ Database error: {e}")
            raise e
        finally:
            conn.close()

    def _create_tables(self):
        """Create all necessary database tables"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Chat History Table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS chat_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    user_message TEXT NOT NULL,
                    bot_response TEXT NOT NULL,
                    intent TEXT DEFAULT 'unknown',
                    confidence REAL DEFAULT 0.0,
                    method TEXT DEFAULT 'unknown',
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    ip_address TEXT DEFAULT '',
                    user_agent TEXT DEFAULT ''
                )
            ''')

            # Feedback Table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id INTEGER,
                    rating INTEGER CHECK(rating >= 1 AND rating <= 5),
                    comment TEXT DEFAULT '',
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (chat_id) REFERENCES chat_history(id)
                )
            ''')

            # Unresolved Queries
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS unresolved_queries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_message TEXT NOT NULL,
                    session_id TEXT,
                    confidence REAL DEFAULT 0.0,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    resolved BOOLEAN DEFAULT 0,
                    admin_response TEXT DEFAULT ''
                )
            ''')

    # ✅ NEW: Cleanup old chats
    def cleanup_old_chats(self, days=90):
        """Delete chat history older than X days"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                DELETE FROM chat_history 
                WHERE timestamp < datetime('now', ? || ' days')
            ''', (f'-{days}',))
            deleted = cursor.rowcount
            print(f"🗑️ Cleaned up {deleted} old chat records (>{days} days)")
            return deleted

    def save_chat(self, session_id, user_message, bot_response,
                  intent='unknown', confidence=0.0, method='unknown',
                  ip_address='', user_agent=''):
        """Save a chat interaction to database"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO chat_history
                (session_id, user_message, bot_response, intent, confidence, method, ip_address, user_agent)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (session_id, user_message, bot_response, intent,
                  confidence, method, ip_address, user_agent))

            chat_id = cursor.lastrowid

            # Save as unresolved if low confidence
            if confidence < 0.35 and intent == 'default':
                cursor.execute('''
                    INSERT INTO unresolved_queries (user_message, session_id, confidence)
                    VALUES (?, ?, ?)
                ''', (user_message, session_id, confidence))

            return chat_id

    def save_feedback(self, chat_id, rating, comment=''):
        """Save user feedback"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO feedback (chat_id, rating, comment)
                VALUES (?, ?, ?)
            ''', (chat_id, rating, comment))

    def get_chat_history(self, session_id=None, limit=50):
        """Get chat history"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if session_id:
                cursor.execute('''
                    SELECT * FROM chat_history
                    WHERE session_id = ?
                    ORDER BY timestamp DESC LIMIT ?
                ''', (session_id, limit))
            else:
                cursor.execute('''
                    SELECT * FROM chat_history
                    ORDER BY timestamp DESC LIMIT ?
                ''', (limit,))
            return [dict(row) for row in cursor.fetchall()]

    def get_analytics(self):
        """Get dashboard analytics data"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute('SELECT COUNT(*) as total FROM chat_history')
            total_chats = cursor.fetchone()['total']

            today = datetime.date.today().isoformat()
            cursor.execute(
                'SELECT COUNT(*) as count FROM chat_history WHERE DATE(timestamp) = ?',
                (today,)
            )
            today_chats = cursor.fetchone()['count']

            cursor.execute('SELECT COUNT(DISTINCT session_id) as count FROM chat_history')
            unique_sessions = cursor.fetchone()['count']

            cursor.execute('SELECT AVG(confidence) as avg FROM chat_history WHERE confidence > 0')
            avg_confidence = cursor.fetchone()['avg'] or 0

            cursor.execute('''
                SELECT intent, COUNT(*) as count
                FROM chat_history
                WHERE intent NOT IN ('default', 'greeting', 'goodbye', 'thanks', 'empty')
                GROUP BY intent
                ORDER BY count DESC
                LIMIT 10
            ''')
            top_intents = [dict(row) for row in cursor.fetchall()]

            cursor.execute('SELECT COUNT(*) as count FROM unresolved_queries WHERE resolved = 0')
            unresolved = cursor.fetchone()['count']

            cursor.execute('''
                SELECT * FROM unresolved_queries
                WHERE resolved = 0
                ORDER BY timestamp DESC LIMIT 20
            ''')
            unresolved_queries = [dict(row) for row in cursor.fetchall()]

            cursor.execute('''
                SELECT strftime('%H', timestamp) as hour, COUNT(*) as count
                FROM chat_history
                GROUP BY hour
                ORDER BY hour
            ''')
            hourly_dist = [dict(row) for row in cursor.fetchall()]

            cursor.execute('''
                SELECT method, COUNT(*) as count
                FROM chat_history
                GROUP BY method
            ''')
            method_dist = [dict(row) for row in cursor.fetchall()]

            return {
                'total_chats': total_chats,
                'today_chats': today_chats,
                'unique_sessions': unique_sessions,
                'avg_confidence': round(avg_confidence, 4),
                'top_intents': top_intents,
                'unresolved_count': unresolved,
                'unresolved_queries': unresolved_queries,
                'hourly_distribution': hourly_dist,
                'method_distribution': method_dist
            }

    def resolve_query(self, query_id, admin_response=''):
        """Mark an unresolved query as resolved"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE unresolved_queries
                SET resolved = 1, admin_response = ?
                WHERE id = ?
            ''', (admin_response, query_id))

    def clear_history(self):
        """Clear all chat history (admin function)"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM chat_history')
            cursor.execute('DELETE FROM feedback')
            cursor.execute('DELETE FROM unresolved_queries')
            print("✅ All chat history cleared!")
