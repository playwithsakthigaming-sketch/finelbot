import discord
import aiosqlite
import time
import random
import requests
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from discord.ext import commands
from discord import app_commands

DB_NAME = "bot.db"

# =========================================================
# CONFIG
# =========================================================
UPI_ID = "psgfamily@upi"
RUPEE_RATE = 2
COINS_PER_RATE = 6

LOGO_URL = "https://cdn.discordapp.com/attachments/1415142396341256275/1463808464840294463/1000068286-removebg-preview.png"

INVOICE_BG_URL = "PUT_YOUR_UPLOADED_IMAGE_URL_HERE"
SHOW_GRID = False   # True for design alignment

PAYMENT_CATEGORY = "Payments"

# =========================================================
# FONT HELPER
# =========================================================
def get_font(size):
    try:
        return ImageFont.truetype("arial.ttf", size)
    except:
        return ImageFont.load_default()

# =========================================================
# INVOICE GENERATOR
# =========================================================
def generate_invoice(username: str, rupees: int, coins: int):
    bg = Image.open(BytesIO(requests.get(INVOICE_BG_URL).content)).convert("RGB")
    img = bg.resize((1000, 650))
    draw = ImageDraw.Draw(img)

    gold = (255, 200, 60)
    white = (255, 255, 255)
    green = (0, 255, 0)

    # ================= GRID =================
    if SHOW_GRID:
        for x in range(0, 1000, 50):
            draw.line((x, 0, x, 650), fill=(40, 40, 40))
        for y in range(0, 650, 50):
            draw.line((0, y, 1000, y), fill=(40, 40, 40))

    invoice_id = f"PSG-{random.randint(10000,99999)}"
    date = time.strftime("%d / %m / %Y")

    # ================= TEXT LAYOUT =================
    texts = [
        (f"Invoice ID: {invoice_id}", 150, 260, 24, gold),
        (f"Date: {date}", 700, 260, 24, gold),

        (f"Customer Name: {username}", 150, 320, 26, white),
        (f"Paid Amount: ₹{rupees}", 150, 370, 26, white),
        (f"Coin Credit: {coins} PSG Coins", 150, 420, 26, white),

        ("Payment Status: PAID", 150, 470, 26, green),
        ("Payment Method: UPI", 700, 470, 22, white),

        ("Authorized By: PSG FAMILY", 550, 520, 22, gold),
        ("Kingofmyqueen", 750, 520, 24, gold),

        ("Thank you for your support!", 350, 610, 26, gold)
    ]

    for text, x, y, size, color in texts:
        draw.text((x, y), text, font=get_font(size), fill=color)

    buf = BytesIO()
    img.save(buf, "PNG")
    buf.seek(0)
    return buf

# =========================================================
# PAYMENT PANEL VIEW
# =========================================================
class PaymentPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="💰 Buy Coins",
        style=discord.ButtonStyle.success,
        custom_id="payment_buy"
    )
    async def buy(self, interaction: discord.Interaction, _):
        guild = interaction.guild

        category = discord.utils.get(guild.categories, name=PAYMENT_CATEGORY)
        if not category:
            category = await guild.create_category(PAYMENT_CATEGORY)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True)
        }

        channel = await guild.create_text_channel(
            name=f"payment-{interaction.user.name}".lower(),
            category=category,
            overwrites=overwrites
        )

        await channel.send(
            f"{interaction.user.mention}\n\n"
            "💳 **Payment Instructions**\n"
            f"UPI ID: `{UPI_ID}`\n"
            f"💱 ₹{RUPEE_RATE} = {COINS_PER_RATE} PSG Coins\n\n"
            "📸 Upload payment screenshot here.\n"
            "Admin will verify and confirm."
        )

        await interaction.response.send_message(
            f"✅ Payment ticket created: {channel.mention}",
            ephemeral=True
        )

# =========================================================
# PAYMENT COG
# =========================================================
class Payment(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # -----------------------------------------------------
    # /payment_panel
    # -----------------------------------------------------
    @app_commands.command(name="payment_panel", description="💳 Create payment panel")
    @app_commands.checks.has_permissions(administrator=True)
    async def payment_panel(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="💳 Buy PSG Coins",
            description=(
                f"💱 Conversion Rate\n"
                f"₹{RUPEE_RATE} = {COINS_PER_RATE} PSG Coins\n\n"
                "Click the button below to create a payment request."
            ),
            color=discord.Color.gold()
        )
        embed.set_thumbnail(url=LOGO_URL)

        await interaction.channel.send(embed=embed, view=PaymentPanelView())
        await interaction.response.send_message(
            "✅ Payment panel created.",
            ephemeral=True
        )

    # -----------------------------------------------------
    # /confirm_payment
    # -----------------------------------------------------
    @app_commands.command(name="confirm_payment", description="✅ Confirm payment & add coins")
    @app_commands.checks.has_permissions(administrator=True)
    async def confirm_payment(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        rupees: int
    ):
        if rupees <= 0:
            return await interaction.response.send_message("❌ Invalid amount.", ephemeral=True)

        coins = (rupees // RUPEE_RATE) * COINS_PER_RATE

        async with aiosqlite.connect(DB_NAME) as db:
            await db.execute(
                "INSERT OR IGNORE INTO coins (user_id, balance) VALUES (?,0)",
                (member.id,)
            )
            await db.execute(
                "UPDATE coins SET balance = balance + ? WHERE user_id=?",
                (coins, member.id)
            )
            await db.commit()

        invoice = generate_invoice(member.name, rupees, coins)

        await interaction.channel.send(
            content="🧾 **Payment Confirmed**",
            file=discord.File(invoice, "invoice.png")
        )

        try:
            await member.send(
                "🧾 **Your PSG Family Invoice**",
                file=discord.File(invoice, "invoice.png")
            )
        except:
            pass

        await interaction.response.send_message(
            f"✅ Added **{coins} PSG Coins** to {member.mention}",
            ephemeral=True
        )

# =========================================================
# SETUP
# =========================================================
async def setup(bot: commands.Bot):
    bot.add_view(PaymentPanelView())
    await bot.add_cog(Payment(bot))
