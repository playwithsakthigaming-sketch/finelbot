import discord
from discord.ext import commands
from discord import app_commands
from supabase import create_client
import os, time, random
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import requests

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

UPI_ID = "psgfamily@upi"
RUPEE_RATE = 2
COINS_PER_RATE = 6
LOGO_URL = "https://cdn.discordapp.com/attachments/1415142396341256275/1463808464840294463/1000068286-removebg-preview.png"
FONT_PATH = "fonts/CinzelDecorative-Bold.ttf"
BG_URL = "https://files.catbox.moe/yslxzu.png"

def generate_invoice(username, rupees, coins):
    bg = Image.open(BytesIO(requests.get(BG_URL).content)).resize((900, 500))
    draw = ImageDraw.Draw(bg)
    font = ImageFont.truetype(FONT_PATH, 30)

    invoice_id = f"PSG-{random.randint(10000,99999)}"
    date = time.strftime("%d-%m-%Y")

    draw.text((140,430), f"Invoice: {invoice_id}", font=font, fill="white")
    draw.text((680,430), f"Date: {date}", font=font, fill="white")
    draw.text((140,500), f"User: {username}", font=font, fill="white")
    draw.text((140,600), f"Paid: ₹{rupees}", font=font, fill="white")
    draw.text((140,670), f"Coins: {coins}", font=font, fill="white")

    buf = BytesIO()
    bg.save(buf, "PNG")
    buf.seek(0)
    return buf, invoice_id


class Payment(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ---------------- PANEL ----------------
    @app_commands.command(name="payment_panel", description="Create payment panel")
    @app_commands.checks.has_permissions(administrator=True)
    async def payment_panel(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="💳 Buy PSG Coins",
            description=f"₹{RUPEE_RATE} = {COINS_PER_RATE} coins\nUPI: `{UPI_ID}`",
            color=discord.Color.gold()
        )

        view = discord.ui.View(timeout=None)
        btn = discord.ui.Button(label="Buy Coins", style=discord.ButtonStyle.success)

        async def buy_callback(inter):
            await inter.response.send_message("📸 Send payment screenshot to admin.", ephemeral=True)

        btn.callback = buy_callback
        view.add_item(btn)

        await interaction.channel.send(embed=embed, view=view)
        await interaction.response.send_message("✅ Payment panel created", ephemeral=True)

    # ---------------- CONFIRM ----------------
    @app_commands.command(name="confirm_payment", description="Confirm payment")
    @app_commands.checks.has_permissions(administrator=True)
    async def confirm_payment(self, interaction: discord.Interaction, member: discord.Member, rupees: int):
        coins = (rupees // RUPEE_RATE) * COINS_PER_RATE

        res = supabase.table("coins").select("*").eq("user_id", member.id).execute()
        balance = res.data[0]["balance"] if res.data else 0

        supabase.table("coins").upsert({
            "user_id": member.id,
            "balance": balance + coins
        }).execute()

        invoice_img, invoice_id = generate_invoice(member.name, rupees, coins)

        supabase.table("payments").insert({
            "invoice_id": invoice_id,
            "user_id": member.id,
            "rupees": rupees,
            "coins": coins,
            "timestamp": int(time.time())
        }).execute()

        await interaction.channel.send(file=discord.File(invoice_img, "invoice.png"))
        await interaction.response.send_message(
            f"✅ {coins} coins added to {member.mention}",
            ephemeral=True
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Payment(bot))
