import discord
import aiosqlite
from discord.ext import commands
from discord import app_commands

# =========================================================
# WELCOME COG
# =========================================================

class Welcome(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # -----------------------------------------------------
    # /welcome_setup COMMAND
    # -----------------------------------------------------
    @app_commands.command(
        name="welcome_setup",
        description="🎉 Setup welcome & auto-role system"
    )
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(
        welcome_channel="Channel for welcome messages",
        auto_role="Role to give on join (optional)",
        goodbye_channel="Channel for goodbye messages (optional)"
    )
    async def welcome_setup(
        self,
        interaction: discord.Interaction,
        welcome_channel: discord.TextChannel,
        auto_role: discord.Role | None = None,
        goodbye_channel: discord.TextChannel | None = None
    ):
        async with aiosqlite.connect("bot.db") as db:
            await db.execute(
                """
                INSERT INTO guild_settings
                (guild_id, welcome_channel, welcome_role, goodbye_channel)
                VALUES (?,?,?,?)
                ON CONFLICT(guild_id)
                DO UPDATE SET
                    welcome_channel=excluded.welcome_channel,
                    welcome_role=excluded.welcome_role,
                    goodbye_channel=excluded.goodbye_channel
                """,
                (
                    interaction.guild.id,
                    welcome_channel.id,
                    auto_role.id if auto_role else None,
                    goodbye_channel.id if goodbye_channel else None
                )
            )
            await db.commit()

        await interaction.response.send_message(
            "✅ **Welcome system configured successfully!**",
            ephemeral=True
        )

    # -----------------------------------------------------
    # MEMBER JOIN EVENT
    # -----------------------------------------------------
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        async with aiosqlite.connect("bot.db") as db:
            cur = await db.execute(
                """
                SELECT welcome_channel, welcome_role
                FROM guild_settings
                WHERE guild_id=?
                """,
                (member.guild.id,)
            )
            data = await cur.fetchone()

        if not data:
            return

        welcome_channel_id, role_id = data

        # ---------- AUTO ROLE ----------
        if role_id:
            role = member.guild.get_role(role_id)
            if role:
                try:
                    await member.add_roles(role, reason="Auto role on join")
                except:
                    pass

        # ---------- WELCOME MESSAGE ----------
        welcome_text = (
            "🎉 Welcome {user} to **{server}**!\n"
            "👥 You are member **#{count}**\n"
            "Enjoy your stay ❤️"
        )

        message = (
            welcome_text
            .replace("{user}", member.mention)
            .replace("{server}", member.guild.name)
            .replace("{count}", str(member.guild.member_count))
        )

        channel = member.guild.get_channel(welcome_channel_id)
        if channel:
            try:
                await channel.send(message)
            except:
                pass

        # ---------- DM WELCOME ----------
        try:
            await member.send(
                f"👋 **Welcome to {member.guild.name}!**\n\n"
                "🤖 **PSG Family Bot Features**\n"
                "🎫 Ticket Support\n"
                "🪙 Coins & Premium System\n"
                "🎨 Rank Cards & Themes\n"
                "🎞️ Animated Rank Cards (Premium)\n"
                "🎵 Music Commands\n"
                "📢 Announcements\n\n"
                "Type `/help` to see all commands.\n"
                "Have fun! ❤️"
            )
        except:
            pass

    # -----------------------------------------------------
    # MEMBER LEAVE EVENT
    # -----------------------------------------------------
    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        async with aiosqlite.connect("bot.db") as db:
            cur = await db.execute(
                """
                SELECT goodbye_channel
                FROM guild_settings
                WHERE guild_id=?
                """,
                (member.guild.id,)
            )
            data = await cur.fetchone()

        if not data or not data[0]:
            return

        channel = member.guild.get_channel(data[0])
        if channel:
            try:
                await channel.send(
                    f"👋 **{member.name}** has left the server."
                )
            except:
                pass

# =========================================================
# SETUP
# =========================================================

async def setup(bot: commands.Bot):
    await bot.add_cog(Welcome(bot))
