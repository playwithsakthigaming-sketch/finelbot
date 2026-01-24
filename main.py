import discord
from discord.ext import commands, tasks
import asyncio
import os
from dotenv import load_dotenv

print("▶ loading env")
load_dotenv()
from utils.db import init_db
print("▶ importing utils") 

from utils.backup import backup_db

# =========================================================
# INTENTS
# =========================================================
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.voice_states = True

# =========================================================
# COG LIST
# =========================================================
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
    "cogs.coupons",
    "cogs.backup",
    "cogs.admin",
    "cogs.youtube"
]

# =========================================================
# BOT CLASS
# =========================================================
class MyBot(commands.Bot):
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

# =========================================================
# BOT INSTANCE
# =========================================================
bot = MyBot(command_prefix="!", intents=intents)

# =========================================================
# BACKUP TASK
# =========================================================
@tasks.loop(hours=6)
async def db_backup_loop():
    backup_db()
    print("💾 Database backup created")

@db_backup_loop.before_loop
async def before_backup():
    await bot.wait_until_ready()

# =========================================================
# EVENTS
# =========================================================
@bot.event
async def on_ready():
    print(f"🤖 Logged in as {bot.user}")
    if not db_backup_loop.is_running():
        db_backup_loop.start()
    print("✅ Bot fully ready")

# =========================================================
# START
# =========================================================
async def main():
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise RuntimeError("❌ DISCORD_TOKEN missing")
    await bot.start(token)

asyncio.run(main())
