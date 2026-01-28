# cogs/moderation.py
import discord
from discord.ext import commands
from discord import app_commands
from supabase import create_client
import os

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ---------------- KICK ----------------
    @app_commands.command(name="kick", description="Kick a member")
    @app_commands.checks.has_permissions(kick_members=True)
    async def kick(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason"):
        await member.kick(reason=reason)
        await interaction.response.send_message(f"✅ Kicked {member.mention}")

    # ---------------- BAN ----------------
    @app_commands.command(name="ban", description="Ban a member")
    @app_commands.checks.has_permissions(ban_members=True)
    async def ban(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason"):
        await member.ban(reason=reason)
        await interaction.response.send_message(f"✅ Banned {member.mention}")

    # ---------------- TIMEOUT ----------------
    @app_commands.command(name="timeout", description="Timeout a member (minutes)")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def timeout(self, interaction: discord.Interaction, member: discord.Member, minutes: int):
        await member.timeout(discord.utils.utcnow() + discord.timedelta(minutes=minutes))
        await interaction.response.send_message(f"⏱️ Timed out {member.mention} for {minutes} minutes")

    # ---------------- WARN ----------------
    @app_commands.command(name="warn", description="Warn a member")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def warn(self, interaction: discord.Interaction, member: discord.Member):
        res = supabase.table("warnings").select("*").eq("user_id", member.id).eq("guild_id", interaction.guild.id).execute()

        if not res.data:
            count = 1
            supabase.table("warnings").insert({
                "user_id": member.id,
                "guild_id": interaction.guild.id,
                "count": count
            }).execute()
        else:
            count = res.data[0]["count"] + 1
            supabase.table("warnings").update({"count": count}).eq(
                "user_id", member.id).eq("guild_id", interaction.guild.id).execute()

        await interaction.response.send_message(f"⚠️ {member.mention} warned ({count}/3)")

        if count >= 3:
            await member.timeout(discord.utils.utcnow() + discord.timedelta(minutes=10))
            await interaction.followup.send(f"🔇 {member.mention} auto-muted for 10 minutes")

    # ---------------- WARN LIST ----------------
    @app_commands.command(name="warnings", description="Check warnings")
    async def warnings(self, interaction: discord.Interaction, member: discord.Member):
        res = supabase.table("warnings").select("*").eq("user_id", member.id).eq("guild_id", interaction.guild.id).execute()

        if not res.data:
            return await interaction.response.send_message("✅ No warnings")

        await interaction.response.send_message(
            f"⚠️ {member.mention} has {res.data[0]['count']} warnings"
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Moderation(bot))
