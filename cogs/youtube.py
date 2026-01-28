# cogs/youtube.py
import discord, os, requests
from discord.ext import commands, tasks
from discord import app_commands
from supabase import create_client

supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

class YouTube(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_videos.start()

    @app_commands.command(name="setup_channel", description="Add YouTube alert")
    @app_commands.checks.has_permissions(administrator=True)
    async def setup_channel(
        self,
        interaction: discord.Interaction,
        youtube_channel: str,
        discord_channel: discord.TextChannel,
        role: discord.Role = None
    ):
        supabase.table("youtube_alerts").insert({
            "guild_id": interaction.guild.id,
            "youtube_channel": youtube_channel,
            "discord_channel": discord_channel.id,
            "role_ping": role.id if role else None,
            "last_video": ""
        }).execute()

        await interaction.response.send_message("✅ YouTube channel added")

    @app_commands.command(name="list_channels", description="List YouTube alerts")
    async def list_channels(self, interaction: discord.Interaction):
        res = supabase.table("youtube_alerts").select("*").eq(
            "guild_id", interaction.guild.id
        ).execute()

        embed = discord.Embed(title="📺 YouTube Alerts")
        for row in res.data:
            embed.add_field(
                name=row["youtube_channel"],
                value=f"<#{row['discord_channel']}>",
                inline=False
            )

        await interaction.response.send_message(embed=embed)

    @tasks.loop(minutes=5)
    async def check_videos(self):
        rows = supabase.table("youtube_alerts").select("*").execute().data

        for row in rows:
            url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&channelId={row['youtube_channel']}&order=date&maxResults=1&key={YOUTUBE_API_KEY}"
            r = requests.get(url).json()

            if "items" not in r:
                continue

            video_id = r["items"][0]["id"].get("videoId")
            if not video_id or video_id == row["last_video"]:
                continue

            supabase.table("youtube_alerts").update({
                "last_video": video_id
            }).eq("youtube_channel", row["youtube_channel"]).execute()

            guild = self.bot.get_guild(row["guild_id"])
            channel = guild.get_channel(row["discord_channel"])

            ping = f"<@&{row['role_ping']}>" if row["role_ping"] else ""

            await channel.send(
                f"{ping} 📢 New YouTube video!\nhttps://youtu.be/{video_id}"
            )

    @check_videos.before_loop
    async def before_loop(self):
        await self.bot.wait_until_ready()


async def setup(bot):
    await bot.add_cog(YouTube(bot))
