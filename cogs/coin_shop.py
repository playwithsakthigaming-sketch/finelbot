import discord
from discord.ext import commands
from discord import app_commands
from supabase import create_client
import os
import time

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

TIERS = {
    "Bronze": 100,
    "Silver": 200,
    "Gold": 300
}

class CoinShop(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ---------------- PANEL ----------------
    @app_commands.command(name="coin_shop_panel", description="Create coin shop panel")
    @app_commands.checks.has_permissions(administrator=True)
    async def coin_shop_panel(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🛒 PSG Coin Shop",
            description=(
                "Bronze – 100 coins\n"
                "Silver – 200 coins\n"
                "Gold – 300 coins\n\n"
                "Click button to buy premium"
            ),
            color=discord.Color.gold()
        )

        view = discord.ui.View(timeout=None)

        for tier in TIERS:
            btn = discord.ui.Button(label=tier, style=discord.ButtonStyle.primary)
            async def callback(inter, t=tier):
                await self.buy_premium(inter, t)
            btn.callback = callback
            view.add_item(btn)

        await interaction.channel.send(embed=embed, view=view)
        await interaction.response.send_message("✅ Coin shop panel created", ephemeral=True)

    # ---------------- BUY ----------------
    async def buy_premium(self, interaction: discord.Interaction, tier: str):
        user_id = interaction.user.id
        cost = TIERS[tier]

        res = supabase.table("coins").select("*").eq("user_id", user_id).execute()
        balance = res.data[0]["balance"] if res.data else 0

        if balance < cost:
            return await interaction.response.send_message(
                f"❌ Not enough coins. Need {cost}",
                ephemeral=True
            )

        # Deduct coins
        supabase.table("coins").update(
            {"balance": balance - cost}
        ).eq("user_id", user_id).execute()

        # Add premium
        supabase.table("premium").upsert({
            "user_id": user_id,
            "tier": tier,
            "expires": int(time.time()) + (86400 * 7)
        }).execute()

        await interaction.response.send_message(
            f"✅ You bought **{tier} Premium**!",
            ephemeral=True
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(CoinShop(bot))
