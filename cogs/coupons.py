# cogs/coupons.py
import discord
from discord.ext import commands
from discord import app_commands
from supabase import create_client
import os, time

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

class Coupons(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ---------------- CREATE COUPON ----------------
    @app_commands.command(name="create_coupon", description="Create coupon")
    @app_commands.checks.has_permissions(administrator=True)
    async def create_coupon(
        self,
        interaction: discord.Interaction,
        code: str,
        value: int,
        max_uses: int,
        days_valid: int
    ):
        expires = int(time.time()) + (days_valid * 86400)

        supabase.table("coupons").insert({
            "code": code.upper(),
            "value": value,
            "max_uses": max_uses,
            "used": 0,
            "expires": expires
        }).execute()

        await interaction.response.send_message(f"✅ Coupon `{code}` created")

    # ---------------- REDEEM COUPON ----------------
    @app_commands.command(name="redeem_coupon", description="Redeem coupon")
    async def redeem_coupon(self, interaction: discord.Interaction, code: str):
        res = supabase.table("coupons").select("*").eq("code", code.upper()).execute()

        if not res.data:
            return await interaction.response.send_message("❌ Invalid coupon")

        coupon = res.data[0]

        if coupon["used"] >= coupon["max_uses"]:
            return await interaction.response.send_message("❌ Coupon limit reached")

        if coupon["expires"] < int(time.time()):
            return await interaction.response.send_message("❌ Coupon expired")

        # Add coins
        coin = supabase.table("coins").select("*").eq("user_id", interaction.user.id).execute()

        if not coin.data:
            supabase.table("coins").insert({
                "user_id": interaction.user.id,
                "balance": coupon["value"]
            }).execute()
        else:
            supabase.table("coins").update({
                "balance": coin.data[0]["balance"] + coupon["value"]
            }).eq("user_id", interaction.user.id).execute()

        supabase.table("coupons").update({
            "used": coupon["used"] + 1
        }).eq("code", code.upper()).execute()

        await interaction.response.send_message(
            f"🎉 Coupon redeemed! You got **{coupon['value']} coins**"
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Coupons(bot))
