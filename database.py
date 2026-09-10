import os

import aiosqlite


def get_db_path() -> str:
    """Use the persistent Railway volume when present, otherwise the local database."""
    return "/app/data/levels.db" if os.path.isdir("/app/data") else "levels.db"


DB_NAME = get_db_path()

def get_economy_db_path() -> str:
    """Use the persistent Railway volume for the Station economy database."""
    return "/app/data/economy.db" if os.path.isdir("/app/data") else "economy.db"


ECONOMY_DB_NAME = get_economy_db_path()


async def init_economy_db():
    """Initialize the separate Station economy database."""
    async with aiosqlite.connect(ECONOMY_DB_NAME) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                stardust INTEGER DEFAULT 0,
                hp INTEGER DEFAULT 100,
                max_hp INTEGER DEFAULT 100,
                mining_charges INTEGER DEFAULT 5,
                scavenge_charges INTEGER DEFAULT 5,
                last_mined REAL DEFAULT 0,
                last_scavenged REAL DEFAULT 0,
                knocked_out_until TEXT DEFAULT '',
                active_effects TEXT DEFAULT '{}',
                legacy_payout INTEGER DEFAULT 0,
                time_crystals INTEGER DEFAULT 0,
                tc_uses_this_month INTEGER DEFAULT 0,
                tc_last_used_month TEXT DEFAULT '',
                nanite_patchs INTEGER DEFAULT 0,
                medkits INTEGER DEFAULT 0,
                bio TEXT DEFAULT 'Exploring the outer rims of Enceladus Station. 🚀',
                profile_card TEXT DEFAULT 'default_nebula',
                equipped_title TEXT DEFAULT ''
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS inventory (
                user_id INTEGER,
                item_id TEXT,
                item_type TEXT,
                quantity INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, item_id)
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS pets (
                pet_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                pet_stage TEXT DEFAULT 'egg',
                nickname TEXT,
                level INTEGER DEFAULT 1,
                xp INTEGER DEFAULT 0
            )
        """)

        await db.commit()

async def init_db(db_path: str = DB_NAME):
    """Initializes tables and performs schema migrations asynchronously."""
    async with aiosqlite.connect(db_path) as db:
        # 1. USERS TABLE - Consolidated duplicate stats, retained item columns for current compatibility
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                stardust INTEGER DEFAULT 0,
                xp INTEGER DEFAULT 0,
                level INTEGER DEFAULT 1,
                hp INTEGER DEFAULT 100,
                max_hp INTEGER DEFAULT 100,
                mining_charges INTEGER DEFAULT 5,
                scavenge_charges INTEGER DEFAULT 5,
                last_mined REAL DEFAULT 0,
                last_scavenged REAL DEFAULT 0,
                knocked_out_until TEXT DEFAULT '',
                active_effects TEXT DEFAULT '{}',
                legacy_payout INTEGER DEFAULT 0,
                time_crystals INTEGER DEFAULT 0,
                tc_uses_this_month INTEGER DEFAULT 0,
                tc_last_used_month TEXT DEFAULT '',
                nanite_patchs INTEGER DEFAULT 0,
                medkits INTEGER DEFAULT 0,
                bio TEXT DEFAULT 'Exploring the outer rims of Enceladus Station. 🚀',
                profile_card TEXT DEFAULT 'default_nebula'
            )
        """)

        # 4. DYNAMIC MIGRATIONS
        async with db.execute("PRAGMA table_info(users)") as cursor:
            columns = [row[1] async for row in cursor]

        columns_to_add = {
            "stardust": "INTEGER DEFAULT 0",
            "hp": "INTEGER DEFAULT 100",
            "max_hp": "INTEGER DEFAULT 100",
            "mining_charges": "INTEGER DEFAULT 5",
            "scavenge_charges": "INTEGER DEFAULT 5",
            "last_mined": "REAL DEFAULT 0",
            "last_scavenged": "REAL DEFAULT 0",
            "knocked_out_until": "TEXT DEFAULT ''",
            "active_effects": "TEXT DEFAULT '{}'",
            "legacy_payout": "INTEGER DEFAULT 0",
            "time_crystals": "INTEGER DEFAULT 0",
            "tc_uses_this_month": "INTEGER DEFAULT 0",
            "tc_last_used_month": "TEXT DEFAULT ''",
            "nanite_patchs": "INTEGER DEFAULT 0",
            "medkits": "INTEGER DEFAULT 0",
            "bio": "TEXT DEFAULT 'Exploring the outer rims of Enceladus Station. 🚀'",
            "profile_card": "TEXT DEFAULT 'default_nebula'"
        }

        for col, col_def in columns_to_add.items():
            if col not in columns:
                await db.execute(f"ALTER TABLE users ADD COLUMN {col} {col_def}")

        await db.commit()

    await init_economy_db()
