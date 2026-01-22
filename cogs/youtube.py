import discord
import aiosqlite
from discord.ext import commands, tasks
from discord import app_commands

# =========================================================
# CONFIG
# =========================================================

CHECK_INTERVAL_MINUTES = 10   # placeholder loop
ALERT_ROLE_MENTION = None    # set role ID or None

# =========================================================
# COG
# =========================================================

class YouTube(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.check_loop.start()

    # -----------------------------------------------------
    # /setup_channel
    # -----------------------------------------------------
    @app_commands.command(
        name="setup_channel",
        description="🔔 Setup YouTube alerts"
    )
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(
        youtube_channel="YouTube channel URL",
        discord_channel="Discord channel for alerts"
    )
    async def setup_channel(
        self,
        interaction: discord.Interaction,
        youtube_channel: str,
        discord_channel: discord.TextChannel
    ):
        async with aiosqlite.connect("bot.db") as db:
            await db.execute(
                """
                INSERT INTO youtube_alerts
                (guild_id, youtube_channel, discord_channel)
                VALUES (?,?,?)
                ON CONFLICT(guild_id)
                DO UPDATE SET
                    youtube_channel=excluded.youtube_channel,
                    discord_channel=excluded.discord_channel
                """,
                (
                    interaction.guild.id,
                    youtube_channel,
                    discord_channel.id
                )
            )
            await db.commit()

        await interaction.response.send_message(
            f"✅ YouTube alerts configured!\n"
            f"📺 Channel: {youtube_channel}\n"
            f"📢 Alerts → {discord_channel.mention}",
            ephemeral=True
        )

    # -----------------------------------------------------
    # /remove_channel
    # -----------------------------------------------------
    @app_commands.command(
        name="remove_channel",
        description="❌ Remove YouTube alerts"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def remove_channel(self, interaction: discord.Interaction):
        async with aiosqlite.connect("bot.db") as db:
            await db.execute(
                "DELETE FROM youtube_alerts WHERE guild_id=?",
                (interaction.guild.id,)
            )
            await db.commit()

        await interaction.response.send_message(
            "❌ YouTube alerts removed.",
            ephemeral=True
        )

    # -----------------------------------------------------
    # /youtube_status
    # -----------------------------------------------------
    @app_commands.command(
        name="youtube_status",
        description="📊 View YouTube alert status"
    )
    async def youtube_status(self, interaction: discord.Interaction):
        async with aiosqlite.connect("bot.db") as db:
            cur = await db.execute(
                "SELECT youtube_channel, discord_channel FROM youtube_alerts WHERE guild_id=?",
                (interaction.guild.id,)
            )
            row = await cur.fetchone()

        if not row:
            return await interaction.response.send_message(
                "❌ YouTube alerts not configured.",
                ephemeral=True
            )

        yt, ch = row
        channel = interaction.guild.get_channel(ch)

        embed = discord.Embed(
            title="📺 YouTube Alerts Status",
            color=discord.Color.red()
        )
        embed.add_field(name="YouTube Channel", value=yt, inline=False)
        embed.add_field(
            name="Alert Channel",
            value=channel.mention if channel else "Missing",
            inline=False
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    # -----------------------------------------------------
    # BACKGROUND CHECK LOOP (PLACEHOLDER)
    # -----------------------------------------------------
    @tasks.loop(minutes=CHECK_INTERVAL_MINUTES)
    async def check_loop(self):
        """
        SAFE PLACEHOLDER LOOP
        --------------------------------
        This is where you would:
        - Check RSS feed
        - Check PubSubHubbub webhook
        - Or manual admin trigger

        Left intentionally minimal
        to avoid ToS violations.
        """
        async with aiosqlite.connect("bot.db") as db:
            cur = await db.execute(
                "SELECT guild_id, youtube_channel, discord_channel FROM youtube_alerts"
            )
            rows = await cur.fetchall()

        for guild_id, yt, ch_id in rows:
            guild = self.bot.get_guild(guild_id)
            if not guild:
                continue

            channel = guild.get_channel(ch_id)
            if not channel:
                continue

            # Example placeholder message (disabled by default)
            # await channel.send(f"📢 New activity on {yt}")

            pass

    @check_loop.before_loop
    async def before_loop(self):
        await self.bot.wait_until_ready()

# =========================================================
# SETUP
# =========================================================

async def setup(bot: commands.Bot):
    await bot.add_cog(YouTube(bot))
