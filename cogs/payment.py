import discord
import os
import time
import random
from discord.ext import commands
from discord import app_commands
from supabase import create_client
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
BG_URL = "https://files.catbox.moe/yslxzu.png"

# ================= INVOICE IMAGE =================
def generate_invoice(username: str, rupees: int, coins: int):
    bg = Image.open(BytesIO(requests.get(BG_URL).content)).resize((900, 500))
    draw = ImageDraw.Draw(bg)

    try:
        font_big = ImageFont.truetype("fonts/CinzelDecorative-Bold.ttf", 36)
        font_small = ImageFont.truetype("fonts/CinzelDecorative-Bold.ttf", 24)
    except:
        font_big = font_small = ImageFont.load_default()

    invoice_id = f"PSG-{random.randint(10000,99999)}"
    date = time.strftime("%d-%m-%Y %H:%M")

    draw.text((50, 50), "PSG FAMILY INVOICE", font=font_big, fill="white")
    draw.text((50, 130), f"Customer: {username}", font=font_small, fill="white")
    draw.text((50, 180), f"Paid Amount: ₹{rupees}", font=font_small, fill="white")
    draw.text((50, 230), f"Coins Credited: {coins}", font=font_small, fill="white")
    draw.text((50, 280), f"Invoice ID: {invoice_id}", font=font_small, fill="white")
    draw.text((50, 330), f"Date: {date}", font=font_small, fill="white")
    draw.text((700, 420), "PAID", font=font_big, fill="green")

    buf = BytesIO()
    bg.save(buf, "PNG")
    buf.seek(0)

    return buf, invoice_id


# ================= VIEW =================
class PaymentPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="💰 Buy Coins",
        style=discord.ButtonStyle.success,
        custom_id="payment_buy"
    )
    async def buy(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            f"💳 Send payment to UPI: `{UPI_ID}`\n"
            f"Rate: ₹{RUPEE_RATE} = {COINS_PER_RATE} coins\n\n"
            "After payment, wait for admin to confirm using `/confirm_payment`.",
            ephemeral=True
        )


# ================= COG =================
class Payment(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ---------------- PANEL ----------------
    @app_commands.command(name="payment_panel", description="Create payment panel")
    @app_commands.checks.has_permissions(administrator=True)
    async def payment_panel(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="💳 Buy PSG Coins",
            description=(
                f"💱 **Conversion Rate**\n"
                f"₹{RUPEE_RATE} = {COINS_PER_RATE} PSG Coins\n\n"
                "Click button below to start payment."
            ),
            color=discord.Color.gold()
        )

        await interaction.channel.send(embed=embed, view=PaymentPanelView())
        await interaction.response.send_message(
            "✅ Payment panel created",
            ephemeral=True
        )

    # ---------------- CONFIRM PAYMENT ----------------
    @app_commands.command(name="confirm_payment", description="Confirm payment and add coins")
    @app_commands.checks.has_permissions(administrator=True)
    async def confirm_payment(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        rupees: int
    ):
        await interaction.response.defer(ephemeral=True)

        if rupees <= 0:
            return await interaction.followup.send("❌ Invalid amount")

        coins = (rupees // RUPEE_RATE) * COINS_PER_RATE

        # save coins
        supabase.table("coins").upsert({
            "user_id": member.id,
            "balance": coins
        }).execute()

        # generate invoice
        invoice_img, invoice_id = generate_invoice(member.name, rupees, coins)

        # save payment
        supabase.table("payments").insert({
            "invoice_id": invoice_id,
            "user_id": member.id,
            "rupees": rupees,
            "coins": coins,
            "timestamp": int(time.time())
        }).execute()

        await interaction.channel.send(
            content="🧾 **Payment Confirmed**",
            file=discord.File(invoice_img, "invoice.png")
        )

        try:
            await member.send(
                "🧾 Your PSG Family Invoice",
                file=discord.File(invoice_img, "invoice.png")
            )
        except:
            pass

        await interaction.followup.send(
            f"✅ Added **{coins} coins** to {member.mention}"
        )


# ================= SETUP =================
async def setup(bot: commands.Bot):
    bot.add_view(PaymentPanelView())  # persistent button
    await bot.add_cog(Payment(bot))
