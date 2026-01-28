# cogs/tickets.py
import discord, os, time
from discord.ext import commands
from discord import app_commands
from supabase import create_client

supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

STAFF_ROLE_NAME = "Staff"

class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🖐 Claim", style=discord.ButtonStyle.primary, custom_id="ticket_claim")
    async def claim(self, interaction: discord.Interaction, button: discord.ui.Button):
        staff_role = discord.utils.get(interaction.guild.roles, name=STAFF_ROLE_NAME)
        if staff_role not in interaction.user.roles:
            return await interaction.response.send_message("❌ Staff only", ephemeral=True)

        supabase.table("tickets").update({
            "claimed_by": interaction.user.id
        }).eq("channel_id", interaction.channel.id).execute()

        await interaction.channel.send(f"✅ Ticket claimed by {interaction.user.mention}")
        await interaction.response.defer()

    @discord.ui.button(label="🔒 Close", style=discord.ButtonStyle.danger, custom_id="ticket_close")
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.channel.set_permissions(interaction.guild.default_role, view_channel=False)
        await interaction.response.send_message("🔒 Ticket closed", ephemeral=True)


class Tickets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        bot.add_view(TicketView())

    @app_commands.command(name="ticket_panel", description="Create ticket panel")
    @app_commands.checks.has_permissions(administrator=True)
    async def ticket_panel(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🎫 Support Tickets",
            description="Click button to open ticket",
            color=discord.Color.green()
        )
        await interaction.channel.send(embed=embed, view=TicketView())
        await interaction.response.send_message("✅ Ticket panel created", ephemeral=True)

    @app_commands.command(name="create_ticket", description="Create a ticket")
    async def create_ticket(self, interaction: discord.Interaction, category: str):
        guild = interaction.guild
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True),
        }

        channel = await guild.create_text_channel(
            name=f"ticket-{interaction.user.name}",
            overwrites=overwrites
        )

        supabase.table("tickets").insert({
            "channel_id": channel.id,
            "user_id": interaction.user.id,
            "claimed_by": None,
            "category": category,
            "created_at": int(time.time())
        }).execute()

        await channel.send(f"{interaction.user.mention}", view=TicketView())
        await interaction.response.send_message(f"✅ Ticket created: {channel.mention}", ephemeral=True)


async def setup(bot):
    await bot.add_cog(Tickets(bot))
