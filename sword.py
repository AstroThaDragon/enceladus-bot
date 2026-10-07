import random
import asyncio
import aiosqlite
import discord
from discord.ext import commands


SWORD_DB_PATH = "/app/data/sword.db"

SWORD_ROLE_ID = 1505077643567956069
SWORD_ANNOUNCE_CHANNEL_ID = 1306602160527507456

OWNER_ROLE_ID = 891356074689560626

SUCCESS_CHANCE = 0.005


FAIL_MESSAGES = [
    "You pull with all your might... nothing happens.",
    "The sword wiggles slightly. Progress? Maybe.",
    "The stone cracks a tiny bit, then immediately fixes itself out of spite.",
    "The sword hums softly... then ignores you.",
    "You pull so hard your dignity leaves your body.",
    "The sword moves upward by approximately one molecule.",
    "A distant dragon laughs. That cannot be good.",
    "The sword judges your posture and refuses.",
    "Cosmic energy surges... then fizzles out awkwardly.",
    "The sword whispers: 'nah.'",
    "You hear dramatic orchestral music... for someone else.",
    "The sword glows brightly.\nThen the glow turns off.",
    "You swear it moved.\nIt did not.",
    "The stone emits a disappointed crack noise.",
    "Several stars align overhead.\nThe sword remains unmoved.",
    "The sword becomes slightly warm.\nThat feels concerning.",
    "You grip the sword heroically.\nThe sword remains unconvinced.",
    "Reality bends for a moment.\nThe sword still says no.",
    "The sword acknowledges your existence.\nBarely.",
    "The sword almost lifts...\nthen settles back down smugly.",
    "Ancient energy flows through the stone.\nMostly annoyance.",
    "A nearby bird watches your failure silently.",
    "The sword emits a low hum.\nIt sounds judgmental.",
    "The sword refuses to participate in your ambitions.",
    "You pull.\nThe sword files a restraining order.",
    "The stone trembles violently.\nYou are unsure if that helped.",
    "A cosmic voice whispers:\n`try again tomorrow.`",
    "The sword glows purple briefly.\nThat probably means something terrible.",
    "Your determination is admirable.\nThe sword does not care.",
    "The sword remains embedded.\nYour spine, however, does not.",
    "A faint crack appears in the stone.\nIt was your back.",
    "The sword considers your request.\nRequest denied.",
    "You feel destiny calling.\nWrong number.",
    "The sword hums with ancient power.\nThen starts ignoring you again.",
    "The sword shifts slightly.\nA nearby raccoon claps politely.",
    "Cosmic winds swirl dramatically around you.\nThe sword remains planted.",
    "The sword briefly becomes translucent.\nThat cannot be normal.",
    "The sword pulses with energy.\nYou immediately regret touching it.",
    "The sword remains motionless.\nSomehow mockingly so.",
    "You pull with legendary determination.\nThe sword responds with legendary stubbornness.",
    "Somewhere in the cosmos, a dragon snorts dismissively.",
    "The stone cracks loudly.\nFalse alarm.",
    "The sword radiates ancient authority.\nIt has denied your application.",
    "The sword lifts slightly...\nthen laughs.",
    "The sword emits cosmic static noises.",
    "The sword recognizes you.\nUnfortunately.",
    "You attempt the chosen one pose.\nThe sword remains unconvinced.",
    "A tiny meteor falls in the distance.\nProbably unrelated.",
    "The sword briefly sparks with Void energy.\nYou decide not to ask questions.",
    "The sword seems heavier today.\nRude.",
    "The sword emits a disappointed sigh.",
    "You pull heroically.\nThe sword remains deeply unimpressed.",
    "The sword vibrates slightly.\nYou immediately let go.",
    "Cosmic dust swirls around the stone.\nMostly for dramatic effect.",
    "The sword briefly glows gold.\nThen goes back to sleep.",
    "The sword refuses your request politely.\nWhich somehow hurts more.",
    "You hear ancient chanting in the distance.\nThey're laughing at you.",
    "The sword grows heavier the harder you pull.",
    "The sword emits a tiny spark.\nYou smell burnt confidence.",
    "The sword appears spiritually unavailable right now.",
    "You feel watched.\nThe sword is definitely judging you.",
    "The stone trembles.\nThen pretends nothing happened.",
    "The sword acknowledges your effort with complete silence.",
    "Cosmic winds howl around you.\nThe sword remains stubborn.",
    "The sword twitches slightly.\nYou question reality for a moment.",
    "Ancient power surges through the sword.\nIt still refuses.",
    "A low draconic growl echoes nearby.\nThe sword stays put.",
    "The sword glows ominously.\nYou stop pulling out of self-preservation.",
    "The sword becomes freezing cold.\nThat feels important.",
    "The stone cracks.\nA tiny pebble falls off dramatically.",
    "You pull with all your strength.\nThe sword responds with emotional damage.",
    "The sword lets out a faint cosmic hum.\nVery mysterious. Very unhelpful.",
    "You briefly believe in yourself.\nThe sword corrects this mistake.",
    "A nearby crow caws ominously.\nThe sword agrees with it.",
    "The sword flickers with starlight.\nThen resumes bullying you.",
    "The sword loosens slightly.\nThen tightens again out of spite.",
    "Reality bends around the sword for a split second.",
    "The sword radiates ancient draconic energy.\nYou radiate panic.",
    "The sword briefly disappears.\nThen reappears exactly where it was.",
    "You hear whispers from beyond the stars.\nThey are not encouraging.",
    "The sword hums an ancient melody.\nIt sounds sarcastic.",
    "The sword crackles with cosmic static.\nYour hair stands up instantly.",
    "You pull so hard the stone feels secondhand embarrassment.",
    "The sword refuses to elaborate further.",
    "The sword shifts upward slightly.\nA nearby star explodes dramatically.",
    "The sword emits Void energy.\nYou decide ignorance is safer.",
    "You almost become the chosen one.\nAlmost.",
    "The sword pulses once.\nThat definitely awakened something.",
    "The sword stares into your soul.\nYou lose the staring contest.",
    "The stone groans loudly.\nThe sword does not.",
    "You feel destiny within reach.\nDestiny disagrees.",
    "The sword accepts your attempt.\nThen immediately rejects it.",
    "The sword radiates overwhelming power.\nAnd overwhelming sass.",
    "A dragon somewhere probably felt that attempt.",
    "The sword begins glowing violently.\nThen stops to be dramatic.",
    "The sword remains perfectly still.\nAlmost offensively so.",
    "The sword senses your determination.\nIt raises you one stubbornness.",
    "You pull.\nThe sword files a formal complaint with the cosmos.",
    "The sword briefly levitates.\nYou blink and miss it.",
    "The sword seems amused today.",
    "The stone emits a tiny cosmic burp.",
    "The sword whispers ancient secrets.\nNone of them are useful.",
    "The sword remains embedded.\nYour ego does not.",
    "Cosmic lightning crackles overhead.\nThe sword continues being difficult.",
    "The sword considers your worthiness.\nThe meeting was short.",
    "The sword resonates with celestial power.\nUnfortunately not for you.",
    "The sword becomes alarmingly warm.\nYou stop touching it immediately.",
    "The sword glows brighter as you pull.\nThen dims out of disrespect.",
    "You feel the cosmos watching.\nThey're invested in your failure now.",
    "The sword gives you exactly one millimeter of hope.",
    "The sword vibrates angrily.\nYou politely stop asking questions.",
    "The sword shifts slightly.\nYou celebrate too early and fall over.",
    "The sword hums thoughtfully.\nThen decides against it.",
    "You hear ancient whispers from the stone.\nThey're making fun of you.",
    "The sword glows faintly.\nMostly out of annoyance.",
    "The sword allows exactly 0.2 seconds of hope before crushing it.",
    "You pull with incredible determination.\nThe sword responds with incredible resistance.",
    "The stone emits a dramatic crack.\nFalse alarm.",
    "The sword seems interested.\nThen remembers who you are.",
    "A mysterious cosmic wind swirls around you.\nThe sword remains deeply planted.",
    "You almost look worthy for a second there.",
    "The sword trembles briefly.\nProbably laughing.",
    "The sword radiates ancient energy.\nAnd ancient disappointment.",
    "The sword feels lighter for a moment.\nYou were hallucinating.",
    "You pull hard enough to concern nearby wildlife.",
    "The sword glows ominously.\nThat feels less encouraging than intended.",
    "The sword appears spiritually unavailable today.",
    "A nearby dragon watches silently.\nJudgmentally.",
    "The sword recognizes your ambition.\nIt does not share it.",
    "The sword shifts upward by approximately one atom.",
    "Cosmic energy surges through the stone.\nThe sword remains stubborn.",
    "The sword briefly levitates.\nThen remembers it hates effort.",
    "The sword emits a low hum.\nYou are unsure if it's approval or mockery.",
    "The sword crackles with Void energy.\nYou stop touching it immediately.",
    "You feel destiny approaching.\nDestiny changes direction.",
    "The sword grows warm beneath your hands.\nThen cold.\nThen judgmental.",
    "Ancient power gathers around the sword.\nNothing useful happens.",
    "The sword wiggles slightly.\nThe stone files a complaint.",
    "You hear triumphant music swelling...\nfrom somewhere else entirely.",
    "The sword stares into your soul.\nIt remains unconvinced.",
    "The sword pulses with cosmic light.\nThen returns to bullying you.",
    "The stone cracks dramatically.\nA tiny pebble falls out.",
    "You attempt the legendary chosen-one stance.\nThe sword visibly recoils.",
    "The sword hums ancient draconic chants.\nNone of them are supportive.",
    "You feel a surge of confidence.\nThe sword removes it immediately.",
    "The sword refuses to elaborate further.",
    "The sword becomes impossibly heavy.\nRude.",
    "A nearby crow witnesses your failure.\nIt seems entertained.",
    "The sword shifts upward slightly.\nYou dislocate something celebrating.",
    "The sword allows itself to be moved.\nEmotionally, not physically.",
    "The sword emits celestial sparks.\nThis somehow feels threatening.",
    "You pull with heroic strength.\nThe sword counters with legendary pettiness.",
    "The stone groans loudly.\nThe sword remains silent and stubborn.",
    "Reality flickers around the sword for a split second.",
    "The sword grants you exactly one molecule of progress.",
    "The sword whispers:\n`try harder.`",
    "You pull with all your might.\nThe sword files emotional damage paperwork.",
    "The sword radiates enough power to shake the stars.\nStill no.",
    "The sword seems almost impressed.\nAlmost.",
    "Cosmic lightning flashes overhead dramatically.\nThe sword continues being difficult.",
    "The sword briefly acknowledges your existence.\nThat is all.",
    "You swear the sword moved.\nThe sword swears it didn't.",
    "The sword glows brightly enough to blind nearby witnesses.\nStill stuck though.",
    "The sword judges your entire bloodline silently.",
    "The stone shakes violently.\nYou are somehow the only thing injured.",
    "The sword emits a faint draconic growl.\nConcerning.",
    "The sword becomes translucent briefly.\nNobody knows why.",
    "The sword almost accepts you.\nThen remembers standards exist.",
    "Ancient celestial energy spirals around the sword.\nYou accomplish nothing.",
    "The sword hums approvingly.\nThen immediately changes its mind.",
    "The sword grants you a brief glimpse of greatness.\nThen takes it back.",
    "The Cosmic Sword considered your request.\nIt respectfully declined.",
	"You reached for the sword.\nThe sword reached for a different destiny.",
	"The sword examined your qualifications.\nThe examination was brief.",
	"The Cosmic Sword remains unconvinced.",
	"You attempted to look worthy.\nThe sword attempted not to laugh.",
	"The sword sensed your presence.\nIt immediately sensed danger.",
	"You pulled with all your strength.\nThe sword remained mildly amused.",
	"The sword whispered:\n'Not today.'",
	"You gave an inspiring speech.\nThe sword was not inspired.",
	"The Cosmic Sword has rejected your application.",
	"The sword admired your determination.\nIt did not admire your odds.",
	"You approached with confidence.\nThe sword approached with skepticism.",
	"The sword stared into your soul.\nIt left disappointed.",
	"The Cosmic Sword has seen heroes.\nYou are certainly somebody.",
	"You attempted to draw the sword.\nThe sword remained employed elsewhere.",
	"The sword says:\n'Ask again in another timeline.'",
	"The Cosmic Sword rolled a higher number.",
	"You nearly grasped greatness.\nThe keyword is 'nearly.'",
	"The sword has placed you on a waiting list.",
	"You reached for the sword.\nThe sword reached for popcorn.",
	"The Cosmic Sword politely requested a different wielder.",
	"The sword appreciates your enthusiasm.\nIt fears your execution.",
	"You attempted a legendary pull.\nThe sword attempted a legendary refusal.",
	"The sword says:\n'We're not there yet, champ.'",
	"The Cosmic Sword remains firmly attached to destiny.",
	"The sword reviewed your request.\nRequest denied.",
	"You felt a powerful connection.\nThe sword did not.",
	"The sword sensed potential.\nIt is still searching.",
	"The Cosmic Sword has elected to remain unclaimed.",
	"You tugged heroically.\nThe sword tugged emotionally.",
	"The sword stared back.\nThe awkward silence continued for several minutes.",
	"The sword says:\n'Come back after the training montage.'",
	"The Cosmic Sword has forwarded your request to management.",
	"You attempted to prove your worth.\nThe sword requested additional evidence.",
	"The sword remains untouched.\nYour pride does not.",
	"The Cosmic Sword was not forged for quitters.\nUnfortunately it wasn't forged for this either.",
	"You gave it your all.\nThe sword gave you nothing.",
	"The sword says:\n'I admire the effort.'",
	"The Cosmic Sword has marked today as another successful rejection.",
	"You pulled with heroic strength.\nThe sword responded with heroic resistance.",
	"The sword felt destiny calling.\nIt wasn't your destiny.",
	"The Cosmic Sword remains exactly where it was five seconds ago.",
    "You dramatically reached for the Cosmic Sword.\nThe Cosmic Sword dramatically remained where it was.",
	"The sword sensed your arrival.\nIt locked itself.",
	"You pulled with all your might.\nThe sword rated the attempt 3/10.",
	"The Cosmic Sword says:\n'Bold of you to assume.'",
	"You heard a mysterious voice.\nIt was the sword laughing.",
	"The sword reviewed your application.\nIt used red ink.",
	"The Cosmic Sword has chosen a worthy hero.\nIt wasn't you.",
	"You struck a heroic pose.\nThe sword struck a judgmental one.",
	"The sword remained motionless.\nYour confidence followed shortly after.",
	"The Cosmic Sword has blocked your number.",
	"You attempted to summon destiny.\nDestiny sent you to voicemail.",
	"The sword says:\n'I'm gonna stop you right there.'",
	"You felt the sword calling.\nIt was calling security.",
	"The Cosmic Sword has filed a restraining order.",
	"You pulled heroically.\nThe sword pulled a prank.",
	"The sword looked deep into your soul.\nIt kept looking for a few minutes.",
	"The Cosmic Sword says:\n'Have you tried being worthy?'",
	"You challenged fate.\nFate accepted and won.",
	"The sword witnessed your attempt.\nIt wishes it hadn't.",
	"The Cosmic Sword is currently unavailable.\nPlease try another century.",
	"You gave the sword your best effort.\nThe sword gave you its funniest rejection.",
	"The sword remains unconquered.\nYou remain optimistic somehow.",
	"The Cosmic Sword has updated your status to:\n'Maybe later.'",
	"You attempted to claim the sword.\nThe sword claimed emotional damages.",
	"The sword says:\n'Interesting strategy. Terrible strategy, but interesting.'",
	"The Cosmic Sword rolled its eyes.",
	"You almost looked legendary.\nAlmost.",
	"The sword has requested a more experienced protagonist.",
	"You reached enlightenment.\nThe sword remained out of reach.",
	"The Cosmic Sword has seen many heroes.\nToday's not looking promising.",
	"You attempted a destiny speedrun.\nThe sword patched the exploit.",
	"The sword stared silently.\nThe silence was devastating.",
	"The Cosmic Sword says:\n'Skill issue.'",
	"You were one step away from greatness.\nUnfortunately it was the wrong step.",
	"The sword appreciated the comedy.\nIt did not appreciate the attempt.",
	"The Cosmic Sword remains firmly lodged in reality.",
	"You tried the power of friendship.\nThe sword tried the power of saying no.",
	"The sword sensed immense potential.\nIn somebody nearby.",
	"The Cosmic Sword has promoted you to spectator.",
	"You attempted to become the chosen one.\nThe sword chose violence instead.",
	"The sword says:\n'You miss 100% of the pulls you don't make.\nYou also miss some of the ones you do.'",
	"The Cosmic Sword has concluded today's comedy show.",
	"You grabbed the handle.\nThe handle grabbed your self-esteem.",
	"The sword has been advised by its lawyers not to comment."
]


class Sword(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Pulls can race globally: only one successful/failed attempt may update
        # the daily-attempt state and current-wielder state at a time.
        self.pull_lock = asyncio.Lock()
        self.bot.loop.create_task(self.setup_database())

    async def setup_database(self):
        async with aiosqlite.connect(SWORD_DB_PATH) as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS sword_stats (
                    user_id INTEGER PRIMARY KEY,
                    attempts INTEGER DEFAULT 0,
                    last_pull_date TEXT
                )
                """
            )
            async with db.execute("PRAGMA table_info(sword_stats)") as cursor:
                columns = await cursor.fetchall()

            column_names = [column[1] for column in columns]

            if "last_pull_date" not in column_names:
                await db.execute("ALTER TABLE sword_stats ADD COLUMN last_pull_date TEXT")

            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS sword_global (
                    id INTEGER PRIMARY KEY,
                    total_attempts INTEGER DEFAULT 0,
                    current_wielder_id INTEGER
                )
                """
            )

            await db.execute(
                """
                INSERT OR IGNORE INTO sword_global (
                    id,
                    total_attempts,
                    current_wielder_id
                )
                VALUES (1, 0, NULL)
                """
            )

            await db.commit()

    async def add_attempt(self, user_id):
        today_et = self.get_today_et()

        async with aiosqlite.connect(SWORD_DB_PATH) as db:
            await db.execute("BEGIN IMMEDIATE")

            async with db.execute(
                "SELECT attempts, last_pull_date FROM sword_stats WHERE user_id = ?",
                (user_id,)
            ) as cursor:
                row = await cursor.fetchone()

            if row and row[1] == today_et:
                await db.rollback()
                return None, None, None, True

            await db.execute(
                """
                INSERT INTO sword_stats (user_id, attempts, last_pull_date)
                VALUES (?, 1, ?)
                ON CONFLICT(user_id)
                DO UPDATE SET
                    attempts = attempts + 1,
                    last_pull_date = excluded.last_pull_date
                """,
                (user_id, today_et)
            )

            await db.execute(
                """
                UPDATE sword_global
                SET total_attempts = total_attempts + 1
                WHERE id = 1
                """
            )

            async with db.execute(
                "SELECT attempts FROM sword_stats WHERE user_id = ?",
                (user_id,)
            ) as cursor:
                user_row = await cursor.fetchone()

            async with db.execute(
                "SELECT total_attempts, current_wielder_id FROM sword_global WHERE id = 1"
            ) as cursor:
                global_row = await cursor.fetchone()

            await db.commit()

        user_attempts = user_row[0] if user_row else 1
        total_attempts = global_row[0] if global_row else 1
        current_wielder_id = global_row[1] if global_row else None

        return user_attempts, total_attempts, current_wielder_id, False

    async def set_wielder(self, user_id):
        async with aiosqlite.connect(SWORD_DB_PATH) as db:
            await db.execute(
                """
                UPDATE sword_global
                SET current_wielder_id = ?
                WHERE id = 1
                """,
                (user_id,)
            )

            await db.commit()

    def get_today_et(self):
        import datetime
        import pytz

        et_timezone = pytz.timezone("US/Eastern")
        now_et = datetime.datetime.now(et_timezone)

        return now_et.date().isoformat()
    
    def get_next_midnight_reset(self):
        import datetime
        import pytz

        et = pytz.timezone("US/Eastern")
        now = datetime.datetime.now(et)

        reset_time = now.replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0
        ) + datetime.timedelta(days=1)

        return int(reset_time.timestamp())

    @commands.hybrid_command(
        name="pullsword",
        aliases=["ps"],
        description="Attempt to pull the cosmic sword from the stone!"
    )
    async def pullsword(self, ctx):
        # This lock is intentionally global, not per-user.  The sword has one
        # shared wielder, so two different users must not resolve simultaneously.
        async with self.pull_lock:
            user = ctx.author
            guild = ctx.guild

            user_attempts, total_attempts, previous_wielder_id, already_pulled = await self.add_attempt(user.id)

            if already_pulled:
                reset_timestamp = self.get_next_midnight_reset()

                return await ctx.send(
                    f"**You've already attempted to pull the cosmic sword today!** ⚔️\n"
                    f"You may attempt another pull <t:{reset_timestamp}:R>"
                )

            sword_role = guild.get_role(SWORD_ROLE_ID)

            success = random.random() < SUCCESS_CHANCE
            owner_ping = f"<@&{OWNER_ROLE_ID}>"

            if not success:
                fail_text = random.choice(FAIL_MESSAGES).replace("\\n", "\n")

                return await ctx.send(
                    f"{user.mention} attempts to pull the sword! ⚔️\n\n"
                    f"*{fail_text}*\n\n"
                    f"**You've failed to pull the sword!** Maybe you'll be more determined tomorrow? Probably?\n\n"
                    f"-# **Your attempts: {user_attempts}**"
                )

            previous_wielder = None
            if previous_wielder_id:
                previous_wielder = guild.get_member(previous_wielder_id)

            added_new_role = False
            removed_old_role = False

            try:
                if sword_role:
                    # Give the new wielder the role before removing it from the old
                    # wielder, so a role/API failure does not leave nobody holding it.
                    if sword_role not in user.roles:
                        await user.add_roles(
                            sword_role,
                            reason="Pulled the cosmic sword from the stone."
                        )
                        added_new_role = True

                    if previous_wielder and previous_wielder.id != user.id and sword_role in previous_wielder.roles:
                        await previous_wielder.remove_roles(
                            sword_role,
                            reason="The cosmic sword chose a new wielder."
                        )
                        removed_old_role = True

                await self.set_wielder(user.id)

            except Exception:
                # Best-effort rollback keeps the Discord role state aligned with
                # the database if the claim or role transition fails.
                if sword_role:
                    if removed_old_role and previous_wielder and sword_role not in previous_wielder.roles:
                        try:
                            await previous_wielder.add_roles(
                                sword_role,
                                reason="Rolling back failed cosmic sword transfer."
                            )
                        except discord.HTTPException:
                            pass

                    if added_new_role and sword_role in user.roles:
                        try:
                            await user.remove_roles(
                                sword_role,
                                reason="Rolling back failed cosmic sword transfer."
                            )
                        except discord.HTTPException:
                            pass

                raise

            message = (
                f"{owner_ping}\n"
                f"🌌⚔️ **THE COSMIC SWORD HAS BEEN PULLED FROM THE STONE!** ⚔️🌌\n\n"
                f"{user.mention} has become the new wielder of the Cosmic Sword! Congratulations!\n"
            )

            if previous_wielder and previous_wielder.id != user.id:
                message += (
                    f"\n*The sword's blessing leaves {previous_wielder.mention}...*"
                )

            message += (
                f"\n\n-#**{user.display_name}'s attempts: {user_attempts}** ⚔️"
            )

            await ctx.send(message)

            announce_channel = guild.get_channel(SWORD_ANNOUNCE_CHANNEL_ID)

            if announce_channel and announce_channel.id != ctx.channel.id:
                await announce_channel.send(message)

    @commands.hybrid_command(
        name="swordstats",
        aliases=["ss"],
        description="View the Cosmic Sword's global pull stats."
    )
    async def swordstats(self, ctx):
        async with aiosqlite.connect(SWORD_DB_PATH) as db:
            async with db.execute(
                "SELECT total_attempts, current_wielder_id FROM sword_global WHERE id = 1"
            ) as cursor:
                row = await cursor.fetchone()

        if not row:
            return await ctx.send("The Cosmic Sword has no recorded history yet.")

        total_attempts, current_wielder_id = row

        if current_wielder_id:
            wielder_text = f"<@{current_wielder_id}>"
        else:
            wielder_text = "No one yet."

        await ctx.send(
            "**Cosmic Sword Stats** 🌌⚔️\n\n"
            f"**Global pull attempts:** {total_attempts}\n"
            f"**Current Cosmic Sword wielder:** {wielder_text} 👑"
        )


async def setup(bot):
    await bot.add_cog(Sword(bot))