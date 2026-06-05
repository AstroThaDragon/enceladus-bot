import random
import aiosqlite
import discord
from discord.ext import commands


FLIGHT_DB_PATH = "/app/data/dragonflight.db"

LICENSE_ROLE_ID = 1505083974509269074

SUCCESS_CHANCE = 0.00333


FAIL_MESSAGES = [
    "🐉 You flap confidently into the air...\nthen immediately fly into a tree.",
    "🐉 Your dragon takes off beautifully.\nYou do not.",
    "🐉 You accidentally mounted the dragon backwards.",
    "🐉 You passed out during takeoff.\nThe dragon completed the lesson alone.",
    "🐉 Your dragon achieved flight.\nYou achieved screaming.",
    "🐉 The instructor rubs their temples silently.",
    "🐉 You flew successfully for 3 seconds.\nNew personal record!",
    "🐉 Your dragon performs a barrel roll.\nYou become a projectile.",
    "🐉 You crash directly into a floating moon rock.",
    "🐉 The dragon refuses to make eye contact after that attempt.",
    "🐉 Your instructor has revoked your sky privileges temporarily.",
    "🐉 You forgot which direction was up.",
    "🐉 Your dragon is requesting a different rider.",
    "🐉 The landing was technically survivable.",
    "🐉 You hit a cloud at full speed.\nThe cloud won.",
    "🐉 You somehow got stuck in a tree despite being in open sky.",
    "🐉 Your dragon flew perfectly.\nYour steering did not.",
    "🐉 The instructor marks your test as:\n'catastrophically airborne.'",
    "🐉 You fell off the dragon midair and shattered 90% of your bones.\nYou can no longer try until your bones are 100% healed. </3",
    "🐉 You attempted a dramatic aerial maneuver.\nIt became a dramatic emergency.",
    "🐉 You successfully mounted the dragon.\nUnfortunately upside down.",
    "🐉 Your dragon took off beautifully.\nYou remained on the ground.",
    "🐉 The instructor gives you a thumbs up.\nIt is unclear if this is encouragement or pity.",
    "🐉 You flew directly into restricted airspace.\nWhich somehow included a tree.",
    "🐉 Your dragon attempted a graceful landing.\nYou attempted survival.",
    "🐉 You screamed the entire flight.\nThe dragon screamed back.",
    "🐉 You achieved temporary flight.\nGravity achieved permanent victory.",
    "🐉 The dragon performed perfectly.\nYou became airborne debris.",
    "🐉 Your instructor wrote:\n'please stop doing that.'",
    "🐉 You forgot the most important rule of dragon riding:\nhold on.",
    "🐉 Your dragon banked left.\nYou continued going forward.",
    "🐉 You crashed into a cloud so hard it started raining.",
    "🐉 Your dragon refuses to continue until you apologize.",
    "🐉 The instructor has added several new safety regulations because of you.",
    "🐉 You accidentally challenged another dragon to aerial combat.\nYou lost immediately.",
    "🐉 The dragon landed safely.\nSeveral miles away from you.",
    "🐉 Your dragon attempted a loop-de-loop.\nYou attempted to meet your ancestors.",
    "🐉 You are now banned from low-altitude flying.",
    "🐉 Your dragon filed an official workplace complaint.",
    "🐉 You reached incredible speeds.\nMostly downward.",
    "🐉 Your dragon flew majestically through the stars.\nYou were hanging on emotionally.",
    "🐉 You nearly passed.\nThen you waved at someone and crashed.",
    "🐉 Your instructor stared silently into the distance after your attempt.",
    "🐉 You flew directly into a moon-shaped billboard.",
    "🐉 The dragon says you're improving.\nThe instructor disagrees.",
    "🐉 You somehow caused turbulence indoors.",
    "🐉 You clipped a floating lantern and caused an international incident.",
    "🐉 Your dragon attempted to save the test.\nIt could not save your reputation.",
    "🐉 You forgot to buckle your cosmic safety harness.",
    "🐉 The dragon flew upside down.\nYou did not survive spiritually.",
    "🐉 You attempted advanced flight maneuvers.\nAdvanced mistakes occurred instead.",
    "🐉 The instructor writes:\n'creative, but medically concerning.'",
    "🐉 You hit a cloud and bounced off somehow.",
    "🐉 Your dragon had complete confidence in you.\nPast tense.",
    "🐉 You accidentally entered orbit.",
    "🐉 Your dragon refuses to explain what just happened.",
    "🐉 The flight lasted 4 seconds.\nThree were screaming.",
    "🐉 You missed the landing zone by an entire biome.",
    "🐉 Your dragon did a perfect landing.\nYou landed later.",
    "🐉 The instructor quietly updates your insurance costs.",
    "🐉 You attempted to look cool during takeoff.\nThat was your first mistake.",
    "🐉 The dragon achieved enlightenment mid-flight.\nYou achieved panic.",
    "🐉 Your dragon briefly reconsidered domestication.",
    "🐉 You accidentally flew into a migrating flock of celestial geese.",
    "🐉 The stars themselves seemed concerned.",
    "🐉 You forgot the emergency landing procedure.\nImprovisation did not help.",
    "🐉 Your dragon stalled midair after hearing your flight plan.",
    "🐉 You were technically airborne.\nThat is the nicest thing anyone can say about the attempt.",
    "🐉 The instructor simply circles 'no' on your test sheet.",
    "🐉 Your dragon flew into the sunset dramatically.\nYou fell off before the dramatic part.",
    "🐉 You nearly stuck the landing.\nThen physics remembered you existed.",
    "🐉 The dragon requests hazard pay before the next lesson.",
    "🐉 Your flight pattern has been described as:\n'legally alarming.'",
    "🐉 You crashed into a tower.\nThe tower would like compensation.",
    "🐉 You attempted to wave mid-flight.\nThis caused several new problems.",
    "🐉 The dragon landed perfectly.\nYou landed emotionally.",
    "🐉 Your instructor has started drinking heavily during your lessons.",
    "🐉 You accidentally invented several new safety violations.",
    "🐉 The dragon refuses to fly until morale improves.",
    "🐉 Your landing was visible from space.",
    "🐉 You achieved a new altitude record.\nCompletely unintentionally.",
    "🐉 Your dragon looked embarrassed on your behalf.",
    "🐉 You passed several stages of grief during that flight.",
    "🐉 Your dragon flew beautifully.\nYou spun through the air like a confused comet.",
    "🐉 The instructor says:\n'at least nobody exploded this time.'",
    "🐉 You flew directly into a star-shaped sign.\nIronically inspirational.",
    "🐉 Your dragon attempted evasive maneuvers.\nFrom you.",
    "🐉 The dragon completed the course.\nYou completed a medical form.",
    "🐉 Your dragon completed a flawless aerial spin.\nYou completed several emotional breakdowns.",
    "🐉 The instructor stared at your flight path silently.\nThen added a new chapter to the safety manual.",
    "🐉 You attempted a heroic launch.\nThe ground objected strongly.",
    "🐉 Your dragon briefly looked proud of you.\nThen the landing happened.",
    "🐉 You accidentally flew through someone's picnic.",
    "🐉 The dragon flew gracefully between the clouds.\nYou hit every single one.",
    "🐉 Your instructor now keeps emergency paperwork nearby.",
    "🐉 You performed a maneuver previously thought impossible.\nFor legal reasons, it will remain impossible.",
    "🐉 The dragon attempted to carry you.\nEmotionally, not physically.",
    "🐉 You forgot the emergency brake.\nThe dragon did not.",
    "🐉 Your dragon sighed before takeoff.\nThat should've been a warning.",
    "🐉 You achieved temporary control of the dragon.\nVery temporary.",
    "🐉 The instructor writes:\n'please return tomorrow with less confidence.'",
    "🐉 Your dragon executed a perfect spiral dive.\nYou were not informed beforehand.",
    "🐉 You became one with the wind.\nMostly because the saddle rejected you.",
    "🐉 The dragon flew directly through a rainbow.\nYou flew directly through regret.",
    "🐉 Your flight was technically successful.\nBy extremely flexible definitions.",
    "🐉 You accidentally saluted midair and fell off dramatically.",
    "🐉 The instructor has started charging emotional damages.",
    "🐉 Your dragon attempted to save the maneuver.\nPhysics vetoed the idea.",
    "🐉 You reached cruising altitude.\nThen immediately stopped cruising.",
    "🐉 The dragon looked back at you mid-flight.\nThat was the last stable moment.",
    "🐉 You attempted a combat roll.\nAgainst the ground.",
    "🐉 The instructor quietly whispers:\n'why is it always this one.'",
    "🐉 Your dragon now flinches whenever you approach the saddle.",
    "🐉 You accidentally flew into a parade.\nYou are now legally part of it.",
    "🐉 The dragon completed the obstacle course.\nYou became one of the obstacles.",
    "🐉 Your takeoff was inspiring.\nYour landing inspired concern.",
    "🐉 The instructor has updated your status to:\n'flammable.'",
    "🐉 Your dragon attempted to drift around a mountain.\nYou drifted off the dragon.",
    "🐉 You successfully discovered three entirely new ways to fail.",
    "🐉 The dragon landed elegantly.\nYou landed eventually.",
    "🐉 You flew directly into a flock of birds.\nThe birds were offended.",
    "🐉 Your instructor briefly considered retirement.",
    "🐉 The dragon gave 110%.\nYou gave a concussion.",
    "🐉 You attempted advanced dragon communication.\nThe dragon pretended not to know you.",
    "🐉 Your dragon completed the lesson safely.\nYou were found later.",
    "🐉 The instructor says:\n'technically, that counted as flight.'",
    "🐉 You achieved liftoff.\nThe dragon celebrated too early.",
    "🐉 Your dragon attempted a soft landing.\nThe universe attempted comedy.",
    "🐉 You forgot the basic rule:\nnever scream directly into the dragon's ear.",
    "🐉 Your flight pattern resembled interpretive dance.",
    "🐉 The dragon made it clear this was your fault specifically.",
    "🐉 You somehow caused a sonic boom at low speed.",
    "🐉 The instructor now carries stress medication.",
    "🐉 Your dragon attempted to stabilize the flight.\nYou attempted to become airborne confetti.",
    "🐉 You flew through a banner that read:\n'good luck.'",
    "🐉 The dragon believes in you.\nNobody else does.",
    "🐉 Your landing was described as:\n'cinematic but medically unfortunate.'",
    "🐉 You attempted to flex during takeoff.\nThe dragon took this personally.",
    "🐉 Your dragon flew beautifully beneath the stars.\nYou flew beautifully into a wall.",
    "🐉 The instructor circles your entire exam sheet in red.",
    "🐉 Your dragon requested a union representative.",
    "🐉 You attempted to wave to the crowd.\nThe crowd waved goodbye.",
    "🐉 The dragon avoided the obstacle perfectly.\nYou hit it with enthusiasm.",
    "🐉 Your instructor says:\n'at least your screams are improving.'",
    "🐉 You achieved negative aerodynamic performance somehow.",
    "🐉 The dragon carried you bravely into the skies.\nThe skies rejected you immediately.",
    "🐉 You attempted a legendary maneuver.\nLegends will indeed be told about it.",
    "🐉 Your dragon stared at you after landing.\nThe disappointment was palpable.",
    "🐉 Your dragon took one look at your flight plan.\nIt immediately filed for retirement.",
    "🐉 You mounted the dragon backwards.\nThe dragon has not stopped laughing.",
    "🐉 Your dragon approved the takeoff.\nThe landing remains under investigation.",
    "🐉 The dragon politely suggested a different career path.",
    "🐉 You achieved flight.\nThe dragon achieved distance.",
    "🐉 Your dragon reviewed your performance.\nThe review contained only question marks.",
    "🐉 The dragon admired your confidence.\nIt did not admire anything else.",
    "🐉 You attempted an advanced maneuver.\nThe maneuver was advanced directly into a tree.",
    "🐉 Your dragon asked if this was your first test.\nYour performance answered for you.",
    "🐉 The dragon carried you into the skies.\nThe skies requested a refund.",
    "🐉 Your dragon gave you a practice score.\nThe score was confidential for your protection.",
    "🐉 You attempted to bond with the dragon.\nThe dragon bonded with a nearby rock instead.",
    "🐉 Your flight path has been added to several safety training courses.",
    "🐉 The dragon complimented your bravery.\nIt had concerns about everything else.",
    "🐉 You attempted a heroic landing.\nThe ground remained unconvinced.",
    "🐉 The dragon flew perfectly.\nYou contributed very little to this achievement.",
    "🐉 Your instructor says:\n'At least nobody exploded this time.'",
    "🐉 You achieved a new record.\nUnfortunately it was the wrong record.",
    "🐉 The dragon trusted you with its life.\nIt has since reconsidered.",
    "🐉 You attempted to impress the crowd.\nThe crowd was impressed by the dragon.",
    "🐉 Your dragon requested hazard pay.",
    "🐉 The dragon stared at your exam results.\nThe silence was deafening.",
    "🐉 You nearly became a Dragonrider.\nThe keyword is 'nearly.'",
    "🐉 Your dragon performed beautifully.\nYou performed creatively.",
    "🐉 The dragon has recommended additional training.\nSeveral additional years of training.",
    "🐉 You landed successfully.\nThe definition of 'successfully' is currently under review.",
    "🐉 Your dragon called the flight 'memorable.'\nNobody was comforted by this statement.",
    "🐉 The dragon avoided every obstacle.\nYou introduced several new ones.",
    "🐉 Your instructor circled the entire exam in red.",
    "🐉 You attempted a legendary maneuver.\nLegends will indeed be told about it.",
    "🐉 Your dragon requested emotional support after the test.",
    "🐉 You flew directly into the sunset.\nAnd then directly into a lake.",
    "🐉 The dragon applauded your effort.\nIt did not applaud your results.",
    "🐉 Your takeoff was magnificent.\nThe landing was a separate event.",
    "🐉 The dragon gave you a map.\nIt led to the nearest training academy.",
    "🐉 Your dragon says:\n'Please do not do that again.'",
    "🐉 The skies welcomed your arrival.\nThe ground welcomed your return.",
    "🐉 You attempted to wave to the crowd.\nThe crowd waved goodbye.",
    "🐉 Your dragon filed a formal complaint with management.",
    "🐉 The dragon believes in you.\nThe instructor does not.",
    "🐉 You achieved negative aerodynamic performance somehow.",
    "🐉 The dragon carried you bravely into the skies.\nThe skies rejected you immediately.",
    "🐉 Your dragon stared at you after landing.\nThe disappointment was palpable.",
    "🐉 The dragon asked if you had any experience.\nYou changed the subject.",
	"🐉 Your dragon reviewed the footage.\nIt somehow got worse on replay.",
	"🐉 You attempted to look cool.\nThe dragon attempted to look elsewhere.",
	"🐉 The dragon admired your optimism.\nIt did not share it.",
	"🐉 Your flight instructor has requested a vacation.",
	"🐉 You successfully located the dragon.\nThe rest was less successful.",
	"🐉 The dragon says:\n'We're gonna pretend this never happened.'",
	"🐉 You attempted a barrel roll.\nThe barrel performed better.",
	"🐉 Your dragon submitted a transfer request.",
	"🐉 The dragon has seen worse.\nIt refuses to elaborate.",
	"🐉 You flew with confidence.\nThe dragon flew with concern.",
	"🐉 Your landing has been classified as a natural disaster.",
	"🐉 The dragon was impressed.\nNot by the flying, but still.",
	"🐉 You attempted a shortcut.\nThe shortcut was longer somehow.",
	"🐉 Your dragon says:\n'I miss my previous rider.'",
	"🐉 The dragon believes every failure is a lesson.\nYou provided many lessons today.",
	"🐉 Your exam results have been forwarded to several comedians.",
	"🐉 The dragon requested a helmet.\nFor itself.",
	"🐉 You attempted a smooth landing.\nThe ground disagreed.",
	"🐉 The dragon asked you to point north.\nYou pointed at the dragon.",
	"🐉 Your dragon has updated its will.",
	"🐉 The skies were clear.\nYour future was not.",
	"🐉 The dragon complimented your courage.\nIt questioned everything else.",
	"🐉 You attempted an emergency maneuver.\nThe emergency was the maneuver.",
	"🐉 Your dragon rated the experience 2 stars.",
	"🐉 The dragon says:\n'At least it was entertaining.'",
	"🐉 You flew directly into the history books.\nMostly the accident reports section.",
	"🐉 Your dragon carried you safely.\nYou did not return the favor.",
	"🐉 The dragon has requested additional rider screening procedures.",
	"🐉 You attempted to inspire confidence.\nInstead you inspired paperwork.",
	"🐉 The dragon avoided the mountain.\nYou introduced yourself to it personally.",
	"🐉 Your flight path was unique.\nLet's leave it at that.",
	"🐉 The dragon says:\n'Have you considered walking instead?'",
	"🐉 You attempted to become one with the dragon.\nThe dragon declined.",
	"🐉 Your instructor wrote:\n'Needs improvement.'\nSeveral pages later it continued.",
	"🐉 The dragon applauded your determination.\nIt was unclear what else to applaud.",
	"🐉 You attempted a graceful dismount.\nWitnesses described it differently.",
	"🐉 The dragon carried you beyond your limits.\nUnfortunately your limits were very close.",
	"🐉 Your performance has been archived for future safety demonstrations.",
	"🐉 The dragon says:\n'Well... nobody can say you didn't try.'",
	"🐉 You attempted to ride the dragon.\nThe dragon ended up riding the situation instead.",
	"🐉 Your dragon stared into the distance.\nPerhaps remembering better riders.",
    "🐉 You passed the written test.\nUnfortunately there was also a flying test.",
	"🐉 The dragon says:\n'Is mayonnaise a flight plan?'",
	"🐉 You attempted to fly.\nThe dragon attempted to forget.",
	"🐉 The dragon stared at you for several seconds.\nYou somehow scored lower during the staring portion.",
	"🐉 You were THIS close to success.\nThe dragon refuses to specify what 'this' means.",
	"🐉 The dragon has diagnosed you with severe skill deficiency.",
	"🐉 You attempted a barrel roll.\nThe barrel has requested an apology.",
	"🐉 The dragon says:\n'How are you still alive?'",
	"🐉 You prepared for years.\nThe dragon prepared for five minutes and still won.",
	"🐉 Your dragon riding license application was eaten by a seagull.",
	"🐉 The dragon would like to know what exactly your plan was.",
	"🐉 You attempted to soar through the skies.\nInstead you explored gravity.",
	"🐉 The dragon has rated your performance:\n'Certified Goober.'",
	"🐉 You flew directly into danger.\nDanger was not expecting visitors.",
	"🐉 The dragon says:\n'You make Patrick look prepared.'",
	"🐉 You attempted a legendary takeoff.\nWitnesses described it as 'an event.'",
	"🐉 The dragon is currently laughing too hard to continue the exam.",
	"🐉 Your flight path looked like a toddler drawing.",
	"🐉 The dragon has suggested training wheels.",
	"🐉 You achieved a new record.\nNobody knows what record.",
	"🐉 The dragon says:\n'Write that down so we never do it again.'",
	"🐉 You attempted advanced dragon riding.\nThe dragon attempted advanced patience.",
	"🐉 The dragon would like to remind you that the ground is not optional.",
	"🐉 You approached the dragon with confidence.\nThe dragon approached with concern.",
	"🐉 The dragon says:\n'Bold strategy. Horrible strategy, but bold.'",
	"🐉 You somehow missed the sky.",
	"🐉 The dragon reviewed your results.\nThe review simply says 'bruh.'",
	"🐉 You flew into a cloud.\nThe cloud is considering legal action.",
	"🐉 The dragon has hidden your exam results for public safety.",
	"🐉 You attempted a smooth landing.\nSeveral geologists are studying the impact site.",
	"🐉 The dragon says:\n'Who taught you that?'",
	"🐉 You answered every question incorrectly.\nIncluding your name somehow.",
	"🐉 The dragon has recommended a nice career in walking.",
	"🐉 Your flight instructor has disconnected from reality.",
	"🐉 You attempted to become one with the dragon.\nThe dragon requested personal space.",
	"🐉 The dragon says:\n'Congratulations. That was definitely one of the attempts of all time.'",
	"🐉 You nearly became a Dragonrider.\nThe dragon nearly agreed.",
	"🐉 The dragon is forwarding your footage to the annual comedy festival.",
	"🐉 You successfully discovered several new ways to fail.",
	"🐉 The dragon says:\n'Next time, bring a map. And a miracle.'",
	"🐉 Your test results have been classified.\nMostly to protect your reputation.",
	"🐉 The dragon would like to remind you that screaming is not a flight technique.",
	"🐉 You attempted to look heroic.\nThe dragon attempted not to make eye contact."
]


SUCCESS_MESSAGES = [
    "🐉✨ AGAINST ALL ODDS...\nYou passed your Dragon Flight Test!",
    "🐉✨ Your dragon instructor bursts into tears.\nYou finally passed.",
    "🐉✨ The skies accept you at last.",
    "🐉✨ You completed the flying course without exploding!",
    "🐉✨ Certified airborne creature detected.",
    "🐉✨ Against every prediction, every law of physics, and several instructor warnings...\nYou passed your Dragon Flight Test!",
    "🐉✨ Your instructor collapses to their knees.\nYou finally did it.",
    "🐉✨ The skies themselves acknowledge your success.",
    "🐉✨ Your dragon lets out a proud roar.\nNobody can believe this actually worked.",
    "🐉✨ You completed the flight course without crashing into a single object!",
    "🐉✨ The instructor quietly mutters:\n'holy sh-.'",
    "🐉✨ Your dragon performs a majestic landing.\nFor once, you are still attached.",
    "🐉✨ After countless disasters, broken fences, and emotional trauma...\nYou are officially licensed.",
    "🐉✨ The stars shine brighter as your dragon lands successfully.",
    "🐉✨ You landed perfectly.\nThe instructor immediately checks if this is a hallucination.",
    "🐉✨ Your dragon circles proudly overhead.\nYou are now officially airborne certified.",
    "🐉✨ The entire training grounds erupt into confused applause.",
    "🐉✨ The instructor signs your license with trembling hands.",
    "🐉✨ Your dragon seems genuinely happy for you.\nA terrifyingly rare moment.",
    "🐉✨ You completed the entire test without screaming once!",
    "🐉✨ The dragon nuzzles you proudly after the successful flight.",
    "🐉✨ Against impossible odds, you are now legally trusted with a dragon.",
    "🐉✨ The instructor stares at your completed test sheet in stunned silence.",
    "🐉✨ You passed so cleanly that several nearby dragons look impressed.",
    "🐉✨ Your dragon soars through the skies flawlessly.\nYou somehow keep up.",
    "🐉✨ You are now a Licensed Dragonrider!\nInsurance companies everywhere are nervous.",
    "🐉✨ The dragon lands dramatically beneath the stars.\nYou strike a heroic pose instinctively.",
    "🐉✨ The instructor wipes away a tear.\nMostly from stress relief.",
    "🐉✨ Your dragon lets out a victorious roar heard across the skies.",
    "🐉✨ You completed the course with style, grace, and minimal property damage.",
    "🐉✨ The training grounds officially recognize you as flight-capable.",
    "🐉✨ Your dragon circles the moon triumphantly before landing.",
    "🐉✨ The instructor says:\n'I genuinely did not think you'd survive long enough to pass.'",
    "🐉✨ Your dragon seems proud to call you its rider now.",
    "🐉✨ After all the crashes, bruises, and catastrophes...\nYou finally earned your wings.",
    "🐉✨ The skies open before you as your dragon ascends flawlessly.",
    "🐉✨ You passed the test so cleanly that the instructor suspects sorcery.",
    "🐉✨ Your dragon bows proudly as your license is awarded.",
    "🐉✨ The stars glitter overhead as you complete your first successful licensed flight.",
    "🐉✨ You are now officially approved for aerial chaos.",
    "🐉✨ Your dragon lands gracefully.\nYou somehow also land gracefully.",
    "🐉✨ The instructor quietly updates your status from:\n'concerning' to 'certified.'",
    "🐉✨ Your successful flight has restored hope to the entire academy.",
    "🐉✨ Your dragon spins proudly through the clouds in celebration.",
    "🐉✨ You have officially proven that miracles are real.",
]


class DragonFlight(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.loop.create_task(self.setup_database())

    async def setup_database(self):
        async with aiosqlite.connect(FLIGHT_DB_PATH) as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS dragonflight (
                    user_id INTEGER PRIMARY KEY,
                    attempts INTEGER DEFAULT 0,
                    last_attempt_date TEXT,
                    licensed INTEGER DEFAULT 0
                )
                """
            )

            await db.commit()

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
        ) +     datetime.timedelta(days=1)

        return int(reset_time.timestamp())

    def get_today_et(self):
        import datetime
        import pytz

        et_timezone = pytz.timezone("US/Eastern")
        now_et = datetime.datetime.now(et_timezone)

        return now_et.date().isoformat()

    @commands.hybrid_command(
        name="dragonrider",
        aliases=["flytest", "ft"],
        description="Attempt your Dragonrider test!"
    )
    async def dragonflight(self, ctx):
        user = ctx.author
        guild = ctx.guild

        today_et = self.get_today_et()

        async with aiosqlite.connect(FLIGHT_DB_PATH) as db:
            async with db.execute(
                """
                SELECT attempts, last_attempt_date, licensed
                FROM dragonflight
                WHERE user_id = ?
                """,
                (user.id,)
            ) as cursor:
                row = await cursor.fetchone()

            if row:
                attempts, last_attempt_date, licensed = row

                if licensed:
                    return await ctx.send(
                        "🐉 You already possess a Dragonrider License! Don't try to make the instructor feel even more pain, bro."
                    )

                if last_attempt_date == today_et:
                    reset_timestamp = self.get_next_midnight_reset()

                    return await ctx.send(
                        f"⏳ You've already attempted your Dragon Rider Test today!\n"
                        f"🐉 You may attempt another test <t:{reset_timestamp}:R>."
                )
                
            await db.execute(
                """
                INSERT INTO dragonflight (
                    user_id,
                    attempts,
                    last_attempt_date,
                    licensed
                )
                VALUES (?, 1, ?, 0)

                ON CONFLICT(user_id)
                DO UPDATE SET
                    attempts = attempts + 1,
                    last_attempt_date = excluded.last_attempt_date
                """,
                (user.id, today_et)
            )

            async with db.execute(
                "SELECT attempts FROM dragonflight WHERE user_id = ?",
                (user.id,)
            ) as cursor:
                updated_row = await cursor.fetchone()

            attempts = updated_row[0] if updated_row else 1

            success = random.random() < SUCCESS_CHANCE

            if success:
                await db.execute(
                    """
                    UPDATE dragonflight
                    SET licensed = 1
                    WHERE user_id = ?
                    """,
                    (user.id,)
                )

            await db.commit()

        if not success:
            return await ctx.send(
                f"🐲 {user.mention} attempts their Dragonrider Test...\n\n"
                f"**{random.choice(FAIL_MESSAGES)}**\n\n"
                f"You've failed your test! Your instructor must endure another day... 💔\n\n"
                f"-# ***Test Attempts:*** {attempts}"
            )

        license_role = guild.get_role(LICENSE_ROLE_ID)

        if license_role:
            try:
                await user.add_roles(
                    license_role,
                    reason="Passed Dragon Flight Test."
                )
            except:
                pass

        await ctx.send(
            f"{random.choice(SUCCESS_MESSAGES)}\n\n"
            f"🐉 {user.mention} has earned their **Dragonrider License! The instructor can finally sleep at night.**\n"
            f"**Test Attempts:** {attempts}"
        )


async def setup(bot):
    await bot.add_cog(DragonFlight(bot))