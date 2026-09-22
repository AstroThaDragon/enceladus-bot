# © 2026 The Cosmic Lair & AstroThaDragon. All Rights Reserved.
# Unauthorized use of this code is prohibited.

import random
import asyncio
from typing import Any, Callable

import aiosqlite
import discord
from discord.ext import commands
from discord import app_commands



class BlackjackView(discord.ui.View):
    """Interactive blackjack table for one player."""

    def __init__(self, cog, ctx, bet, deck, player, dealer):
        super().__init__(timeout=90)
        self.cog = cog
        self.ctx = ctx
        user = getattr(ctx, "author", None) or getattr(ctx, "user", None)
        self.user_id = user.id if user is not None else 0
        self.display_name = user.display_name if user is not None else "Explorer"
        self.bet = bet
        self.deck = deck
        self.player = player
        self.dealer = dealer
        self.finished = False
        self.doubled = False
        self.payout_multiplier = 1.0
        self.trickster_active = False
        self.action_lock = asyncio.Lock()
        self.message: discord.Message | None = None

    def hand_value(self, hand):
        total = sum(10 if card > 10 else card for card in hand)
        aces = hand.count(11)
        while total > 21 and aces:
            total -= 10
            aces -= 1
        return total

    def card_text(self, card):
        names = {11: "A", 10: "10", 9: "9", 8: "8", 7: "7", 6: "6", 5: "5", 4: "4", 3: "3", 2: "2"}
        return names[card]

    def hand_text(self, hand):
        return " ".join(self.card_text(card) for card in hand)

    def build_embed(self, finished=False, status=None, show_entry_fee=True):
        player_total = self.hand_value(self.player)
        dealer_text = self.hand_text(self.dealer) if finished else f"{self.card_text(self.dealer[0])} 🂠"
        dealer_total = self.hand_value(self.dealer) if finished else "?"

        description = (
            f"**Your hand:** {self.hand_text(self.player)}  → **{player_total}**\n"
            f"**Dealer:** {dealer_text}  → **{dealer_total}**\n\n"
            f"💰 Bet: **{self.bet:,} Stardust**"
        )

        if show_entry_fee and not finished:
            description += "\n🪙 Entry fee: **1 Arcade Token**"

        if status:
            description += f"\n\n{status}"
        else:
            description += "\n\nChoose **Hit**, **Stand**, or **Double Down**."

        embed = discord.Embed(
            title=f"🃏 Enceladus Blackjack — {self.display_name}",
            description=description,
            color=discord.Color.from_rgb(0, 229, 255)
        )
        return embed

    async def interaction_check(self, interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "⚠️ This blackjack table belongs to another player.", ephemeral=True
            )
            return False
        return True

    async def finish(self, outcome, payout):
        if self.finished:
            return
        self.finished = True
        self.clear_items()

        # The Arcade Token entry token and initial Stardust wager were already
        # removed when the hand opened. Normal outcomes only add the payout.
        # A timeout additionally refunds the 1 Arcade Token entry token.
        db_path = self.cog.get_db_path()
        async with aiosqlite.connect(db_path) as db:
            await db.execute("BEGIN IMMEDIATE")
            async with db.execute(
                "SELECT stardust FROM users WHERE user_id = ?",
                (self.user_id,)
            ) as cursor:
                row = await cursor.fetchone()

            if row is None:
                await db.rollback()
                return

            async with db.execute(
                "SELECT COALESCE(arcade_coins, 0) FROM users WHERE user_id = ?",
                (self.user_id,)
            ) as cursor:
                token_row = await cursor.fetchone()

            balance = row[0] or 0
            arcade_coins = (token_row[0] or 0) if token_row else 0
            adjusted_payout = payout if outcome == "timeout" else int(payout * self.payout_multiplier)
            new_balance = balance + adjusted_payout

            # Cosmic Trickster: the initial entry token was already consumed.
            # A win refunds one bonus token; a loss/bust consumes one additional
            # token. Timeouts are handled as a normal refund.
            if outcome == "timeout":
                token_change = 1
            elif self.trickster_active and outcome in {"win", "blackjack"}:
                token_change = 1
            elif self.trickster_active and outcome in {"loss", "bust"}:
                token_change = -1
            else:
                token_change = 0

            new_arcade_coins = max(0, min(1000, arcade_coins + token_change))
            tokens_spent = 0 if outcome == "timeout" else (2 if self.trickster_active and outcome in {"loss", "bust"} else 1)

            await db.execute(
                "UPDATE users SET stardust = ?, arcade_coins = ? WHERE user_id = ?",
                (new_balance, new_arcade_coins, self.user_id)
            )
            await self.cog.record_stats(
                db,
                self.user_id,
                "blackjack",
                outcome=outcome,
                stardust_wagered=self.bet,
                stardust_returned=adjusted_payout,
                arcade_coins_spent=tokens_spent,
            )
            await db.commit()

        outcome_text = {
            "blackjack": "🃏 **BLACKJACK!**",
            "win": "🎉 **You win!**",
            "push": "🤝 **Push.**",
            "bust": "💥 **Bust!**",
            "loss": "💀 **Dealer wins.**",
            "timeout": "⏰ **Table closed.** Your unfinished hand is refunded.",
        }[outcome]

        result_summary = self.cog.format_game_result(self.bet, adjusted_payout)
        outcome_text = f"{outcome_text}\n{result_summary}"
        if outcome == "timeout":
            outcome_text += "\n🪙 Your **1 Arcade Token** entry token is also returned."
        elif self.trickster_active and outcome in {"win", "blackjack"}:
            outcome_text += "\n🃏 **Cosmic Trickster:** +1 Arcade Token for winning!"
        elif self.trickster_active and outcome in {"loss", "bust"}:
            outcome_text += "\n🃏 **Cosmic Trickster:** The loss consumed an extra Arcade Token."

        embed = self.build_embed(finished=True, status=outcome_text)
        if outcome == "timeout":
            embed.set_footer(
                text=f"Stardust: {new_balance:,} • Arcade Tokens: {new_arcade_coins:,}"
            )
        else:
            embed.set_footer(text=f"Stardust: {new_balance:,}")
        message = self.message
        if message is not None:
            await message.edit(embed=embed, view=self)

    async def on_timeout(self):
        if not self.finished:
            await self.finish("timeout", self.bet)

    async def hit_callback(self, interaction):
        async with self.action_lock:
            if self.finished or self.doubled:
                return
            await interaction.response.defer()
            self.player.append(self.deck.pop())
        # Double Down is only available before taking a regular hit.
        for child in self.children:
            if isinstance(child, discord.ui.Button) and child.label == "Double Down":
                child.disabled = True
                break
        total = self.hand_value(self.player)
        if total > 21:
            await self.finish("bust", 0)
            return
        if total == 21:
            await self.dealer_turn()
            return
        message = self.message
        if message is not None:
            await message.edit(
                embed=self.build_embed(show_entry_fee=False),
                view=self
            )

    async def dealer_turn(self):
        while self.hand_value(self.dealer) < 17:
            self.dealer.append(self.deck.pop())
        player_total = self.hand_value(self.player)
        dealer_total = self.hand_value(self.dealer)

        if dealer_total > 21 or player_total > dealer_total:
            await self.finish("win", self.bet * 2)
        elif player_total == dealer_total:
            await self.finish("push", self.bet)
        else:
            await self.finish("loss", 0)

    async def stand_callback(self, interaction):
        async with self.action_lock:
            if self.finished:
                return
            await interaction.response.defer()
            await self.dealer_turn()

    async def double_callback(self, interaction):
        async with self.action_lock:
            # Double Down is only available once, before a regular hit.
            if self.doubled or self.finished:
                return

            db_path = self.cog.get_db_path()
            async with aiosqlite.connect(db_path) as db:
                await db.execute("BEGIN IMMEDIATE")
                balance = await self.cog.get_stardust(db, self.user_id)
                if balance is None:
                    await db.rollback()
                    return await interaction.response.send_message(
                        "❌ Your station profile could not be loaded.", ephemeral=True
                    )

                if balance < self.bet:
                    await db.rollback()
                    return await interaction.response.send_message(
                        f"💸 **Not enough Stardust to double down!** You need **{self.bet:,}** more Stardust, "
                        f"but only have **{balance:,}**.", ephemeral=True
                    )

                new_balance = balance - self.bet
                await db.execute(
                    "UPDATE users SET stardust = ? WHERE user_id = ?",
                    (new_balance, self.user_id)
                )
                await db.commit()

            self.bet *= 2
            self.doubled = True
            self.clear_items()
            self.player.append(self.deck.pop())
            total = self.hand_value(self.player)

            await interaction.response.defer()
            if total > 21:
                await self.finish("bust", 0)
            else:
                await self.dealer_turn()

    @discord.ui.button(label="Hit", emoji="🃏", style=discord.ButtonStyle.primary)
    async def hit(self, interaction, button):
        await self.hit_callback(interaction)

    @discord.ui.button(label="Stand", emoji="✋", style=discord.ButtonStyle.secondary)
    async def stand(self, interaction, button):
        await self.stand_callback(interaction)

    @discord.ui.button(label="Double Down", emoji="💰", style=discord.ButtonStyle.success)
    async def double_down(self, interaction, button):
        await self.double_callback(interaction)


class TriviaView(discord.ui.View):
    """One-question, multiple-choice space trivia table."""

    def __init__(self, cog, ctx, question, options, answer, reward):
        super().__init__(timeout=45)
        self.cog = cog
        self.ctx = ctx
        user = getattr(ctx, "author", None) or getattr(ctx, "user", None)
        self.user_id = user.id if user is not None else 0
        self.display_name = user.display_name if user is not None else "Explorer"
        self.question = question
        self.options = options
        self.answer = answer
        self.reward = reward
        self.message: discord.Message | None = None
        self.finished = False

    async def interaction_check(self, interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "⚠️ This trivia terminal belongs to another explorer.", ephemeral=True
            )
            return False
        return True

    async def answer_question(self, interaction, choice):
        if self.finished:
            return
        self.finished = True
        self.clear_items()
        correct = choice == self.answer
        payout = self.reward if correct else 0

        db_path = self.cog.get_db_path()
        async with aiosqlite.connect(db_path) as db:
            await db.execute("BEGIN IMMEDIATE")
            balance = await self.cog.get_stardust(db, self.user_id)
            if balance is None:
                balance = 0
            new_balance = balance + payout
            await db.execute(
                "UPDATE users SET stardust = ? WHERE user_id = ?",
                (new_balance, self.user_id)
            )
            await self.cog.record_stats(
                db,
                self.user_id,
                "trivia",
                outcome="win" if correct else "loss",
                stardust_returned=payout,
                arcade_coins_spent=1,
            )
            await db.commit()

        if correct:
            result = "🧠 **Correct!**"
        else:
            result = f"❌ **Incorrect.** The correct answer was **{self.options[self.answer]}**."

        result_summary = self.cog.format_game_result(0, payout)

        embed = discord.Embed(
            title=f"🚀 Enceladus Space Trivia — {self.display_name}",
            description=f"**{self.question}**\n\n{result}\n{result_summary}",
            color=discord.Color.from_rgb(0, 229, 255)
        )
        embed.set_footer(text=f"Stardust: {new_balance:,}")
        message = self.message
        if message is not None:
            await message.edit(embed=embed, view=self)

    async def on_timeout(self):
        if self.finished:
            return
        self.finished = True
        self.clear_items()
        db_path = self.cog.get_db_path()
        async with aiosqlite.connect(db_path) as db:
            await db.execute("BEGIN IMMEDIATE")
            await self.cog.record_stats(
                db, self.user_id, "trivia", outcome="timeout",
                arcade_coins_spent=1,
            )
            await db.commit()
        result_summary = self.cog.format_game_result(0, 0)

        embed = discord.Embed(
            title=f"🚀 Enceladus Space Trivia — {self.display_name}",
            description=(
                f"**{self.question}**\n\n"
                f"⏰ **Time's up!** The correct answer was **{self.options[self.answer]}**.\n"
                f"{result_summary}"
            ),
            color=discord.Color.from_rgb(0, 229, 255)
        )
        message = self.message
        if message is not None:
            await message.edit(embed=embed, view=self)



class RouletteBetModal(discord.ui.Modal):
    def __init__(self, view):
        super().__init__(title="🎡 Roulette — Place Your Bet")
        self.view = view
        self.bet_input = discord.ui.TextInput(
            label="Stardust Bet",
            placeholder="Enter 1-5000 Stardust",
            required=True,
            max_length=6,
        )
        self.choice_input = discord.ui.TextInput(
            label="Bet",
            placeholder="red, black, odd, even, 0-36",
            required=True,
            max_length=5,
        )
        self.add_item(self.bet_input)
        self.add_item(self.choice_input)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            bet = int(str(self.bet_input.value).replace(",", "").strip())
        except ValueError:
            return await interaction.response.send_message(
                "❌ Enter a whole-number Stardust bet.", ephemeral=True
            )

        choice = str(self.choice_input.value).strip().lower()
        if choice not in {"red", "black", "odd", "even"}:
            try:
                number = int(choice)
            except ValueError:
                return await interaction.response.send_message(
                    "❌ Bet on `red`, `black`, `odd`, `even`, or a number from `0` to `36`.",
                    ephemeral=True,
                )
            if not 0 <= number <= 36:
                return await interaction.response.send_message(
                    "❌ Roulette numbers must be between `0` and `36`.", ephemeral=True
                )
            choice = str(number)

        await interaction.response.defer()
        await self.view.cog.play_roulette(interaction, bet, choice)


class MinigameBetModal(discord.ui.Modal):
    def __init__(self, view, game):
        super().__init__(title={
            "slots": "🎰 Slots — Place Your Bet",
            "blackjack": "🃏 Blackjack — Place Your Bet",
        }[game])
        self.view = view
        self.game = game
        self.bet_input = discord.ui.TextInput(
            label="Stardust Bet",
            placeholder="Enter 1-5000 Stardust",
            required=True,
            max_length=6,
        )
        self.add_item(self.bet_input)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            bet = int(str(self.bet_input.value).replace(",", "").strip())
        except ValueError:
            return await interaction.response.send_message(
                "❌ Enter a whole-number Stardust bet.", ephemeral=True
            )

        await interaction.response.defer()
        if self.game == "slots":
            await self.view.cog.play_slots(interaction, bet)
        else:
            await self.view.cog.play_blackjack(interaction, bet)


class DiceBetModal(discord.ui.Modal):
    def __init__(self, view):
        super().__init__(title="🎲 Dice — Place Your Bet")
        self.view = view
        self.bet_input = discord.ui.TextInput(
            label="Stardust Bet",
            placeholder="Enter 1-5000 Stardust",
            required=True,
            max_length=6,
        )
        self.choice_input = discord.ui.TextInput(
            label="Bet Type",
            placeholder="low, seven, or high",
            required=True,
            max_length=5,
        )
        self.add_item(self.bet_input)
        self.add_item(self.choice_input)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            bet = int(str(self.bet_input.value).replace(",", "").strip())
        except ValueError:
            return await interaction.response.send_message(
                "❌ Enter a whole-number Stardust bet.", ephemeral=True
            )

        choice = str(self.choice_input.value).strip().lower()
        aliases = {"l": "low", "s": "seven", "h": "high", "7": "seven"}
        choice = aliases.get(choice, choice)
        if choice not in {"low", "seven", "high"}:
            return await interaction.response.send_message(
                "❌ Bet type must be `low`, `seven`, or `high`.", ephemeral=True
            )

        await interaction.response.defer()
        await self.view.cog.play_dice(interaction, bet, choice)


class ArcadeCoinExchangeModal(discord.ui.Modal):
    def __init__(self, view):
        super().__init__(title="🪙 Buy Arcade Tokens")
        self.view = view
        self.amount_input = discord.ui.TextInput(
            label="Arcade Tokens to Buy",
            placeholder="1-1000 Arcade Tokens (100 Stardust each)",
            required=True,
            max_length=4,
        )
        self.add_item(self.amount_input)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            coins = int(str(self.amount_input.value).replace(",", "").strip())
        except ValueError:
            return await interaction.response.send_message(
                "❌ Enter a whole number of Arcade Tokens.", ephemeral=True
            )

        if coins < 1 or coins > 1000:
            return await interaction.response.send_message(
                "❌ You can exchange between **1 and 1,000 Arcade Tokens** at a time.",
                ephemeral=True,
            )

        db_path = self.view.cog.get_db_path()
        cost = coins * self.view.cog.ARCADE_COIN_COST

        async with aiosqlite.connect(db_path) as db:
            await db.execute("BEGIN IMMEDIATE")
            stardust = await self.view.cog.get_stardust(db, interaction.user.id)
            if stardust is None:
                await db.rollback()
                return await interaction.response.send_message(
                    "❌ You don't have an active station profile yet. Run `/profile`, `/scavenge` or `/mine` first!",
                    ephemeral=True,
                )

            if stardust < cost:
                await db.rollback()
                await interaction.response.send_message(
                    f"💸 **Not enough Stardust!** You need **{cost:,}** Stardust for **{coins:,} Arcade Tokens**, "
                    f"but only have **{stardust:,}**.",
                    ephemeral=True,
                )
                await self.view.reset_menu()
                return

            async with db.execute(
                "SELECT COALESCE(arcade_coins, 0) FROM users WHERE user_id = ?",
                (interaction.user.id,),
            ) as cursor:
                row = await cursor.fetchone()

            current_coins = (row[0] or 0) if row else 0
            if current_coins + coins > 1000:
                await db.rollback()
                return await interaction.response.send_message(
                    f"❌ You can hold at most **1,000 Arcade Tokens**. You currently have **{current_coins:,}**.",
                    ephemeral=True,
                )

            new_stardust = stardust - cost
            new_coins = current_coins + coins

            await db.execute(
                "UPDATE users SET stardust = ?, arcade_coins = ? WHERE user_id = ?",
                (new_stardust, new_coins, interaction.user.id),
            )
            await db.commit()

        embed = discord.Embed(
            title=f"🪙 Arcade Token Exchange — {interaction.user.display_name}",
            description=(
                f"You exchanged **{cost:,} Stardust** for **{coins:,} Arcade Tokens**.\n\n"
                f"🪙 Arcade Tokens: **{new_coins:,}**\n"
                f"💰 Stardust remaining: **{new_stardust:,}**"
            ),
            color=discord.Color.from_rgb(0, 229, 255),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        await self.view.reset_menu()

class MinigameSelect(discord.ui.Select):
    def __init__(self, view):
        self.menu_view = view
        options = [
            discord.SelectOption(
                label="Slots", emoji="🎰", value="slots",
                description="Spin the station reels. The house has an edge."
            ),
            discord.SelectOption(
                label="Dice", emoji="🎲", value="dice",
                description="Bet low, seven, or high against the house."
            ),
            discord.SelectOption(
                label="Blackjack", emoji="🃏", value="blackjack",
                description="Play Hit, Stand, or Double Down."
            ),
            discord.SelectOption(
                label="Space Trivia", emoji="🚀", value="trivia",
                description="Spend 1 Arcade Token and answer for Stardust."
            ),
            discord.SelectOption(
                label="Roulette", emoji="🎡", value="roulette",
                description="Bet on colors, parity, or a single number."
            ),
            discord.SelectOption(
                label="Arcade Token Exchange", emoji="🪙", value="exchange",
                description="Convert Stardust into Arcade Tokens."
            ),
            discord.SelectOption(
                label="My Stats", emoji="📊", value="stats",
                description="View your minigame history and performance."
            ),
        ]
        super().__init__(
            placeholder="🎮 Choose a minigame...",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.menu_view.user_id:
            return await interaction.response.send_message(
                "⚠️ This minigame terminal belongs to another player.", ephemeral=True
            )

        game = self.values[0]
        if game == "slots":
            return await interaction.response.send_modal(
                MinigameBetModal(self.menu_view, "slots")
            )
        if game == "blackjack":
            return await interaction.response.send_modal(
                MinigameBetModal(self.menu_view, "blackjack")
            )
        if game == "dice":
            return await interaction.response.send_modal(
                DiceBetModal(self.menu_view)
            )
        if game == "roulette":
            return await interaction.response.send_modal(
                RouletteBetModal(self.menu_view)
            )
        if game == "exchange":
            return await interaction.response.send_modal(
                ArcadeCoinExchangeModal(self.menu_view)
            )
        if game == "stats":
            await interaction.response.defer(ephemeral=True)
            return await self.menu_view.cog.send_stats(interaction, ephemeral=True)
        return await self.menu_view.cog.send_trivia(interaction)


class MinigamesView(discord.ui.View):
    def __init__(self, cog, user_id):
        super().__init__(timeout=300)
        self.cog = cog
        self.user_id = user_id
        self.message: discord.Message | None = None
        self.add_item(MinigameSelect(self))

    async def reset_menu(self):
        if self.message:
            new_view = MinigamesView(self.cog, self.user_id)
            new_view.message = self.message
            await self.message.edit(view=new_view)
            self.stop()



class Minigames(commands.Cog):
    """Casino-style station minigames using Arcade Tokens."""

    ARCADE_COIN_COST = 100  # Stardust per Arcade Token.
    MIN_BET = 1
    MAX_BET = 5000
    SLOT_MAX_BET = 1500

    SLOT_SYMBOLS = ["🌌", "⭐", "🌙", "🪐", "☄️", "💎"]

    # These are total-return multipliers. The wager itself is included in a win.
    # With six equally likely symbols, this gives the slots a modest house edge.
    SLOT_PAYOUTS = {
        3: 4,   # Three matching symbols.
        2: 2,   # Two matching symbols.
    }

    DICE_PAYOUTS = {
        "low": 2,       # 2-6: 2x total return, 41.7% hit chance.
        "high": 2,      # 8-12: 2x total return, 41.7% hit chance.
        "seven": 3,     # Exact 7: 5x total return, 16.7% hit chance.
    }

    TRIVIA_QUESTIONS = [
        ('Which planet has the shortest day in the Solar System?', ['Jupiter', 'Mercury', 'Mars', 'Neptune'], 0),
        ('Which moon is famous for its thick nitrogen atmosphere and methane lakes?', ['Europa', 'Titan', 'Io', 'Triton'], 1),
        ('What is the largest volcano in the Solar System?', ['Olympus Mons', 'Mauna Kea', 'Elysium Mons', 'Maxwell Montes'], 0),
        ('Which planet is known for having the strongest winds in the Solar System?', ['Saturn', 'Uranus', 'Neptune', 'Venus'], 2),
        ('What is the primary component of the Sun?', ['Oxygen', 'Hydrogen', 'Helium', 'Carbon'], 1),
        ('Which spacecraft was the first to enter interstellar space?', ['Voyager 1', 'Voyager 2', 'New Horizons', 'Pioneer 10'], 0),
        ('Which planet has the Great Red Spot?', ['Jupiter', 'Saturn', 'Neptune', 'Mars'], 0),
        ("What is the name of Saturn's largest moon?", ['Rhea', 'Titan', 'Enceladus', 'Iapetus'], 1),
        ('Which dwarf planet is located in the Kuiper Belt?', ['Ceres', 'Vesta', 'Pluto', 'Io'], 2),
        ('What galaxy contains our Solar System?', ['Andromeda', 'Triangulum', 'Whirlpool', 'Milky Way'], 3),
        ('Which planet rotates on its side with an axial tilt of about 98 degrees?', ['Uranus', 'Venus', 'Saturn', 'Mercury'], 0),
        ("What is the name of the boundary beyond which the Sun's solar wind is no longer dominant?", ['Magnetopause', 'Heliopause', 'Photosphere', 'Roche limit'], 1),
        ('What is the largest planet in our Solar System?', ['Saturn', 'Jupiter', 'Neptune', 'Earth'], 1),
        ('Which planet is closest to the Sun?', ['Venus', 'Earth', 'Mars', 'Mercury'], 3),
        ('Which planet is known for its prominent ring system?', ['Uranus', 'Saturn', 'Neptune', 'Jupiter'], 1),
        ("What is the name of Earth's natural satellite?", ['Europa', 'Phobos', 'The Moon', 'Titan'], 2),
        ('Which planet is often called the Red Planet?', ['Venus', 'Mars', 'Jupiter', 'Mercury'], 1),
        ('Which planet is the hottest in our Solar System?', ['Mercury', 'Mars', 'Jupiter', 'Venus'], 3),
        ('What type of object is the Sun?', ['Comet', 'Asteroid', 'Star', 'Planet'], 2),
        ('Which planet has the Great Red Spot?', ['Neptune', 'Mars', 'Jupiter', 'Saturn'], 2),
        ('What is the smallest planet in our Solar System?', ['Earth', 'Venus', 'Mercury', 'Mars'], 2),
        ('Which planet is famous for rotating on its side?', ['Saturn', 'Uranus', 'Venus', 'Neptune'], 1),
        ('Which planet is farthest from the Sun?', ['Jupiter', 'Saturn', 'Neptune', 'Uranus'], 2),
        ('What is the asteroid belt primarily located between?', ['Earth and Mars', 'Jupiter and Saturn', 'Venus and Earth', 'Mars and Jupiter'], 3),
        ('Which planet has the shortest year?', ['Venus', 'Mercury', 'Mars', 'Earth'], 1),
        ('Which planet has the longest day, measured by one rotation?', ['Mercury', 'Jupiter', 'Venus', 'Mars'], 2),
        ("What is a space rock called when it survives passage through Earth's atmosphere and reaches the ground?", ['Asteroid', 'Meteor', 'Comet', 'Meteorite'], 3),
        ("What is the glowing streak produced when a space rock enters Earth's atmosphere?", ['Meteorite', 'Meteor', 'Asteroid', 'Moon'], 1),
        ('What is the icy object that develops a tail when it approaches the Sun?', ['Planet', 'Comet', 'Asteroid', 'Meteorite'], 1),
        ('Which moon is the largest moon in the Solar System?', ['Titan', 'Europa', 'Callisto', 'Ganymede'], 3),
        ('Which moon is famous for its subsurface ocean and icy surface?', ['Europa', 'Titan', 'Triton', 'Phobos'], 0),
        ('Which moon is known for its thick atmosphere and methane lakes?', ['Io', 'Europa', 'Titan', 'Ganymede'], 2),
        ('Which moon of Mars is the larger of the two?', ['Deimos', 'Phobos', 'Triton', 'Titan'], 1),
        ('Which planet has the moon Triton?', ['Saturn', 'Jupiter', 'Neptune', 'Uranus'], 2),
        ('Which moon of Jupiter is known for intense volcanic activity?', ['Europa', 'Callisto', 'Ganymede', 'Io'], 3),
        ('What is the name of the region beyond Neptune containing many icy bodies?', ['Van Allen Belt', 'Kuiper Belt', 'Asteroid Belt', 'Oort Belt'], 1),
        ('What is the enormous, distant cloud of icy objects thought to surround the Solar System?', ['Heliosphere', 'Asteroid Belt', 'Oort Cloud', 'Kuiper Belt'], 2),
        ('What force keeps planets in orbit around the Sun?', ['Gravity', 'Magnetism', 'Electricity', 'Friction'], 0),
        ("What is the name of the boundary where the Sun's solar wind meets interstellar space?", ['Photosphere', 'Magnetopause', 'Event Horizon', 'Heliopause'], 3),
        ('What is the visible surface of the Sun called?', ['Corona', 'Photosphere', 'Core', 'Chromosphere'], 1),
        ('Which layer of the Sun is its outer atmosphere?', ['Photosphere', 'Radiative Zone', 'Corona', 'Core'], 2),
        ('Where does nuclear fusion occur inside the Sun?', ['Chromosphere', 'Core', 'Corona', 'Photosphere'], 1),
        ('What element makes up most of the Sun?', ['Carbon', 'Iron', 'Oxygen', 'Hydrogen'], 3),
        ('What is a supernova?', ['A type of comet', 'A galaxy collision', 'A powerful stellar explosion', 'A newborn planet'], 2),
        ('What remains after a massive star explodes as a supernova, if its core collapses into an extremely dense object?', ['Red giant', 'Neutron star or black hole', 'Gas giant', 'White dwarf'], 1),
        ('What type of star is the Sun classified as?', ['White dwarf', 'Red giant', 'Neutron star', 'G-type main-sequence star'], 3),
        ('What is a white dwarf?', ['A giant planet', 'A type of galaxy', 'The dense remnant of a low- or medium-mass star', 'A newborn star'], 2),
        ('What is a neutron star?', ['A type of planet', 'An extremely dense stellar remnant', 'A comet nucleus', 'A failed galaxy'], 1),
        ('What is a pulsar?', ['A type of asteroid', 'A solar flare', 'A young galaxy', 'A rapidly rotating neutron star that emits beams of radiation'], 3),
        ('What is the boundary around a black hole beyond which light cannot escape?', ['Accretion disk', 'Photosphere', 'Event horizon', 'Heliopause'], 2),
        ('What is an accretion disk?', ['A cloud of frozen comets', "A planet's ring system", 'A disk of matter spiraling around a massive object', "A galaxy's outer edge"], 2),
        ('What galaxy contains our Solar System?', ['Whirlpool', 'Milky Way', 'Andromeda', 'Triangulum'], 1),
        ('What type of galaxy is the Milky Way?', ['Irregular galaxy', 'Ring galaxy', 'Elliptical galaxy', 'Barred spiral galaxy'], 3),
        ('Which galaxy is expected to eventually interact and merge with the Milky Way?', ['Whirlpool', 'Sombrero', 'Andromeda', 'Triangulum'], 2),
        ('What is a galaxy?', ['A type of black hole', 'A huge collection of stars, gas, dust, and dark matter', 'A cluster of planets only', 'A single enormous star'], 1),
        ('What is the name of the galaxy nearest to the Milky Way among the major spiral galaxies?', ['Cartwheel Galaxy', 'Whirlpool Galaxy', 'Sombrero Galaxy', 'Andromeda Galaxy'], 3),
        ('What does NASA stand for?', ['National Aeronautics and Space Administration', 'National Aerospace Science Association', 'North American Space Administration', 'National Astronomy and Space Agency'], 0),
        ('Which spacecraft was the first human-made object to enter interstellar space?', ['Pioneer 10', 'New Horizons', 'Voyager 1', 'Apollo 11'], 2),
        ('Which mission first landed humans on the Moon?', ['Apollo 13', 'Gemini 4', 'Apollo 8', 'Apollo 11'], 3),
        ('What was the first artificial satellite launched into space?', ['Explorer 1', 'Sputnik 1', 'Apollo 1', 'Vostok 1'], 1),
        ('Which spacecraft explored Pluto during its historic 2015 flyby?', ['Juno', 'Cassini', 'Voyager 2', 'New Horizons'], 3),
        ('Which spacecraft orbited Saturn and studied the planet and its moons for many years?', ['Cassini', 'Galileo', 'Magellan', 'Juno'], 0),
    ]

    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        """Add the arcade currency column without requiring a database reset."""
        db_path = self.get_db_path()
        async with aiosqlite.connect(db_path) as db:
            async with db.execute("PRAGMA table_info(users)") as cursor:
                columns = {row[1] for row in await cursor.fetchall()}

            if "arcade_coins" not in columns:
                await db.execute(
                    "ALTER TABLE users ADD COLUMN arcade_coins INTEGER DEFAULT 0"
                )

            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS minigame_stats (
                    user_id INTEGER NOT NULL,
                    game TEXT NOT NULL,
                    games_played INTEGER NOT NULL DEFAULT 0,
                    wins INTEGER NOT NULL DEFAULT 0,
                    losses INTEGER NOT NULL DEFAULT 0,
                    pushes INTEGER NOT NULL DEFAULT 0,
                    timeouts INTEGER NOT NULL DEFAULT 0,
                    stardust_wagered INTEGER NOT NULL DEFAULT 0,
                    stardust_returned INTEGER NOT NULL DEFAULT 0,
                    net_stardust INTEGER NOT NULL DEFAULT 0,
                    arcade_coins_spent INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY (user_id, game)
                )
                """
            )

            # One-time migration: legacy Arcade Tokens were stored as inventory rows.
            # Preserve those balances in the new users.arcade_coins column, then remove
            # the legacy rows so there is only one source of truth. If a balance already
            # exists in users.arcade_coins, it came from an earlier migration and must not
            # be added again.
            async with db.execute(
                """
                SELECT i.user_id, i.quantity, COALESCE(u.arcade_coins, 0)
                FROM inventory AS i
                INNER JOIN users AS u ON u.user_id = i.user_id
                WHERE i.item_id = 'arcade_token'
                """
            ) as cursor:
                legacy_tokens = await cursor.fetchall()

            for legacy_user_id, quantity, current_coins in legacy_tokens:
                if (current_coins or 0) <= 0:
                    migrated_coins = min(1000, max(0, quantity or 0))
                    await db.execute(
                        "UPDATE users SET arcade_coins = ? WHERE user_id = ?",
                        (migrated_coins, legacy_user_id),
                    )

            if legacy_tokens:
                await db.execute(
                    "DELETE FROM inventory WHERE item_id = 'arcade_token'"
                )

            await db.commit()

    def get_db_path(self):
        from database import ECONOMY_DB_NAME
        return ECONOMY_DB_NAME

    async def get_balance(self, db, user_id) -> int | None:
        """Return the user's Arcade Token balance from users.arcade_coins."""
        async with db.execute(
            "SELECT COALESCE(arcade_coins, 0) FROM users WHERE user_id = ?",
            (user_id,)
        ) as cursor:
            row = await cursor.fetchone()

        return (row[0] or 0) if row else None

    async def get_stardust(self, db, user_id):
        async with db.execute(
            "SELECT stardust FROM users WHERE user_id = ?",
            (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
        return (row[0] or 0) if row else None

    async def change_balance(self, user_id, bet, game_callback: Callable[[], dict[str, Any]], game: str) -> tuple[dict[str, Any] | None, int | None]:
        """Consume one Arcade Token and resolve one Stardust wager atomically."""
        db_path = self.get_db_path()

        async with aiosqlite.connect(db_path) as db:
            await db.execute("BEGIN IMMEDIATE")
            async with db.execute(
                "SELECT stardust FROM users WHERE user_id = ?",
                (user_id,)
            ) as cursor:
                row = await cursor.fetchone()

            async with db.execute(
                "SELECT COALESCE(arcade_coins, 0) FROM users WHERE user_id = ?",
                (user_id,)
            ) as cursor:
                token_row = await cursor.fetchone()

            if not row:
                await db.rollback()
                return None, None

            arcade_coins = (token_row[0] or 0) if token_row else 0
            stardust = row[0] or 0

            from pets import get_active_pet_effects
            pet_effects = await get_active_pet_effects(db, user_id)
            trickster_active = (
                game != "trivia"
                and int(pet_effects.get("trickster_tokens", 0)) > 0
            )
            required_tokens = 2 if trickster_active else 1

            if arcade_coins < required_tokens:
                await db.rollback()
                return {
                    "error": "no_token",
                    "stardust": stardust,
                    "required_tokens": required_tokens,
                }, stardust

            if stardust < bet:
                await db.rollback()
                return {"error": "insufficient", "stardust": stardust}, stardust

            result: dict[str, Any] = game_callback()
            payout = int(result.get("payout", 0) or 0)
            payout_multiplier = 1.0 + float(pet_effects.get("minigame_payout", 0.0))
            adjusted_payout = int(payout * payout_multiplier)
            new_stardust = stardust - bet + adjusted_payout

            outcome = result.get("outcome")
            if trickster_active and outcome == "win":
                new_arcade_coins = arcade_coins  # spend one, gain one
                token_spent = 1
            elif trickster_active and outcome == "loss":
                new_arcade_coins = arcade_coins - 2
                token_spent = 2
            else:
                new_arcade_coins = arcade_coins - 1
                token_spent = 1

            await db.execute(
                "UPDATE users SET stardust = ?, arcade_coins = ? WHERE user_id = ?",
                (new_stardust, new_arcade_coins, user_id)
            )

            result_game = result.get("game")
            outcome = result.get("outcome")
            if isinstance(result_game, str):
                await self.record_stats(
                    db,
                    user_id,
                    result_game,
                    outcome=outcome,
                    stardust_wagered=bet,
                    stardust_returned=adjusted_payout,
                    arcade_coins_spent=token_spent,
                )

            await db.commit()

        result["payout"] = adjusted_payout
        result["payout_multiplier"] = payout_multiplier
        result["trickster_active"] = trickster_active
        result["new_balance"] = new_stardust
        result["arcade_tokens"] = new_arcade_coins
        result["arcade_tokens_spent"] = token_spent
        return result, new_stardust

    async def record_stats(
        self,
        db,
        user_id,
        game,
        *,
        outcome=None,
        stardust_wagered=0,
        stardust_returned=0,
        arcade_coins_spent=0,
    ):
        """Record one completed minigame session inside the caller's transaction."""
        wins = 1 if outcome in {"win", "blackjack"} else 0
        losses = 1 if outcome in {"loss", "bust"} else 0
        pushes = 1 if outcome == "push" else 0
        timeouts = 1 if outcome == "timeout" else 0
        net = stardust_returned - stardust_wagered
        await db.execute(
            """
            INSERT INTO minigame_stats (
                user_id, game, games_played, wins, losses, pushes, timeouts,
                stardust_wagered, stardust_returned, net_stardust, arcade_coins_spent
            ) VALUES (?, ?, 1, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, game) DO UPDATE SET
                games_played = games_played + 1,
                wins = wins + excluded.wins,
                losses = losses + excluded.losses,
                pushes = pushes + excluded.pushes,
                timeouts = timeouts + excluded.timeouts,
                stardust_wagered = stardust_wagered + excluded.stardust_wagered,
                stardust_returned = stardust_returned + excluded.stardust_returned,
                net_stardust = net_stardust + excluded.net_stardust,
                arcade_coins_spent = arcade_coins_spent + excluded.arcade_coins_spent
            """,
            (
                user_id, game, wins, losses, pushes, timeouts,
                stardust_wagered, stardust_returned, net, arcade_coins_spent
            ),
        )

    async def fetch_stats(self, user_id):
        db_path = self.get_db_path()
        async with aiosqlite.connect(db_path) as db:
            async with db.execute(
                """
                SELECT game, games_played, wins, losses, pushes, timeouts,
                       stardust_wagered, stardust_returned, net_stardust, arcade_coins_spent
                FROM minigame_stats
                WHERE user_id = ?
                ORDER BY CASE game
                    WHEN 'slots' THEN 1
                    WHEN 'dice' THEN 2
                    WHEN 'blackjack' THEN 3
                    WHEN 'roulette' THEN 4
                    WHEN 'trivia' THEN 5
                    ELSE 99 END
                """,
                (user_id,),
            ) as cursor:
                rows = await cursor.fetchall()
        return rows

    async def send_stats(self, interaction, ephemeral=False):
        user = getattr(interaction, "user", None) or getattr(interaction, "author", None)
        user_id = user.id if user is not None else 0
        display_name = getattr(user, "display_name", "Explorer") if user is not None else "Explorer"
        rows = await self.fetch_stats(user_id)
        labels = {
            "slots": "🎰 Slots",
            "dice": "🎲 Dice",
            "blackjack": "🃏 Blackjack",
            "roulette": "🎡 Roulette",
            "trivia": "🚀 Space Trivia",
        }
        if not rows:
            description = (
                "You haven't played any minigames yet.\n\n"
                "Use `/minigames` to enter the recreational deck!"
            )
        else:
            total_played = sum(row[1] for row in rows)
            total_wins = sum(row[2] for row in rows)
            total_losses = sum(row[3] for row in rows)
            total_pushes = sum(row[4] for row in rows)
            total_timeouts = sum(row[5] for row in rows)
            total_wagered = sum(row[6] for row in rows)
            total_returned = sum(row[7] for row in rows)
            total_net = sum(row[8] for row in rows)
            total_tokens = sum(row[9] for row in rows)

            description = (
                f"**Overall**\n"
                f"🎮 Games played: **{total_played:,}**\n"
                f"🏆 Wins: **{total_wins:,}** • 💀 Losses: **{total_losses:,}** • 🤝 Pushes: **{total_pushes:,}**\n"
                f"⏰ Timeouts: **{total_timeouts:,}**\n"
                f"💰 Stardust wagered: **{total_wagered:,}**\n"
                f"📈 Net Stardust: **{total_net:+,}**\n"
                f"🪙 Arcade Tokens spent: **{total_tokens:,}**"
            )

        embed = discord.Embed(
            title=f"📊 {display_name}'s Minigame Stats",
            description=description,
            color=discord.Color.from_rgb(0, 229, 255),
        )

        for row in rows:
            game, played, wins, losses, pushes, timeouts, wagered, returned, net, tokens = row
            embed.add_field(
                name=labels.get(game, game.title()),
                value=(
                    f"Games: **{played:,}** • Wins: **{wins:,}** • Losses: **{losses:,}**\n"
                    f"Wagered: **{wagered:,}** • Net: **{net:+,}** Stardust\n"
                    f"🪙 Tokens used: **{tokens:,}**"
                    + (f" • ⏰ Timeouts: **{timeouts:,}**" if timeouts else "")
                ),
                inline=False,
            )

        embed.set_footer(text="Good luck out there! 👾")
        if isinstance(interaction, commands.Context):
            return await interaction.send(embed=embed)
        return await interaction.followup.send(embed=embed)

    @commands.hybrid_command(
        name="minigame_stats",
        description="View your Enceladus minigame statistics."
    )
    async def minigame_stats(self, ctx: commands.Context):
        """Show the invoking user's persistent minigame statistics."""
        await self.send_stats(ctx, ephemeral=False)

    def validate_bet(self, bet, game=None):
        if bet < self.MIN_BET:
            return f"🎰 **Minimum bet:** {self.MIN_BET:,} Stardust."
        max_bet = self.SLOT_MAX_BET if game == "slots" else self.MAX_BET
        if bet > max_bet:
            return f"🎰 **Maximum bet:** {max_bet:,} Stardust."
        return None

    @staticmethod
    def format_game_result(bet, payout):
        """Build one consistent result summary for every Stardust wager game."""
        profit = payout - bet

        if profit > 0:
            result_line = f"🎉 **WIN!** Profit: **+{profit:,} Stardust**"
        elif profit == 0:
            result_line = "🤝 **PUSH!** Profit: **0 Stardust**"
        else:
            result_line = f"💀 **LOSS!** Profit: **{profit:,} Stardust**"

        return (
            f"{result_line}\n"
            f"💰 Stardust returned: **{payout:,}**"
        )

    async def play_slots(self, interaction, bet):
        error = self.validate_bet(bet, "slots")
        if error:
            return await interaction.followup.send(error, ephemeral=True)

        def spin() -> dict[str, Any]:
            reels = [random.choice(self.SLOT_SYMBOLS) for _ in range(3)]
            counts = {symbol: reels.count(symbol) for symbol in set(reels)}
            highest_match = max(counts.values())
            multiplier = self.SLOT_PAYOUTS.get(highest_match, 0)
            return {
                "reels": reels,
                "matches": highest_match,
                "payout": bet * multiplier,
                "game": "slots",
                "outcome": "win" if highest_match >= 2 else "loss",
            }

        result, new_balance = await self.change_balance(interaction.user.id, bet, spin, "slots")
        if result is None:
            return await interaction.followup.send(
                "❌ You don't have an active station profile yet. Run `/profile`, `/scavenge` or `/mine` first!",
                ephemeral=True,
            )
        if result.get("error") == "no_token":
            required_tokens = result.get("required_tokens", 1)
            token_text = "Arcade Token" if required_tokens == 1 else "Arcade Tokens"
            return await interaction.followup.send(
                f"🪙 **You need {required_tokens} {token_text} to play this round!** "
                "Exchange Stardust for Arcade Tokens from the minigame terminal.",
                ephemeral=True,
            )
        if result.get("error") == "insufficient":
            stardust_available = int(new_balance or 0)
            return await interaction.followup.send(
                f"💸 **Not enough Stardust!** You have **{stardust_available:,}**, but your bet is **{bet:,}**.\n"
                f"🪙 Your Arcade Token is not consumed.",
                ephemeral=True,
            )

        if new_balance is None:
            return await interaction.followup.send(
                "❌ The minigame result could not be finalized. Please try again.",
                ephemeral=True,
            )

        reels = result["reels"]
        matches = result["matches"]
        payout = result["payout"]
        display = " | ".join(reels)

        if matches == 3:
            outcome = "🎰 **JACKPOT!** Three matching symbols!"
        elif matches == 2:
            outcome = "✨ **Two of a kind!**"
        else:
            outcome = "💨 **No match.** The house wins this spin."

        result_summary = self.format_game_result(bet, payout)

        embed = discord.Embed(
            title=f"🎰 Slots — {interaction.user.display_name}",
            description=(
                f"**{display}**\n\n"
                f"💰 Bet: **{bet:,} Stardust**\n"
                f"🪙 Entry fee: **1 Arcade Token**\n"
                f"{outcome}\n"
                f"{result_summary}"
            ),
            color=discord.Color.from_rgb(0, 229, 255),
        )
        token_note = (
            " • 🃏 Trickster token returned" if result.get("trickster_active") and result.get("outcome") == "win"
            else " • 🃏 Trickster extra token consumed" if result.get("trickster_active") and result.get("outcome") == "loss"
            else ""
        )
        embed.set_footer(text=f"Stardust: {new_balance:,} • Arcade Token(s) used{token_note}")
        await interaction.followup.send(embed=embed)

    async def play_dice(self, interaction, bet, choice):
        error = self.validate_bet(bet, "dice")
        if error:
            return await interaction.followup.send(error, ephemeral=True)

        def roll() -> dict[str, Any]:
            die_one = random.randint(1, 6)
            die_two = random.randint(1, 6)
            total = die_one + die_two
            won = (
                choice == "low" and 2 <= total <= 6
            ) or (
                choice == "seven" and total == 7
            ) or (
                choice == "high" and 8 <= total <= 12
            )
            multiplier = self.DICE_PAYOUTS[choice] if won else 0
            return {
                "die_one": die_one,
                "die_two": die_two,
                "total": total,
                "won": won,
                "payout": bet * multiplier,
                "game": "dice",
                "outcome": "win" if won else "loss",
            }

        result, new_balance = await self.change_balance(interaction.user.id, bet, roll, "dice")
        if result is None:
            return await interaction.followup.send(
                "❌ You don't have an active station profile yet. Run `/profile`, `/scavenge` or `/mine` first!",
                ephemeral=True,
            )
        if result.get("error") == "no_token":
            required_tokens = result.get("required_tokens", 1)
            token_text = "Arcade Token" if required_tokens == 1 else "Arcade Tokens"
            return await interaction.followup.send(
                f"🪙 **You need {required_tokens} {token_text} to play this round!** "
                "Exchange Stardust for Arcade Tokens from the minigame terminal.",
                ephemeral=True,
            )
        if result.get("error") == "insufficient":
            stardust_available = int(new_balance or 0)
            return await interaction.followup.send(
                f"💸 **Not enough Stardust!** You have **{stardust_available:,}**, but your bet is **{bet:,}**.\n"
                f"🪙 Your Arcade Token is not consumed.",
                ephemeral=True,
            )

        if new_balance is None:
            return await interaction.followup.send(
                "❌ The minigame result could not be finalized. Please try again.",
                ephemeral=True,
            )

        choice_names = {"low": "Low (2-6)", "seven": "Seven (exactly 7)", "high": "High (8-12)"}
        if result["won"]:
            outcome = f"🎯 **You hit {choice_names[choice]}!**"
        else:
            outcome = "💨 **No hit.** The house keeps your wager."

        result_summary = self.format_game_result(bet, result["payout"])

        embed = discord.Embed(
            title=f"🎲 Enceladus Dice Table — {interaction.user.display_name}",
            description=(
                f"🎲 **{result['die_one']} + {result['die_two']} = {result['total']}**\n\n"
                f"💰 Bet: **{bet:,} Stardust**\n"
                f"🪙 Entry fee: **1 Arcade Token**\n"
                f"🎯 Choice: **{choice_names[choice]}**\n"
                f"{outcome}\n"
                f"{result_summary}"
            ),
            color=discord.Color.from_rgb(0, 229, 255),
        )
        token_note = (
            " • 🃏 Trickster token returned" if result.get("trickster_active") and result.get("outcome") == "win"
            else " • 🃏 Trickster extra token consumed" if result.get("trickster_active") and result.get("outcome") == "loss"
            else ""
        )
        embed.set_footer(text=f"Stardust: {new_balance:,} • Arcade Token(s) used{token_note}")
        await interaction.followup.send(embed=embed)

    async def play_blackjack(self, interaction, bet):
        error = self.validate_bet(bet, "blackjack")
        if error:
            return await interaction.followup.send(error, ephemeral=True)

        db_path = self.get_db_path()
        async with aiosqlite.connect(db_path) as db:
            await db.execute("BEGIN IMMEDIATE")
            async with db.execute(
                "SELECT stardust FROM users WHERE user_id = ?",
                (interaction.user.id,)
            ) as cursor:
                row = await cursor.fetchone()

            async with db.execute(
                "SELECT COALESCE(arcade_coins, 0) FROM users WHERE user_id = ?",
                (interaction.user.id,)
            ) as cursor:
                token_row = await cursor.fetchone()

            if not row:
                await db.rollback()
                return await interaction.followup.send(
                    "❌ You don't have an active station profile yet. Run `/profile`, `/scavenge` or `/mine` first!",
                    ephemeral=True
                )

            arcade_coins = (token_row[0] or 0) if token_row else 0
            stardust = row[0] or 0

            from pets import get_active_pet_effects
            pet_effects = await get_active_pet_effects(db, interaction.user.id)
            trickster_active = int(pet_effects.get("trickster_tokens", 0)) > 0
            required_tokens = 2 if trickster_active else 1
            if arcade_coins < required_tokens:
                await db.rollback()
                token_text = "Arcade Token" if required_tokens == 1 else "Arcade Tokens"
                return await interaction.followup.send(
                    f"🪙 **You need {required_tokens} {token_text} to play this round!** "
                    "Exchange Stardust for Arcade Tokens from the minigame terminal.",
                    ephemeral=True
                )

            if stardust < bet:
                await db.rollback()
                return await interaction.followup.send(
                    f"💸 **Not enough Stardust!** You have **{stardust:,}**, but your bet is **{bet:,}**.\n"
                    f"🪙 Your Arcade Token is not consumed.",
                    ephemeral=True
                )

            new_stardust = stardust - bet
            new_arcade_coins = arcade_coins - 1
            await db.execute(
                "UPDATE users SET stardust = ?, arcade_coins = ? WHERE user_id = ?",
                (new_stardust, new_arcade_coins, interaction.user.id),
            )
            await db.commit()

        deck = [2, 3, 4, 5, 6, 7, 8, 9, 10, 10, 10, 10, 11] * 4
        random.shuffle(deck)
        player = [deck.pop(), deck.pop()]
        dealer = [deck.pop(), deck.pop()]
        view = BlackjackView(self, interaction, bet, deck, player, dealer)
        view.payout_multiplier = 1.0 + float(pet_effects.get("minigame_payout", 0.0))
        view.trickster_active = trickster_active
        view.message = await interaction.followup.send(
            embed=view.build_embed(),
            view=view,
            wait=True
        )

        player_total = view.hand_value(player)
        dealer_total = view.hand_value(dealer)
        if player_total == 21:
            if dealer_total == 21:
                await view.finish("push", bet)
            else:
                await view.finish("blackjack", bet + (bet * 3 // 2))

    async def play_roulette(self, interaction, bet, choice):
        error = self.validate_bet(bet, "roulette")
        if error:
            return await interaction.followup.send(error, ephemeral=True)

        red_numbers = {1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36}

        def spin() -> dict[str, Any]:
            result = random.randint(0, 36)
            is_red = result in red_numbers
            is_black = result != 0 and not is_red

            won = (
                choice == "red" and is_red
                or choice == "black" and is_black
                or choice == "odd" and result != 0 and result % 2 == 1
                or choice == "even" and result != 0 and result % 2 == 0
                or choice.isdigit() and int(choice) == result
            )

            if choice in {"red", "black", "odd", "even"}:
                payout = bet * 2 if won else 0
                bet_type = "even-money"
            else:
                payout = bet * 10 if won else 0
                bet_type = "straight-up"

            color = "🟢 Green" if result == 0 else ("🔴 Red" if is_red else "⚫ Black")
            return {
                "result": result,
                "color": color,
                "won": won,
                "payout": payout,
                "bet_type": bet_type,
                "game": "roulette",
                "outcome": "win" if won else "loss",
            }

        result, new_balance = await self.change_balance(interaction.user.id, bet, spin, "roulette")
        if result is None:
            return await interaction.followup.send(
                "❌ You don't have an active station profile yet. Run `/profile`, `/scavenge` or `/mine` first!",
                ephemeral=True,
            )
        if result.get("error") == "no_token":
            required_tokens = result.get("required_tokens", 1)
            token_text = "Arcade Token" if required_tokens == 1 else "Arcade Tokens"
            return await interaction.followup.send(
                f"🪙 **You need {required_tokens} {token_text} to play this round!** "
                "Exchange Stardust for Arcade Tokens from the minigame terminal.",
                ephemeral=True,
            )
        if result.get("error") == "insufficient":
            stardust_available = int(new_balance or 0)
            return await interaction.followup.send(
                f"💸 **Not enough Stardust!** You have **{stardust_available:,}**, but your bet is **{bet:,}**.\n"
                f"🪙 Your Arcade Token is not consumed.",
                ephemeral=True,
            )

        if result["won"]:
            status = f"🎉 **WIN!** Your {result['bet_type']} bet hit!"
        else:
            status = "💀 **LOSS!** The house wins."

        result_summary = self.format_game_result(bet, result["payout"])

        embed = discord.Embed(
            title=f"🎡 Roulette — {interaction.user.display_name}",
            description=(
                f"**The wheel lands on:** {result['result']} — {result['color']}\n\n"
                f"🎟️ Your bet: **{bet:,} Stardust** on **{choice}**\n"
                f"{status}\n"
                f"{result_summary}"
            ),
            color=discord.Color.from_rgb(0, 229, 255),
        )
        embed.set_footer(text=f"Stardust: {new_balance:,} • 1 Arcade Token used • European wheel (0-36)")
        await interaction.followup.send(embed=embed)


    async def consume_arcade_token(self, user_id) -> int | None:
        """Consume exactly one Arcade Token from users.arcade_coins."""
        db_path = self.get_db_path()
        async with aiosqlite.connect(db_path) as db:
            await db.execute("BEGIN IMMEDIATE")
            balance = await self.get_balance(db, user_id)

            async with db.execute(
                "SELECT 1 FROM users WHERE user_id = ?",
                (user_id,)
            ) as cursor:
                profile = await cursor.fetchone()

            if profile is None:
                await db.rollback()
                return None
            if balance is None:
                await db.rollback()
                return None
            if balance < 1:
                await db.rollback()
                return -1

            new_balance = balance - 1
            await db.execute(
                "UPDATE users SET arcade_coins = ? WHERE user_id = ?",
                (new_balance, user_id)
            )
            await db.commit()
        return new_balance

    async def send_trivia(self, interaction):
        token_balance = await self.consume_arcade_token(interaction.user.id)
        if token_balance is None:
            return await interaction.followup.send(
                "❌ You don't have an active station profile yet. Run `/profile`, `/scavenge` or `/mine` first!",
                ephemeral=True,
            )
        if token_balance < 0:
            return await interaction.followup.send(
                "🪙 **You need an Arcade Token to play!** Exchange Stardust for Arcade Tokens from the minigame terminal.",
                ephemeral=True,
            )

        question, options, answer = random.choice(self.TRIVIA_QUESTIONS)
        shuffled_options = list(options)
        correct_answer = shuffled_options[answer]
        random.shuffle(shuffled_options)
        shuffled_answer = shuffled_options.index(correct_answer)
        reward = 100
        view = TriviaView(self, interaction, question, shuffled_options, shuffled_answer, reward)
        embed = discord.Embed(
            title=f"🚀 Space Trivia — {interaction.user.display_name}",
            description=(
                f"**{question}**\n\nChoose the answer before the terminal times out.\n"
                f"💰 Correct answer: **+{reward:,} Stardust**\n🪙 Entry fee: **1 Arcade Token**\n🔀 Answer choices are shuffled each time."
            ),
            color=discord.Color.from_rgb(0, 229, 255),
        )
        for index, option in enumerate(shuffled_options):
            embed.add_field(name=f"{chr(65 + index)}.", value=option, inline=False)

        for index, option in enumerate(shuffled_options):
            button = discord.ui.Button(
                label=chr(65 + index),
                style=discord.ButtonStyle.secondary,
                custom_id=f"trivia_{interaction.user.id}_{index}",
            )

            async def callback(button_interaction, selected=index):
                await view.answer_question(button_interaction, selected)

            button.callback = callback
            view.add_item(button)

        view.message = await interaction.followup.send(
            embed=view.build_embed(),
            view=view,
            wait=True
        )

    @commands.hybrid_command(
        name="minigames",
        description="Open the Enceladus station minigame terminal."
    )
    async def minigames(self, ctx: commands.Context):
        """Open the minigame dropdown menu."""
        user_id = ctx.author.id
        db_path = self.get_db_path()
        async with aiosqlite.connect(db_path) as db:
            arcade_coins = await self.get_balance(db, user_id)

        if arcade_coins is None:
            return await ctx.send(
                "❌ You don't have an active station profile yet. Run `/profile`, `/scavenge` or `/mine` first!"
            )

        embed = discord.Embed(
            title="🎮 Enceladus Minigame Terminal",
            description=(
                "Welcome to the station's recreational deck.\n\n"
                f"🪙 **Arcade Token Balance:** {arcade_coins:,}\n"
                "Each game costs **1 Arcade Token** to play.\n"
                "Your actual wagers are paid in **Stardust** inside the games.\n"
                "Use the exchange option to convert Stardust at **100 Stardust = 1 Arcade Token**.\n\n"
                "Choose a game below. **The house has an edge.** "
                "Don't bet what you can't afford to lose!\n\n"
                "🎰 **Slots** — spend 1 token, then wager Stardust\n"
                "🎲 **Dice** — spend 1 token, then wager Stardust\n"
                "🃏 **Blackjack** — spend 1 token, then wager Stardust\n"
                "🎡 **Roulette** — spend 1 token, then wager Stardust\n"
                "🚀 **Space Trivia** — spend 1 token to answer for Stardust\n"
                "🪙 **Arcade Token Exchange** — buy Arcade Tokens with Stardust\n"
                "📊 **My Stats** — view your minigame history"
            ),
            color=discord.Color.from_rgb(0, 229, 255),
        )
        embed.set_footer(text="Select a game to begin.")
        view = MinigamesView(self, ctx.author.id)
        view.message = await ctx.send(embed=embed, view=view)


async def setup(bot):
    await bot.add_cog(Minigames(bot))
