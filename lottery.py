# © 2026 The Cosmic Lair & AstroThaDragon. All Rights Reserved.
# Unauthorized use of this code is prohibited.

"""Monthly Enceladus lottery.

The game is Powerball-inspired, but intentionally uses Enceladus-specific rules:
players choose five unique numbers from 1-99 and there is no separate bonus ball.
Tickets are stored as individual rows because every ticket carries its own numbers.
"""

import json
import random
from collections import Counter, defaultdict
from datetime import datetime

import aiosqlite
import discord
import pytz
from discord.ext import commands

from database import ECONOMY_DB_NAME


class Lottery(commands.Cog):
    """Monthly Stardust lottery with staff-controlled drawings."""

    TICKET_COST = 100
    MAX_TICKETS_PER_USER = 25
    NUMBER_MIN = 1
    NUMBER_MAX = 99
    NUMBERS_PER_TICKET = 5

    # The 5/5 match is the 10,000 Stardust top prize requested for the lottery.
    # Lower tiers are deliberately modest so the jackpot remains the headline prize.
    PRIZES = {
        1: 50,
        2: 200,
        3: 750,
        4: 2_500,
        5: 10_000,
    }

    MODERATOR_ROLE_ID = 1036583011405266974
    ADMIN_ROLE_ID = 593718477831929858
    OWNER_ROLE_ID = 891356074689560626
    STAFF_ROLE_IDS = {
        MODERATOR_ROLE_ID,
        ADMIN_ROLE_ID,
        OWNER_ROLE_ID,
    }

    def __init__(self, bot):
        self.bot = bot
        self.db_path = ECONOMY_DB_NAME

    @staticmethod
    def eastern_now():
        return datetime.now(pytz.timezone("US/Eastern"))

    async def cog_load(self):
        async with aiosqlite.connect(self.db_path) as db:
            await self.ensure_schema(db)
            await db.commit()

    async def ensure_schema(self, db):
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS lottery_cycles (
                cycle_id INTEGER PRIMARY KEY AUTOINCREMENT,
                status TEXT NOT NULL DEFAULT 'open',
                opened_at TEXT NOT NULL,
                drawn_at TEXT,
                opened_by INTEGER NOT NULL,
                drawn_by INTEGER,
                winning_numbers TEXT,
                tickets_sold INTEGER NOT NULL DEFAULT 0,
                total_payout INTEGER NOT NULL DEFAULT 0,
                results_json TEXT NOT NULL DEFAULT '{}'
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS lottery_tickets (
                ticket_id INTEGER PRIMARY KEY AUTOINCREMENT,
                cycle_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                n1 INTEGER NOT NULL,
                n2 INTEGER NOT NULL,
                n3 INTEGER NOT NULL,
                n4 INTEGER NOT NULL,
                n5 INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(cycle_id) REFERENCES lottery_cycles(cycle_id),
                UNIQUE(cycle_id, user_id, n1, n2, n3, n4, n5)
            )
            """
        )
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_lottery_tickets_cycle ON lottery_tickets(cycle_id)"
        )
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_lottery_tickets_user_cycle ON lottery_tickets(user_id, cycle_id)"
        )

    @staticmethod
    def normalize_numbers(numbers):
        try:
            values = sorted(int(number) for number in numbers)
        except (TypeError, ValueError):
            return None

        if len(values) != Lottery.NUMBERS_PER_TICKET:
            return None
        if len(set(values)) != Lottery.NUMBERS_PER_TICKET:
            return None
        if any(number < Lottery.NUMBER_MIN or number > Lottery.NUMBER_MAX for number in values):
            return None
        return values

    @staticmethod
    def format_numbers(numbers):
        return " • ".join(f"**{number}**" for number in numbers)

    def is_staff(self, member):
        if member is None or not hasattr(member, "roles"):
            return False
        return any(role.id in self.STAFF_ROLE_IDS for role in member.roles)

    async def get_active_cycle(self, db):
        async with db.execute(
            """
            SELECT cycle_id, opened_at, opened_by, tickets_sold, total_payout
            FROM lottery_cycles
            WHERE status = 'open'
            ORDER BY cycle_id DESC
            LIMIT 1
            """
        ) as cursor:
            return await cursor.fetchone()

    async def send_status(self, ctx, *, ephemeral=False):
        async with aiosqlite.connect(self.db_path) as db:
            await self.ensure_schema(db)
            cycle = await self.get_active_cycle(db)

            if cycle:
                cycle_id, opened_at, opened_by, tickets_sold, total_payout = cycle
                async with db.execute(
                    "SELECT COUNT(*) FROM lottery_tickets WHERE cycle_id = ?",
                    (cycle_id,),
                ) as cursor:
                    row = await cursor.fetchone()
                    active_tickets = row[0] if row else 0
            else:
                cycle_id = opened_at = tickets_sold = total_payout = active_tickets = None

            async with db.execute(
                "SELECT cycle_id, winning_numbers, drawn_at, tickets_sold, total_payout FROM lottery_cycles WHERE status = 'drawn' ORDER BY cycle_id DESC LIMIT 1"
            ) as cursor:
                last_draw = await cursor.fetchone()

        if cycle:
            description = (
                f"🎟️ **Ticket price:** **{self.TICKET_COST:,} Stardust**\n"
                f"📦 **Your ticket limit:** **{self.MAX_TICKETS_PER_USER}** active tickets\n"
                f"🎫 **Tickets in this cycle:** **{active_tickets:,}**\n\n"
                "Choose **5 different numbers from 1–99** for every ticket. "
                "You can buy multiple tickets, but each ticket must have its own number combination.\n\n"
                "**Prize tiers**\n"
                + "\n".join(
                    f"{matches}/5 matches — **{payout:,} Stardust**"
                    for matches, payout in sorted(self.PRIZES.items())
                )
                + f"\n\n🆔 Current cycle: **#{cycle_id}**"
            )
            title = "🎟️ Enceladus Monthly Lottery — OPEN"
        else:
            description = (
                "There is no lottery open right now.\n\n"
                f"🎟️ Ticket price: **{self.TICKET_COST:,} Stardust**\n"
                f"📦 Maximum active tickets per user: **{self.MAX_TICKETS_PER_USER}**\n\n"
                "Staff can start the next cycle with `/lottery open`."
            )
            title = "🎟️ Enceladus Monthly Lottery"

        if last_draw:
            last_cycle_id, winning_numbers, drawn_at, sold, payout = last_draw
            try:
                last_numbers = json.loads(winning_numbers)
            except (TypeError, json.JSONDecodeError):
                last_numbers = []
            if last_numbers:
                description += (
                    f"\n\n**Last drawing — Cycle #{last_cycle_id}**\n"
                    f"Winning numbers: {self.format_numbers(last_numbers)}\n"
                    f"Tickets drawn: **{sold:,}** • Paid out: **{payout:,} Stardust**"
                )

        embed = discord.Embed(
            title=title,
            description=description,
            color=discord.Color.from_rgb(0, 229, 255),
        )
        embed.add_field(
            name="🎁 How to play",
            value="Use `/lottery buy` with your five chosen numbers while a cycle is open.",
            inline=False,
        )
        await ctx.send(embed=embed, ephemeral=ephemeral)

    @commands.hybrid_group(
        name="lottery",
        description="View and participate in the monthly Enceladus lottery."
    )
    async def lottery(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            await self.send_status(ctx)

    @lottery.command(name="status", description="View the current lottery status.")
    async def lottery_status(self, ctx: commands.Context):
        await self.send_status(ctx)

    @lottery.command(name="buy", description="Buy one lottery ticket with five unique numbers.")
    async def lottery_buy(
        self,
        ctx: commands.Context,
        number1: int,
        number2: int,
        number3: int,
        number4: int,
        number5: int,
    ):
        numbers = self.normalize_numbers((number1, number2, number3, number4, number5))
        if numbers is None:
            return await ctx.send(
                "❌ Your ticket must contain **5 different whole numbers from 1 to 99**."
            )

        user_id = ctx.author.id
        now = self.eastern_now().isoformat()

        async with aiosqlite.connect(self.db_path) as db:
            await self.ensure_schema(db)
            await db.execute("BEGIN IMMEDIATE")

            cycle = await self.get_active_cycle(db)
            if not cycle:
                await db.rollback()
                return await ctx.send("🎟️ **There isn't an open lottery right now.**")

            cycle_id = cycle[0]
            async with db.execute(
                "SELECT COUNT(*) FROM lottery_tickets WHERE cycle_id = ? AND user_id = ?",
                (cycle_id, user_id),
            ) as cursor:
                    row = await cursor.fetchone()
                    ticket_count = row[0] if row else 0

            if ticket_count >= self.MAX_TICKETS_PER_USER:
                await db.rollback()
                return await ctx.send(
                    f"📦 **Ticket limit reached!** You can only have **{self.MAX_TICKETS_PER_USER}** active tickets in a cycle."
                )

            async with db.execute(
                "SELECT stardust FROM users WHERE user_id = ?",
                (user_id,),
            ) as cursor:
                row = await cursor.fetchone()

            if not row:
                await db.rollback()
                return await ctx.send(
                    "❌ You don't have an active station profile yet. Run `/profile`, `/scavenge`, or `/mine` first!"
                )

            stardust = row[0] or 0
            if stardust < self.TICKET_COST:
                await db.rollback()
                return await ctx.send(
                    f"💸 **Not enough Stardust!** A lottery ticket costs **{self.TICKET_COST:,}**, "
                    f"but you only have **{stardust:,}**."
                )

            try:
                await db.execute(
                    """
                    INSERT INTO lottery_tickets
                        (cycle_id, user_id, n1, n2, n3, n4, n5, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (cycle_id, user_id, *numbers, now),
                )
            except aiosqlite.IntegrityError:
                await db.rollback()
                return await ctx.send(
                    "⚠️ You already own a ticket with that exact number combination in this cycle. "
                    "Pick a different combination!"
                )

            await db.execute(
                "UPDATE users SET stardust = stardust - ? WHERE user_id = ?",
                (self.TICKET_COST, user_id),
            )
            await db.execute(
                "UPDATE lottery_cycles SET tickets_sold = tickets_sold + 1 WHERE cycle_id = ?",
                (cycle_id,),
            )
            await db.commit()

        await ctx.send(
            f"🎟️ **Lottery Ticket Purchased!**\n\n"
            f"Numbers: {self.format_numbers(numbers)}\n"
            f"💰 Cost: **{self.TICKET_COST:,} Stardust**\n"
            f"📦 Tickets owned this cycle: **{ticket_count + 1}/{self.MAX_TICKETS_PER_USER}**\n\n"
            "Good luck, explorer! 🌌"
        )

    @lottery.command(name="tickets", description="View your active lottery tickets for the current cycle.")
    async def lottery_tickets(self, ctx: commands.Context):
        user_id = ctx.author.id
        async with aiosqlite.connect(self.db_path) as db:
            await self.ensure_schema(db)
            cycle = await self.get_active_cycle(db)
            if not cycle:
                return await ctx.send("🎟️ **There isn't an open lottery right now.**")

            cycle_id = cycle[0]
            async with db.execute(
                """
                SELECT n1, n2, n3, n4, n5
                FROM lottery_tickets
                WHERE cycle_id = ? AND user_id = ?
                ORDER BY ticket_id
                """,
                (cycle_id, user_id),
            ) as cursor:
                rows = await cursor.fetchall()

        if not rows:
            return await ctx.send(
                f"🎟️ You don't have any tickets in **Lottery Cycle #{cycle_id}**."
            )

        lines = [
            f"**#{index}:** {self.format_numbers(row)}"
            for index, row in enumerate(rows, start=1)
        ]
        embed = discord.Embed(
            title=f"🎟️ Your Lottery Tickets — Cycle #{cycle_id}",
            description="\n".join(lines),
            color=discord.Color.from_rgb(0, 229, 255),
        )
        embed.set_footer(text=f"{len(lines)}/{self.MAX_TICKETS_PER_USER} tickets • {self.TICKET_COST:,} Stardust each")
        await ctx.send(embed=embed)

    @lottery.command(name="open", description="Open a new monthly lottery cycle. Staff only.")
    async def lottery_open(self, ctx: commands.Context):
        if not self.is_staff(ctx.author):
            return await ctx.send("🚫 **Staff only.**")

        now = self.eastern_now().isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            await self.ensure_schema(db)
            await db.execute("BEGIN IMMEDIATE")
            active = await self.get_active_cycle(db)
            if active:
                await db.rollback()
                return await ctx.send(f"⚠️ **Lottery Cycle #{active[0]} is already open.**")

            cursor = await db.execute(
                "INSERT INTO lottery_cycles (status, opened_at, opened_by) VALUES ('open', ?, ?)",
                (now, ctx.author.id),
            )
            cycle_id = cursor.lastrowid
            await db.commit()

        await ctx.send(
            f"🎟️ **Lottery Cycle #{cycle_id} is now OPEN!**\n\n"
            f"Tickets cost **{self.TICKET_COST:,} Stardust** each, with a maximum of **{self.MAX_TICKETS_PER_USER}** active tickets per user.\n"
            "Players choose five different numbers from **1–99**.\n\n"
            "Staff can run `/lottery draw` when it's time to hold the drawing."
        )

    @lottery.command(name="draw", description="Draw the five winning lottery numbers. Staff only.")
    async def lottery_draw(
        self,
        ctx: commands.Context,
        number1: int,
        number2: int,
        number3: int,
        number4: int,
        number5: int,
    ):
        if not self.is_staff(ctx.author):
            return await ctx.send("🚫 **Staff only.**")

        winning_numbers = self.normalize_numbers((number1, number2, number3, number4, number5))
        if winning_numbers is None:
            return await ctx.send(
                "❌ The winning draw must contain **5 different whole numbers from 1 to 99**."
            )

        now = self.eastern_now().isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            await self.ensure_schema(db)
            await db.execute("BEGIN IMMEDIATE")
            cycle = await self.get_active_cycle(db)
            if not cycle:
                await db.rollback()
                return await ctx.send("🎟️ **There isn't an open lottery to draw.**")

            cycle_id = cycle[0]
            async with db.execute(
                """
                SELECT ticket_id, user_id, n1, n2, n3, n4, n5
                FROM lottery_tickets
                WHERE cycle_id = ?
                ORDER BY ticket_id
                """,
                (cycle_id,),
            ) as cursor:
                tickets = list(await cursor.fetchall())

            winning_set = set(winning_numbers)
            payouts_by_user = defaultdict(int)
            tier_counts = Counter()
            winning_ticket_rows = []

            for ticket_id, user_id, n1, n2, n3, n4, n5 in tickets:
                numbers = (n1, n2, n3, n4, n5)
                matches = len(winning_set.intersection(numbers))
                payout = self.PRIZES.get(matches, 0)
                if payout:
                    payouts_by_user[user_id] += payout
                    tier_counts[matches] += 1
                    winning_ticket_rows.append({
                        "ticket_id": ticket_id,
                        "user_id": user_id,
                        "matches": matches,
                        "payout": payout,
                    })

            for user_id, payout in payouts_by_user.items():
                await db.execute(
                    "UPDATE users SET stardust = stardust + ? WHERE user_id = ?",
                    (payout, user_id),
                )

            results = {
                "tier_counts": {str(key): value for key, value in tier_counts.items()},
                "winning_tickets": winning_ticket_rows,
            }

            await db.execute(
                """
                UPDATE lottery_cycles
                SET status = 'drawn', drawn_at = ?, drawn_by = ?,
                    winning_numbers = ?, tickets_sold = ?, total_payout = ?, results_json = ?
                WHERE cycle_id = ?
                """,
                (
                    now,
                    ctx.author.id,
                    json.dumps(winning_numbers),
                    len(tickets),
                    sum(payouts_by_user.values()),
                    json.dumps(results),
                    cycle_id,
                ),
            )

            # Tickets are intentionally deleted after the cycle is resolved.
            # The cycle row retains the winning numbers and payout history.
            await db.execute("DELETE FROM lottery_tickets WHERE cycle_id = ?", (cycle_id,))
            await db.commit()

        total_payout = sum(payouts_by_user.values())
        winners = len(payouts_by_user)
        tier_lines = [
            f"{matches}/5: **{count:,} winning ticket{'s' if count != 1 else ''}** — **{self.PRIZES[matches]:,} Stardust each**"
            for matches, count in sorted(tier_counts.items(), reverse=True)
        ]
        if not tier_lines:
            tier_lines = ["No tickets matched at least one number."]

        embed = discord.Embed(
            title=f"🎉 Lottery Cycle #{cycle_id} — DRAWN!",
            description=(
                f"🎱 **Winning numbers:** {self.format_numbers(winning_numbers)}\n\n"
                f"🎟️ Tickets drawn: **{len(tickets):,}**\n"
                f"🏆 Winning users: **{winners:,}**\n"
                f"💰 Total Stardust paid: **{total_payout:,}**\n\n"
                + "\n".join(tier_lines)
            ),
            color=discord.Color.from_rgb(0, 229, 255),
        )
        embed.set_footer(text="All tickets from this cycle have been cleared. Staff can open the next monthly cycle when ready.")
        await ctx.send(embed=embed)

    @lottery.command(name="cancel", description="Cancel the active lottery and delete its tickets. Staff only.")
    async def lottery_cancel(self, ctx: commands.Context):
        if not self.is_staff(ctx.author):
            return await ctx.send("🚫 **Staff only.**")

        async with aiosqlite.connect(self.db_path) as db:
            await self.ensure_schema(db)
            await db.execute("BEGIN IMMEDIATE")
            cycle = await self.get_active_cycle(db)
            if not cycle:
                await db.rollback()
                return await ctx.send("🎟️ **There isn't an open lottery to cancel.**")

            cycle_id = cycle[0]
            async with db.execute(
                "SELECT COUNT(*) FROM lottery_tickets WHERE cycle_id = ?",
                (cycle_id,),
            ) as cursor:
                row = await cursor.fetchone()
                ticket_count = row[0] if row else 0

            await db.execute(
                "UPDATE lottery_cycles SET status = 'cancelled', drawn_by = ?, drawn_at = ? WHERE cycle_id = ?",
                (ctx.author.id, self.eastern_now().isoformat(), cycle_id),
            )
            await db.execute("DELETE FROM lottery_tickets WHERE cycle_id = ?", (cycle_id,))
            await db.commit()

        await ctx.send(
            f"🛑 **Lottery Cycle #{cycle_id} cancelled.** {ticket_count:,} ticket{'s' if ticket_count != 1 else ''} cleared."
        )


async def setup(bot):
    await bot.add_cog(Lottery(bot))
