import discord
import aiosqlite
import time
from discord.ext import commands
from discord import app_commands

# =========================================================
# CONFIG
# =========================================================

# Coin prices + duration (days)
PREMIUM_SHOP = {
    "bronze": {"price": 100, "days": 3},
    "silver": {"price": 200, "days": 5},
    "gold":   {"price": 300, "days": 7}
}

# MUST match cogs.premium.py
PREMIUM_ROLES = {
    "bronze": 1463834717987274814,
    "silver": 1463884119032463433,
    "gold":   1463884209025187880
}

# =========================================================
# HELPERS
# =========================================================

async def get_user_coins(user_id: int) -> int:
    async with aiosqlite.connect("bot.db") as db:
        cur = await db.execute(
            "SELECT balance FROM coins WHERE user_id=?",
            (user_id,)
        )
        row = await cur.fetchone()
        return row[0] if row else 0

async def add_premium(user: discord.Member, tier: str, days: int):
    now = int(time.time())
    add_seconds = days * 86400

    async with aiosqlite.connect("bot.db") as db:
        cur = await db.execute(
            "SELECT expires FROM premium WHERE user_id=?",
            (user.id,)
        )
        row = await cur.fetchone()

        if row:
            expires = max(row[0], now) + add_seconds
        else:
            expires = now + add_seconds

        await db.execute(
            """
            INSERT INTO premium (user_id, tier, expires)
            VALUES (?,?,?)
            ON CONFLICT(user_id)
            DO UPDATE SET tier=excluded.tier, expires=excluded.expires
            """,
            (user.id, tier, expires)
        )
        await db.commit()

    role = user.guild.get_role(PREMIUM_ROLES[tier])
    if role:
        try:
            await user.add_roles(role, reason="Purchased premium via coin shop")
        except:
            pass

# =========================================================
# SHOP VIEW (BUTTONS)
# =========================================================

class CoinShopView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def buy(self, interaction: discord.Interaction, tier: str):
        cfg = PREMIUM_SHOP[tier]
        price = cfg["price"]
        days = cfg["days"]

        coins = await get_user_coins(interaction.user.id)
        if coins < price:
            return await interaction.response.send_message(
                f"❌ Not enough coins.\nRequired: **{price}**, You have: **{coins}**",
                ephemeral=True
            )

        async with aiosqlite.connect("bot.db") as db:
            await db.execute(
                "UPDATE coins SET balance = balance - ? WHERE user_id=?",
                (price, interaction.user.id)
            )
            await db.commit()

        await add_premium(interaction.user, tier, days)

        await interaction.response.send_message(
            f"✅ **{tier.title()} Premium** activated for **{days} days** 🎉",
            ephemeral=True
        )

    @discord.ui.button(label="🥉 Bronze (100)", style=discord.ButtonStyle.secondary, custom_id="buy_bronze")
    async def bronze(self, interaction: discord.Interaction, _):
        await self.buy(interaction, "bronze")

    @discord.ui.button(label="🥈 Silver (200)", style=discord.ButtonStyle.primary, custom_id="buy_silver")
    async def silver(self, interaction: discord.Interaction, _):
        await self.buy(interaction, "silver")

    @discord.ui.button(label="🥇 Gold (300)", style=discord.ButtonStyle.success, custom_id="buy_gold")
    async def gold(self, interaction: discord.Interaction, _):
        await self.buy(interaction, "gold")

# =========================================================
# COG
# =========================================================

class CoinShop(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # -----------------------------------------------------
    # /coin_shop
    # -----------------------------------------------------
    @app_commands.command(name="coin_shop", description="🛒 Buy premium using coins")
    async def coin_shop(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🛒 PSG Coin Shop",
            description=(
                "Use your PSG Coins to buy Premium.\n\n"
                "🥉 **Bronze** – 100 coins (3 days)\n"
                "🥈 **Silver** – 200 coins (5 days)\n"
                "🥇 **Gold** – 300 coins (7 days)"
            ),
            color=discord.Color.gold()
        )
        await interaction.response.send_message(
            embed=embed,
            view=CoinShopView(),
            ephemeral=True
        )

# =========================================================
# SETUP
# =========================================================

async def setup(bot: commands.Bot):
    bot.add_view(CoinShopView())  # persistent
    await bot.add_cog(CoinShop(bot))
