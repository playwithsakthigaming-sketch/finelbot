import discord
from discord.ext import commands
import asyncio, os
from dotenv import load_dotenv
from utils.db import init_db

load_dotenv()

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.voice_states = True

class MyBot(commands.Bot):
    async def setup_hook(self):
        # Load cogs
        for cog in COGS:
            try:
                await self.load_extension(cog)
                print(f"✅ Loaded {cog}")
            except Exception as e:
                print(f"❌ Failed to load {cog}: {e}")

        # Sync slash commands
        await self.tree.sync()
        print("✅ Slash commands synced")

bot = MyBot(command_prefix="!", intents=intents)

COGS = [
    "cogs.welcome",
    "cogs.tickets",
    "cogs.economy",
    "cogs.levels",
    "cogs.themes",
    "cogs.premium",
    "cogs.payment",
    "cogs.coin_shop",
    "cogs.announce",
    "cogs.moderation",
    "cogs.music",
    "cogs.coupons",
    "cogs.youtube"
]

@bot.event
async def on_ready():
    print(f"🤖 Logged in as {bot.user}")
    await init_db()
    print("✅ Bot fully ready")

async def main():
    await bot.start(os.getenv("DISCORD_TOKEN"))

asyncio.run(main())
