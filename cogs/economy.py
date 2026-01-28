import discord
from discord.ext import commands
from discord import app_commands
from utils.supabase_db import get_coins, set_coins

class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="balance")
    async def balance(self, interaction: discord.Interaction):
        bal = await get_coins(interaction.user.id)
        await interaction.response.send_message(f"💰 Balance: {bal}")

    @app_commands.command(name="addcoins")
    @app_commands.checks.has_permissions(administrator=True)
    async def addcoins(self, interaction: discord.Interaction, member: discord.Member, amount: int):
        bal = await get_coins(member.id)
        await set_coins(member.id, bal + amount)
        await interaction.response.send_message("✅ Coins added")

async def setup(bot):
    await bot.add_cog(Economy(bot))
