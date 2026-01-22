import discord
import aiosqlite
import time
from discord.ext import commands
from discord import app_commands

# =========================================================
# CONFIG
# =========================================================

TICKET_CATEGORY_NAME = "Tickets"  # auto-created if not exists
STAFF_ROLE_NAME = "Support"       # staff role allowed to claim

# =========================================================
# MODAL
# =========================================================

class TicketModal(discord.ui.Modal, title="🎫 Create Ticket"):
    subject = discord.ui.TextInput(
        label="Subject",
        placeholder="Short title of your issue",
        max_length=100
    )
    description = discord.ui.TextInput(
        label="Describe your issue",
        style=discord.TextStyle.paragraph,
        max_length=1000
    )

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild

        # Find or create category
        category = discord.utils.get(guild.categories, name=TICKET_CATEGORY_NAME)
        if not category:
            category = await guild.create_category(TICKET_CATEGORY_NAME)

        # Permissions
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }

        staff_role = discord.utils.get(guild.roles, name=STAFF_ROLE_NAME)
        if staff_role:
            overwrites[staff_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        channel = await guild.create_text_channel(
            name=f"ticket-{interaction.user.name}".lower(),
            category=category,
            overwrites=overwrites
        )

        # Save ticket
        async with aiosqlite.connect("bot.db") as db:
            await db.execute(
                "INSERT OR REPLACE INTO tickets (channel_id, user_id, created_at, claimed_by) VALUES (?,?,?,?)",
                (channel.id, interaction.user.id, int(time.time()), None)
            )
            await db.commit()

        embed = discord.Embed(
            title="🎫 New Ticket",
            description=(
                f"**User:** {interaction.user.mention}\n"
                f"**Subject:** {self.subject}\n\n"
                f"{self.description}"
            ),
            color=discord.Color.gold()
        )

        await channel.send(
            embed=embed,
            view=TicketView()
        )

        await interaction.response.send_message(
            f"✅ Ticket created: {channel.mention}",
            ephemeral=True
        )

# =========================================================
# VIEW (BUTTONS)
# =========================================================

class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    # ---------- CLAIM ----------
    @discord.ui.button(label="🖐 Claim", style=discord.ButtonStyle.primary, custom_id="ticket_claim")
    async def claim(self, interaction: discord.Interaction, _):
        async with aiosqlite.connect("bot.db") as db:
            cur = await db.execute(
                "SELECT claimed_by FROM tickets WHERE channel_id=?",
                (interaction.channel.id,)
            )
            row = await cur.fetchone()

            if not row:
                return await interaction.response.send_message(
                    "❌ This is not a valid ticket channel.",
                    ephemeral=True
                )

            if row[0]:
                return await interaction.response.send_message(
                    "❌ Ticket already claimed.",
                    ephemeral=True
                )

            await db.execute(
                "UPDATE tickets SET claimed_by=? WHERE channel_id=?",
                (interaction.user.id, interaction.channel.id)
            )
            await db.commit()

        await interaction.channel.send(
            f"🟢 Ticket claimed by {interaction.user.mention}"
        )
        await interaction.response.defer()

    # ---------- CLOSE ----------
    @discord.ui.button(label="🔒 Close", style=discord.ButtonStyle.danger, custom_id="ticket_close")
    async def close(self, interaction: discord.Interaction, _):
        await interaction.response.send_message(
            "🔒 Closing ticket in 3 seconds...",
            ephemeral=True
        )
        await save_transcript(interaction.channel)
        await interaction.channel.delete(delay=3)

# =========================================================
# TRANSCRIPT
# =========================================================

async def save_transcript(channel: discord.TextChannel):
    async with aiosqlite.connect("bot.db") as db:
        async for msg in channel.history(limit=None, oldest_first=True):
            if msg.author.bot:
                continue
            await db.execute(
                "INSERT INTO ticket_transcripts (ticket_id, message, author, timestamp) VALUES (?,?,?,?)",
                (
                    channel.id,
                    msg.content,
                    msg.author.id,
                    int(msg.created_at.timestamp())
                )
            )
        await db.commit()

# =========================================================
# COG
# =========================================================

class Tickets(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ---------- CREATE PANEL ----------
    @app_commands.command(name="ticket_panel", description="🎫 Create ticket panel")
    @app_commands.checks.has_permissions(administrator=True)
    async def ticket_panel(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🎫 Support Tickets",
            description="Click the button below to create a support ticket.",
            color=discord.Color.gold()
        )
        await interaction.channel.send(
            embed=embed,
            view=TicketPanelView()
        )
        await interaction.response.send_message("✅ Ticket panel created.", ephemeral=True)

    # ---------- CREATE TICKET ----------
    @app_commands.command(name="ticket", description="🎫 Create a support ticket")
    async def ticket(self, interaction: discord.Interaction):
        await interaction.response.send_modal(TicketModal())

    # ---------- MESSAGE LISTENER (TRANSCRIPTS) ----------
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        if message.channel.name.startswith("ticket-"):
            async with aiosqlite.connect("bot.db") as db:
                await db.execute(
                    "INSERT INTO ticket_transcripts (ticket_id, message, author, timestamp) VALUES (?,?,?,?)",
                    (
                        message.channel.id,
                        message.content,
                        message.author.id,
                        int(time.time())
                    )
                )
                await db.commit()

# =========================================================
# PANEL VIEW
# =========================================================

class TicketPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🎫 Create Ticket", style=discord.ButtonStyle.success, custom_id="ticket_create")
    async def create(self, interaction: discord.Interaction, _):
        await interaction.response.send_modal(TicketModal())

# =========================================================
# SETUP
# =========================================================

async def setup(bot: commands.Bot):
    bot.add_view(TicketPanelView())   # persistent
    bot.add_view(TicketView())        # persistent
    await bot.add_cog(Tickets(bot))
