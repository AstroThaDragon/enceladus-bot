import os
import json
import random
import datetime
import pytz
import aiosqlite
import aiohttp

from discord.ext import commands, tasks


FORTUNE_RESET_CHANNEL_ID = 1306602160527507456
FORTUNE_PING_ROLE_ID = 1503642487586029568

RARITY_WEIGHTS = {
    "common": 75,
    "uncommon": 18,
    "rare": 5,
    "legendary": 1.5,
    "void": 0.5
}

HALLOWEEN_RARITY_WEIGHTS = {
    "common": 55,
    "uncommon": 24,
    "rare": 10,
    "legendary": 3,
    "void": 8
}

CHRISTMAS_RARITY_WEIGHTS = {
    "common": 72,
    "uncommon": 20,
    "rare": 6,
    "legendary": 1.5,
    "void": 0.5
}

VALENTINES_RARITY_WEIGHTS = {
    "common": 68,
    "uncommon": 22,
    "rare": 7,
    "legendary": 2.5,
    "void": 0.5
}

NEW_YEAR_RARITY_WEIGHTS = {
    "common": 60,
    "uncommon": 25,
    "rare": 10,
    "legendary": 4,
    "void": 1
}

FOURTH_OF_JULY_RARITY_WEIGHTS = {
    "common": 73,
    "uncommon": 18,
    "rare": 6,
    "legendary": 2,
    "void": 1
}

EASTER_RARITY_WEIGHTS = {
    "common": 72,
    "uncommon": 20,
    "rare": 6,
    "legendary": 1.5,
    "void": 0.5
}

THANKSGIVING_RARITY_WEIGHTS = {
    "common": 74,
    "uncommon": 18,
    "rare": 6,
    "legendary": 1.5,
    "void": 0.5
}

APRIL_FOOLS_RARITY_WEIGHTS = {
    "common": 50,
    "uncommon": 28,
    "rare": 14,
    "legendary": 6,
    "void": 2
}

SUMMER_RARITY_WEIGHTS = {
    "common": 75,
    "uncommon": 18,
    "rare": 5,
    "legendary": 1.5,
    "void": 0.5
}

WINTER_RARITY_WEIGHTS = {
    "common": 73,
    "uncommon": 20,
    "rare": 5,
    "legendary": 1.5,
    "void": 0.5
}

LUNAR_NEW_YEAR_RARITY_WEIGHTS = {
    "common": 60,
    "uncommon": 25,
    "rare": 10,
    "legendary": 4.5,
    "void": 0.5
}

FULL_MOON_RARITY_WEIGHTS = {
    "common": 60,
    "uncommon": 25,
    "rare": 10,
    "legendary": 3,
    "void": 10
}

RARITY_PREFIXES = {
    "common": "🥠",
    "uncommon": "✨",
    "rare": "🌙",
    "legendary": "🌌 **A LEGENDARY FORTUNE APPEARS... (Legendary!)**\n",
    "void": "💀 **The cookie cracks open incorrectly... (Void?)**\n"
}

EVENT_NOTES = {
    "halloween": "🎃 **Spooky season twists today's fortune...**\n",
    "christmas": "🎄 **Holiday magic warms today's fortune...**\n",
    "valentines": "💘 **Love drifts through today's fortune...**\n",
    "new_year": "🎆 **A fresh year reshapes today's fortune...**\n",
    "fourth_of_july": "🎇 **Fireworks spark through today's fortune...**\n",
    "easter": "🐣 **Springtime energy colors today's fortune...**\n",
    "thanksgiving": "🦃 **Warm gratitude flavors today's fortune...**\n",
    "april_fools": "🤡 **Something feels suspicious about today's fortune...**\n",
    "summer": "☀️ **Summer energy brightens today's fortune...**\n",
    "winter": "❄️ **Winter calm settles over today's fortune...**\n",
    "lunar_new_year": "🐉🧧 **Lunar luck coils around today's fortune...**\n",
    "full_moon": "🌕 **The full moon empowers today's fortune...**\n"
}

LUNAR_NEW_YEAR_DATES = {
    2026: "2026-02-17",
    2027: "2027-02-06",
    2028: "2028-01-26",
    2029: "2029-02-13",
    2030: "2030-02-03",
    2031: "2031-01-23",
    2032: "2032-02-11",
    2033: "2033-01-31",
    2034: "2034-02-19",
    2035: "2035-02-08"
}


class Fortunes(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_path = "/app/data/levels.db"
        self.is_full_moon_event = False

        self.bot.loop.create_task(self.setup_database())
        self.bot.loop.create_task(self.update_full_moon_status())
        self.fortune_reset_announcement.start() # type: ignore

    def cog_unload(self):
        self.fortune_reset_announcement.cancel() # type: ignore

    def get_easter_date(self, year):
        # Western/Gregorian Easter calculation
        a = year % 19
        b = year // 100
        c = year % 100
        d = b // 4
        e = b % 4
        f = (b + 8) // 25
        g = (b - f + 1) // 3
        h = (19 * a + b - d - g + 15) % 30
        i = c // 4
        k = c % 4
        l = (32 + 2 * e + 2 * i - h - k) % 7
        m = (a + 11 * h + 22 * l) // 451
        month = (h + l - 7 * m + 114) // 31
        day = ((h + l - 7 * m + 114) % 31) + 1

        return datetime.date(year, month, day)

    def is_lunar_new_year_window(self, today):
        lunar_new_year = LUNAR_NEW_YEAR_DATES.get(today.year)

        if not lunar_new_year:
            return False

        start_date = datetime.date.fromisoformat(lunar_new_year)
        end_date = start_date + datetime.timedelta(days=7)

        return start_date <= today <= end_date

    def load_fortunes(self):
        base_dir = os.path.join(os.path.dirname(__file__), "fortunes")
        active_event = self.get_active_event()

        MIX_WITH_NORMAL_EVENTS = {
            "christmas": 0.65,
            "halloween": 0.8,
            "summer": 0.55,
            "winter": 0.5
        }

        fortunes = {}

        for rarity in RARITY_WEIGHTS.keys():
            fortunes[rarity] = []

            # Only load normal fortunes if:
            # - there is no event
            # - OR the active event is month/season-long
            should_load_normal = active_event is None or active_event in MIX_WITH_NORMAL_EVENTS

            if should_load_normal:
                rarity_path = os.path.join(base_dir, rarity)

                if os.path.isdir(rarity_path):
                    for file_name in os.listdir(rarity_path):
                        if not file_name.endswith(".json"):
                            continue

                        file_path = os.path.join(rarity_path, file_name)

                        with open(file_path, "r", encoding="utf-8") as f:
                            fortunes[rarity].extend(json.load(f))

            # Load event fortunes
            if active_event:
                event_file = os.path.join(base_dir, "events", active_event, f"{rarity}.json")

                if os.path.exists(event_file):
                    with open(event_file, "r", encoding="utf-8") as f:
                        fortunes[rarity].extend(json.load(f))

        return fortunes

    def choose_fortune(self):
        fortunes = self.load_fortunes()
        active_event = self.get_active_event()

        event_weights = {
            "halloween": HALLOWEEN_RARITY_WEIGHTS,
            "christmas": CHRISTMAS_RARITY_WEIGHTS,
            "valentines": VALENTINES_RARITY_WEIGHTS,
            "new_year": NEW_YEAR_RARITY_WEIGHTS,
            "fourth_of_july": FOURTH_OF_JULY_RARITY_WEIGHTS,
            "easter": EASTER_RARITY_WEIGHTS,
            "thanksgiving": THANKSGIVING_RARITY_WEIGHTS,
            "april_fools": APRIL_FOOLS_RARITY_WEIGHTS,
            "summer": SUMMER_RARITY_WEIGHTS,
            "winter": WINTER_RARITY_WEIGHTS,
            "lunar_new_year": LUNAR_NEW_YEAR_RARITY_WEIGHTS,
            "full_moon": FULL_MOON_RARITY_WEIGHTS
        }

        weights = event_weights.get(active_event or "", RARITY_WEIGHTS)

        rarity = random.choices(
            population=list(weights.keys()),
            weights=list(weights.values()),
            k=1
        )[0]

        selected_fortune = random.choice(fortunes[rarity])

        return rarity, selected_fortune

    @tasks.loop(minutes=1)
    async def fortune_reset_announcement(self):
        et_timezone = pytz.timezone("US/Eastern")
        now_et = datetime.datetime.now(et_timezone)

        if now_et.hour == 0 and now_et.minute == 0:
            await self.update_full_moon_status()

            channel = self.bot.get_channel(FORTUNE_RESET_CHANNEL_ID)

            role_mention = f"<@&{FORTUNE_PING_ROLE_ID}>"

            await channel.send(
                f"{role_mention}\n"
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
        await self.update_full_moon_status()

    def get_active_event(self):
        et_timezone = pytz.timezone("US/Eastern")
        now_et = datetime.datetime.now(et_timezone)

        today = now_et.date()
        month = now_et.month
        day = now_et.day

        # Full moon gets priority because it is rare and only lasts one day
        if self.is_full_moon_event:
            return "full_moon"

        # New Year
        if month == 1 and day <= 7:
            return "new_year"

        # Lunar New Year
        if self.is_lunar_new_year_window(today):
            return "lunar_new_year"

        # Valentines
        if month == 2 and 7 <= day <= 14:
            return "valentines"

        # April Fools
        if month == 4 and day == 1:
            return "april_fools"

        # Easter window: Good Friday through the following Sunday
        easter_date = self.get_easter_date(today.year)
        easter_start = easter_date - datetime.timedelta(days=2)
        easter_end = easter_date + datetime.timedelta(days=7)

        if easter_start <= today <= easter_end:
            return "easter"

        # Fourth of July
        if month == 7 and 1 <= day <= 7:
            return "fourth_of_july"

        # Halloween
        if month == 10:
            return "halloween"

        # Thanksgiving
        if month == 11 and 20 <= day <= 30:
            return "thanksgiving"

        # Christmas
        if month == 12:
            return "christmas"

        # Seasonal events
        if month in [6, 7, 8]:
            return "summer"

        if month in [1, 2]:
            return "winter"

        return None

    async def update_full_moon_status(self):
        self.is_full_moon_event = await self.is_full_moon_today()

    def parse_usno_phase_date(self, phase):
        # USNO responses may include either date string or year/month/day fields.
        if "year" in phase and "month" in phase and "day" in phase:
            try:
                return datetime.date(
                    int(phase["year"]),
                    int(phase["month"]),
                    int(phase["day"])
                )
            except (ValueError, TypeError):
                return None

        date_text = phase.get("date")

        if not date_text:
            return None

        for date_format in ("%Y-%m-%d", "%Y %b %d", "%b %d, %Y"):
            try:
                return datetime.datetime.strptime(date_text, date_format).date()
            except ValueError:
                continue

        return None

    async def is_full_moon_today(self):
        et_timezone = pytz.timezone("US/Eastern")
        now_et = datetime.datetime.now(et_timezone)
        today = now_et.date()

        url = f"https://aa.usno.navy.mil/api/moon/phases/year?year={now_et.year}"

        try:
            timeout = aiohttp.ClientTimeout(total=10)

            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        return False

                    data = await response.json()
        except Exception:
            return False

        phases = data.get("phasedata", [])

        for phase in phases:
            if phase.get("phase") != "Full Moon":
                continue

            phase_date = self.parse_usno_phase_date(phase)

            if phase_date == today:
                return True

        return False

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

        active_event = self.get_active_event()
        event_note = EVENT_NOTES.get(active_event or "", "")

        await ctx.send(
            f"{event_note}"
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