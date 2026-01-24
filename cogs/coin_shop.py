import discord, time, aiosqlite
from discord.ext import commands, tasks
from discord import app_commands

DB_NAME = "bot.db"

PRICES = {"bronze":100, "silver":200, "gold":300}
DAYS = {"bronze":3, "silver":5, "gold":7}

PREMIUM_ROLE_IDS = {
    "bronze": 1463834717987274814,
    "silver": 1463884119032463433,
    "gold": 1463884209025187880
}

INVOICE_GIF_URL = "https://media.discordapp.net/attachments/812969396540145694/1464198209390772285/animation_download_20260122080227_599994.gif?ex=6975e9d8&is=69749858&hm=5cd29609b54f15dfd4a0ab652da80fa3eca9b48c6ade746eac6f2c78c0e62fc5&="


# ================= TIER SELECT =================
class TierSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Bronze", value="bronze", emoji="🥉"),
            discord.SelectOption(label="Silver", value="silver", emoji="🥈"),
            discord.SelectOption(label="Gold", value="gold", emoji="🥇")
        ]
        super().__init__(placeholder="Choose Premium Tier", options=options)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(BuyPremiumModal(self.values[0]))


# ================= BUY MODAL =================
class BuyPremiumModal(discord.ui.Modal):
    def __init__(self, tier):
        super().__init__(title="Buy Premium")
        self.tier = tier

        self.name = discord.ui.TextInput(label="Your Name")
        self.coupon = discord.ui.TextInput(label="Coupon (optional)", required=False)

        self.add_item(self.name)
        self.add_item(self.coupon)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        tier = self.tier
        user_id = interaction.user.id
        price = PRICES[tier]
        discount = 0

        async with aiosqlite.connect(DB_NAME) as db:
            async with db.execute("SELECT balance FROM coins WHERE user_id=?", (user_id,)) as cur:
                row = await cur.fetchone()
                balance = row[0] if row else 0

        # ===== COUPON =====
        if self.coupon.value:
            async with aiosqlite.connect(DB_NAME) as db:
                async with db.execute(
                    "SELECT type,value,used,max_uses FROM coupons WHERE code=?",
                    (self.coupon.value,)
                ) as cur:
                    coupon = await cur.fetchone()

            if not coupon:
                return await interaction.followup.send("❌ Invalid coupon.")

            c_type, value, used, max_uses = coupon
            if used >= max_uses:
                return await interaction.followup.send("❌ Coupon expired.")

            discount = int(price * value / 100) if c_type == "percent" else value

        final_price = max(price - discount, 0)

        if balance < final_price:
            return await interaction.followup.send(f"❌ Not enough coins. Need {final_price} coins.")

        expires = int(time.time()) + DAYS[tier] * 86400

        async with aiosqlite.connect(DB_NAME) as db:
            await db.execute("UPDATE coins SET balance=balance-? WHERE user_id=?", (final_price, user_id))
            await db.execute(
                "INSERT OR REPLACE INTO premium (user_id,tier,expires) VALUES (?,?,?)",
                (user_id, tier, expires)
            )
            if self.coupon.value:
                await db.execute("UPDATE coupons SET used=used+1 WHERE code=?", (self.coupon.value,))
            await db.execute(
                "INSERT INTO payments (invoice_id,user_id,rupees,coins,timestamp) VALUES (?,?,?,?,?)",
                (f"INV-{int(time.time())}", user_id, 0, final_price, int(time.time()))
            )
            await db.commit()

        role = interaction.guild.get_role(PREMIUM_ROLE_IDS[tier])
        if role:
            await interaction.user.add_roles(role)

        embed = discord.Embed(title="🧾 Invoice", color=discord.Color.gold())
        embed.add_field(name="Name", value=self.name.value)
        embed.add_field(name="Tier", value=tier.capitalize())
        embed.add_field(name="Coins Paid", value=str(final_price))
        embed.add_field(name="Duration", value=f"{DAYS[tier]} days")
        embed.set_image(url=INVOICE_GIF_URL)

        await interaction.followup.send(embed=embed, view=RefundView(user_id, tier, final_price))


# ================= REFUND BUTTON =================
class RefundView(discord.ui.View):
    def __init__(self, user_id, tier, coins):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.tier = tier
        self.coins = coins

    @discord.ui.button(label="🔁 Refund", style=discord.ButtonStyle.danger)
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


# ================= VIEW =================
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
    @app_commands.command(name="coin_shop_panel", description="Create premium coin shop panel")
    async def coin_shop_panel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ Admin only.", ephemeral=True)

        embed = discord.Embed(
            title="💎 Premium Coin Shop",
            description=(
                "🥉 Bronze – 100 coins (3 days)\n"
                "🥈 Silver – 200 coins (5 days)\n"
                "🥇 Gold – 300 coins (7 days)\n\n"
                "Select a tier below to buy Premium."
            ),
            color=discord.Color.blue()
        )

        await channel.send(embed=embed, view=CoinShopView())
        await interaction.response.send_message("✅ Coin shop panel created.", ephemeral=True)

    # HISTORY
    @app_commands.command(name="coin_shop_history", description="View your purchase history")
    async def coin_shop_history(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        async with aiosqlite.connect(DB_NAME) as db:
            async with db.execute(
                "SELECT invoice_id,coins,timestamp FROM payments WHERE user_id=?",
                (interaction.user.id,)
            ) as cur:
                rows = await cur.fetchall()

        if not rows:
            return await interaction.followup.send("❌ No purchase history.")

        msg = ""
        for inv, coins, ts in rows:
            msg += f"🧾 `{inv}` → {coins} coins at <t:{ts}:R>\n"

        embed = discord.Embed(title="📜 Coin Shop History", description=msg, color=discord.Color.green())
        await interaction.followup.send(embed=embed)

    # PREMIUM AUTO EXPIRY
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


async def setup(bot):
    bot.add_view(CoinShopView())
    await bot.add_cog(CoinShop(bot))
