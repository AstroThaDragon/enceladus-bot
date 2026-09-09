import discord
from discord.ext import commands
import aiosqlite
import time
import json
import random

# Master Item Registry used across inventory, shop, and exploration
ITEM_REGISTRY = {
    # Currencies & Consumables
    "fuel_refill": {"name": "Emergency Fuel Cell (5 Charges)", "emoji": "⚡", "type": "Consumable", "desc": "Instantly refills your starship mining laser back to 5/5 charges."},
    "pet_snack": {"name": "Cosmic Bio-Feed", "emoji": "🧬", "type": "Consumable", "desc": "Nutrient pack for your station pet."},
    "arcade_token": {"name": "Arcade Token", "emoji": "🪙", "type": "Currency", "desc": "Shiny token for future station mini-games."},
    "time_crystal": {"name": "Dilated Time Crystal", "emoji": "💎", "type": "Consumable", "desc": "Bends time backwards to restore a fortune streak missed yesterday."},
    "nanite_patch": {"name": "Nanite Stim-Patch", "emoji": "🩹", "type": "Consumable", "desc": "Quickly knits minor planetary surface wounds. Restores +35 HP."},
    "medkit": {"name": "Field Trauma Medkit", "emoji": "🧰", "type": "Consumable", "desc": "Standard planetary survival trauma kit. Restores +100 HP."},
    "revive_kit": {"name": "Emergency Revival Kit", "emoji": "💉", "type": "Consumable", "desc": "Rare salvage that revives an unconscious explorer with 50% HP."},
    "fuel_stabilizer": {"name": "Fuel Stabilizer", "emoji": "🛢️", "type": "Consumable", "desc": "Makes the next mining run cost no fuel charge."},
    "station_rations": {"name": "Station Rations", "emoji": "🥫", "type": "Consumable", "desc": "Restores 15 HP."},
    "hazard_shield": {"name": "Hazard Shield", "emoji": "🛡️", "type": "Consumable", "desc": "Blocks the next scavenging hazard."},
    "drone_battery": {"name": "Drone Battery Pack", "emoji": "🔋", "type": "Consumable", "desc": "Restores two scavenge charges."},
    "lucky_scanner": {"name": "Deep-Space Scanner", "emoji": "📡", "type": "Consumable", "desc": "Improves rare-find odds on the next scavenging run."},
    "ore_magnet": {"name": "Ore Magnet", "emoji": "🧲", "type": "Consumable", "desc": "Guarantees a titanium ore find on the next mining run."},
    "prototype_drill_bit": {"name": "Prototype Drill Bit", "emoji": "⚙️", "type": "Consumable", "desc": "Boosts Stardust from the next mining run."},
    "time_warp_coupon": {"name": "Time Warp Coupon", "emoji": "⏳", "type": "Consumable", "desc": "Reduces one exploration cooldown by one hour."},
    "salvage_insurance": {"name": "Salvage Insurance", "emoji": "📋", "type": "Consumable", "desc": "Prevents a knockout from the next scavenging hazard."},
    "fate_anchor": {"name": "Fate Anchor", "emoji": "⚓", "type": "Consumable", "desc": "Protects one missed fortune streak day."},
    "stardust_cache": {"name": "Contraband Stardust Cache", "emoji": "🎁", "type": "Consumable", "desc": "Opens for an unpredictable Stardust payoff."},

    # Minerals
    "titanium_chunk": {"name": "Titanium Ore Chunk", "emoji": "⛏️", "type": "Mineral", "desc": "High-purity raw titanium extracted from deep sector asteroids."},

    # Space Junk
    "space_pizza": {"name": "Dehydrated Space Pizza", "emoji": "🍕", "type": "Space Junk", "desc": "Slightly freezer-burned."},
    "floppy_disk": {"name": "Ancient Alien Floppy Disk", "emoji": "💾", "type": "Space Junk", "desc": "Contains mysterious code. Highly ancient tbh."},
    "meteorite": {"name": "Suspiciously Warm Meteorite Chunk", "emoji": "🪨", "type": "Space Junk", "desc": "Emits a faint ambient heat."},
    "rubber_duck": {"name": "Rubber Duck in a Micro-Spacesuit", "emoji": "🐤", "type": "Space Junk", "desc": "Ready for zero-gravity bath time."},
    "rusty_gear": {"name": "Tarnished Station Gear", "emoji": "⚙️", "type": "Space Junk", "desc": "Coated in interstellar grease."},
    "tape_deck": {"name": "Broken Cassette Player", "emoji": "📼", "type": "Space Junk", "desc": "Stuck looping an old synthwave tape."},
    "alien_artifact": {"name": "Miniature Alien Artifact", "emoji": "🛸", "type": "Space Junk", "desc": "Glows faintly."},
    "space_boot": {"name": "Single Space Boot", "emoji": "🥾", "type": "Space Junk", "desc": "Missing its matching pair."},
    "cosmic_coin": {"name": "Cosmic Coin", "emoji": "🪙", "type": "Space Junk", "desc": "Heads: Unknown, Tails: Mystery."},
    "holo_poster": {"name": "Faded Holographic Poster", "emoji": "🖼️", "type": "Space Junk", "desc": "Features a legendary Galactic Band."},
    "broken_laser": {"name": "Broken Laser Pistol", "emoji": "🔫", "type": "Space Junk", "desc": "Sparks occasionally."},
    "lost_logbook": {"name": "Waterlogged Starship Logbook", "emoji": "📓", "type": "Space Junk", "desc": "Completely unreadable."},
    "left_sock": {"name": "Single Left Space Sock", "emoji": "🧦", "type": "Space Junk", "desc": "The right one was lost to a wormhole."},
    "warp_mug": {"name": "Leaky Thermal Mug", "emoji": "☕", "type": "Space Junk", "desc": "Holds coffee across space-time, leaks in 3D."},
    "space_pudding": {"name": "Expired Void Pudding", "emoji": "🍮", "type": "Space Junk", "desc": "Tastes suspiciously like dark matter."},
    "tangled_cables": {"name": "Quantum Cable Knot", "emoji": "🔌", "type": "Space Junk", "desc": "Physically impossible to untangle."},
    "screaming_crystal": {"name": "Screaming Crystal", "emoji": "💎", "type": "Space Junk", "desc": "Relentlessly sings 80s synth-pop."},
    "moon_cheese": {"name": "Chunk of Moon Cheese", "emoji": "🧀", "type": "Space Junk", "desc": "Smells like sharp Gouda."},
    "alien_spatula": {"name": "Intergalactic Spatula", "emoji": "🛸", "type": "Space Junk", "desc": "Slightly sticky with cosmic grease."},
    "parking_ticket": {"name": "Cosmic Parking Ticket", "emoji": "📜", "type": "Space Junk", "desc": "Overdue by 400 light-years."},
    "floating_plant": {"name": "Suspicious Houseplant", "emoji": "🪴", "type": "Space Junk", "desc": "Directly stares at you when you turn around."},
    "tinted_visor": {"name": "Broken Solar Visor", "emoji": "🕶️", "type": "Space Junk", "desc": "Now just regular 3D glasses."},
    "purring_lint": {"name": "Ball of Space Lint", "emoji": "🧶", "type": "Space Junk", "desc": "It purrs when you touch it."},
    "pet_rock": {"name": "Asteroid Pet Rock", "emoji": "🪨", "type": "Space Junk", "desc": "Includes tiny drawn-on googly eyes."},
    "haunted_circuit": {"name": "Haunted Circuit Board", "emoji": "⚡", "type": "Space Junk", "desc": "Sparks every time you whisper near it."},
    "space_taco": {"name": "Cosmic Taco", "emoji": "🌮", "type": "Space Junk", "desc": "The salsa is surprisingly unaffected by zero-G."},
    
    # Background Vouchers
    "neon_grid": {"name": "Background Voucher: Neon Grid", "emoji": "🌆", "type": "Voucher", "desc": "Unlocks the Cyberpunk Neon Grid profile card."},
    "deep_void": {"name": "Background Voucher: Deep Void", "emoji": "🌌", "type": "Voucher", "desc": "Unlocks the Deep Void galaxy profile card."},
    "solaris_ring": {"name": "Background Voucher: Solaris Ring", "emoji": "☀️", "type": "Voucher", "desc": "Unlocks the Solaris Ring star system profile card."}
}

class Inventory(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_db_path(self):
        """Use the same database as the rest of the economy system."""
        leveling_cog = self.bot.get_cog("Leveling")
        if leveling_cog and hasattr(leveling_cog, "db_path"):
            return leveling_cog.db_path
        return "levels.db"

    async def ensure_effect_schema(self, db):
        async with db.execute("PRAGMA table_info(users)") as cursor:
            columns = {row[1] async for row in cursor}
        if "active_effects" not in columns:
            await db.execute("ALTER TABLE users ADD COLUMN active_effects TEXT DEFAULT '{}'")
            await db.commit()

    @commands.hybrid_command(name="inventory", description="Open your station storage locker to view collected items and vouchers.")
    async def inventory(self, ctx: commands.Context):
        await ctx.defer()
        user_id = ctx.author.id

        async with aiosqlite.connect(self.get_db_path()) as db:
            # 1. Fetch standard items from the inventory table
            async with db.execute("SELECT item_id, item_type, quantity FROM inventory WHERE user_id = ?", (user_id,)) as cursor:
                inv_rows = await cursor.fetchall()

            # 2. Fetch healing items and time crystals from the users table
            # (Failsafes added using PRAGMA to ensure columns exist before querying)
            async with db.execute("PRAGMA table_info(users)") as cursor:
                columns = [row[1] async for row in cursor]
            
            user_items = []
            if all(col in columns for col in ["time_crystals", "nanite_patchs", "medkits"]):
                async with db.execute("SELECT time_crystals, nanite_patchs, medkits FROM users WHERE user_id = ?", (user_id,)) as cursor:
                    row = await cursor.fetchone()
                    if row:
                        tc, nanites, medkits = row[0] or 0, row[1] or 0, row[2] or 0
                        if tc > 0: user_items.append(("time_crystal", tc))
                        if nanites > 0: user_items.append(("nanite_patch", nanites))
                        if medkits > 0: user_items.append(("medkit", medkits))

        if not inv_rows and not user_items:
            return await ctx.send("📦 **Your storage locker is completely empty!** Head out with `/mine` or `/scavenge` to fill it up!")

        embed = discord.Embed(
            title=f"📦 {ctx.author.display_name}'s Storage Locker",
            description="Here is a manifest of all salvaged artifacts, minerals, and vouchers in your inventory:",
            color=discord.Color.from_rgb(0, 229, 255)
        )

        categories = {"Space Junk": [], "Mineral": [], "Consumable": [], "Voucher": [], "Currency": []}

        # Format and append items tracked in the users table
        for item_id, count in user_items:
            item_info = ITEM_REGISTRY.get(item_id)
            cat = item_info.get("type", "Consumable")
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(f"{item_info['emoji']} **{item_info['name']}** (x{count})\n└ *{item_info['desc']}* (`{item_id}`)")

        # Format and append items tracked in the inventory table
        for item_id, item_type, quantity in inv_rows:
            item_info = ITEM_REGISTRY.get(item_id, {"name": item_id, "emoji": "📦", "type": "Space Junk", "desc": "A weird salvage find."})
            cat = item_info.get("type", "Space Junk")
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(f"{item_info['emoji']} **{item_info['name']}** (x{quantity or 1})\n└ *{item_info['desc']}* (`{item_id}`)")

        for cat_name, items in categories.items():
            if items:
                embed.add_field(name=f"✨ {cat_name}s", value="\n".join(items), inline=False)

        embed.set_footer(text="Tip: Sell your unwanted salvage at the trading post using /shop sell <item_id>")
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="use", description="Use a consumable from your inventory.")
    async def use_item(self, ctx: commands.Context, item_id: str, target: str = None):
        await ctx.defer()
        user_id = ctx.author.id
        item_id = item_id.lower().strip()
        valid = {"fuel_stabilizer", "station_rations", "hazard_shield", "drone_battery", "lucky_scanner", "ore_magnet", "prototype_drill_bit", "time_warp_coupon", "salvage_insurance", "fate_anchor", "stardust_cache"}
        if item_id not in valid:
            return await ctx.send("❌ That item cannot be used here. Use `/revive` for an Emergency Revival Kit.")

        async with aiosqlite.connect(self.get_db_path()) as db:
            await self.ensure_effect_schema(db)
            async with db.execute("SELECT quantity FROM inventory WHERE user_id = ? AND item_id = ?", (user_id, item_id)) as cursor:
                row = await cursor.fetchone()
            if not row or (row[0] or 0) <= 0:
                return await ctx.send(f"❌ You do not have `{item_id}` in your inventory.")

            async with db.execute("SELECT hp, max_hp, mining_charges, scavenge_charges, last_mined, last_scavenged, active_effects FROM users WHERE user_id = ?", (user_id,)) as cursor:
                user = await cursor.fetchone()
            if not user:
                return await ctx.send("❌ Profile not found! Explore Enceladus first.")
            hp, max_hp, mining, scavenging, last_mined, last_scavenged, effects_raw = user
            effects = json.loads(effects_raw or "{}")
            message = ""

            if item_id == "station_rations":
                if (hp or 0) <= 0: return await ctx.send("💀 Rations cannot revive an unconscious explorer.")
                hp = min(max_hp or 100, (hp or 0) + 15); await db.execute("UPDATE users SET hp = ? WHERE user_id = ?", (hp, user_id)); message = f"🥫 Restored 15 HP. Current health: **{hp}/{max_hp or 100}**."
            elif item_id == "drone_battery":
                scavenging = min(5, (scavenging or 0) + 2); await db.execute("UPDATE users SET scavenge_charges = ? WHERE user_id = ?", (scavenging, user_id)); message = f"🔋 Drone charges restored to **{scavenging}/5**."
            elif item_id == "stardust_cache":
                payout = random.randint(150, 700); await db.execute("UPDATE users SET stardust = stardust + ? WHERE user_id = ?", (payout, user_id)); message = f"🎁 Cache opened: **{payout:,} Stardust** recovered."
            elif item_id == "time_warp_coupon":
                if target not in {"mine", "scavenge"}: return await ctx.send("⏳ Use `/use time_warp_coupon mine` or `/use time_warp_coupon scavenge`.")
                column = "last_mined" if target == "mine" else "last_scavenged"
                await db.execute(f"UPDATE users SET {column} = MAX(0, COALESCE({column}, 0) - 3600) WHERE user_id = ?", (user_id,)); message = f"⏳ Reduced your {target} cooldown by **1 hour**."
            else:
                effects[item_id] = True
                await db.execute("UPDATE users SET active_effects = ? WHERE user_id = ?", (json.dumps(effects), user_id))
                labels = {"fuel_stabilizer": "next mining run costs no charge", "hazard_shield": "next scavenging hazard is blocked", "lucky_scanner": "next scavenging run has improved rare-find odds", "ore_magnet": "next mining run guarantees titanium ore", "prototype_drill_bit": "next mining run earns bonus Stardust", "salvage_insurance": "next knockout is prevented", "fate_anchor": "next missed fortune streak is protected"}
                message = f"✅ **{item_id.replace('_', ' ').title()} activated:** your {labels[item_id]}."

            if row[0] > 1: await db.execute("UPDATE inventory SET quantity = quantity - 1 WHERE user_id = ? AND item_id = ?", (user_id, item_id))
            else: await db.execute("DELETE FROM inventory WHERE user_id = ? AND item_id = ?", (user_id, item_id))
            await db.commit()
        await ctx.send(message)

    @commands.hybrid_command(name="status", description="View your health, exploration charges, and cooldowns.")
    async def status(self, ctx: commands.Context):
        await ctx.defer()
        user_id = ctx.author.id
        now = time.time()

        async with aiosqlite.connect(self.get_db_path()) as db:
            async with db.execute(
                "SELECT hp, max_hp, mining_charges, scavenge_charges, last_mined, last_scavenged, knocked_out_until, active_effects FROM users WHERE user_id = ?",
                (user_id,),
            ) as cursor:
                row = await cursor.fetchone()

        if not row:
            return await ctx.send("❌ No station profile found yet. Run `/mine` or `/scavenge` first!")

        hp, max_hp, mining, scavenging, last_mined, last_scavenged, knocked_out_until, effects_raw = row
        def cooldown(last_used):
            remaining = max(0, int(4 * 3600 - (now - (last_used or 0))))
            return "Ready" if remaining == 0 else f"{remaining // 3600}h {(remaining % 3600) // 60}m"

        embed = discord.Embed(title=f"📟 {ctx.author.display_name}'s Expedition Status", color=discord.Color.teal())
        embed.add_field(name="❤️ Health", value=f"`{hp or 0}/{max_hp or 100}`", inline=True)
        embed.add_field(name="⛏️ Mining", value=f"`{mining or 0}/5` charges\n{cooldown(last_mined)}", inline=True)
        embed.add_field(name="🛠️ Scavenging", value=f"`{scavenging or 0}/5` charges\n{cooldown(last_scavenged)}", inline=True)
        if (hp or 0) <= 0:
            embed.add_field(name="💀 Recovery", value=f"Unconscious until `{knocked_out_until or 'revived'}`", inline=False)
        effects = json.loads(effects_raw or "{}")
        if effects:
            embed.add_field(name="✨ Active Effects", value="\n".join(f"• {name.replace('_', ' ').title()}" for name in effects), inline=False)
        embed.set_footer(text="Use /inventory for items, /shop rotating for today's offers, and /revive if unconscious.")
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Inventory(bot))
