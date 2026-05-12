import os
import json
import random
import datetime
import pytz
import aiosqlite

from discord.ext import commands, tasks


FORTUNE_RESET_CHANNEL_ID = 1306602160527507456

RARITY_WEIGHTS = {
    "common": 75,
    "uncommon": 18,
    "rare": 5,
    "legendary": 1.5,
    "void": 0.5
}

RARITY_PREFIXES = {
    "common": "🥠",
    "uncommon": "✨",
    "rare": "🌙",
    "legendary": "🌌 **A LEGENDARY FORTUNE APPEARS...**\n",
    "void": "💀 **The cookie cracks open incorrectly...**\n"
}


class Fortunes(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_path = "/app/data/levels.db" 

        self.bot.loop.create_task(self.setup_database())
        self.fortune_reset_announcement.start() # type: ignore

    def cog_unload(self):
        self.fortune_reset_announcement.cancel() # type: ignore

    def load_fortunes(self):
        fortune_dir = os.path.join(os.path.dirname(__file__), "fortunes")
        fortunes = {}

        for rarity in RARITY_WEIGHTS.keys():
            file_path = os.path.join(fortune_dir, f"{rarity}.json")

            with open(file_path, "r", encoding="utf-8") as f:
                fortunes[rarity] = json.load(f)

        return fortunes

    def choose_fortune(self):
        fortunes = self.load_fortunes()

        rarity = random.choices(
            population=list(RARITY_WEIGHTS.keys()),
            weights=list(RARITY_WEIGHTS.values()),
            k=1
        )[0]

        selected_fortune = random.choice(fortunes[rarity])

        return rarity, selected_fortune

    @tasks.loop(minutes=1)
    async def fortune_reset_announcement(self):
        et_timezone = pytz.timezone("US/Eastern")
        now_et = datetime.datetime.now(et_timezone)

        if now_et.hour == 0 and now_et.minute == 0:
            channel = self.bot.get_channel(FORTUNE_RESET_CHANNEL_ID)

            if channel:
                await channel.send(
                    "🌙✨ **The cosmic fortune cookies have reset!**\n"
                    "Use `/fortune` to open today's cookie!"
                )

    async def setup_database(self):
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("PRAGMA table_info(users)") as cursor:
                columns = await cursor.fetchall()

            column_names = [column[1] for column in columns]

            if "last_fortune_date" not in column_names:
                await db.execute("ALTER TABLE users ADD COLUMN last_fortune_date TEXT")
                await db.commit()

    @fortune_reset_announcement.before_loop
    async def before_fortune_reset_announcement(self):
        await self.bot.wait_until_ready()
        await self.setup_database()

    @commands.hybrid_command(name="fortune", description="Open your daily cosmic fortune cookie!")
    async def fortune(self, ctx):
        user_id = ctx.author.id

        et_timezone = pytz.timezone("US/Eastern")
        now_et = datetime.datetime.now(et_timezone)
        current_date_et = now_et.date().isoformat()

        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT last_fortune_date FROM users WHERE user_id = ?",
                (user_id,)
            ) as cursor:
                result = await cursor.fetchone()

            if result and result[0] == current_date_et:
                return await ctx.send(
                    "⏳ You've already opened your cookie for today! Come back after midnight **Eastern Time**."
                )

            rarity, selected_fortune = self.choose_fortune()

            if rarity == "void":
                lucky_nums = "0, 0, 0, 0, 0"
            else:
                lucky_nums = ", ".join(map(str, random.sample(range(1, 99), 5)))

            await db.execute(
                """
                INSERT INTO users (user_id, last_fortune_date)
                VALUES (?, ?)
                ON CONFLICT(user_id)
                DO UPDATE SET last_fortune_date = excluded.last_fortune_date
                """,
                (user_id, current_date_et)
            )
            await db.commit()

        prefix = RARITY_PREFIXES.get(rarity, "🥠")

        await ctx.send(
            f"{prefix} **{ctx.author.mention} pulls apart the cookie...**\n"
            f"> *\"{selected_fortune}\"*\n"
            f"🔮 **Lucky Numbers:** `{lucky_nums}`"
        )

    @fortune.error
    async def fortune_error(self, ctx, error):
        await ctx.send(f"⚠️ Fortune command error: `{error}`")
        raise error

async def setup(bot):
    await bot.add_cog(Fortunes(bot))