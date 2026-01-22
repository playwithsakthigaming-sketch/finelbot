import discord
import aiosqlite
import time
import random
import requests
from io import BytesIO
from PIL import Image, ImageDraw
from discord.ext import commands
from discord import app_commands

# =========================================================
# CONFIG
# =========================================================

UPI_ID = "psgfamily@upi"
RUPEE_RATE = 2          # ₹2
COINS_PER_RATE = 6      # = 6 coins
LOGO_URL = "https://cdn.discordapp.com/attachments/1415142396341256275/1463808464840294463/1000068286-removebg-preview.png"

PAYMENT_CATEGORY = "Payments"

# =========================================================
# INVOICE GENERATOR
# =========================================================

def generate_invoice(username: str, rupees: int, coins: int):
    img = Image.new("RGB", (900, 500), (20, 20, 20))
    draw = ImageDraw.Draw(img)

    # Logo
    try:
        logo = Image.open(BytesIO(requests.get(LOGO_URL).content)).resize((80, 80))
        img.paste(logo, (30, 30))
    except:
        pass

    invoice_id = f"PSG-{random.randint(10000,99999)}"
    date = time.strftime("%d-%m-%Y %H:%M")

    draw.text((140, 45), "PSG FAMILY - INVOICE", fill=(255, 200, 50))
    draw.text((50, 160), f"User: {username}", fill="white")
    draw.text((50, 210), f"Paid Amount: ₹{rupees}", fill="white")
    draw.text((50, 260), f"Coins Credited: {coins}", fill="white")
    draw.text((50, 320), f"Invoice ID: {invoice_id}", fill="white")
    draw.text((50, 360), f"Date: {date}", fill="white")

    draw.text((650, 380), "PAID", fill=(0, 200, 0))

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
            return await interaction.response.send_message(
                "❌ Invalid amount.",
                ephemeral=True
            )

        coins = (rupees // RUPEE_RATE) * COINS_PER_RATE

        async with aiosqlite.connect("bot.db") as db:
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
    bot.add_view(PaymentPanelView())  # persistent buttons
    await bot.add_cog(Payment(bot))
