import discord
import time
import aiosqlite
from discord.ext import commands, tasks
from discord import app_commands

DB_NAME = "bot.db"

# ================= CONFIG =================
PRICES = {"bronze": 100, "silver": 200, "gold": 300}
DAYS = {"bronze": 3, "silver": 5, "gold": 7}

PREMIUM_ROLE_IDS = {
    ""bronze": 1463834717987274814,
    "silver": 1463884119032463433,
    "gold": 1463884209025187880
}

LOGO_URL = "https://your-logo.png"
INVOICE_BG = "https://i.imgur.com/zvWTUVu.png"


# ================= TIER SELECT =================
class TierSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Bronze (3 Days)", value="bronze", emoji="🥉"),
            discord.SelectOption(label="Silver (5 Days)", value="silver", emoji="🥈"),
            discord.SelectOption(label="Gold (7 Days)", value="gold", emoji="🥇"),
        ]
        super().__init__(
            placeholder="Select Premium Tier",
            options=options,
            custom_id="coinshop_select"
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(BuyPremiumModal(self.values[0]))


# ================= BUY MODAL =================
class BuyPremiumModal(discord.ui.Modal):
    def __init__(self, tier):
        super().__init__(title="PSG FAMILY - Buy Premium")
        self.tier = tier

        self.name = discord.ui.TextInput(label="Your Name")
        self.coupon = discord.ui.TextInput(label="Coupon (optional)", required=False)

        self.add_item(self.name)
        self.add_item(self.coupon)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        user_id = interaction.user.id
        tier = self.tier
        price = PRICES[tier]
        discount = 0

        # Get balance
        async with aiosqlite.connect(DB_NAME) as db:
            async with db.execute("SELECT balance FROM coins WHERE user_id=?", (user_id,)) as cur:
                row = await cur.fetchone()
                balance = row[0] if row else 0

        if balance < price:
            return await interaction.followup.send("❌ Not enough coins.", ephemeral=True)

        expires = int(time.time()) + DAYS[tier] * 86400

        async with aiosqlite.connect(DB_NAME) as db:
            await db.execute("UPDATE coins SET balance=balance-? WHERE user_id=?", (price, user_id))
            await db.execute(
                "INSERT OR REPLACE INTO premium (user_id,tier,expires) VALUES (?,?,?)",
                (user_id, tier, expires)
            )
            await db.execute(
                "INSERT INTO payments (invoice_id,user_id,rupees,coins,timestamp) VALUES (?,?,?,?,?)",
                (f"PSG-{int(time.time())}", user_id, 0, price, int(time.time()))
            )
            await db.commit()

        role = interaction.guild.get_role(PREMIUM_ROLE_IDS[tier])
        if role:
            await interaction.user.add_roles(role)

        # Invoice Embed
        embed = discord.Embed(
            title="👑 PSG FAMILY\nOfficial Payment Invoice",
            color=discord.Color.gold()
        )
        embed.set_thumbnail(url=LOGO_URL)

        embed.add_field(name="🆔 Invoice ID", value=f"PSG-{int(time.time())}", inline=True)
        embed.add_field(name="📅 Date", value=time.strftime("%d / %m / %Y"), inline=True)
        embed.add_field(name="👤 Customer Name", value=self.name.value, inline=False)

        embed.add_field(name="━━━━━━━━ Payment Details ━━━━━━━━", value="\u200b", inline=False)
        embed.add_field(name="💰 Paid Amount", value=f"{price} Coins", inline=True)
        embed.add_field(name="⭐ Premium Tier", value=f"{tier.capitalize()} ({DAYS[tier]} Days)", inline=True)

        embed.add_field(name="✅ Payment Status", value="🟢 PAID", inline=True)
        embed.add_field(name="✍ Authorized By", value="PSG FAMILY", inline=True)
        embed.add_field(name="🖊 Signature", value="Kingofmyqueen", inline=True)

        embed.set_footer(text="Thank you for your support!")
        embed.set_image(url=INVOICE_BG)

        await interaction.followup.send(embed=embed, view=RefundView(user_id, tier, price))


# ================= REFUND VIEW =================
class RefundView(discord.ui.View):
    def __init__(self, user_id, tier, coins):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.tier = tier
        self.coins = coins

    @discord.ui.button(label="🔁 Refund", style=discord.ButtonStyle.danger, custom_id="coinshop_refund")
    async def refund(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ Admin only.", ephemeral=True)

        async with aiosqlite.connect(DB_NAME) as db:
            await db.execute("UPDATE coins SET balance=balance+? WHERE user_id=?", (self.coins, self.user_id))
            await db.execute("DELETE FROM premium WHERE user_id=?", (self.user_id,))
            await db.commit()

        member = interaction.guild.get_member(self.user_id)
        if member:
            role = interaction.guild.get_role(PREMIUM_ROLE_IDS[self.tier])
            if role:
                await member.remove_roles(role)

        await interaction.response.send_message("✅ Refund completed.", ephemeral=True)


# ================= SHOP VIEW =================
class CoinShopView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TierSelect())


# ================= COG =================
class CoinShop(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.expiry_task.start()

    # PANEL
    @app_commands.command(name="coin_shop_panel", description="Create PSG Family coin shop panel")
    async def coin_shop_panel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ Admin only.", ephemeral=True)

        embed = discord.Embed(
            title="👑 PSG FAMILY\nOfficial Premium & Coin Shop",
            description=(
                "🥉 **Bronze** – 100 Coins (3 Days)\n"
                "🥈 **Silver** – 200 Coins (5 Days)\n"
                "🥇 **Gold** – 300 Coins (7 Days)\n\n"
                "💱 Conversion: `₹2 = 6 PSG Coins`\n\n"
                "Select your Premium Tier below to generate invoice & buy.\n\n"
                "**Thank you for supporting PSG FAMILY ❤️**"
            ),
            color=discord.Color.gold()
        )

        embed.set_thumbnail(url=LOGO_URL)
        embed.set_footer(text="PSG FAMILY • Official Payment System")

        await channel.send(embed=embed, view=CoinShopView())
        await interaction.response.send_message("✅ Coin shop panel created.", ephemeral=True)

    # HISTORY
    @app_commands.command(name="coin_shop_history", description="View your coin shop history")
    async def coin_shop_history(self, interaction: discord.Interaction):
        async with aiosqlite.connect(DB_NAME) as db:
            async with db.execute(
                "SELECT invoice_id,coins,timestamp FROM payments WHERE user_id=?",
                (interaction.user.id,)
            ) as cur:
                rows = await cur.fetchall()

        if not rows:
            return await interaction.response.send_message("❌ No history.", ephemeral=True)

        text = ""
        for inv, coins, ts in rows:
            text += f"🧾 `{inv}` → {coins} coins at <t:{ts}:R>\n"

        embed = discord.Embed(title="📜 Coin Shop History", description=text, color=discord.Color.green())
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # AUTO EXPIRY
    @tasks.loop(minutes=1)
    async def expiry_task(self):
        async with aiosqlite.connect(DB_NAME) as db:
            async with db.execute("SELECT user_id,tier,expires FROM premium") as cur:
                rows = await cur.fetchall()

        now = int(time.time())
        for user_id, tier, expires in rows:
            if expires <= now:
                async with aiosqlite.connect(DB_NAME) as db:
                    await db.execute("DELETE FROM premium WHERE user_id=?", (user_id,))
                    await db.commit()

                for guild in self.bot.guilds:
                    member = guild.get_member(user_id)
                    if member:
                        role = guild.get_role(PREMIUM_ROLE_IDS[tier])
                        if role:
                            await member.remove_roles(role)

    @expiry_task.before_loop
    async def before_expiry(self):
        await self.bot.wait_until_ready()


# ================= SETUP =================
async def setup(bot):
    bot.add_view(CoinShopView())  # persistent view
    await bot.add_cog(CoinShop(bot))
