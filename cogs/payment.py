import discord
from discord.ext import commands
from discord import app_commands
from supabase import create_client
import os, time, random
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import requests

# ================= CONFIG =================
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

UPI_ID = "psgfamily@upi"
RUPEE_RATE = 2
COINS_PER_RATE = 6

INVOICE_BG_URL = "https://files.catbox.moe/yslxzu.png"
LOGO_URL = "https://cdn.discordapp.com/attachments/1415142396341256275/1463808464840294463/1000068286-removebg-preview.png"
FONT_PATH = "fonts/CinzelDecorative-Bold.ttf"

# ================= INVOICE GENERATOR =================
def generate_invoice(username: str, rupees: int, coins: int):
    bg = Image.open(BytesIO(requests.get(INVOICE_BG_URL).content)).resize((900, 500))
    draw = ImageDraw.Draw(bg)
    font = ImageFont.truetype(FONT_PATH, 30)

    try:
        logo = Image.open(BytesIO(requests.get(LOGO_URL).content)).resize((80, 80))
        bg.paste(logo, (30, 30), logo.convert("RGBA"))
    except:
        pass

    invoice_id = f"PSG-{random.randint(10000,99999)}"
    date = time.strftime("%d-%m-%Y %H:%M")

    draw.text((140,430), f"Invoice ID: {invoice_id}", font=font, fill="white")
    draw.text((680,430), f"Date: {date}", font=font, fill="white")
    draw.text((140,500), f"Customer: {username}", font=font, fill="white")
    draw.text((140,600), f"Paid Amount: ₹{rupees}", font=font, fill="white")
    draw.text((140,670), f"Coin Credit: {coins}", font=font, fill="white")

    buf = BytesIO()
    bg.save(buf, "PNG")
    buf.seek(0)
    return buf, invoice_id


# ================= VIEW =================
class PaymentPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="💰 Buy Coins", style=discord.ButtonStyle.success, custom_id="buy_coins")
    async def buy(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            f"💳 **Payment Instructions**\n"
            f"UPI: `{UPI_ID}`\n"
            f"₹{RUPEE_RATE} = {COINS_PER_RATE} coins\n\n"
            "📸 Send screenshot to admin.",
            ephemeral=True
        )


# ================= COG =================
class Payment(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # -------- PAYMENT PANEL --------
    @app_commands.command(name="payment_panel", description="Create payment panel")
    @app_commands.checks.has_permissions(administrator=True)
    async def payment_panel(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="💳 Buy PSG Coins",
            description=(
                f"💱 Conversion Rate\n"
                f"₹{RUPEE_RATE} = {COINS_PER_RATE} PSG Coins\n\n"
                "Click button to start payment."
            ),
            color=discord.Color.gold()
        )

        await interaction.channel.send(embed=embed, view=PaymentPanelView())
        await interaction.response.send_message("✅ Payment panel created.", ephemeral=True)

    # -------- CONFIRM PAYMENT --------
    @app_commands.command(name="confirm_payment", description="Confirm payment & add coins")
    @app_commands.checks.has_permissions(administrator=True)
    async def confirm_payment(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        rupees: int
    ):
        await interaction.response.defer(ephemeral=True)

        if rupees <= 0:
            return await interaction.followup.send("❌ Invalid amount.")

        coins = (rupees // RUPEE_RATE) * COINS_PER_RATE

        # Get current balance
        res = supabase.table("coins").select("*").eq("user_id", member.id).execute()
        balance = res.data[0]["balance"] if res.data else 0

        # Update coins
        supabase.table("coins").upsert({
            "user_id": member.id,
            "balance": balance + coins
        }).execute()

        # Generate invoice
        invoice_img, invoice_id = generate_invoice(member.name, rupees, coins)

        # Save payment
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
                "🧾 **Your PSG Family Invoice**",
                file=discord.File(invoice_img, "invoice.png")
            )
        except:
            pass

        await interaction.followup.send(
            f"✅ Added **{coins} PSG Coins** to {member.mention}"
        )


# ================= SETUP =================
async def setup(bot: commands.Bot):
    bot.add_view(PaymentPanelView())
    await bot.add_cog(Payment(bot))
