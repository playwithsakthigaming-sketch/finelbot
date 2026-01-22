import discord
import yt_dlp
import asyncio
from discord.ext import commands
from discord import app_commands

# =========================================================
# YTDLP OPTIONS
# =========================================================

YTDLP_OPTIONS = {
    "format": "bestaudio/best",
    "quiet": True,
    "noplaylist": True
}

FFMPEG_OPTIONS = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn"
}

# =========================================================
# MUSIC COG
# =========================================================

class Music(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # -----------------------------------------------------
    # /play
    # -----------------------------------------------------
    @app_commands.command(name="play", description="🎵 Play music from YouTube")
    @app_commands.describe(query="Song name or YouTube URL")
    async def play(self, interaction: discord.Interaction, query: str):
        if not interaction.user.voice or not interaction.user.voice.channel:
            return await interaction.response.send_message(
                "❌ You must be in a voice channel.",
                ephemeral=True
            )

        await interaction.response.defer()

        vc = interaction.guild.voice_client
        if not vc:
            vc = await interaction.user.voice.channel.connect()

        if vc.is_playing():
            vc.stop()

        with yt_dlp.YoutubeDL(YTDLP_OPTIONS) as ydl:
            info = ydl.extract_info(query, download=False)
            if "entries" in info:
                info = info["entries"][0]

        audio_url = info["url"]
        title = info.get("title", "Unknown")

        vc.play(
            discord.FFmpegPCMAudio(audio_url, **FFMPEG_OPTIONS),
            after=lambda e: asyncio.run_coroutine_threadsafe(
                self.after_play(interaction.guild), self.bot.loop
            )
        )

        embed = discord.Embed(
            title="🎶 Now Playing",
            description=title,
            color=discord.Color.green()
        )

        await interaction.followup.send(embed=embed)

    # -----------------------------------------------------
    # AFTER PLAY
    # -----------------------------------------------------
    async def after_play(self, guild: discord.Guild):
        vc = guild.voice_client
        if vc and not vc.is_playing():
            await vc.disconnect()

    # -----------------------------------------------------
    # /stop
    # -----------------------------------------------------
    @app_commands.command(name="stop", description="⏹ Stop music and disconnect")
    async def stop(self, interaction: discord.Interaction):
        vc = interaction.guild.voice_client
        if not vc:
            return await interaction.response.send_message(
                "❌ No music is playing.",
                ephemeral=True
            )

        await vc.disconnect()
        await interaction.response.send_message(
            "⏹ Music stopped and disconnected.",
            ephemeral=True
        )

# =========================================================
# SETUP
# =========================================================

async def setup(bot: commands.Bot):
    await bot.add_cog(Music(bot))
