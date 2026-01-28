import discord
from discord.ext import commands
import asyncio
import os
from dotenv import load_dotenv

from utils.db import init_db

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.voice_states = True

COGS = [
    "cogs.coin_shop",
    "cogs.levels",
    "cogs.coupons",
    "cogs.premium",
    "cogs.themes",
    "cogs.tickets",
    "cogs.youtube"
]

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await init_db()
        print("✅ Database initialized")

        for cog in COGS:
            try:
                await self.load_extension(cog)
                print(f"✅ Loaded {cog}")
            except Exception as e:
                print(f"❌ Failed to load {cog}: {e}")

        await self.tree.sync()
        print("✅ Slash commands synced")


bot = MyBot()


@bot.event
async def on_ready():
    print(f"🤖 Logged in as {bot.user}")


async def main():
    if not TOKEN:
        raise RuntimeError("❌ DISCORD_TOKEN not found in .env")

    async with bot:
        await bot.start(TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
