"""Private, temporary-access tools for trusted Enceladus administrators."""

import hmac
import os
import time
import json

import discord
from discord.ext import commands
from database import ECONOMY_DB_NAME


class Debug(commands.Cog):
    SESSION_SECONDS = 30 * 60

    def __init__(self, bot):
        self.bot = bot
        self.sessions = {}

    async def is_authorized(self, ctx):
        if await self.bot.is_owner(ctx.author):
            return True
        return self.sessions.get(ctx.author.id, 0) > time.time()

    async def require_access(self, ctx):
        if await self.is_authorized(ctx):
            return True
        await ctx.send("🔒 Debug access is locked. Use `/debug unlock <code>` first.", ephemeral=True)
        return False

    @commands.hybrid_group(name="debug", description="Private diagnostic and administration tools.")
    async def debug(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send("Use `/debug unlock <code>` to start a temporary admin session.", ephemeral=True)

    @debug.command(name="unlock", description="Unlock debug tools for 30 minutes with the server secret.")
    @commands.has_permissions(administrator=True)
    async def unlock(self, ctx, code: str):
        if await self.bot.is_owner(ctx.author):
            self.sessions[ctx.author.id] = time.time() + self.SESSION_SECONDS
            await ctx.send(
                "**Owner detected.** You already have permanent debug access, so no unlock timer is needed.",
                ephemeral=True
            )
            return

        secret = os.getenv("DEBUG_ACCESS_CODE")
        if not secret:
            return await ctx.send(
                "⚠️ Debug access is not configured. Add `DEBUG_ACCESS_CODE` to the bot environment.",
                ephemeral=True
            )

        if not code or not hmac.compare_digest(code, secret):
            return await ctx.send(
                "❌ Invalid debug access code.",
                ephemeral=True
            )

        self.sessions[ctx.author.id] = time.time() + self.SESSION_SECONDS
        await ctx.send(
            "🔓 Debug access enabled for 30 minutes. This session resets if the bot restarts.",
            ephemeral=True
        )

    @debug.command(name="status", description="View the active debug-session status.")
    @commands.has_permissions(administrator=True)
    async def status(self, ctx):
        if not await self.require_access(ctx):
            return
        remaining = max(0, int(self.sessions.get(ctx.author.id, time.time()) - time.time()))
        owner_note = "Bot-owner access" if await self.bot.is_owner(ctx.author) else f"{remaining // 60} minutes remaining"
        await ctx.send(f"🛠️ Debug session active: **{owner_note}**.", ephemeral=True)

    @debug.command(name="lock", description="End your temporary debug session.")
    @commands.has_permissions(administrator=True)
    async def lock(self, ctx):
        if await self.bot.is_owner(ctx.author):
            self.sessions.pop(ctx.author.id, None)
            await ctx.send(
                "**Owner detected.** Your debug access cannot be locked because owner access always overrides the debug lock.",
                ephemeral=True
            )
            return

        self.sessions.pop(ctx.author.id, None)
        await ctx.send("🔒 Debug session ended.", ephemeral=True)

    @debug.command(name="stardust", description="Grant Stardust to a member for testing.")
    @commands.has_permissions(administrator=True)
    async def stardust(self, ctx, member: discord.Member, amount: int):
        if not await self.require_access(ctx):
            return
        if amount <= 0 or amount > 1_000_000:
            return await ctx.send("❌ Choose an amount from 1 to 1,000,000.", ephemeral=True)

        db_path = ECONOMY_DB_NAME
        import aiosqlite
        async with aiosqlite.connect(db_path) as db:
            await db.execute("INSERT OR IGNORE INTO users (user_id, stardust) VALUES (?, 0)", (member.id,))
            await db.execute("UPDATE users SET stardust = COALESCE(stardust, 0) + ? WHERE user_id = ?", (amount, member.id))
            await db.commit()

        await ctx.send(f"✨ Granted **{amount:,} Stardust** to {member.mention} for testing.", ephemeral=True)

    @debug.command(name="item", description="Grant a registered inventory item for testing.")
    @commands.has_permissions(administrator=True)
    async def item(self, ctx, member: discord.Member, item_id: str, quantity: int = 1):
        if not await self.require_access(ctx):
            return
        from inventory import ITEM_REGISTRY
        item_id = item_id.lower().strip()
        if item_id not in ITEM_REGISTRY:
            return await ctx.send("❌ Unknown item ID. Check `/item <item_id>` or the item registry.", ephemeral=True)
        if quantity <= 0 or quantity > 100:
            return await ctx.send("❌ Choose a quantity from 1 to 100.", ephemeral=True)

        db_path = ECONOMY_DB_NAME
        import aiosqlite
        item_type = ITEM_REGISTRY[item_id]["type"].lower().replace(" ", "_")
        async with aiosqlite.connect(db_path) as db:
            await db.execute("""
                INSERT INTO inventory (user_id, item_id, item_type, quantity)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id, item_id) DO UPDATE SET
                    item_type = excluded.item_type,
                    quantity = quantity + excluded.quantity
            """, (member.id, item_id, item_type, quantity))
            await db.commit()
        await ctx.send(f"📦 Granted **{quantity}× {ITEM_REGISTRY[item_id]['name']}** to {member.mention} for testing.", ephemeral=True)

    @debug.command(name="ready", description="Clear a mining or scavenging cooldown for testing.")
    @commands.has_permissions(administrator=True)
    async def ready(self, ctx, member: discord.Member, activity: str):
        if not await self.require_access(ctx):
            return
        activity = activity.lower().strip()
        if activity not in {"mine", "scavenge"}:
            return await ctx.send("❌ Activity must be `mine` or `scavenge`.", ephemeral=True)
        column = "last_mined" if activity == "mine" else "last_scavenged"
        db_path = ECONOMY_DB_NAME
        import aiosqlite
        async with aiosqlite.connect(db_path) as db:
            await db.execute(f"UPDATE users SET {column} = 0 WHERE user_id = ?", (member.id,))
            await db.commit()
        await ctx.send(f"⏱️ Cleared {activity} cooldown for {member.mention}.", ephemeral=True)

    @debug.command(name="hazard", description="Force the next scavenging run to roll a hazard.")
    @commands.has_permissions(administrator=True)
    async def hazard(self, ctx, member: discord.Member):
        if not await self.require_access(ctx):
            return
        db_path = ECONOMY_DB_NAME
        import aiosqlite
        async with aiosqlite.connect(db_path) as db:
            async with db.execute("SELECT active_effects FROM users WHERE user_id = ?", (member.id,)) as cursor:
                row = await cursor.fetchone()
            effects = json.loads((row[0] if row else "") or "{}")
            effects["force_hazard"] = True
            await db.execute("UPDATE users SET active_effects = ? WHERE user_id = ?", (json.dumps(effects), member.id))
            await db.commit()
        await ctx.send(f"⚠️ The next scavenging run for {member.mention} will trigger a hazard.", ephemeral=True)

    @debug.command(name="health", description="Set a member's HP for testing.")
    @commands.has_permissions(administrator=True)
    async def health(self, ctx, member: discord.Member, hp: int):
        if not await self.require_access(ctx):
            return
        if hp < 1 or hp > 100:
            return await ctx.send("❌ Choose an HP value from 1 to 100.", ephemeral=True)
        db_path = ECONOMY_DB_NAME
        import aiosqlite
        async with aiosqlite.connect(db_path) as db:
            await db.execute("UPDATE users SET hp = ?, max_hp = MAX(COALESCE(max_hp, 100), ?) WHERE user_id = ?", (hp, hp, member.id))
            await db.commit()
        await ctx.send(f"❤️ Set {member.mention}'s HP to **{hp}** for testing.", ephemeral=True)


async def setup(bot):
    await bot.add_cog(Debug(bot))
