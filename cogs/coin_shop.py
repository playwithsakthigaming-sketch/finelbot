# cogs/coin_shop.py
import discord
from discord.ext import commands
from discord import app_commands
from supabase import create_client
import os

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

class CoinShop(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ---------------- BALANCE ----------------
    @app_commands.command(name="balance", description="Check your coin balance")
    async def balance(self, interaction: discord.Interaction):
        res = supabase.table("coins").select("*").eq("user_id", interaction.user.id).execute()

        if not res.data:
            supabase.table("coins").insert({"user_id": interaction.user.id, "balance": 0}).execute()
            balance = 0
        else:
            balance = res.data[0]["balance"]

        await interaction.response.send_message(
            f"💰 {interaction.user.mention} you have **{balance} coins**"
        )

    # ---------------- ADD COINS (ADMIN) ----------------
    @app_commands.command(name="add_coins", description="Add coins to user (admin)")
    @app_commands.checks.has_permissions(administrator=True)
    async def add_coins(self, interaction: discord.Interaction, member: discord.Member, amount: int):
        if amount <= 0:
            return await interaction.response.send_message("❌ Amount must be positive", ephemeral=True)

        res = supabase.table("coins").select("*").eq("user_id", member.id).execute()
        if not res.data:
            supabase.table("coins").insert({"user_id": member.id, "balance": amount}).execute()
        else:
            supabase.table("coins").update(
                {"balance": res.data[0]["balance"] + amount}
            ).eq("user_id", member.id).execute()

        await interaction.response.send_message(f"✅ Added {amount} coins to {member.mention}")

    # ---------------- SHOP PANEL ----------------
    @app_commands.command(name="coin_shop_panel", description="Create coin shop panel")
    @app_commands.checks.has_permissions(administrator=True)
    async def coin_shop_panel(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🪙 PSG Coin Shop",
            description=(
                "Bronze – 100 coins\n"
                "Silver – 200 coins\n"
                "Gold – 300 coins\n\n"
                "Use `/balance` to check coins."
            ),
            color=discord.Color.gold()
        )
        await interaction.channel.send(embed=embed)
        await interaction.response.send_message("✅ Coin shop panel created", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(CoinShop(bot))
