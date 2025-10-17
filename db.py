import aiosqlite
from config import DB_PATH

CREATE_USERS = """
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    name TEXT,
    username TEXT,
    shared_count INTEGER DEFAULT 0
);
"""

CREATE_CODES = """
CREATE TABLE IF NOT EXISTS codes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code_text TEXT NOT NULL,
    sharer_id INTEGER,
    sharer_name TEXT,
    sharer_username TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

CREATE_SHARES = """
CREATE TABLE IF NOT EXISTS shares (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code_id INTEGER,
    receiver_id INTEGER,
    receiver_name TEXT,
    receiver_username TEXT,
    given_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(CREATE_USERS)
        await db.execute(CREATE_CODES)
        await db.execute(CREATE_SHARES)
        await db.commit()

async def add_or_update_user(user_id: int, name: str, username: str):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
        row = await cur.fetchone()
        if row:
            await db.execute("UPDATE users SET name = ?, username = ? WHERE user_id = ?",
                             (name, username, user_id))
        else:
            await db.execute("INSERT INTO users (user_id, name, username) VALUES (?, ?, ?)",
                             (user_id, name, username))
        await db.commit()

async def increment_shared_count(user_id: int, delta: int = 1):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO users(user_id, name, username, shared_count) VALUES(?, '', '', 0)", (user_id,))
        await db.execute("UPDATE users SET shared_count = shared_count + ? WHERE user_id = ?", (delta, user_id))
        await db.commit()

async def decrement_shared_count(user_id: int, delta: int = 1):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET shared_count = CASE WHEN shared_count >= ? THEN shared_count - ? ELSE 0 END WHERE user_id = ?", (delta, delta, user_id))
        await db.commit()

async def add_code(code_text: str, sharer_id: int, sharer_name: str, sharer_username: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO codes (code_text, sharer_id, sharer_name, sharer_username) VALUES (?, ?, ?, ?)",
            (code_text.strip(), sharer_id, sharer_name, sharer_username)
        )
        await db.commit()

async def get_random_code():
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT id, code_text, sharer_id, sharer_name, sharer_username FROM codes ORDER BY RANDOM() LIMIT 1")
        row = await cur.fetchone()
        return row  # None or tuple

async def get_sharer_by_code_id(code_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT sharer_id FROM codes WHERE id = ?", (code_id,))
        row = await cur.fetchone()
        return row[0] if row else None

async def delete_code(code_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM codes WHERE id = ?", (code_id,))
        await db.commit()

async def add_share_record(code_id: int, receiver_id: int, receiver_name: str, receiver_username: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO shares (code_id, receiver_id, receiver_name, receiver_username) VALUES (?, ?, ?, ?)",
            (code_id, receiver_id, receiver_name, receiver_username)
        )
        await db.commit()

async def get_leaderboard(limit: int = 20):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT name, username, shared_count FROM users ORDER BY shared_count DESC LIMIT ?", (limit,))
        rows = await cur.fetchall()
        return rows

async def count_codes():
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT COUNT(*) FROM codes")
        row = await cur.fetchone()
        return row[0] if row else 0

async def list_codes(limit: int = 100):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT id, code_text, sharer_name, sharer_username, created_at FROM codes ORDER BY created_at DESC LIMIT ?", (limit,))
        rows = await cur.fetchall()
        return rows