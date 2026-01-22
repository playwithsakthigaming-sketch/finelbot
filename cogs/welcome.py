import discord
import aiosqlite
from discord.ext import commands
from discord import app_commands

# =========================================================
# PLACEHOLDERS
# =========================================================
# {user}   -> user mention
# {server} -> server name
# {count}  -> member count

# =========================================================
# WELCOME COG
# =========================================================

class Welcome(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # -----------------------------------------------------
    # /welcome_setup
    # -----------------------------------------------------
    @app_commands.command(
        name="welcome_setup",
        description="🎉 Setup welcome system"
    )
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(
        welcome_channel="Channel for welcome messages",
        auto_role="Role to give on join (optional)",
        goodbye_channel="Channel for goodbye messages (optional)",
        welcome_message="Custom welcome message (placeholders supported)",
        background_image="Background image URL (optional)",
        mode="embed or text"
    )
    async def welcome_setup(
        self,
        interaction: discord.Interaction,
        welcome_channel: discord.TextChannel,
        auto_role: discord.Role | None = None,
        goodbye_channel: discord.TextChannel | None = None,
        welcome_message: str = "🎉 Welcome {user} to **{server}**! You are member #{count}",
        background_image: str | None = None,
        mode: str = "embed"
    ):
        mode = mode.lower()
        if mode not in ["embed", "text"]:
            return await interaction.response.send_message(
                "❌ Mode must be `embed` or `text`",
                ephemeral=True
            )

        async with aiosqlite.connect("bot.db") as db:
            await db.execute(
                """
                INSERT INTO guild_settings
                (guild_id, welcome_channel, welcome_role, goodbye_channel,
                 welcome_message, welcome_bg, welcome_mode)
                VALUES (?,?,?,?,?,?,?)
                ON CONFLICT(guild_id)
                DO UPDATE SET
                    welcome_channel=excluded.welcome_channel,
                    welcome_role=excluded.welcome_role,
                    goodbye_channel=excluded.goodbye_channel,
                    welcome_message=excluded.welcome_message,
                    welcome_bg=excluded.welcome_bg,
                    welcome_mode=excluded.welcome_mode
                """,
                (
                    interaction.guild.id,
                    welcome_channel.id,
                    auto_role.id if auto_role else None,
                    goodbye_channel.id if goodbye_channel else None,
                    welcome_message,
                    background_image,
                    mode
                )
            )
            await db.commit()

        await interaction.response.send_message(
            "✅ **Welcome system configured successfully!**",
            ephemeral=True
        )

    # -----------------------------------------------------
    # MEMBER JOIN
    # -----------------------------------------------------
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        async with aiosqlite.connect("bot.db") as db:
            cur = await db.execute(
                """
                SELECT welcome_channel, welcome_role, welcome_message,
                       welcome_bg, welcome_mode
                FROM guild_settings
                WHERE guild_id=?
                """,
                (member.guild.id,)
            )
            data = await cur.fetchone()

        if not data:
            return

        channel_id, role_id, message, bg, mode = data

        # ---------- AUTO ROLE ----------
        if role_id:
            role = member.guild.get_role(role_id)
            if role:
                try:
                    await member.add_roles(role, reason="Auto role on join")
                except:
                    pass

        # ---------- FORMAT MESSAGE ----------
        text = (
            message
            .replace("{user}", member.mention)
            .replace("{server}", member.guild.name)
            .replace("{count}", str(member.guild.member_count))
        )

        channel = member.guild.get_channel(channel_id)
        if not channel:
            return

        # ---------- SEND WELCOME ----------
        try:
            if mode == "text":
                await channel.send(text)
            else:
                embed = discord.Embed(
                    description=text,
                    color=discord.Color.green()
                )
                embed.set_author(
                    name=f"Welcome {member.name}",
                    icon_url=member.display_avatar.url
                )
                if bg:
                    embed.set_image(url=bg)

                await channel.send(embed=embed)
        except:
            pass

        # ---------- DM WELCOME ----------
        try:
            await member.send(
                f"👋 **Welcome to {member.guild.name}!**\n\n"
                "🤖 **PSG Family Bot Features**\n"
                "🎫 Tickets & Support\n"
                "🪙 Coins & Premium\n"
                "🎞️ Animated Rank Cards\n"
                "🎨 Themes & Shop\n"
                "🎵 Music\n"
                "🛡 Moderation\n\n"
                "Type `/help` to see all commands ❤️"
            )
        except:
            pass

    # -----------------------------------------------------
    # MEMBER LEAVE
    # -----------------------------------------------------
    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        async with aiosqlite.connect("bot.db") as db:
            cur = await db.execute(
                "SELECT goodbye_channel FROM guild_settings WHERE guild_id=?",
                (member.guild.id,)
            )
            row = await cur.fetchone()

        if not row or not row[0]:
            return

        channel = member.guild.get_channel(row[0])
        if channel:
            try:
                await channel.send(
                    f"👋 **{member.name}** left the server."
                )
            except:
                pass

# =========================================================
# SETUP
# =========================================================

async def setup(bot: commands.Bot):
    await bot.add_cog(Welcome(bot))
