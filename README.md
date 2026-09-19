# Enceladus

A custom multipurpose Discord bot built for **The Cosmic Lair** — focused on community interaction, utility, automation, cosmic-themed fun, server events, and a persistent space-themed RPG/economy system. ✨

## Features

### 🌌 Community & Utility
~ Birthday System: Members can register birthdays and automatically receive a birthday role and celebration announcement at midnight EST.
~ Upcoming Birthdays: View the next upcoming server birthdays in a clean embed display.
~ Persistent Daily Systems: Daily commands properly save progress through restarts/redeploys using SQLite databases.
~ Daily Rewards: Consecutive daily rewards increase through a weekly reward cycle while preserving the user's streak.
~ Quick Report (!qr): Allows users to quickly report messages to the staff channel.
~ Auto-Cleanup: Deletes report command usage to keep channels tidy.
~ Echo Command: Send bot messages into selected channels.
~ Choice Picker: Lets the bot choose between multiple options.

### 🎲 Fun Commands
~ Fortune Cookies: Daily cosmic fortunes with persistent cooldown resets at midnight EST.
~ Astral Relic: A themed magic 8-ball style response system.
~ Coinflip & Dice Rolling
~ Aura / IQ / Cringe / Freaky / Cool / Furry Rating Systems
~ Mock Text Generator
~ Black Hole Text Distortion
~ Hug & Slap Commands
~ Random Jokes

### 💰 Economy & Progression
~ Stardust Economy: Earn and spend the server's primary currency.
~ Bank & Vault: Store Stardust separately from spendable funds with a dedicated vault capacity.
~ Arcade Tokens: A secondary currency used by the bot's arcade/minigame systems.
~ Inventory: Persistent item storage organized into browsable categories.
~ Daily Streaks: Maintain a persistent consecutive-day reward streak.
~ Exploration Upgrades: Improve mining and scavenging capabilities through multiple upgrade levels.
~ Persistent Progress: Economy, inventory, upgrades, collectibles, pets, achievements, and other gameplay data survive bot restarts and redeploys.

### ⛏️ Exploration
~ Mining: Search for Stardust, ores, special loot, and other discoveries.
~ Scavenging: Search abandoned areas for Stardust, materials, medical supplies, seasonal finds, and other loot.
~ Exploration Charges: Mining and scavenging use rechargeable daily charges.
~ Exploration Upgrades: Increase charge capacity, Stardust rewards, and rare-loot opportunities.
~ Hazards: Exploration can include dangerous encounters requiring defensive equipment or other protective effects.
~ Consumable Effects: Special items can temporarily modify exploration outcomes.

### 🎒 Crafting & Materials
~ Materials: Collect ores, scrap, wiring, circuit boards, glue, nuts and bolts, and other crafting resources.
~ Crafting: Combine collected materials into useful equipment, upgrade components, and consumables.
~ Upgrade Kits: Craft components used to advance exploration systems.
~ Medical Crafting: Craft healing items from scavenged medical supplies.
~ Material Overflow: Excess or duplicate finds can be converted into Stardust where appropriate.

### 🐾 Pets
~ Pet Eggs: Discover eggs and incubate them before hatching.
~ Pet Collection: Collect permanent pets with different passive abilities.
~ Pet XP: Level pets through normal gameplay and consumable treats.
~ Equipped Pets: Equip a pet to benefit from its passive effect during supported activities.
~ Seasonal Pets: Limited-time seasonal eggs can provide themed pets that remain part of a user's collection after the event.

### 🏆 Achievements & Collectibles
~ Achievements: Complete milestones and unlock permanent rewards.
~ Collectibles: Discover and permanently record special items and seasonal collectibles.
~ Progress Tracking: View achievement and collection progress through the bot.
~ Seasonal Achievements: Special events can introduce limited-time collection and gameplay milestones.

### 🎃 Seasonal Events
~ Seasonal Systems: Temporary events can add themed loot, collectibles, achievements, pets, crafting materials, and other content.
~ Halloween: A dedicated seasonal event featuring Halloween-themed exploration finds, collectibles, candy, eggs, pets, and other surprises.
~ Permanent Progress: Seasonal collectibles, pets, achievements, and other designated rewards can remain permanently available after an event ends.
~ Seasonal Content: Event references and themed material are kept modular so future events can be added without changing the core systems.

### 🩹 Healing & Defense
~ Healing System: Dedicated healing commands support multiple consumable healing items.
~ Medical Supplies: Scavenge supplies and craft healing items.
~ Defensive Equipment: Equip defensive items to improve survival during hazardous exploration encounters.
~ Protective Effects: Certain equipment, upgrades, pets, and consumables can provide additional protection.

### 🌠 Space & API Features
~ Space Facts: Pulls live celestial body data from a solar system API.
~ Horoscopes: Fetches real-time zodiac readings.
~ FNF Mod Search: Quickly search Friday Night Funkin' mods on GameBanana.
~ FNF Song Search: Search FNF songs directly on YouTube.

## ⚙️ Technical Features

~ SQLite Database Persistence
~ Separate persistent databases for core levels/server data and economy/gameplay data
~ Cog-Based Modular Structure
~ Hybrid Commands Support
~ Slash Commands Support
~ Railway Deployment Compatible
~ Async API Handling
~ Persistent Timers & Cooldowns
~ Automatic Database Migration Support
~ Persistent UI components for supported interactive bot features
~ Modular seasonal content

## 🗃️ Data & Privacy

Enceladus stores persistent gameplay data required for its economy, inventory, exploration, crafting, pets, achievements, collectibles, and related systems.

For details about information Enceladus may access, store, process, and retain, see:

- `PRIVACY.md` — Privacy Policy
- `TOS.md` — Terms of Service & usage rules

## Setup

This bot is designed to run on Railway.

### Required Environment Variables

`DISCORD_TOKEN` — Discord bot token

### Tech Stack

- Python
- discord.py
- SQLite / aiosqlite
- aiohttp
- Railway

## Project Status

Actively developed and constantly expanding. 🚀

Enceladus is a community project for The Cosmic Lair, with new gameplay systems, seasonal content, utilities, and quality-of-life improvements added over time.
