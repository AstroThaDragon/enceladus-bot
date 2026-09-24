import json
import math
import aiosqlite
import discord
from discord.ext import commands

from database import ECONOMY_DB_NAME
from seasonal_updates.halloween.halloween import get_collectibles as get_halloween_collectibles
from seasonal_updates.halloween.haunted import HAUNTED_IMPOSSIBLE_DISCOVERIES

ACHIEVEMENTS = {
    "halloween_half": {
        "name": "Haunted Collector",
        "emoji": "🎃",
        "description": "Collect at least 50% of the Halloween collectibles.",
        "reward": "Permanent profile background: Haunted Halloween",
    },
    "halloween_full": {
        "name": "Horror Enthusiast",
        "emoji": "👻",
        "description": "Collect 100% of the Halloween collectibles.",
        "reward": "Permanent profile title: Horror Enthusiast",
    },

    "halloween_bag_crafter": {
        "name": "Trick-or-Treater",
        "emoji": "🎃",
        "description": "Craft 25 Trick-or-Treat Bags.",
        "reward": "Permanent profile background: Trick-or-Treat",
    },

    "candy_background": {
        "name": "Candy Collector",
        "emoji": "🍬",
        "description": "Consume 100 pieces of Halloween Candy and/or Trick or Treat bags.",
        "reward": "Permanent profile background: Candy Collector",
    },
    "candy_nommer": {
        "name": "Candy Nommer",
        "emoji": "🍫",
        "description": "Consume 250 or more pieces of Halloween Candy and/or Trick or Treat bags. Diabeetus.",
        "reward": "Permanent profile title: Candy Nommer",
    },

    "halloween_hatch": {
        "name": "Haunting Friend",
        "emoji": "🐣",
        "description": "Hatch a Halloween Egg.",
        "reward": "Permanent profile background: Haunting Friend",
    },
    "halloween_wine_cabinet": {
        "name": "Seal Breaker",
        "emoji": "🍷",
        "description": "Break the seal on the Cursed Wine Cabinet. You were warned.",
        "reward": "Permanent profile title: Seal Breaker",
    },


    # -----------------------------------------------------------------------
    # Haunted Exploration discovery achievements
    # -----------------------------------------------------------------------
    "haunted_asylum": {"name": "Patient Zero", "emoji": "🏥", "description": "Discover every rare discovery in the Abandoned Asylum.", "reward": "Permanent profile title: Patient Zero"},
    "haunted_graveyard": {"name": "Six Feet Under", "emoji": "🪦", "description": "Discover every rare discovery in the Forgotten Graveyard.", "reward": "Permanent profile background: The Graveyard"},
    "haunted_house": {"name": "Housebroken", "emoji": "🏚️", "description": "Discover every rare discovery in the Haunted House.", "reward": "Permanent profile title: Housebroken"},
    "haunted_church": {"name": "Forgive Me", "emoji": "⛪", "description": "Discover every rare discovery in the Abandoned Church.", "reward": "Permanent profile background: Abandoned Sanctuary"},
    "haunted_witch_woods": {"name": "Into the Woods", "emoji": "🌲", "description": "Discover every rare discovery in Witch's Woods.", "reward": "Permanent profile title: Into the Woods"},
    "haunted_pizzeria": {"name": "Five Nights Wasn't Enough", "emoji": "🍕", "description": "Discover every rare discovery in the Dilapidated Pizzeria.", "reward": "Permanent profile background: Midnight Pizzeria"},
    "haunted_toy_workshop": {"name": "Playtime Is Over", "emoji": "🧸", "description": "Discover every rare discovery in the Abandoned Toy Workshop.", "reward": "Permanent profile title: Playtime Is Over"},
    "haunted_broadcast": {"name": "You're Live", "emoji": "📡", "description": "Discover every rare discovery in the Abandoned Broadcast Station.", "reward": "Permanent profile background: Dead Air"},
    "haunted_hotel": {"name": "No Vacancy", "emoji": "🏨", "description": "Discover every rare discovery in the Endless Hotel.", "reward": "Permanent profile title: No Vacancy"},
    "haunted_fogbound": {"name": "Population: ???", "emoji": "🌫️", "description": "Discover every rare discovery in Fogbound Town.", "reward": "Permanent profile background: Fogbound"},
    "haunted_research": {"name": "It Saw You Too", "emoji": "🧪", "description": "Discover all four rare discoveries in the Derelict Research Facility.", "reward": "Permanent profile title: It Saw You Too"},
    "haunted_yellow_halls": {"name": "Lost, Actually", "emoji": "🟨", "description": "Discover every rare discovery in the Yellow Halls.", "reward": "Permanent profile title: Lost, Actually"},
    "haunted_highway": {"name": "Wrong Turn", "emoji": "🛣️", "description": "Discover every rare discovery on the Dead-End Highway.", "reward": "Permanent profile background: Dead-End"},
    "haunted_drowned": {"name": "Mind the Water", "emoji": "🌊", "description": "Discover every rare discovery in the Drowned Station.", "reward": "Permanent profile title: Mind the Water"},
    "haunted_campground": {"name": "Don't Look Behind You", "emoji": "🌲", "description": "Discover every rare discovery in the Silent Campground.", "reward": "Permanent profile background: Watched From the Trees"},
    "haunted_first_discovery": {"name": "I Was Curious", "emoji": "👁️", "description": "Discover your first rare Haunted discovery.", "reward": "Permanent profile title: Haunted Explorer"},
    "haunted_impossible": {"name": "That Wasn't There Before", "emoji": "👁️", "description": "Discover an impossible environmental anomaly.", "reward": "Permanent profile title: Something Is Very Wrong"},
    "haunted_worth_it": {"name": "Worth It", "emoji": "🩸", "description": "Survive a rare discovery that causes a major Sanity loss.", "reward": "Permanent profile title: Worth It"},
    "haunted_unwell": {"name": "Unwell", "emoji": "🫥", "description": "Reach 0 Sanity after triggering a rare discovery.", "reward": "Permanent profile title: Unwell"},
    "haunted_other_side": {"name": "The Other Side", "emoji": "👁️", "description": "Discover a rare event while at 0 Sanity.", "reward": "Permanent profile title: The Other Side"},
    "haunted_all_discoveries": {"name": "I Shouldn't Have Looked", "emoji": "🕳️", "description": "Discover every rare discovery across all Haunted locations.", "reward": "Permanent profile title: I Shouldn't Have Looked"},

    # Haunted crafting achievements
    "haunted_cauldron_first": {"name": "Brewed Something Questionable", "emoji": "🧪", "description": "Craft your first item using the Haunted Cauldron.", "reward": "Permanent profile title: Practiced Alchemist"},
    "haunted_cauldron_five": {"name": "Alchemist", "emoji": "🧪", "description": "Craft 5 items using the Haunted Cauldron.", "reward": "Permanent profile title: Alchemist"},
    "haunted_workshop_first": {"name": "Made With Whatever Was Lying Around", "emoji": "🛠️", "description": "Craft your first item using the Haunted Workshop.", "reward": "Permanent profile title: Improvised Engineer"},
    "haunted_workshop_five": {"name": "I Can Fix It", "emoji": "🛠️", "description": "Craft 5 items using the Haunted Workshop.", "reward": "Permanent profile title: Haunted Handyman"},
    "haunted_ritual_first": {"name": "Something Answered", "emoji": "🕯️", "description": "Craft your first item using the Ritual Table.", "reward": "Permanent profile title: Occult Hobbyist"},
    "haunted_ritual_five": {"name": "Occultist", "emoji": "🕯️", "description": "Craft 5 items using the Ritual Table.", "reward": "Permanent profile title: Occultist"},

    # Future one-time Halloween item achievements.
    # These remain locked/inactive until their corresponding item is enabled
    # in inventory.py.
    "halloween_glitched_cartridge": {
        "name": "Drowned in Code",
        "emoji": "💾",
        "description": "Use the Glitched Cartridge.",
        "reward": "Permanent profile title: Drowned in Code",
    },
    "halloween_smile_photo": {
        "name": "Spread the Word",
        "emoji": "📸",
        "description": "Use the Hyper-realistic Dog Photo.",
        "reward": "Permanent profile title: Spread the Word",
    },
    "halloween_red_pokeball": {
        "name": "Red's Shadow",
        "emoji": "🔴",
        "description": "Use the Glitched Red Pokeball.",
        "reward": "Permanent profile title: Red's Shadow",
    },
    "halloween_hazmat_suit": {
        "name": "Boundary Breaker",
        "emoji": "☣️",
        "description": "Use the Yellow Hazmat Suit.",
        "reward": "Permanent profile title: Boundary Breaker",
    },
    "halloween_glow_chalk": {
        "name": "Otherworld Passenger",
        "emoji": "🖍️",
        "description": "Use the Glow-in-the-dark Chalk.",
        "reward": "Permanent profile title: Otherworld Passenger",
    },
    "halloween_ouija_board": {
        "name": "Spirit Communicator",
        "emoji": "🔮",
        "description": "Use the Ouija Board.",
        "reward": "Permanent profile title: Spirit Communicator",
    },
    "halloween_marker": {
        "name": "Unitologist",
        "emoji": "👽",
        "description": "Use the Unknown Alien Artifact.",
        "reward": "Permanent profile title: Unitologist",
    },
    "halloween_tails": {
        "name": "Glowing Gem",
        "emoji": "💎",
        "description": "Use the Doll of Tails.",
        "reward": "Permanent profile background: Glowing Gem",
    },
    "halloween_malo": {
        "name": "MalO",
        "emoji": "📱",
        "description": "Use the Hacked Phone.",
        "reward": "Permanent profile background: MalO",
    },
}

HALLOWEEN_BACKGROUND_ID = "halloween_haunted"
HALLOWEEN_TITLE_ID = "title_horror_enthusiast"
HALLOWEEN_CANDY_BACKGROUND_ID = "halloween_candy_collector"
HALLOWEEN_CANDY_TITLE_ID = "title_candy_nommer"
HALLOWEEN_HATCH_BACKGROUND_ID = "halloween_haunting_friend"
HALLOWEEN_BAG_BACKGROUND_ID = "halloween_trick_or_treat"
HALLOWEEN_WINE_TITLE_ID = "title_seal_breaker"

HAUNTED_DISCOVERY_ACHIEVEMENTS = {
    "asylum": ("haunted_asylum", 3, "title_patient_zero", None),
    "graveyard": ("haunted_graveyard", 3, None, "background_the_graveyard"),
    "haunted_house": ("haunted_house", 3, "title_housebroken", None),
    "church": ("haunted_church", 3, None, "background_abandoned_sanctuary"),
    "witch_woods": ("haunted_witch_woods", 3, "title_into_the_woods", None),
    "dilapidated_pizzeria": ("haunted_pizzeria", 3, None, "background_midnight_pizzeria"),
    "abandoned_toy_workshop": ("haunted_toy_workshop", 3, "title_playtime_is_over", None),
    "broadcast_station": ("haunted_broadcast", 3, None, "background_dead_air"),
    "endless_hotel": ("haunted_hotel", 3, "title_no_vacancy", None),
    "fogbound_town": ("haunted_fogbound", 3, None, "background_fogbound"),
    "derelict_research_facility": ("haunted_research", 4, "title_it_saw_you_too", None),
    "yellow_halls": ("haunted_yellow_halls", 3, "title_lost_actually", None),
    "dead_end_highway": ("haunted_highway", 3, None, "background_dead_end"),
    "drowned_station": ("haunted_drowned", 3, "title_mind_the_water", None),
    "silent_campground": ("haunted_campground", 3, None, "background_watched_from_the_trees"),
}

HAUNTED_CRAFTING_ACHIEVEMENTS = {
    "cauldron": (("haunted_cauldron_first", 1, "title_practiced_alchemist"), ("haunted_cauldron_five", 5, "title_alchemist")),
    "workshop": (("haunted_workshop_first", 1, "title_improvised_engineer"), ("haunted_workshop_five", 5, "title_haunted_handyman")),
    "ritual_table": (("haunted_ritual_first", 1, "title_occult_hobbyist"), ("haunted_ritual_five", 5, "title_occultist")),
}

HAUNTED_GLOBAL_DISCOVERY_ACHIEVEMENTS = {
    "haunted_first_discovery": ("title_haunted_explorer", None),
    "haunted_impossible": ("title_something_is_very_wrong", None),
    "haunted_worth_it": ("title_worth_it", None),
    "haunted_unwell": ("title_unwell", None),
    "haunted_other_side": ("title_the_other_side", None),
    "haunted_all_discoveries": ("title_i_shouldnt_have_looked", None),
}

HALLOWEEN_SPECIAL_ITEM_TITLE_IDS = {
    "halloween_wine_cabinet": "title_seal_breaker",
    "halloween_glitched_cartridge": "title_drowned_in_code",
    "halloween_smile_photo": "title_spread_the_word",
    "halloween_red_pokeball": "title_reds_shadow",
    "halloween_hazmat_suit": "title_boundary_breaker",
    "halloween_glow_chalk": "title_otherworld_passenger",
    "halloween_ouija_board": "title_spirit_communicator",
    "halloween_marker": "title_unitologist",
}

HALLOWEEN_SPECIAL_ITEM_BACKGROUND_IDS = {
    "halloween_tails": "background_glowing_gem",
    "halloween_malo": "background_malo",
}

HALLOWEEN_SPECIAL_ITEM_ACHIEVEMENTS = set(
    HALLOWEEN_SPECIAL_ITEM_TITLE_IDS
) | set(HALLOWEEN_SPECIAL_ITEM_BACKGROUND_IDS)


async def ensure_achievement_tables(db):
    await db.execute("""
        CREATE TABLE IF NOT EXISTS collectibles (
            user_id INTEGER NOT NULL,
            collectible_id TEXT NOT NULL,
            category TEXT NOT NULL,
            discovered_at TEXT DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, collectible_id)
        )
    """)
    await db.execute("""
        CREATE TABLE IF NOT EXISTS achievements (
            user_id INTEGER NOT NULL,
            achievement_id TEXT NOT NULL,
            unlocked_at TEXT DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, achievement_id)
        )
    """)

    await db.execute("""
        CREATE TABLE IF NOT EXISTS achievement_progress (
            user_id INTEGER NOT NULL,
            achievement_id TEXT NOT NULL,
            progress INTEGER DEFAULT 0,
            PRIMARY KEY (user_id, achievement_id)
        )
    """)
    await db.execute("""
        CREATE TABLE IF NOT EXISTS haunted_discoveries (
            user_id INTEGER NOT NULL,
            discovery_id TEXT NOT NULL,
            location_id TEXT NOT NULL,
            discovered_at TEXT DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, discovery_id)
        )
    """)

    await db.execute("""
        CREATE TABLE IF NOT EXISTS used_collectibles (
            user_id INTEGER NOT NULL,
            collectible_id TEXT NOT NULL,
            used_at TEXT DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, collectible_id)
        )
    """)


class Achievements(commands.Cog):
    """Permanent achievement tracking and rewards."""

    def __init__(self, bot):
        self.bot = bot

    async def add_candy_progress(self, user_id, amount, db=None):
        """Track Halloween candy consumption and unlock cosmetic rewards at 100 and 250+ pieces."""
        owns_db = db is None

        if owns_db:
            db = await aiosqlite.connect(ECONOMY_DB_NAME)

        try:
            await ensure_achievement_tables(db)

            await db.execute(
                """
                INSERT INTO achievement_progress (user_id, achievement_id, progress)
                VALUES (?, 'candy_nommer', ?)
                ON CONFLICT(user_id, achievement_id)
                DO UPDATE SET progress = progress + excluded.progress
                """,
                (user_id, amount),
            )

            async with db.execute(
                """
                SELECT progress
                FROM achievement_progress
                WHERE user_id = ? AND achievement_id = 'candy_nommer'
                """,
                (user_id,),
            ) as cursor:
                row = await cursor.fetchone()

            progress = row[0] if row else 0

            # 100 consumed: permanently unlock the Halloween candy background.
            if progress >= 100:
                async with db.execute(
                    """
                    SELECT 1
                    FROM achievements
                    WHERE user_id = ? AND achievement_id = 'candy_background'
                    """,
                    (user_id,),
                ) as cursor:
                    background_already_unlocked = await cursor.fetchone()

                if not background_already_unlocked:
                    await db.execute(
                        """
                        INSERT INTO achievements (user_id, achievement_id)
                        VALUES (?, 'candy_background')
                        """,
                        (user_id,),
                    )

                async with db.execute(
                    "SELECT unlocked_backgrounds FROM users WHERE user_id = ?",
                    (user_id,),
                ) as cursor:
                    bg_row = await cursor.fetchone()

                try:
                    unlocked = json.loads(
                        bg_row[0] if bg_row and bg_row[0] else '["default"]'
                    )
                    if not isinstance(unlocked, list):
                        unlocked = ["default"]
                except (TypeError, ValueError):
                    unlocked = ["default"]

                if "default" not in unlocked:
                    unlocked.insert(0, "default")

                if HALLOWEEN_CANDY_BACKGROUND_ID not in unlocked:
                    unlocked.append(HALLOWEEN_CANDY_BACKGROUND_ID)

                await db.execute(
                    "UPDATE users SET unlocked_backgrounds = ? WHERE user_id = ?",
                    (json.dumps(unlocked), user_id),
                )

            # 250+: permanently unlock the Candy Nommer title.
            if progress >= 250:
                async with db.execute(
                    """
                    SELECT 1
                    FROM achievements
                    WHERE user_id = ? AND achievement_id = 'candy_nommer'
                    """,
                    (user_id,),
                ) as cursor:
                    already_unlocked = await cursor.fetchone()

                if not already_unlocked:
                    await db.execute(
                        """
                        INSERT INTO achievements (user_id, achievement_id)
                        VALUES (?, 'candy_nommer')
                        """,
                        (user_id,),
                    )

                    await db.execute(
                        """
                        INSERT INTO inventory (user_id, item_id, item_type, quantity)
                        VALUES (?, 'title_candy_nommer', 'title', 1)
                        ON CONFLICT(user_id, item_id)
                        DO UPDATE SET quantity = MAX(quantity, 1)
                        """,
                        (user_id,),
                    )

            if owns_db:
                await db.commit()

            return progress >= 250, progress

        finally:
            if owns_db:
                await db.close()

    async def add_halloween_hatch_progress(self, user_id, db=None):
        """Unlock the permanent Haunting Friend background after hatching a Halloween Egg."""
        owns_db = db is None

        if owns_db:
            db = await aiosqlite.connect(ECONOMY_DB_NAME)

        try:
            await ensure_achievement_tables(db)

            async with db.execute(
                """
                SELECT 1
                FROM achievements
                WHERE user_id = ? AND achievement_id = 'halloween_hatch'
                """,
                (user_id,),
            ) as cursor:
                already_unlocked = await cursor.fetchone()

            if already_unlocked:
                if owns_db:
                    await db.commit()
                return False

            await db.execute(
                """
                INSERT INTO achievements (user_id, achievement_id)
                VALUES (?, 'halloween_hatch')
                """,
                (user_id,),
            )

            async with db.execute(
                "SELECT unlocked_backgrounds FROM users WHERE user_id = ?",
                (user_id,),
            ) as cursor:
                bg_row = await cursor.fetchone()

            try:
                unlocked = json.loads(bg_row[0] if bg_row and bg_row[0] else '["default"]')
                if not isinstance(unlocked, list):
                    unlocked = ["default"]
            except (TypeError, ValueError):
                unlocked = ["default"]

            if "default" not in unlocked:
                unlocked.insert(0, "default")

            if HALLOWEEN_HATCH_BACKGROUND_ID not in unlocked:
                unlocked.append(HALLOWEEN_HATCH_BACKGROUND_ID)

            await db.execute(
                "UPDATE users SET unlocked_backgrounds = ? WHERE user_id = ?",
                (json.dumps(unlocked), user_id),
            )

            if owns_db:
                await db.commit()

            return True
        finally:
            if owns_db:
                await db.close()

    async def add_trick_or_treat_bag_progress(self, user_id, amount=1, db=None):
        """Track crafted Trick-or-Treat Bags and unlock the achievement at 25."""
        owns_db = db is None

        if owns_db:
            db = await aiosqlite.connect(ECONOMY_DB_NAME)

        try:
            await ensure_achievement_tables(db)

            await db.execute(
                """
                INSERT INTO achievement_progress (user_id, achievement_id, progress)
                VALUES (?, 'halloween_bag_crafter', ?)
                ON CONFLICT(user_id, achievement_id)
                DO UPDATE SET progress = progress + excluded.progress
                """,
                (user_id, amount),
            )

            async with db.execute(
                """
                SELECT progress
                FROM achievement_progress
                WHERE user_id = ? AND achievement_id = 'halloween_bag_crafter'
                """,
                (user_id,),
            ) as cursor:
                row = await cursor.fetchone()

            progress = row[0] if row else 0

            if progress >= 25:
                async with db.execute(
                    """
                    SELECT 1
                    FROM achievements
                    WHERE user_id = ? AND achievement_id = 'halloween_bag_crafter'
                    """,
                    (user_id,),
                ) as cursor:
                    already_unlocked = await cursor.fetchone()

                if not already_unlocked:
                    await db.execute(
                        """
                        INSERT INTO achievements (user_id, achievement_id)
                        VALUES (?, 'halloween_bag_crafter')
                        """,
                        (user_id,),
                    )

                    # The achievement reward is a permanent profile background.
                    # Store it in the same unlocked_backgrounds list used by /profile.
                    async with db.execute(
                        "SELECT unlocked_backgrounds FROM users WHERE user_id = ?",
                        (user_id,),
                    ) as cursor:
                        bg_row = await cursor.fetchone()

                    try:
                        unlocked = json.loads(
                            bg_row[0] if bg_row and bg_row[0] else '["default"]'
                        )
                        if not isinstance(unlocked, list):
                            unlocked = ["default"]
                    except (TypeError, ValueError):
                        unlocked = ["default"]

                    if "default" not in unlocked:
                        unlocked.insert(0, "default")
                    if HALLOWEEN_BAG_BACKGROUND_ID not in unlocked:
                        unlocked.append(HALLOWEEN_BAG_BACKGROUND_ID)

                    await db.execute(
                        "UPDATE users SET unlocked_backgrounds = ? WHERE user_id = ?",
                        (json.dumps(unlocked), user_id),
                    )

                    if owns_db:
                        await db.commit()

                    return True, progress

            if owns_db:
                await db.commit()

            return False, progress

        finally:
            if owns_db:
                await db.close()

    async def unlock_special_item_achievement(self, user_id, achievement_id, title_id=None, db=None):
        """Unlock a permanent achievement reward for a one-time special item."""
        owns_db = db is None
        if owns_db:
            db = await aiosqlite.connect(ECONOMY_DB_NAME)

        try:
            await ensure_achievement_tables(db)

            async with db.execute(
                "SELECT 1 FROM achievements WHERE user_id = ? AND achievement_id = ?",
                (user_id, achievement_id),
            ) as cursor:
                already_unlocked = await cursor.fetchone()

            if not already_unlocked:
                await db.execute(
                    "INSERT INTO achievements (user_id, achievement_id) VALUES (?, ?)",
                    (user_id, achievement_id),
                )

            if title_id:
                await db.execute(
                    """
                    INSERT INTO inventory (user_id, item_id, item_type, quantity)
                    VALUES (?, ?, 'title', 1)
                    ON CONFLICT(user_id, item_id) DO UPDATE SET quantity = MAX(quantity, 1)
                    """,
                    (user_id, title_id),
                )

            if owns_db:
                await db.commit()

            return not already_unlocked
        finally:
            if owns_db:
                await db.close()


    async def _grant_haunted_achievement(self, db, user_id, achievement_id, title_id=None, background_id=None):
        async with db.execute(
            "SELECT 1 FROM achievements WHERE user_id = ? AND achievement_id = ?",
            (user_id, achievement_id),
        ) as cursor:
            if await cursor.fetchone():
                return False
        await db.execute(
            "INSERT INTO achievements (user_id, achievement_id) VALUES (?, ?)",
            (user_id, achievement_id),
        )
        if title_id:
            await db.execute(
                """INSERT INTO inventory (user_id, item_id, item_type, quantity)
                   VALUES (?, ?, 'title', 1)
                   ON CONFLICT(user_id, item_id) DO UPDATE SET quantity = MAX(quantity, 1)""",
                (user_id, title_id),
            )
        if background_id:
            async with db.execute("SELECT unlocked_backgrounds FROM users WHERE user_id = ?", (user_id,)) as cursor:
                row = await cursor.fetchone()
            try:
                unlocked = json.loads(row[0] if row and row[0] else '["default"]')
                if not isinstance(unlocked, list): unlocked = ["default"]
            except (TypeError, ValueError):
                unlocked = ["default"]
            if "default" not in unlocked: unlocked.insert(0, "default")
            if background_id not in unlocked: unlocked.append(background_id)
            await db.execute("UPDATE users SET unlocked_backgrounds = ? WHERE user_id = ?", (json.dumps(unlocked), user_id))
        return True

    async def record_haunted_discovery(self, user_id, discovery_id, location_id, sanity=100, db=None):
        """Permanently record a rare Haunted discovery and unlock related achievements."""
        owns_db = db is None
        if owns_db:
            db = await aiosqlite.connect(ECONOMY_DB_NAME)
        try:
            await ensure_achievement_tables(db)
            await db.execute("""CREATE TABLE IF NOT EXISTS haunted_discoveries (
                user_id INTEGER NOT NULL, discovery_id TEXT NOT NULL, location_id TEXT NOT NULL,
                discovered_at TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, discovery_id)
            )""")
            cursor = await db.execute(
                "INSERT OR IGNORE INTO haunted_discoveries (user_id, discovery_id, location_id) VALUES (?, ?, ?)",
                (user_id, discovery_id, location_id),
            )
            newly_discovered = cursor.rowcount > 0

            unlocked = []
            if newly_discovered:
                if await self._grant_haunted_achievement(db, user_id, "haunted_first_discovery", "title_haunted_explorer"):
                    unlocked.append("haunted_first_discovery")

                location_data = HAUNTED_DISCOVERY_ACHIEVEMENTS.get(location_id)
                if location_data:
                    achievement_id, needed, title_id, background_id = location_data
                    async with db.execute("SELECT COUNT(*) FROM haunted_discoveries WHERE user_id = ? AND location_id = ?", (user_id, location_id)) as c:
                        row = await c.fetchone()
                        count = row[0] if row else 0
                    if count >= needed and await self._grant_haunted_achievement(db, user_id, achievement_id, title_id, background_id):
                        unlocked.append(achievement_id)

                async with db.execute("SELECT COUNT(*) FROM haunted_discoveries WHERE user_id = ?", (user_id,)) as c:
                        total_row = await c.fetchone()
                        total = total_row[0] if total_row else 0
                if total >= 46 and await self._grant_haunted_achievement(db, user_id, "haunted_all_discoveries", "title_i_shouldnt_have_looked"):
                    unlocked.append("haunted_all_discoveries")

                if discovery_id in HAUNTED_IMPOSSIBLE_DISCOVERIES and await self._grant_haunted_achievement(db, user_id, "haunted_impossible", "title_something_is_very_wrong"):
                    unlocked.append("haunted_impossible")

                if float(sanity) <= 0 and await self._grant_haunted_achievement(db, user_id, "haunted_other_side", "title_the_other_side"):
                    unlocked.append("haunted_other_side")

            if owns_db:
                await db.commit()
            return newly_discovered, unlocked
        finally:
            if owns_db:
                await db.close()

    async def add_haunted_crafting_progress(self, user_id, station, amount=1, db=None):
        """Track Haunted crafting milestones for a crafting station."""
        if station not in HAUNTED_CRAFTING_ACHIEVEMENTS:
            return []
        owns_db = db is None
        if owns_db:
            db = await aiosqlite.connect(ECONOMY_DB_NAME)
        try:
            await ensure_achievement_tables(db)
            progress_id = f"haunted_crafting_{station}"
            await db.execute("""INSERT INTO achievement_progress (user_id, achievement_id, progress)
                VALUES (?, ?, ?) ON CONFLICT(user_id, achievement_id)
                DO UPDATE SET progress = progress + excluded.progress""", (user_id, progress_id, amount))
            async with db.execute("SELECT progress FROM achievement_progress WHERE user_id = ? AND achievement_id = ?", (user_id, progress_id)) as c:
                row = await c.fetchone()
                progress = row[0] if row else 0
            unlocked = []
            for achievement_id, threshold, title_id in HAUNTED_CRAFTING_ACHIEVEMENTS[station]:
                if progress >= threshold and await self._grant_haunted_achievement(db, user_id, achievement_id, title_id):
                    unlocked.append(achievement_id)
            if owns_db:
                await db.commit()
            return unlocked
        finally:
            if owns_db:
                await db.close()

    async def mark_haunted_discovery_outcome(self, user_id, discovery_id, sanity_delta, new_sanity, db=None):
        """Unlock global discovery achievements tied to surviving or breaking from a discovery."""
        owns_db = db is None
        if owns_db:
            db = await aiosqlite.connect(ECONOMY_DB_NAME)
        try:
            await ensure_achievement_tables(db)
            unlocked = []
            if sanity_delta <= -10 and new_sanity > 0 and await self._grant_haunted_achievement(db, user_id, "haunted_worth_it", "title_worth_it"):
                unlocked.append("haunted_worth_it")
            if sanity_delta < 0 and new_sanity <= 0 and await self._grant_haunted_achievement(db, user_id, "haunted_unwell", "title_unwell"):
                unlocked.append("haunted_unwell")
            if owns_db:
                await db.commit()
            return unlocked
        finally:
            if owns_db:
                await db.close()

    async def check_user_achievements(self, user_id, db=None):
        entries = get_halloween_collectibles()
        total = len(entries)
        if total <= 0:
            return []

        owns_db = db is None
        if owns_db:
            db = await aiosqlite.connect(ECONOMY_DB_NAME)
        try:
            await ensure_achievement_tables(db)
            async with db.execute(
                "SELECT collectible_id FROM collectibles WHERE user_id = ? AND category = 'Halloween'",
                (user_id,),
            ) as cursor:
                owned = {row[0] for row in await cursor.fetchall()}

            found = sum(1 for item_id, *_ in entries if item_id in owned)
            newly_unlocked = []

            thresholds = []
            half_needed = math.ceil(total * 0.5)
            if found >= half_needed:
                thresholds.append("halloween_half")
            if found >= total:
                thresholds.append("halloween_full")

            for achievement_id in thresholds:
                async with db.execute(
                    "SELECT 1 FROM achievements WHERE user_id = ? AND achievement_id = ?",
                    (user_id, achievement_id),
                ) as cursor:
                    if await cursor.fetchone():
                        continue

                await db.execute(
                    "INSERT INTO achievements (user_id, achievement_id) VALUES (?, ?)",
                    (user_id, achievement_id),
                )
                newly_unlocked.append(achievement_id)

                if achievement_id == "halloween_half":
                    # Permanent background unlock. The image can be added later as
                    # assets/presets/backgrounds/halloween_haunted.png.
                    async with db.execute(
                        "SELECT unlocked_backgrounds FROM users WHERE user_id = ?",
                        (user_id,),
                    ) as cursor:
                        row = await cursor.fetchone()
                    try:
                        unlocked = json.loads(row[0] if row and row[0] else '["default"]')
                        if not isinstance(unlocked, list):
                            unlocked = ["default"]
                    except (TypeError, ValueError):
                        unlocked = ["default"]
                    if "default" not in unlocked:
                        unlocked.insert(0, "default")
                    if HALLOWEEN_BACKGROUND_ID not in unlocked:
                        unlocked.append(HALLOWEEN_BACKGROUND_ID)
                    await db.execute(
                        "UPDATE users SET unlocked_backgrounds = ? WHERE user_id = ?",
                        (json.dumps(unlocked), user_id),
                    )

                elif achievement_id == "halloween_full":
                    # Titles are permanent inventory unlocks so /equip title can use them.
                    await db.execute(
                        """
                        INSERT INTO inventory (user_id, item_id, item_type, quantity)
                        VALUES (?, ?, 'title', 1)
                        ON CONFLICT(user_id, item_id) DO UPDATE SET quantity = MAX(quantity, 1)
                        """,
                        (user_id, HALLOWEEN_TITLE_ID),
                    )

            if owns_db:
                await db.commit()

        finally:
            if owns_db:
                await db.close()

        return newly_unlocked

    @commands.hybrid_command(name="achievements", description="View available achievements and how to unlock them.")
    async def achievements(self, ctx: commands.Context):
        await ctx.defer()
        user_id = ctx.author.id

        await self.check_user_achievements(user_id)

        async with aiosqlite.connect(ECONOMY_DB_NAME) as db:
            await ensure_achievement_tables(db)
            async with db.execute(
                "SELECT achievement_id FROM achievements WHERE user_id = ?",
                (user_id,),
            ) as cursor:
                unlocked = {row[0] for row in await cursor.fetchall()}

        total = len(get_halloween_collectibles())
        async with aiosqlite.connect(ECONOMY_DB_NAME) as db:
            async with db.execute(
                "SELECT COUNT(*) FROM collectibles WHERE user_id = ? AND category = 'Halloween'",
                (user_id,),
            ) as cursor:
                row = await cursor.fetchone()
                found = row[0] if row else 0

        embed = discord.Embed(
            title=f"🏆 {ctx.author.display_name}'s Achievements",
            description="Complete seasonal milestones to earn permanent cosmetics.\n",
            color=discord.Color.gold(),
        )

        half_needed = math.ceil(total * 0.5) if total else 0
        for achievement_id, achievement in ACHIEVEMENTS.items():
            is_unlocked = achievement_id in unlocked
            if achievement_id == "halloween_half":
                progress = f"Progress: **{found}/{total}** • Need **{half_needed}**"
            elif achievement_id == "candy_background":
                async with db.execute(
                    """
                    SELECT progress
                    FROM achievement_progress
                    WHERE user_id = ? AND achievement_id = 'candy_nommer'
                    """,
                    (user_id,),
                ) as cursor:
                    candy_row = await cursor.fetchone()
                candy_progress = min(candy_row[0] if candy_row else 0, 100)
                progress = f"Progress: **{candy_progress}/100**"
            elif achievement_id == "candy_nommer":
                async with db.execute(
                    """
                    SELECT progress
                    FROM achievement_progress
                    WHERE user_id = ? AND achievement_id = 'candy_nommer'
                    """,
                    (user_id,),
                ) as cursor:
                    candy_row = await cursor.fetchone()
                candy_progress = min(candy_row[0] if candy_row else 0, 250)
                progress = f"Progress: **{candy_progress}/250+**"
            elif achievement_id == "halloween_bag_crafter":
                async with db.execute(
                    """
                    SELECT progress
                    FROM achievement_progress
                    WHERE user_id = ? AND achievement_id = 'halloween_bag_crafter'
                    """,
                    (user_id,),
                ) as cursor:
                    bag_row = await cursor.fetchone()
                bag_progress = min(bag_row[0] if bag_row else 0, 25)
                progress = f"Progress: **{bag_progress}/25**"
            elif achievement_id in {v[0] for v in HAUNTED_DISCOVERY_ACHIEVEMENTS.values()}:
                location_id = next(k for k, v in HAUNTED_DISCOVERY_ACHIEVEMENTS.items() if v[0] == achievement_id)
                needed = HAUNTED_DISCOVERY_ACHIEVEMENTS[location_id][1]
                async with db.execute("SELECT COUNT(*) FROM haunted_discoveries WHERE user_id = ? AND location_id = ?", (user_id, location_id)) as c:
                    row = await c.fetchone()
                    count = row if row else 0
                progress = f"Progress: **{min(count, needed)}/{needed}**"
            elif achievement_id == "haunted_all_discoveries":
                async with db.execute("SELECT COUNT(*) FROM haunted_discoveries WHERE user_id = ?", (user_id,)) as c:
                    row = await c.fetchone()
                    count = row if row else 0
                progress = f"Progress: **{min(count, 46)}/46**"
            elif achievement_id in {"haunted_first_discovery", "haunted_impossible", "haunted_worth_it", "haunted_unwell", "haunted_other_side"}:
                progress = "Progress: **1/1**" if is_unlocked else "Progress: **0/1**"
            elif achievement_id in {a for pair in HAUNTED_CRAFTING_ACHIEVEMENTS.values() for a, _, _ in pair}:
                station, pair = next((st, p) for st, p in HAUNTED_CRAFTING_ACHIEVEMENTS.items() if any(a == achievement_id for a, _, _ in p))
                progress_id = f"haunted_crafting_{station}"
                threshold = next(t for a, t, _ in pair if a == achievement_id)
                async with db.execute("SELECT progress FROM achievement_progress WHERE user_id = ? AND achievement_id = ?", (user_id, progress_id)) as c:
                    row = await c.fetchone()
                progress = f"Progress: **{min(row[0] if row else 0, threshold)}/{threshold}**"
            elif achievement_id in HALLOWEEN_SPECIAL_ITEM_ACHIEVEMENTS:
                # One-time special collectibles are binary achievements.
                # Their permanent usage record is stored in used_collectibles.
                collectible_id = achievement_id.removeprefix("halloween_")
                try:
                    async with db.execute(
                        """
                        SELECT 1
                        FROM used_collectibles
                        WHERE user_id = ? AND collectible_id = ?
                        """,
                        (user_id, collectible_id),
                    ) as cursor:
                        item_used = await cursor.fetchone()
                    progress = "Progress: **1/1**" if item_used else "Progress: **0/1**"
                except aiosqlite.Error:
                    progress = "Progress: **0/1**"
            else:
                progress = f"Progress: **{found}/{total}**"
            status = "✅ **Unlocked**" if is_unlocked else "🔒 **Locked**"
            embed.add_field(
                name=f"{achievement['emoji']} {achievement['name']} — {status}",
                value=(
                    f"{achievement['description']}\n"
                    f"{progress}\n"
                    f"🎁 Reward: **{achievement['reward']}**"
                ),
                inline=False,
            )

        embed.set_footer(text="Achievement rewards are permanent.")
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Achievements(bot))
