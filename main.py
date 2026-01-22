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

bot = commands.Bot(command_prefix="!", intents=intents)

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
    "cogs.youtube"
]

async def load_all():
    for cog in COGS:
        try:
            await bot.load_extension(cog)
            print(f"✅ Loaded {cog}")
        except Exception as e:
            print(f"❌ Failed to load {cog}: {e}")

@bot.event
async def on_ready():
    print(f"🤖 Logged in as {bot.user}")
    await init_db()
    await bot.tree.sync()
    print("✅ Bot fully ready")

async def main():
    await load_all()
    await bot.start(os.getenv("DISCORD_TOKEN"))

asyncio.run(main())
