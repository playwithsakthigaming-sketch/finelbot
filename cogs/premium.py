import discord
import time
import os
from discord.ext import commands, tasks
from discord import app_commands
from supabase import create_client

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

TIERS = {
    "bronze": 3,
    "silver": 5,
    "gold": 7
}

class Premium(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.check_expiry.start()

    # ---------------- BUY PREMIUM ----------------
    @app_commands.command(name="buy_premium", description="Buy premium tier")
    async def buy_premium(self, interaction: discord.Interaction, tier: str):
        tier = tier.lower()

        if tier not in TIERS:
            return await interaction.response.send_message(
                "❌ Tier must be bronze, silver or gold",
                ephemeral=True
            )

        days = TIERS[tier]
        expires = int(time.time()) + days * 86400

        supabase.table("premium").upsert({
            "user_id": interaction.user.id,
            "tier": tier,
            "expires": expires
        }).execute()

        await interaction.response.send_message(
            f"✅ {interaction.user.mention} bought **{tier.upper()}** premium for {days} days"
        )

    # ---------------- STATUS ----------------
    @app_commands.command(name="premium_status", description="Check premium status")
    async def premium_status(self, interaction: discord.Interaction):
        res = supabase.table("premium").select("*").eq(
            "user_id", interaction.user.id
        ).execute()

        if not res.data:
            return await interaction.response.send_message(
                "❌ You have no premium",
                ephemeral=True
            )

        data = res.data[0]
        remaining = data["expires"] - int(time.time())
        days = max(0, remaining // 86400)

        await interaction.response.send_message(
            f"⭐ Tier: **{data['tier']}**\n⏳ Days left: **{days}**"
        )

    # ---------------- AUTO EXPIRY TASK ----------------
    @tasks.loop(minutes=5)
    async def check_expiry(self):
        now = int(time.time())
        res = supabase.table("premium").select("*").execute()

        for row in res.data:
            if row["expires"] <= now:
                supabase.table("premium").delete().eq(
                    "user_id", row["user_id"]
                ).execute()

    # ✅ FIXED before_loop
    @check_expiry.before_loop
    async def before_check_expiry(self):
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    await bot.add_cog(Premium(bot))
