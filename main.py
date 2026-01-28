import discord
from discord.ext import commands
import os, asyncio
from dotenv import load_dotenv
from utils.supabase_db import init_db

load_dotenv()

intents = discord.Intents.all()

bot = commands.Bot(command_prefix="!", intents=intents)

COGS = [
    "cogs.welcome",
    "cogs.economy",
    "cogs.premium",
    "cogs.coin_shop",
    "cogs.payment",
    "cogs.levels",
    "cogs.tickets"
]

@bot.event
async def on_ready():
    print(f"🤖 Logged in as {bot.user}")
    await init_db()
    await bot.tree.sync()

async def load_cogs():
    for cog in COGS:
        await bot.load_extension(cog)

async def main():
    await load_cogs()
    await bot.start(os.getenv("DISCORD_TOKEN"))

asyncio.run(main())
