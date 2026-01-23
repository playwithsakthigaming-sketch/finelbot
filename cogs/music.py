import discord
import yt_dlp
import asyncio
import re
import requests
from discord.ext import commands
from discord import app_commands

# =================================================
# YTDLP OPTIONS
# =================================================
YTDLP_OPTIONS = {
    "format": "bestaudio/best",
    "quiet": True,
    "default_search": "ytsearch",
    "extract_flat": False,
    "nocheckcertificate": True,
    "ignoreerrors": False,  # IMPORTANT
    "source_address": "0.0.0.0"
}

FFMPEG_OPTIONS = {
    "before_options": (
        "-reconnect 1 "
        "-reconnect_streamed 1 "
        "-reconnect_delay_max 5"
    ),
    "options": "-vn"
}

SPOTIFY_TRACK_REGEX = r"https?://open\.spotify\.com/track/([a-zA-Z0-9]+)"

# =================================================
# SPOTIFY METADATA FETCH (NO AUTH)
# =================================================
def get_spotify_track_info(url: str):
    match = re.search(SPOTIFY_TRACK_REGEX, url)
    if not match:
        return None

    api_url = f"https://open.spotify.com/oembed?url={url}"
    res = requests.get(api_url, timeout=10)
    if res.status_code != 200:
        return None

    data = res.json()
    title = data.get("title")  # "Song – Artist"
    if not title:
        return None

    if "–" in title:
        song, artist = title.split("–", 1)
    else:
        song, artist = title, ""

    return f"{song.strip()} {artist.strip()} audio"

# =================================================
# MUSIC COG
# =================================================
class Music(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ---------------------------------------------
    # /play
    # ---------------------------------------------
    @app_commands.command(name="play", description="🎵 Play YouTube or Spotify track")
    @app_commands.describe(query="YouTube / Spotify link or search")
    async def play(self, interaction: discord.Interaction, query: str):
        if not interaction.user.voice:
            return await interaction.response.send_message(
                "❌ Join a voice channel first.",
                ephemeral=True
            )

        await interaction.response.defer()

        voice = interaction.guild.voice_client
        if not voice:
            voice = await interaction.user.voice.channel.connect()

        if voice.is_playing():
            voice.stop()

        # -----------------------------------------
        # SPOTIFY → YOUTUBE CONVERSION
        # -----------------------------------------
        if "open.spotify.com/track" in query:
            yt_query = get_spotify_track_info(query)
            if not yt_query:
                return await interaction.followup.send(
                    "❌ Failed to read Spotify track.",
                    ephemeral=True
                )
        else:
            yt_query = query

        try:
            # =================================================
            # SAFE YTDLP EXTRACTION (FIXED)
            # =================================================
            with yt_dlp.YoutubeDL(YTDLP_OPTIONS) as ydl:
                info = ydl.extract_info(yt_query, download=False)

                if not info:
                    raise Exception("No results found")

                if "entries" in info:
                    info = next((e for e in info["entries"] if e), None)

                if not info or not info.get("url"):
                    raise Exception("No playable audio found")

                audio_url = info["url"]
                title = info.get("title", "Unknown title")

            source = discord.FFmpegPCMAudio(audio_url, **FFMPEG_OPTIONS)

            voice.play(
                source,
                after=lambda e: asyncio.run_coroutine_threadsafe(
                    self.after_play(interaction.guild),
                    self.bot.loop
                )
            )

            embed = discord.Embed(
                title="🎶 Now Playing",
                description=title,
                color=discord.Color.green()
            )
            await interaction.followup.send(embed=embed)

        except Exception as e:
            await interaction.followup.send(
                f"❌ Failed to play audio:\n```{e}```",
                ephemeral=True
            )

    # ---------------------------------------------
    # AUTO DISCONNECT
    # ---------------------------------------------
    async def after_play(self, guild: discord.Guild):
        vc = guild.voice_client
        if vc and not vc.is_playing():
            await vc.disconnect()

    # ---------------------------------------------
    # /stop
    # ---------------------------------------------
    @app_commands.command(name="stop", description="⏹ Stop music")
    async def stop(self, interaction: discord.Interaction):
        vc = interaction.guild.voice_client
        if not vc:
            return await interaction.response.send_message(
                "❌ No music playing.",
                ephemeral=True
            )

        await vc.disconnect()
        await interaction.response.send_message(
            "⏹ Music stopped.",
            ephemeral=True
        )

# =================================================
# SETUP
# =================================================
async def setup(bot: commands.Bot):
    await bot.add_cog(Music(bot))
