# cogs/help.py
import discord
from discord.ext import commands
from discord import app_commands

class HelpView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=60)
        self.bot = bot

    @discord.ui.select(
        placeholder="Select category",
        options=[
            discord.SelectOption(label="Admin", value="admin"),
            discord.SelectOption(label="Moderation", value="moderation"),
            discord.SelectOption(label="Economy", value="economy"),
            discord.SelectOption(label="Fun", value="fun"),
        ]
    )
    async def select_callback(self, interaction: discord.Interaction, select: discord.ui.Select):
        category = select.values[0]

        embed = discord.Embed(title=f"📖 Help - {category.title()}", color=discord.Color.blue())

        for cmd in self.bot.tree.get_commands():
            if category == "admin" and "admin" in cmd.name:
                embed.add_field(name=f"/{cmd.name}", value=cmd.description or "No description", inline=False)
            elif category == "moderation" and cmd.name in ["ban", "kick", "warn", "timeout"]:
                embed.add_field(name=f"/{cmd.name}", value=cmd.description or "No description", inline=False)
            elif category == "economy" and cmd.name in ["balance", "coin_shop_panel", "add_coins"]:
                embed.add_field(name=f"/{cmd.name}", value=cmd.description or "No description", inline=False)
            elif category == "fun":
                embed.add_field(name=f"/{cmd.name}", value=cmd.description or "No description", inline=False)

        await interaction.response.edit_message(embed=embed, view=self)


class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="help", description="Show help menu")
    async def help(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🤖 Bot Help Menu",
            description="Select a category from the dropdown below",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed, view=HelpView(self.bot))


async def setup(bot: commands.Bot):
    await bot.add_cog(Help(bot))
