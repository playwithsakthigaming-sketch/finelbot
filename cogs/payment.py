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

# ================= CONFIG =================
UPI_ID = "psgfamily@upi"
RUPEE_RATE = 2
COINS_PER_RATE = 6

LOGO_URL = "https://cdn.discordapp.com/attachments/1415142396341256275/1463808464840294463/1000068286-removebg-preview.png"
INVOICE_BG_URL = "https://files.catbox.moe/yslxzu.png"

PAYMENT_CATEGORY = "Payments"

# ================= INVOICE DESIGN =================
SHOW_GRID = False

INVOICE_TEXT_CONFIG = {
    "username": [150, 320, 26],
    "amount": [150, 370, 26],
    "coins": [150, 420, 26],
    "status": [150, 470, 26]
}

# ================= FONT =================
def get_font(size):
    try:
        return ImageFont.truetype("arial.ttf", size)
    except:
        return ImageFont.load_default()

# ================= SAFE BACKGROUND LOAD =================
def load_invoice_background():
    W, H = 1000, 650
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
        draw.text((400, 300), "INVOICE", fill=(255,255,255))
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
            draw.line((x,0,x,650),(40,40,40))
        for y in range(0,650,50):
            draw.line((0,y,1000,y),(40,40,40))

    invoice_id = f"PSG-{random.randint(10000,99999)}"
    date = time.strftime("%d/%m/%Y")

    draw.text((150,260), f"Invoice ID: {invoice_id}", font=get_font(24), fill=gold)
    draw.text((700,260), f"Date: {date}", font=get_font(24), fill=gold)

    draw.text((INVOICE_TEXT_CONFIG["username"][0], INVOICE_TEXT_CONFIG["username"][1]),
              f"Customer: {username}", font=get_font(INVOICE_TEXT_CONFIG["username"][2]), fill=white)

    draw.text((INVOICE_TEXT_CONFIG["amount"][0], INVOICE_TEXT_CONFIG["amount"][1]),
              f"Paid Amount: ₹{rupees}", font=get_font(INVOICE_TEXT_CONFIG["amount"][2]), fill=white)

    draw.text((INVOICE_TEXT_CONFIG["coins"][0], INVOICE_TEXT_CONFIG["coins"][1]),
              f"Coins Credited: {coins}", font=get_font(INVOICE_TEXT_CONFIG["coins"][2]), fill=white)

    draw.text((INVOICE_TEXT_CONFIG["status"][0], INVOICE_TEXT_CONFIG["status"][1]),
              "Payment Status: PAID", font=get_font(INVOICE_TEXT_CONFIG["status"][2]), fill=green)

    draw.text((550,520),"Authorized By: PSG FAMILY",font=get_font(22),fill=gold)
    draw.text((750,520),"Kingofmyqueen",font=get_font(24),fill=gold)
    draw.text((350,610),"Thank you for your support!",font=get_font(26),fill=gold)

    buf = BytesIO()
    img.save(buf,"PNG")
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
        await interaction.response.send_message(f"✅ Payment ticket created: {channel.mention}", ephemeral=True)

# ================= CLOSE BUTTON =================
class PaymentCloseView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🔒 Close Ticket", style=discord.ButtonStyle.danger, custom_id="payment_close")
    async def close_ticket(self, interaction: discord.Interaction, _):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ Only admin can close this ticket.", ephemeral=True)
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
            await db.execute("INSERT OR IGNORE INTO coins (user_id,balance) VALUES (?,0)", (member.id,))
            await db.execute("UPDATE coins SET balance = balance + ? WHERE user_id=?", (coins, member.id))
            await db.commit()

        invoice = generate_invoice(member.name, rupees, coins)

        await interaction.channel.send("🧾 **Payment Confirmed**", file=discord.File(invoice, "invoice.png"))

        try:
            await member.send("🧾 **Your PSG Invoice**", file=discord.File(invoice, "invoice.png"))
        except:
            pass

        await interaction.followup.send(f"✅ Added {coins} coins to {member.mention}")

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
        await interaction.response.send_message(f"✅ Invoice grid set to {show}", ephemeral=True)

    @app_commands.command(name="invoice_edit", description="Edit invoice text position")
    @app_commands.checks.has_permissions(administrator=True)
    async def invoice_edit(self, interaction: discord.Interaction, field: str, x: int, y: int, size: int):
        if field not in INVOICE_TEXT_CONFIG:
            return await interaction.response.send_message(
                "❌ Field must be: username / amount / coins / status",
                ephemeral=True
            )

        INVOICE_TEXT_CONFIG[field] = [x, y, size]
        await interaction.response.send_message(f"✅ Updated `{field}`", ephemeral=True)

# ================= SETUP =================
async def setup(bot: commands.Bot):
    bot.add_view(PaymentPanelView())
    bot.add_view(PaymentCloseView())
    await bot.add_cog(Payment(bot))
