import discord
from discord.ext import commands
from discord import app_commands
from supabase import create_client
import os, time

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


class Announce(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # =========================
    # /announce
    # =========================
    @app_commands.command(name="announce", description="Send announcement")
    @app_commands.checks.has_permissions(administrator=True)
    async def announce(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        message: str,
        role: discord.Role = None,
        image_url: str = None,
        embed: bool = True
    ):
        await interaction.response.defer(ephemeral=True)

        ping = role.mention if role else ""

        if embed:
            ann_embed = discord.Embed(
                title="📢 Announcement",
                description=message,
                color=discord.Color.gold()
            )
            ann_embed.set_footer(text=f"By {interaction.user}")
            ann_embed.timestamp = discord.utils.utcnow()

            if image_url:
                ann_embed.set_image(url=image_url)

            await channel.send(content=ping, embed=ann_embed)

        else:
            await channel.send(f"{ping}\n{message}")

        # Save to Supabase
        supabase.table("announcements").insert({
            "guild_id": interaction.guild.id,
            "channel_id": channel.id,
            "role_ping": role.id if role else None,
            "message": message,
            "image_url": image_url,
            "is_embed": embed,
            "timestamp": int(time.time())
        }).execute()

        await interaction.followup.send("✅ Announcement sent")

    # =========================
    # /announce_history
    # =========================
    @app_commands.command(name="announce_history", description="Show announcement history")
    @app_commands.checks.has_permissions(administrator=True)
    async def announce_history(self, interaction: discord.Interaction):
        res = supabase.table("announcements").select("*").eq(
            "guild_id", interaction.guild.id
        ).order("timestamp", desc=True).limit(10).execute()

        if not res.data:
            return await interaction.response.send_message("❌ No announcements found", ephemeral=True)

        embed = discord.Embed(title="📜 Announcement History", color=discord.Color.blue())

        for row in res.data:
            embed.add_field(
                name=f"ID: {row['id']}",
                value=f"<#{row['channel_id']}>\n{row['message'][:100]}...",
                inline=False
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    # =========================
    # /remove_announce
    # =========================
    @app_commands.command(name="remove_announce", description="Delete announcement record")
    @app_commands.checks.has_permissions(administrator=True)
    async def remove_announce(self, interaction: discord.Interaction, announce_id: int):
        supabase.table("announcements").delete().eq("id", announce_id).execute()
        await interaction.response.send_message("✅ Announcement removed", ephemeral=True)


# =========================
# SETUP
# =========================
async def setup(bot: commands.Bot):
    await bot.add_cog(Announce(bot))
