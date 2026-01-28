# cogs/premium.py
import discord, time, os
from discord.ext import commands, tasks
from discord import app_commands
from supabase import create_client

supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

TIERS = {
    "bronze": 3,
    "silver": 5,
    "gold": 7
}

class Premium(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_expiry.start()

    # ---------------- BUY PREMIUM ----------------
    @app_commands.command(name="buy_premium", description="Buy premium tier")
    async def buy_premium(self, interaction: discord.Interaction, tier: str):
        if tier not in TIERS:
            return await interaction.response.send_message("❌ Tier must be bronze/silver/gold")

        days = TIERS[tier]
        expires = int(time.time()) + (days * 86400)

        supabase.table("premium").upsert({
            "user_id": interaction.user.id,
            "tier": tier,
            "expires": expires
        }).execute()

        await interaction.response.send_message(
            f"✅ {interaction.user.mention} bought **{tier.upper()}** premium for {days} days"
        )

    # ---------------- CHECK PREMIUM ----------------
    @app_commands.command(name="premium_status", description="Check premium status")
    async def premium_status(self, interaction: discord.Interaction):
        res = supabase.table("premium").select("*").eq("user_id", interaction.user.id).execute()

        if not res.data:
            return await interaction.response.send_message("❌ You have no premium")

        data = res.data[0]
        remaining = data["expires"] - int(time.time())
        days = remaining // 86400

        await interaction.response.send_message(
            f"⭐ Tier: {data['tier']}\n⏳ Days left: {days}"
        )

    # ---------------- AUTO EXPIRY ----------------
    @tasks.loop(minutes=10)
    async def check_expiry(self):
        now = int(time.time())
        res = supabase.table("premium").select("*").execute()

        for row in res.data:
            if row["expires"] <= now:
                supabase.table("premium").delete().eq("user_id", row["user_id"]).execute()

    @check_expiry.before_loop
    async def before_loop(self):
        await self.bot.wait_until_ready()


async def setup(bot):
    await bot.add_cog(Premium(bot))
