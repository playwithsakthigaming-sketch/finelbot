import discord
import os
from discord.ext import commands
from discord import app_commands
from supabase import create_client

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ================= VIEW =================
class CoinShopView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="💰 Buy Coins",
        style=discord.ButtonStyle.success,
        custom_id="coinshop_buy"
    )
    async def buy(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = interaction.user.id

        # create user if not exists
        supabase.table("coins").upsert({
            "user_id": user_id,
            "balance": 0
        }).execute()

        await interaction.response.send_message(
            "💳 To buy coins, please contact an admin and use `/confirm_payment`.",
            ephemeral=True
        )


# ================= COG =================
class CoinShop(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ---------------- PANEL ----------------
    @app_commands.command(name="coin_shop_panel", description="Create coin shop panel")
    @app_commands.checks.has_permissions(administrator=True)
    async def coin_shop_panel(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🛒 PSG Coin Shop",
            description=(
                "💱 **Rate:** ₹2 = 6 PSG Coins\n\n"
                "Click the button below to buy coins."
            ),
            color=discord.Color.gold()
        )

        await interaction.channel.send(embed=embed, view=CoinShopView())
        await interaction.response.send_message(
            "✅ Coin shop panel created.",
            ephemeral=True
        )

    # ---------------- BALANCE ----------------
    @app_commands.command(name="balance", description="Check your coin balance")
    async def balance(self, interaction: discord.Interaction):
        res = supabase.table("coins").select("*").eq(
            "user_id", interaction.user.id
        ).execute()

        if not res.data:
            return await interaction.response.send_message(
                "❌ You have no coins yet.",
                ephemeral=True
            )

        bal = res.data[0]["balance"]

        embed = discord.Embed(
            title="💰 Your Coin Balance",
            description=f"**{bal} PSG Coins**",
            color=discord.Color.green()
        )

        await interaction.response.send_message(embed=embed)


# ================= SETUP =================
async def setup(bot: commands.Bot):
    bot.add_view(CoinShopView())   # persistent button
    await bot.add_cog(CoinShop(bot))
