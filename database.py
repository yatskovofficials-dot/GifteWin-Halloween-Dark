import aiosqlite
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
import json
from loguru import logger

from bot.config import settings


class Database:
    def __init__(self, db_path: Path = settings.db_path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    async def connect(self):
        self.conn = await aiosqlite.connect(self.db_path)
        self.conn.row_factory = aiosqlite.Row
        await self.conn.execute("PRAGMA foreign_keys = ON")
        await self._create_tables()
        logger.info(f"Database connected: {self.db_path}")

    async def close(self):
        if hasattr(self, "conn"):
            await self.conn.close()
            logger.info("Database closed")

    async def _create_tables(self):
        await self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                referrer_id INTEGER,
                luck_balls INTEGER DEFAULT 0,
                total_referrals INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                is_blocked INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS giveaways (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                creator_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                prize_type TEXT NOT NULL,          -- gift | stars | nft | other
                prize_info TEXT NOT NULL,           -- description of prize
                winners_count INTEGER DEFAULT 1,
                min_participants INTEGER DEFAULT 2,
                end_at TEXT NOT NULL,               -- ISO datetime when draw happens
                status TEXT DEFAULT 'active',       -- active | finished | cancelled
                winners_json TEXT,                  -- JSON list of winner user_ids
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                finished_at TEXT,
                channel_message_id INTEGER,
                FOREIGN KEY (creator_id) REFERENCES users(user_id)
            );

            CREATE TABLE IF NOT EXISTS participants (
                giveaway_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                joined_at TEXT DEFAULT CURRENT_TIMESTAMP,
                luck_at_join INTEGER DEFAULT 0,
                PRIMARY KEY (giveaway_id, user_id),
                FOREIGN KEY (giveaway_id) REFERENCES giveaways(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            );

            CREATE TABLE IF NOT EXISTS referrals (
                referrer_id INTEGER NOT NULL,
                referred_id INTEGER NOT NULL UNIQUE,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (referrer_id, referred_id),
                FOREIGN KEY (referrer_id) REFERENCES users(user_id),
                FOREIGN KEY (referred_id) REFERENCES users(user_id)
            );

            CREATE INDEX IF NOT EXISTS idx_giveaways_status ON giveaways(status);
            CREATE INDEX IF NOT EXISTS idx_giveaways_end_at ON giveaways(end_at);
            CREATE INDEX IF NOT EXISTS idx_participants_giveaway ON participants(giveaway_id);
            CREATE INDEX IF NOT EXISTS idx_users_referrer ON users(referrer_id);
        """)
        await self.conn.commit()

    # ==================== USERS ====================

    async def get_or_create_user(
        self,
        user_id: int,
        username: Optional[str] = None,
        full_name: Optional[str] = None,
        referrer_id: Optional[int] = None
    ) -> Dict[str, Any]:
        async with self.conn.execute(
            "SELECT * FROM users WHERE user_id = ?", (user_id,)
        ) as cursor:
            row = await cursor.fetchone()

        if row:
            # Update username/full_name if changed
            await self.conn.execute(
                """UPDATE users SET username = ?, full_name = ?, updated_at = CURRENT_TIMESTAMP
                   WHERE user_id = ?""",
                (username, full_name, user_id)
            )
            await self.conn.commit()
            return dict(row)

        # New user
        await self.conn.execute(
            """INSERT INTO users (user_id, username, full_name, referrer_id, luck_balls)
               VALUES (?, ?, ?, ?, 0)""",
            (user_id, username, full_name, referrer_id)
        )
        await self.conn.commit()

        # Process referral bonus
        if referrer_id and referrer_id != user_id:
            await self._process_referral(referrer_id, user_id)

        async with self.conn.execute(
            "SELECT * FROM users WHERE user_id = ?", (user_id,)
        ) as cursor:
            return dict(await cursor.fetchone())

    async def _process_referral(self, referrer_id: int, referred_id: int):
        # Check if already referred
        async with self.conn.execute(
            "SELECT 1 FROM referrals WHERE referred_id = ?", (referred_id,)
        ) as cursor:
            if await cursor.fetchone():
                return

        # Check referrer exists
        async with self.conn.execute(
            "SELECT luck_balls FROM users WHERE user_id = ?", (referrer_id,)
        ) as cursor:
            ref = await cursor.fetchone()
            if not ref:
                return

        # Add referral record
        await self.conn.execute(
            "INSERT OR IGNORE INTO referrals (referrer_id, referred_id) VALUES (?, ?)",
            (referrer_id, referred_id)
        )

        # Give balls (capped)
        new_balls = min(ref["luck_balls"] + settings.REFERRAL_BONUS_BALLS, settings.MAX_BALLS_PER_USER)
        await self.conn.execute(
            """UPDATE users SET luck_balls = ?, total_referrals = total_referrals + 1,
               updated_at = CURRENT_TIMESTAMP WHERE user_id = ?""",
            (new_balls, referrer_id)
        )
        await self.conn.commit()
        logger.info(f"Referral: {referrer_id} got +{settings.REFERRAL_BONUS_BALLS} balls for {referred_id}")

    async def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        async with self.conn.execute(
            "SELECT * FROM users WHERE user_id = ?", (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def add_luck_balls(self, user_id: int, amount: int) -> int:
        user = await self.get_user(user_id)
        if not user:
            return 0
        new_balls = min(user["luck_balls"] + amount, settings.MAX_BALLS_PER_USER)
        await self.conn.execute(
            "UPDATE users SET luck_balls = ?, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?",
            (new_balls, user_id)
        )
        await self.conn.commit()
        return new_balls

    async def get_top_users(self, limit: int = 10) -> List[Dict[str, Any]]:
        async with self.conn.execute(
            """SELECT user_id, username, full_name, luck_balls, total_referrals
               FROM users ORDER BY luck_balls DESC, total_referrals DESC LIMIT ?""",
            (limit,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    # ==================== GIVEAWAYS ====================

    async def create_giveaway(
        self,
        creator_id: int,
        title: str,
        description: str,
        prize_type: str,
        prize_info: str,
        winners_count: int,
        min_participants: int,
        end_at: str
    ) -> int:
        cursor = await self.conn.execute(
            """INSERT INTO giveaways
               (creator_id, title, description, prize_type, prize_info,
                winners_count, min_participants, end_at, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'active')""",
            (creator_id, title, description, prize_type, prize_info,
             winners_count, min_participants, end_at)
        )
        await self.conn.commit()
        return cursor.lastrowid

    async def get_giveaway(self, giveaway_id: int) -> Optional[Dict[str, Any]]:
        async with self.conn.execute(
            "SELECT * FROM giveaways WHERE id = ?", (giveaway_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def get_active_giveaways(self, limit: int = 20) -> List[Dict[str, Any]]:
        async with self.conn.execute(
            """SELECT g.*, u.username as creator_username, u.full_name as creator_name,
                      (SELECT COUNT(*) FROM participants p WHERE p.giveaway_id = g.id) as participants_count
               FROM giveaways g
               JOIN users u ON u.user_id = g.creator_id
               WHERE g.status = 'active'
               ORDER BY g.end_at ASC
               LIMIT ?""",
            (limit,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def get_user_giveaways(self, user_id: int, status: str = None) -> List[Dict[str, Any]]:
        query = """SELECT g.*,
                          (SELECT COUNT(*) FROM participants p WHERE p.giveaway_id = g.id) as participants_count
                   FROM giveaways g WHERE g.creator_id = ?"""
        params = [user_id]
        if status:
            query += " AND g.status = ?"
            params.append(status)
        query += " ORDER BY g.created_at DESC LIMIT 30"

        async with self.conn.execute(query, params) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def join_giveaway(self, giveaway_id: int, user_id: int) -> bool:
        user = await self.get_user(user_id)
        if not user:
            return False

        try:
            await self.conn.execute(
                """INSERT INTO participants (giveaway_id, user_id, luck_at_join)
                   VALUES (?, ?, ?)""",
                (giveaway_id, user_id, user["luck_balls"])
            )
            await self.conn.commit()
            return True
        except aiosqlite.IntegrityError:
            return False  # already joined

    async def is_participant(self, giveaway_id: int, user_id: int) -> bool:
        async with self.conn.execute(
            "SELECT 1 FROM participants WHERE giveaway_id = ? AND user_id = ?",
            (giveaway_id, user_id)
        ) as cursor:
            return await cursor.fetchone() is not None

    async def get_participants(self, giveaway_id: int) -> List[Dict[str, Any]]:
        async with self.conn.execute(
            """SELECT p.*, u.username, u.full_name, u.luck_balls
               FROM participants p
               JOIN users u ON u.user_id = p.user_id
               WHERE p.giveaway_id = ?
               ORDER BY p.joined_at""",
            (giveaway_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def get_participants_count(self, giveaway_id: int) -> int:
        async with self.conn.execute(
            "SELECT COUNT(*) as cnt FROM participants WHERE giveaway_id = ?",
            (giveaway_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return row["cnt"] if row else 0

    async def finish_giveaway(self, giveaway_id: int, winners: List[int]) -> bool:
        winners_json = json.dumps(winners)
        await self.conn.execute(
            """UPDATE giveaways SET status = 'finished', winners_json = ?,
               finished_at = CURRENT_TIMESTAMP WHERE id = ? AND status = 'active'""",
            (winners_json, giveaway_id)
        )
        await self.conn.commit()
        return True

    async def cancel_giveaway(self, giveaway_id: int, creator_id: int) -> bool:
        await self.conn.execute(
            """UPDATE giveaways SET status = 'cancelled', finished_at = CURRENT_TIMESTAMP
               WHERE id = ? AND creator_id = ? AND status = 'active'""",
            (giveaway_id, creator_id)
        )
        await self.conn.commit()
        return True

    async def get_expired_giveaways(self) -> List[Dict[str, Any]]:
        now = datetime.utcnow().isoformat()
        async with self.conn.execute(
            """SELECT * FROM giveaways
               WHERE status = 'active' AND end_at <= ?""",
            (now,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def set_channel_message_id(self, giveaway_id: int, message_id: int):
        await self.conn.execute(
            "UPDATE giveaways SET channel_message_id = ? WHERE id = ?",
            (message_id, giveaway_id)
        )
        await self.conn.commit()


db = Database()
