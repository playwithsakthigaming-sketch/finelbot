# cogs/themes.py
import discord, os
from discord.ext import commands
from discord import app_commands
from supabase import create_client

supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

THEMES = ["default", "neon", "dark", "gold"]

class Themes(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="themes", description="Show themes")
    async def themes(self, interaction: discord.Interaction):
        embed = discord.Embed(title="🎨 Themes", description="\n".join(THEMES))
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="set_theme", description="Set your theme")
    async def set_theme(self, interaction: discord.Interaction, theme: str):
        if theme not in THEMES:
            return await interaction.response.send_message("❌ Invalid theme")

        supabase.table("user_themes").upsert({
            "user_id": interaction.user.id,
            "theme": theme
        }).execute()

        await interaction.response.send_message(f"✅ Theme set to **{theme}**")


async def setup(bot):
    await bot.add_cog(Themes(bot))
