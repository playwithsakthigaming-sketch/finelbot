import discord
import os, sys
from discord.ext import commands
from discord import app_commands


class Admin(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ================= PING =================
    @app_commands.command(name="ping", description="Show bot latency")
    async def ping(self, interaction: discord.Interaction):
        latency = round(self.bot.latency * 1000)
        await interaction.response.send_message(f"🏓 Pong! `{latency}ms`")

    # ================= RESTART =================
    @app_commands.command(name="restart", description="Restart the bot (Admin only)")
    async def restart(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message(
                "❌ Admin only.", ephemeral=True
            )

        await interaction.response.send_message("♻️ Restarting bot...", ephemeral=True)

        # Restart process
        os.execv(sys.executable, ["python"] + sys.argv)

    # ================= SYNC =================
    @app_commands.command(name="sync", description="Sync slash commands (Admin only)")
    async def sync(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message(
                "❌ Admin only.", ephemeral=True
            )

        await interaction.response.defer(ephemeral=True)
        await self.bot.tree.sync()
        await interaction.followup.send("✅ Slash commands synced successfully.")

    # ================= ERROR HANDLER =================
    @commands.Cog.listener()
    async def on_app_command_error(self, interaction: discord.Interaction, error):
        await interaction.response.send_message(
            f"❌ Error: {error}",
            ephemeral=True
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Admin(bot))
