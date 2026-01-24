import discord
import aiohttp
import re
import os
import aiosqlite
from discord.ext import commands, tasks
from discord import app_commands

DB_NAME = "bot.db"
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

YOUTUBE_CHANNEL_REGEX = r"(?:youtube\.com\/(?:channel\/|@))([a-zA-Z0-9_-]+)"


# ================= HELPER =================
def extract_channel_id(url: str):
    match = re.search(YOUTUBE_CHANNEL_REGEX, url)
    if match:
        return match.group(1)
    return None


# ================= COG =================
class YouTubeAlerts(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_live.start()

    def cog_unload(self):
        self.check_live.cancel()

    # =================================================
    # /setup_channel (ADMIN ONLY)
    # =================================================
    @app_commands.command(name="setup_channel", description="Add YouTube live notifications")
    @app_commands.describe(
        youtube_url="YouTube channel URL",
        discord_channel="Discord channel for alerts",
        role="Role to ping",
        message="Custom message"
    )
    async def setup_channel(
        self,
        interaction: discord.Interaction,
        youtube_url: str,
        discord_channel: discord.TextChannel,
        role: discord.Role,
        message: str
    ):
        await interaction.response.defer(ephemeral=True)

        if not interaction.user.guild_permissions.administrator:
            return await interaction.followup.send("❌ Admin only.")

        channel_id = extract_channel_id(youtube_url)
        if not channel_id:
            return await interaction.followup.send("❌ Invalid YouTube channel URL.")

        try:
            async with aiosqlite.connect(DB_NAME) as db:
                await db.execute("""
                    INSERT OR REPLACE INTO youtube_alerts 
                    (guild_id, youtube_channel, discord_channel, role_id, message, last_video)
                    VALUES (?,?,?,?,?,?)
                """, (interaction.guild.id, channel_id, discord_channel.id, role.id, message, ""))
                await db.commit()

            await interaction.followup.send(
                f"✅ YouTube alerts set for `{youtube_url}` in {discord_channel.mention}"
            )

        except Exception as e:
            await interaction.followup.send(f"❌ Error:\n```{e}```")

    # =================================================
    # LIVE CHECK LOOP
    # =================================================
    @tasks.loop(minutes=2)
    async def check_live(self):
        await self.bot.wait_until_ready()

        async with aiosqlite.connect(DB_NAME) as db:
            async with db.execute("SELECT * FROM youtube_alerts") as cursor:
                rows = await cursor.fetchall()

        for guild_id, yt_channel, discord_channel_id, role_id, message, last_video in rows:
            try:
                video = await self.fetch_live_video(yt_channel)
                if not video:
                    continue

                video_id = video["id"]["videoId"]
                title = video["snippet"]["title"]
                thumb = video["snippet"]["thumbnails"]["high"]["url"]
                url = f"https://youtube.com/watch?v={video_id}"

                if video_id == last_video:
                    continue  # already sent

                embed = discord.Embed(
                    title="🔴 LIVE NOW!",
                    description=f"**{title}**\n\n{message}",
                    color=discord.Color.red()
                )
                embed.set_thumbnail(url=thumb)
                embed.add_field(name="Watch Here", value=url)

                guild = self.bot.get_guild(guild_id)
                if not guild:
                    continue

                channel = guild.get_channel(discord_channel_id)
                role = guild.get_role(role_id)

                if not channel:
                    continue

                await channel.send(
                    content=role.mention if role else None,
                    embed=embed
                )

                async with aiosqlite.connect(DB_NAME) as db:
                    await db.execute(
                        "UPDATE youtube_alerts SET last_video=? WHERE guild_id=? AND youtube_channel=?",
                        (video_id, guild_id, yt_channel)
                    )
                    await db.commit()

            except Exception as e:
                print(f"YouTube alert error: {e}")

    # =================================================
    # FETCH LIVE VIDEO
    # =================================================
    async def fetch_live_video(self, channel_id: str):
        url = (
            "https://www.googleapis.com/youtube/v3/search"
            f"?part=snippet&channelId={channel_id}&eventType=live&type=video&key={YOUTUBE_API_KEY}"
        )

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()

        if "items" not in data or len(data["items"]) == 0:
            return None

        return data["items"][0]


# ================= SETUP =================
async def setup(bot: commands.Bot):
    await bot.add_cog(YouTubeAlerts(bot))
