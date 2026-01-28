import discord
from discord.ext import commands
from discord import app_commands
import aiosqlite

DB_NAME = "bot.db"

class Welcome(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ---------------- SETUP COMMAND ----------------
    @app_commands.command(name="welcome_setup", description="Setup welcome system")
    @app_commands.checks.has_permissions(administrator=True)
    async def welcome_setup(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        role: discord.Role,
        message: str,
        mode: str  # text or embed
    ):
        if mode not in ["text", "embed"]:
            return await interaction.response.send_message(
                "❌ Mode must be `text` or `embed`",
                ephemeral=True
            )

        async with aiosqlite.connect(DB_NAME) as db:
            await db.execute("""
            INSERT OR REPLACE INTO guild_settings
            (guild_id, welcome_channel, welcome_role, welcome_message, welcome_mode)
            VALUES (?, ?, ?, ?, ?)
            """, (
                interaction.guild.id,
                channel.id,
                role.id,
                message,
                mode
            ))
            await db.commit()

        await interaction.response.send_message("✅ Welcome system configured!", ephemeral=True)

    # ---------------- PREVIEW COMMAND ----------------
    @app_commands.command(name="welcome_preview", description="Preview welcome message")
    @app_commands.checks.has_permissions(administrator=True)
    async def welcome_preview(self, interaction: discord.Interaction):
        async with aiosqlite.connect(DB_NAME) as db:
            cursor = await db.execute("""
            SELECT welcome_message, welcome_mode
            FROM guild_settings WHERE guild_id=?
            """, (interaction.guild.id,))
            row = await cursor.fetchone()

        if not row:
            return await interaction.response.send_message(
                "❌ Welcome system not configured.",
                ephemeral=True
            )

        message, mode = row

        if mode == "embed":
            embed = discord.Embed(
                title="🎉 Welcome Preview",
                description=message.format(
                    user=interaction.user.mention,
                    server=interaction.guild.name
                ),
                color=discord.Color.green()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(
                message.format(
                    user=interaction.user.mention,
                    server=interaction.guild.name
                ),
                ephemeral=True
            )

    # ---------------- MEMBER JOIN EVENT ----------------
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        async with aiosqlite.connect(DB_NAME) as db:
            cursor = await db.execute("""
            SELECT welcome_channel, welcome_role, welcome_message, welcome_mode
            FROM guild_settings WHERE guild_id=?
            """, (member.guild.id,))
            row = await cursor.fetchone()

        if not row:
            return

        channel_id, role_id, message, mode = row
        channel = member.guild.get_channel(channel_id)

        # ✅ Auto role
        role = member.guild.get_role(role_id)
        if role:
            try:
                await member.add_roles(role)
            except:
                pass

        # ✅ DM Welcome
        try:
            dm_text = (
                f"👋 Welcome to **{member.guild.name}**!\n\n"
                f"{message.format(user=member.name, server=member.guild.name)}\n\n"
                "Enjoy your stay 💖"
            )
            await member.send(dm_text)
        except:
            print(f"❌ Could not DM {member.name}")

        # ✅ Server Welcome
        if not channel:
            return

        if mode == "embed":
            embed = discord.Embed(
                title="🎉 Welcome!",
                description=message.format(
                    user=member.mention,
                    server=member.guild.name
                ),
                color=discord.Color.green()
            )
            await channel.send(embed=embed)
        else:
            await channel.send(
                message.format(
                    user=member.mention,
                    server=member.guild.name
                )
            )

# ---------------- SETUP ----------------
async def setup(bot: commands.Bot):
    await bot.add_cog(Welcome(bot))
