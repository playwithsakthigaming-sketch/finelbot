import discord
from discord.ext import commands
from discord import app_commands

# =========================================================
# HELP VIEW (BUTTONS)
# =========================================================

class HelpView(discord.ui.View):
    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=120)
        self.bot = bot

        for cog_name in sorted(bot.cogs.keys()):
            self.add_item(HelpButton(cog_name))

class HelpButton(discord.ui.Button):
    def __init__(self, cog_name: str):
        super().__init__(
            label=cog_name.replace("_", " ").title(),
            style=discord.ButtonStyle.primary
        )
        self.cog_name = cog_name

    async def callback(self, interaction: discord.Interaction):
        commands_list = []

        for cmd in interaction.client.tree.get_commands():
            if cmd.binding and cmd.binding.__class__.__name__ == self.cog_name:
                commands_list.append(f"/{cmd.name} – {cmd.description}")

        if not commands_list:
            commands_list.append("No commands found.")

        embed = discord.Embed(
            title=f"📂 {self.cog_name.title()} Commands",
            description="\n".join(commands_list),
            color=discord.Color.gold()
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

# =========================================================
# HELP COG
# =========================================================

class Help(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="help",
        description="📖 View all bot commands"
    )
    async def help(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🤖 PSG Family Bot – Help Menu",
            description=(
                "Click a category button below to view commands.\n\n"
                "💎 Premium • 🎫 Tickets • 🪙 Economy • 🎨 Themes • 🎵 Music\n"
                "🛡 Moderation • 📢 Announce • 🔔 YouTube • 💳 Payments"
            ),
            color=discord.Color.gold()
        )

        await interaction.response.send_message(
            embed=embed,
            view=HelpView(self.bot),
            ephemeral=True
        )

# =========================================================
# SETUP
# =========================================================

async def setup(bot: commands.Bot):
    await bot.add_cog(Help(bot))
