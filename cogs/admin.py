import discord
from discord.ext import commands
from discord import app_commands
import os, asyncio

class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # =========================
    # PING
    # =========================
    @app_commands.command(name="ping", description="Check bot latency")
    async def ping(self, interaction: discord.Interaction):
        latency = round(self.bot.latency * 1000)
        await interaction.response.send_message(f"🏓 Pong! `{latency}ms`")

    # =========================
    # CLEAR CHAT
    # =========================
    @app_commands.command(name="clear", description="Clear messages")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def clear(self, interaction: discord.Interaction, amount: int):
        if amount <= 0 or amount > 100:
            return await interaction.response.send_message(
                "❌ Amount must be between 1 and 100.",
                ephemeral=True
            )

        await interaction.channel.purge(limit=amount)
        await interaction.response.send_message(
            f"✅ Deleted {amount} messages.",
            ephemeral=True
        )

    # =========================
    # CREATE CHANNEL
    # =========================
    @app_commands.command(name="create_channel", description="Create a new channel")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def create_channel(
        self,
        interaction: discord.Interaction,
        name: str,
        channel_type: str  # text / voice
    ):
        guild = interaction.guild

        if channel_type.lower() == "text":
            channel = await guild.create_text_channel(name)
        elif channel_type.lower() == "voice":
            channel = await guild.create_voice_channel(name)
        else:
            return await interaction.response.send_message(
                "❌ channel_type must be `text` or `voice`",
                ephemeral=True
            )

        await interaction.response.send_message(
            f"✅ Channel created: {channel.mention}"
        )

    # =========================
    # EDIT CHANNEL NAME
    # =========================
    @app_commands.command(name="edit_channel", description="Rename a channel")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def edit_channel(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        new_name: str
    ):
        await channel.edit(name=new_name)
        await interaction.response.send_message(
            f"✅ Channel renamed to `{new_name}`"
        )

    # =========================
    # DELETE CHANNEL
    # =========================
    @app_commands.command(name="delete_channel", description="Delete a channel")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def delete_channel(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel
    ):
        await interaction.response.send_message(
            f"⚠️ Deleting channel {channel.name}...",
            ephemeral=True
        )
        await channel.delete()

    # =========================
    # ADD EMOJI
    # =========================
    @app_commands.command(name="add_emoji", description="Add custom emoji")
    @app_commands.checks.has_permissions(manage_emojis=True)
    async def add_emoji(
        self,
        interaction: discord.Interaction,
        name: str,
        image_url: str
    ):
        try:
            async with self.bot.http._HTTPClient__session.get(image_url) as resp:
                img_bytes = await resp.read()

            emoji = await interaction.guild.create_custom_emoji(
                name=name,
                image=img_bytes
            )

            await interaction.response.send_message(
                f"✅ Emoji added: {emoji}"
            )
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Failed to add emoji: `{e}`",
                ephemeral=True
            )

    # =========================
    # RESTART BOT
    # =========================
    @app_commands.command(name="restart_bot", description="Restart the bot")
    @app_commands.checks.has_permissions(administrator=True)
    async def restart_bot(self, interaction: discord.Interaction):
        await interaction.response.send_message("♻️ Restarting bot...", ephemeral=True)
        os.execv(sys.executable, ["python"] + sys.argv)


# =========================
# SETUP
# =========================
async def setup(bot: commands.Bot):
    await bot.add_cog(Admin(bot))
