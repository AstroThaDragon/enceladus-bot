import json
import math
import aiosqlite
import discord
from discord.ext import commands

from database import ECONOMY_DB_NAME
from seasonal_updates.halloween import get_collectibles as get_halloween_collectibles

ACHIEVEMENTS = {
    "halloween_half": {
        "name": "Haunted Collector",
        "emoji": "🎃",
        "description": "Collect at least 50% of the Halloween Space Junk collectibles.",
        "reward": "Permanent profile background: Haunted Halloween",
    },
    "halloween_full": {
        "name": "Horror Enthusiast",
        "emoji": "👻",
        "description": "Collect 100% of the Halloween Space Junk collectibles.",
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
}

HALLOWEEN_BACKGROUND_ID = "halloween_haunted"
HALLOWEEN_TITLE_ID = "title_horror_enthusiast"
HALLOWEEN_CANDY_BACKGROUND_ID = "halloween_candy_collector"
HALLOWEEN_CANDY_TITLE_ID = "title_candy_nommer"
HALLOWEEN_HATCH_BACKGROUND_ID = "halloween_haunting_friend"
HALLOWEEN_BAG_BACKGROUND_ID = "halloween_trick_or_treat"


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
                found = (await cursor.fetchone())[0]

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
