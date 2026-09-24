from typing import Protocol

import aiosqlite
import discord


class PetCogHost(Protocol):
    bot: discord.Client

    async def ensure_schema(self, db: aiosqlite.Connection) -> None:
        ...