import discord
import os
from discord.ext import commands
from discord import app_commands
from supabase import create_client

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ================= CLEAR CHAT =================
    @app_commands.command(name="clear", description="Clear messages")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def clear(self, interaction: discord.Interaction, amount: int):
        if amount <= 0 or amount > 100:
            return await interaction.response.send_message(
                "❌ Amount must be between 1 and 100",
                ephemeral=True
            )

        await interaction.channel.purge(limit=amount)
        await interaction.response.send_message(
            f"✅ Cleared {amount} messages",
            ephemeral=True
        )

    # ================= CREATE CHANNEL =================
    @app_commands.command(name="create_channel", description="Create a channel")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def create_channel(
        self,
        interaction: discord.Interaction,
        name: str,
        category: discord.CategoryChannel = None
    ):
        channel = await interaction.guild.create_text_channel(
            name=name,
            category=category
        )
        await interaction.response.send_message(
            f"✅ Channel created: {channel.mention}",
            ephemeral=True
        )

    # ================= EDIT CHANNEL =================
    @app_commands.command(name="edit_channel", description="Edit channel name or topic")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def edit_channel(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        new_name: str = None,
        new_topic: str = None
    ):
        await channel.edit(name=new_name or channel.name, topic=new_topic)
        await interaction.response.send_message(
            f"✅ Channel updated: {channel.mention}",
            ephemeral=True
        )

    # ================= DELETE CHANNEL =================
    @app_commands.command(name="delete_channel", description="Delete a channel")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def delete_channel(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel
    ):
        await channel.delete()
        await interaction.response.send_message(
            "✅ Channel deleted",
            ephemeral=True
        )

    # ================= ADD CUSTOM COMMAND =================
    @app_commands.command(name="add_command", description="Add custom command")
    @app_commands.checks.has_permissions(administrator=True)
    async def add_command(
        self,
        interaction: discord.Interaction,
        name: str,
        response: str
    ):
        supabase.table("custom_commands").upsert({
            "name": name.lower(),
            "response": response
        }).execute()

        await interaction.response.send_message(
            f"✅ Custom command `/{name}` added",
            ephemeral=True
        )

    # ================= RUN CUSTOM COMMAND =================
    @app_commands.command(name="custom", description="Run a custom command")
    async def custom(self, interaction: discord.Interaction, name: str):
        res = supabase.table("custom_commands").select("*").eq(
            "name", name.lower()
        ).execute()

        if not res.data:
            return await interaction.response.send_message(
                "❌ Command not found",
                ephemeral=True
            )

        await interaction.response.send_message(res.data[0]["response"])

    # ================= ADD EMOJI =================
    @app_commands.command(name="add_emoji", description="Add emoji to server")
    @app_commands.checks.has_permissions(manage_emojis=True)
    async def add_emoji(
        self,
        interaction: discord.Interaction,
        name: str,
        image_url: str
    ):
        try:
            import requests
            from io import BytesIO

            r = requests.get(image_url)
            img = BytesIO(r.content)

            emoji = await interaction.guild.create_custom_emoji(
                name=name,
                image=img.read()
            )

            await interaction.response.send_message(
                f"✅ Emoji created: {emoji}",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Failed to create emoji:\n{e}",
                ephemeral=True
            )


# ================= SETUP =================
async def setup(bot: commands.Bot):
    await bot.add_cog(Admin(bot))
