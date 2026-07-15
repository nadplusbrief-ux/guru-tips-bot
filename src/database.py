import sqlite3
import datetime
import asyncio
from contextlib import contextmanager
from src.config import DATABASE_PATH, DAILY_LIMIT

@contextmanager
def get_db_connection():
    conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    """Initializes the SQLite database schema."""
    with get_db_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                daily_count INTEGER DEFAULT 0,
                last_reset TEXT
            )
        """)
        conn.commit()

def check_and_increment_usage(user_id: int, username: str) -> bool:
    """
    Checks if a user is within their daily usage limit.
    If the date has changed, resets the usage count.
    If within limit, increments usage count and returns True.
    If limit reached, returns False.
    """
    # Use UTC or local date. Since we're targeting Brazil, local machine date works.
    today = datetime.date.today().isoformat()  # YYYY-MM-DD
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Check if user exists
        cursor.execute("SELECT daily_count, last_reset FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        
        if row is None:
            # User doesn't exist, create user with initial usage = 1
            cursor.execute(
                "INSERT INTO users (user_id, username, daily_count, last_reset) VALUES (?, ?, 1, ?)",
                (user_id, username or "unknown", today)
            )
            conn.commit()
            return True
        
        daily_count = row['daily_count']
        last_reset = row['last_reset']
        
        if last_reset != today:
            # It's a new day, reset usage to 1
            cursor.execute(
                "UPDATE users SET daily_count = 1, last_reset = ?, username = ? WHERE user_id = ?",
                (today, username or "unknown", user_id)
            )
            conn.commit()
            return True
        else:
            if daily_count >= DAILY_LIMIT:
                # Limit exceeded, but let's update username in case it changed
                cursor.execute("UPDATE users SET username = ? WHERE user_id = ?", (username or "unknown", user_id))
                conn.commit()
                return False
            else:
                # Increment usage
                cursor.execute(
                    "UPDATE users SET daily_count = daily_count + 1, username = ? WHERE user_id = ?",
                    (username or "unknown", user_id)
                )
                conn.commit()
                return True

# Async wrappers to run database operations without blocking the event loop
async def async_init_db():
    await asyncio.to_thread(init_db)

async def async_check_and_increment_usage(user_id: int, username: str) -> bool:
    return await asyncio.to_thread(check_and_increment_usage, user_id, username)
