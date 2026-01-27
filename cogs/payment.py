import discord
import aiosqlite
import time
import random
import requests
import os
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from discord.ext import commands
from discord import app_commands

DB_NAME = "bot.db"

# ================= CONFIG =================
UPI_ID = "psgfamily@upi"
RUPEE_RATE = 2
COINS_PER_RATE = 6

LOGO_URL = "https://cdn.discordapp.com/attachments/1415142396341256275/1463808464840294463/1000068286-removebg-preview.png"
INVOICE_BG_URL = "https://files.catbox.moe/r09xpx.png"

PAYMENT_CATEGORY = "Payments"

# ================= FONT AUTO DOWNLOAD =================
FONT_FILE = "DejaVuSans-Bold.ttf"
FONT_URL = "https://raw.githubusercontent.com/dejavu-fonts/dejavu-fonts/master/ttf/DejaVuSans-Bold.ttf"

def ensure_font():
    if not os.path.exists(FONT_FILE):
        print("⬇ Downloading font...")
        r = requests.get(FONT_URL, timeout=15)
        r.raise_for_status()
        with open(FONT_FILE, "wb") as f:
            f.write(r.content)
        print("✅ Font downloaded")

def get_font(size: int):
    ensure_font()
    return ImageFont.truetype(FONT_FILE, size)

# ================= INVOICE DESIGN =================
SHOW_GRID = False

INVOICE_TEXT_CONFIG = {
    "invoice_id": {"x":140,"y":430,"z":1,"fontSize":32},
    "date": {"x":680,"y":430,"z":1,"fontSize":32},
    "customer": {"x":140,"y":500,"z":1,"fontSize":30},
    "paid_amount": {"x":140,"y":600,"z":1,"fontSize":30},
    "coin_credit": {"x":140,"y":670,"z":1,"fontSize":30}
}

# ================= SAFE BACKGROUND LOAD =================
def load_invoice_background():
    W, H = 1280, 1024
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(INVOICE_BG_URL, headers=headers, timeout=15)
        r.raise_for_status()
        bg = Image.open(BytesIO(r.content)).convert("RGB")
        return bg.resize((W, H))
    except Exception as e:
        print("❌ Invoice BG load failed:", e)
        img = Image.new("RGB", (W, H), (20, 20, 20))
        draw = ImageDraw.Draw(img)
        draw.text((400, 300), "INVOICE", fill=(255,255,255), font=get_font(40))
        return img

# ================= INVOICE GENERATOR =================
def generate_invoice(username, rupees, coins):
    img = load_invoice_background()
    draw = ImageDraw.Draw(img)

    gold = (255,200,60)
    white = (255,255,255)
    green = (0,255,0)

    if SHOW_GRID:
        for x in range(0,1000,50):
            draw.line((x,0,x,800),(40,40,40))
        for y in range(0,800,50):
            draw.line((0,y,1000,y),(40,40,40))

    invoice_id = f"PSG-{random.randint(10000,99999)}"
    date = time.strftime("%d/%m/%Y")

    cfg = INVOICE_TEXT_CONFIG

    draw.text((cfg["invoice_id"]["x"], cfg["invoice_id"]["y"]),
              f"Invoice ID: {invoice_id}",
              font=get_font(cfg["invoice_id"]["fontSize"]),
              fill=gold)

    draw.text((cfg["date"]["x"], cfg["date"]["y"]),
              f"Date: {date}",
              font=get_font(cfg["date"]["fontSize"]),
              fill=gold)

    draw.text((cfg["customer"]["x"], cfg["customer"]["y"]),
              f"Customer: {username}",
              font=get_font(cfg["customer"]["fontSize"]),
              fill=white)

    draw.text((cfg["paid_amount"]["x"], cfg["paid_amount"]["y"]),
              f"Paid Amount: ₹{rupees}",
              font=get_font(cfg["paid_amount"]["fontSize"]),
              fill=white)

    draw.text((cfg["coin_credit"]["x"], cfg["coin_credit"]["y"]),
              f"Coins Credited: {coins}",
              font=get_font(cfg["coin_credit"]["fontSize"]),
              fill=white)

    draw.text((550, 740),
              "Payment Status: PAID",
              font=get_font(30),
              fill=green)

    buf = BytesIO()
    img.save(buf, "PNG")
    buf.seek(0)
    return buf

# ================= PAYMENT PANEL VIEW =================
class PaymentPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="💰 Buy Coins", style=discord.ButtonStyle.success, custom_id="payment_buy")
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

        embed = discord.Embed(
            title="💳 Payment Ticket",
            description=(
                f"{interaction.user.mention}\n\n"
                f"UPI ID: `{UPI_ID}`\n"
                f"₹{RUPEE_RATE} = {COINS_PER_RATE} PSG Coins\n\n"
                "📸 Upload payment screenshot.\n"
                "Admin will confirm."
            ),
            color=discord.Color.gold()
        )

        await channel.send(embed=embed, view=PaymentCloseView())
        await interaction.response.send_message(
            f"✅ Payment ticket created: {channel.mention}", ephemeral=True
        )

# ================= CLOSE BUTTON =================
class PaymentCloseView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🔒 Close Ticket", style=discord.ButtonStyle.danger, custom_id="payment_close")
    async def close_ticket(self, interaction: discord.Interaction, _):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message(
                "❌ Only admin can close this ticket.", ephemeral=True
            )
        await interaction.channel.delete()

# ================= PAYMENT COG =================
class Payment(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="payment_panel", description="Create payment panel")
    @app_commands.checks.has_permissions(administrator=True)
    async def payment_panel(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="💳 Buy PSG Coins",
            description=f"₹{RUPEE_RATE} = {COINS_PER_RATE} PSG Coins\nClick below to buy.",
            color=discord.Color.gold()
        )
        embed.set_thumbnail(url=LOGO_URL)

        await interaction.channel.send(embed=embed, view=PaymentPanelView())
        await interaction.response.send_message("✅ Payment panel created.", ephemeral=True)

    @app_commands.command(name="confirm_payment", description="Confirm payment & add coins")
    @app_commands.checks.has_permissions(administrator=True)
    async def confirm_payment(self, interaction: discord.Interaction, member: discord.Member, rupees: int):
        await interaction.response.defer(ephemeral=True)

        if rupees <= 0:
            return await interaction.followup.send("❌ Invalid amount.")

        coins = (rupees // RUPEE_RATE) * COINS_PER_RATE

        async with aiosqlite.connect(DB_NAME) as db:
            await db.execute(
                "INSERT OR IGNORE INTO coins (user_id,balance) VALUES (?,0)",
                (member.id,)
            )
            await db.execute(
                "UPDATE coins SET balance = balance + ? WHERE user_id=?",
                (coins, member.id)
            )
            await db.commit()

        invoice = generate_invoice(member.name, rupees, coins)

        await interaction.channel.send(
            "🧾 **Payment Confirmed**",
            file=discord.File(invoice, "invoice.png")
        )

        try:
            await member.send(
                "🧾 **Your PSG Invoice**",
                file=discord.File(invoice, "invoice.png")
            )
        except:
            pass

        await interaction.followup.send(
            f"✅ Added {coins} coins to {member.mention}"
        )

    @app_commands.command(name="invoice_preview", description="Preview invoice layout")
    @app_commands.checks.has_permissions(administrator=True)
    async def invoice_preview(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        img = generate_invoice(interaction.user.name, 100, 300)
        await interaction.followup.send(file=discord.File(img, "preview.png"))

    @app_commands.command(name="invoice_grid", description="Toggle invoice grid")
    @app_commands.checks.has_permissions(administrator=True)
    async def invoice_grid(self, interaction: discord.Interaction, show: bool):
        global SHOW_GRID
        SHOW_GRID = show
        await interaction.response.send_message(
            f"✅ Invoice grid set to {show}", ephemeral=True
        )

    @app_commands.command(name="invoice_edit", description="Edit invoice text position")
    @app_commands.checks.has_permissions(administrator=True)
    async def invoice_edit(self, interaction: discord.Interaction, field: str, x: int, y: int, size: int):
        if field not in INVOICE_TEXT_CONFIG:
            return await interaction.response.send_message(
                "❌ Field must be: invoice_id / date / customer / paid_amount / coin_credit",
                ephemeral=True
            )

        INVOICE_TEXT_CONFIG[field] = {"x":x,"y":y,"z":1,"fontSize":size}
        await interaction.response.send_message(
            f"✅ Updated `{field}` position.", ephemeral=True
        )

# ================= SETUP =================
async def setup(bot: commands.Bot):
    ensure_font()
    bot.add_view(PaymentPanelView())
    bot.add_view(PaymentCloseView())
    await bot.add_cog(Payment(bot))
