import os

import aiosqlite


def get_db_path() -> str:
    """Use the persistent Railway volume when present, otherwise the local database."""
    return "/app/data/levels.db" if os.path.isdir("/app/data") else "levels.db"


DB_NAME = get_db_path()

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

        # 2. INVENTORY TABLE 
        await db.execute("""
            CREATE TABLE IF NOT EXISTS inventory (
                user_id INTEGER,
                item_id TEXT,
                item_type TEXT,
                quantity INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, item_id)
            )
        """)

        # 3. PETS TABLE - Aligned with profile.py (user_id and pet_stage)
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

        # Ensure inventory table is up to date
        async with db.execute("PRAGMA table_info(inventory)") as cursor:
            inv_columns = [row[1] async for row in cursor]

        if "item_type" not in inv_columns:
            await db.execute("ALTER TABLE inventory ADD COLUMN item_type TEXT")
            
        if "quantity" not in inv_columns:
            await db.execute("ALTER TABLE inventory ADD COLUMN quantity INTEGER DEFAULT 0")

        # Inventory rows created before stacking was introduced represent one item.
        await db.execute("UPDATE inventory SET quantity = 1 WHERE quantity IS NULL OR quantity < 1")

        await db.commit()
