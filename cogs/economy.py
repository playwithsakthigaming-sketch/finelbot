import discord
from discord.ext import commands
from discord import app_commands
from supabase import create_client
import os

# ================= SUPABASE =================
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ================= COG =================
class Economy(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ---------------- BALANCE ----------------
    @app_commands.command(name="balance", description="💰 Check your coin balance")
    async def balance(self, interaction: discord.Interaction):
        user_id = interaction.user.id

        res = supabase.table("coins").select("*").eq("user_id", user_id).execute()
        balance = res.data[0]["balance"] if res.data else 0

        embed = discord.Embed(
            title="💰 Coin Balance",
            description=f"{interaction.user.mention}\n\n**Balance:** `{balance}` PSG Coins",
            color=discord.Color.gold()
        )
        await interaction.response.send_message(embed=embed)

    # ---------------- ADD COINS (ADMIN) ----------------
    @app_commands.command(name="addcoins", description="➕ Add coins to user")
    @app_commands.checks.has_permissions(administrator=True)
    async def addcoins(self, interaction: discord.Interaction, member: discord.Member, amount: int):
        if amount <= 0:
            return await interaction.response.send_message("❌ Amount must be positive.", ephemeral=True)

        res = supabase.table("coins").select("*").eq("user_id", member.id).execute()
        balance = res.data[0]["balance"] if res.data else 0

        supabase.table("coins").upsert({
            "user_id": member.id,
            "balance": balance + amount
        }).execute()

        await interaction.response.send_message(
            f"✅ Added **{amount} coins** to {member.mention}"
        )

    # ---------------- REMOVE COINS (ADMIN) ----------------
    @app_commands.command(name="removecoins", description="➖ Remove coins from user")
    @app_commands.checks.has_permissions(administrator=True)
    async def removecoins(self, interaction: discord.Interaction, member: discord.Member, amount: int):
        if amount <= 0:
            return await interaction.response.send_message("❌ Amount must be positive.", ephemeral=True)

        res = supabase.table("coins").select("*").eq("user_id", member.id).execute()
        balance = res.data[0]["balance"] if res.data else 0

        new_balance = max(0, balance - amount)

        supabase.table("coins").upsert({
            "user_id": member.id,
            "balance": new_balance
        }).execute()

        await interaction.response.send_message(
            f"✅ Removed **{amount} coins** from {member.mention}\nNew Balance: `{new_balance}`"
        )

    # ---------------- TRANSFER ----------------
    @app_commands.command(name="transfer", description="🔁 Transfer coins to another user")
    async def transfer(self, interaction: discord.Interaction, member: discord.Member, amount: int):
        if amount <= 0:
            return await interaction.response.send_message("❌ Invalid amount.", ephemeral=True)

        sender_id = interaction.user.id
        receiver_id = member.id

        sender_res = supabase.table("coins").select("*").eq("user_id", sender_id).execute()
        sender_balance = sender_res.data[0]["balance"] if sender_res.data else 0

        if sender_balance < amount:
            return await interaction.response.send_message("❌ Not enough coins.", ephemeral=True)

        receiver_res = supabase.table("coins").select("*").eq("user_id", receiver_id).execute()
        receiver_balance = receiver_res.data[0]["balance"] if receiver_res.data else 0

        supabase.table("coins").upsert({
            "user_id": sender_id,
            "balance": sender_balance - amount
        }).execute()

        supabase.table("coins").upsert({
            "user_id": receiver_id,
            "balance": receiver_balance + amount
        }).execute()

        await interaction.response.send_message(
            f"✅ {interaction.user.mention} sent **{amount} coins** to {member.mention}"
        )

    # ---------------- LEADERBOARD ----------------
    @app_commands.command(name="coin_leaderboard", description="🏆 Coin leaderboard")
    async def leaderboard(self, interaction: discord.Interaction):
        res = supabase.table("coins").select("*").order("balance", desc=True).limit(10).execute()

        if not res.data:
            return await interaction.response.send_message("❌ No data found.")

        embed = discord.Embed(title="🏆 Coin Leaderboard", color=discord.Color.gold())

        for i, row in enumerate(res.data, start=1):
            user = self.bot.get_user(row["user_id"])
            name = user.name if user else str(row["user_id"])
            embed.add_field(
                name=f"{i}. {name}",
                value=f"💰 {row['balance']} coins",
                inline=False
            )

        await interaction.response.send_message(embed=embed)

# ================= SETUP =================
async def setup(bot: commands.Bot):
    await bot.add_cog(Economy(bot))
