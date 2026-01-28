# cogs/levels.py
import discord
from discord.ext import commands
from discord import app_commands
from supabase import create_client
import os, random

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

class Levels(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ---------------- XP SYSTEM ----------------
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        xp_add = random.randint(5, 10)

        res = supabase.table("levels").select("*").eq(
            "user_id", message.author.id
        ).eq("guild_id", message.guild.id).execute()

        if not res.data:
            supabase.table("levels").insert({
                "user_id": message.author.id,
                "guild_id": message.guild.id,
                "xp": xp_add,
                "level": 1
            }).execute()
        else:
            xp = res.data[0]["xp"] + xp_add
            level = res.data[0]["level"]

            if xp >= level * 100:
                level += 1
                await message.channel.send(f"🎉 {message.author.mention} leveled up to **{level}**!")

            supabase.table("levels").update({
                "xp": xp,
                "level": level
            }).eq("user_id", message.author.id).eq("guild_id", message.guild.id).execute()

    # ---------------- RANK ----------------
    @app_commands.command(name="rank", description="Show your level")
    async def rank(self, interaction: discord.Interaction, member: discord.Member = None):
        member = member or interaction.user

        res = supabase.table("levels").select("*").eq(
            "user_id", member.id
        ).eq("guild_id", interaction.guild.id).execute()

        if not res.data:
            return await interaction.response.send_message("❌ No data found")

        data = res.data[0]
        await interaction.response.send_message(
            f"🏆 {member.mention}\nLevel: **{data['level']}**\nXP: **{data['xp']}**"
        )

    # ---------------- LEADERBOARD ----------------
    @app_commands.command(name="leaderboard", description="Top 10 users")
    async def leaderboard(self, interaction: discord.Interaction):
        res = supabase.table("levels").select("*").eq(
            "guild_id", interaction.guild.id
        ).order("xp", desc=True).limit(10).execute()

        embed = discord.Embed(title="🏆 Leaderboard", color=discord.Color.blue())

        for i, row in enumerate(res.data, start=1):
            user = interaction.guild.get_member(row["user_id"])
            embed.add_field(
                name=f"{i}. {user.name if user else row['user_id']}",
                value=f"Level {row['level']} | XP {row['xp']}",
                inline=False
            )

        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Levels(bot))
