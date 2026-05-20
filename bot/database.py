import aiosqlite
import hashlib
from datetime import datetime
from config import DB_PATH, WELCOME_CREDITS


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                telegram_id INTEGER UNIQUE NOT NULL,
                username TEXT,
                first_name TEXT,
                credits INTEGER DEFAULT 0,
                referrer_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS bots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                bot_type TEXT DEFAULT 'simple',
                status TEXT DEFAULT 'created',
                dialogue_summary TEXT,
                bot_token TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS dialogues (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                bot_id INTEGER,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS hosting (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                bot_id INTEGER NOT NULL,
                plan TEXT NOT NULL,
                status TEXT DEFAULT 'active',
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (bot_id) REFERENCES bots(id)
            );

            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                amount INTEGER NOT NULL,
                type TEXT NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        await db.commit()


async def get_or_create_user(telegram_id: int, username: str = None, first_name: str = None, referrer_id: int = None):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)
        ) as cursor:
            user = await cursor.fetchone()

        if user:
            return dict(user), False

        ref_id = None
        if referrer_id:
            async with db.execute(
                "SELECT id FROM users WHERE telegram_id = ?", (referrer_id,)
            ) as cursor:
                ref = await cursor.fetchone()
                if ref:
                    ref_id = ref["id"]

        await db.execute(
            "INSERT INTO users (telegram_id, username, first_name, credits, referrer_id) VALUES (?, ?, ?, ?, ?)",
            (telegram_id, username, first_name, WELCOME_CREDITS, ref_id),
        )
        await db.execute(
            "INSERT INTO transactions (user_id, amount, type, description) VALUES "
            "((SELECT id FROM users WHERE telegram_id = ?), ?, 'bonus', 'Приветственные кредиты')",
            (telegram_id, WELCOME_CREDITS),
        )

        if ref_id:
            from config import REFERRAL_BONUS
            await db.execute(
                "UPDATE users SET credits = credits + ? WHERE id = ?",
                (REFERRAL_BONUS, ref_id),
            )
            await db.execute(
                "INSERT INTO transactions (user_id, amount, type, description) VALUES (?, ?, 'referral', 'Реферальный бонус')",
                (ref_id, REFERRAL_BONUS),
            )

        await db.commit()

        async with db.execute(
            "SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)
        ) as cursor:
            user = await cursor.fetchone()
        return dict(user), True


async def get_user(telegram_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)
        ) as cursor:
            user = await cursor.fetchone()
        return dict(user) if user else None


async def get_user_credits(telegram_id: int) -> int:
    user = await get_user(telegram_id)
    return user["credits"] if user else 0


async def deduct_credits(telegram_id: int, amount: int, description: str) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT id, credits FROM users WHERE telegram_id = ?", (telegram_id,)
        ) as cursor:
            user = await cursor.fetchone()
        if not user or user["credits"] < amount:
            return False
        await db.execute(
            "UPDATE users SET credits = credits - ? WHERE telegram_id = ?",
            (amount, telegram_id),
        )
        await db.execute(
            "INSERT INTO transactions (user_id, amount, type, description) VALUES (?, ?, 'spend', ?)",
            (user["id"], -amount, description),
        )
        await db.commit()
        return True


async def add_credits(telegram_id: int, amount: int, description: str):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT id FROM users WHERE telegram_id = ?", (telegram_id,)
        ) as cursor:
            user = await cursor.fetchone()
        if not user:
            return
        await db.execute(
            "UPDATE users SET credits = credits + ? WHERE telegram_id = ?",
            (amount, telegram_id),
        )
        await db.execute(
            "INSERT INTO transactions (user_id, amount, type, description) VALUES (?, ?, 'top_up', ?)",
            (user["id"], amount, description),
        )
        await db.commit()


async def save_dialogue_message(user_id: int, role: str, content: str, bot_id: int = None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO dialogues (user_id, bot_id, role, content) VALUES (?, ?, ?, ?)",
            (user_id, bot_id, role, content),
        )
        await db.commit()


async def get_dialogue_history(user_id: int, bot_id: int = None, limit: int = 20):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if bot_id:
            query = "SELECT role, content FROM dialogues WHERE user_id = ? AND bot_id = ? ORDER BY created_at DESC LIMIT ?"
            params = (user_id, bot_id, limit)
        else:
            query = "SELECT role, content FROM dialogues WHERE user_id = ? AND bot_id IS NULL ORDER BY created_at DESC LIMIT ?"
            params = (user_id, limit)
        async with db.execute(query, params) as cursor:
            rows = await cursor.fetchall()
        return list(reversed([dict(r) for r in rows]))


async def clear_dialogue(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM dialogues WHERE user_id = ? AND bot_id IS NULL", (user_id,)
        )
        await db.commit()


async def create_bot_record(user_id: int, name: str, bot_type: str, summary: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO bots (user_id, name, bot_type, dialogue_summary, status) VALUES (?, ?, ?, ?, 'created')",
            (user_id, name, bot_type, summary),
        )
        await db.commit()
        return cursor.lastrowid


async def get_user_bots(telegram_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT b.* FROM bots b JOIN users u ON b.user_id = u.id WHERE u.telegram_id = ? ORDER BY b.created_at DESC",
            (telegram_id,),
        ) as cursor:
            rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def get_bot(bot_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM bots WHERE id = ?", (bot_id,)) as cursor:
            row = await cursor.fetchone()
        return dict(row) if row else None


async def get_transaction_history(telegram_id: int, limit: int = 10):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT t.* FROM transactions t JOIN users u ON t.user_id = u.id "
            "WHERE u.telegram_id = ? ORDER BY t.created_at DESC LIMIT ?",
            (telegram_id, limit),
        ) as cursor:
            rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def get_referral_count(telegram_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT COUNT(*) as cnt FROM users WHERE referrer_id = (SELECT id FROM users WHERE telegram_id = ?)",
            (telegram_id,),
        ) as cursor:
            row = await cursor.fetchone()
        return row["cnt"] if row else 0


async def get_referral_earnings(telegram_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT COALESCE(SUM(amount), 0) as total FROM transactions t "
            "JOIN users u ON t.user_id = u.id "
            "WHERE u.telegram_id = ? AND t.type = 'referral'",
            (telegram_id,),
        ) as cursor:
            row = await cursor.fetchone()
        return row["total"] if row else 0


async def update_bot_status(bot_id: int, status: str, generated_code: str = None):
    async with aiosqlite.connect(DB_PATH) as db:
        if generated_code is not None:
            await db.execute(
                "UPDATE bots SET status = ?, description = ? WHERE id = ?",
                (status, generated_code, bot_id),
            )
        else:
            await db.execute(
                "UPDATE bots SET status = ? WHERE id = ?", (status, bot_id)
            )
        await db.commit()


async def save_bot_token(bot_id: int, token: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE bots SET bot_token = ? WHERE id = ?", (token, bot_id)
        )
        await db.commit()


async def activate_hosting(user_id: int, bot_id: int, plan: str, days: int = 30):
    from datetime import datetime, timedelta
    expires_at = (datetime.utcnow() + timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO hosting (user_id, bot_id, plan, status, expires_at) VALUES (?, ?, ?, 'active', ?)",
            (user_id, bot_id, plan, expires_at),
        )
        await db.execute("UPDATE bots SET status = 'hosted' WHERE id = ?", (bot_id,))
        await db.commit()


async def get_hosting_record(bot_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT h.*, u.telegram_id FROM hosting h JOIN users u ON h.user_id = u.id WHERE h.bot_id = ? AND h.status = 'active'",
            (bot_id,),
        ) as cursor:
            row = await cursor.fetchone()
        return dict(row) if row else None


async def get_all_hosted_bots():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT b.id as bot_id, b.name, b.status, b.bot_token, u.telegram_id "
            "FROM bots b JOIN users u ON b.user_id = u.id "
            "WHERE b.status IN ('hosted', 'error')"
        ) as cursor:
            rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def get_expiring_hosting(days: int):
    from datetime import datetime, timedelta
    threshold = (datetime.utcnow() + timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
    lower = (datetime.utcnow() + timedelta(days=days - 1)).strftime("%Y-%m-%d %H:%M:%S")
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT h.*, b.name, u.telegram_id FROM hosting h "
            "JOIN bots b ON h.bot_id = b.id "
            "JOIN users u ON h.user_id = u.id "
            "WHERE h.status = 'active' AND h.expires_at BETWEEN ? AND ?",
            (lower, threshold),
        ) as cursor:
            rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def get_user_telegram_id(user_id: int) -> int | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT telegram_id FROM users WHERE id = ?", (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
        return row["telegram_id"] if row else None
