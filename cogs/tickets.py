import discord
from discord.ext import commands
from discord import app_commands
import io

# ================= CONFIG =================
STAFF_ROLE_ID = 123456789012345678        # PUT YOUR STAFF ROLE ID
TRANSCRIPT_CHANNEL_ID = 123456789012345678  # PUT YOUR TRANSCRIPT LOG CHANNEL ID
# =========================================


# =================================================
# TICKET MODAL
# =================================================
class TicketModal(discord.ui.Modal):
    def __init__(self, label: str):
        super().__init__(title=f"🎫 {label} Ticket")

        self.issue = discord.ui.TextInput(
            label="Describe your issue",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=1000
        )
        self.add_item(self.issue)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        guild = interaction.guild
        staff_role = guild.get_role(STAFF_ROLE_ID)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        }

        if staff_role:
            overwrites[staff_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        channel = await guild.create_text_channel(
            name=f"ticket-{interaction.user.name}",
            overwrites=overwrites,
            topic=str(interaction.user.id)
        )

        await channel.send(
            content=f"{interaction.user.mention} {staff_role.mention if staff_role else ''}\n"
                    f"📌 **Issue:**\n{self.issue.value}",
            view=TicketControlView(interaction.user.id)
        )

        await interaction.followup.send(
            f"✅ Ticket created: {channel.mention}",
            ephemeral=True
        )


# =================================================
# CONTROL BUTTONS
# =================================================
class TicketControlView(discord.ui.View):
    def __init__(self, user_id: int):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.claimed_by = None

    def is_staff(self, interaction: discord.Interaction):
        if interaction.user.guild_permissions.administrator:
            return True
        role = interaction.guild.get_role(STAFF_ROLE_ID)
        return role in interaction.user.roles if role else False

    # -------- CLAIM --------
    @discord.ui.button(label="🖐 Claim", style=discord.ButtonStyle.primary)
    async def claim(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)

        if not self.is_staff(interaction):
            return await interaction.followup.send("❌ Staff only.", ephemeral=True)

        if self.claimed_by:
            return await interaction.followup.send(
                f"Already claimed by <@{self.claimed_by}>",
                ephemeral=True
            )

        self.claimed_by = interaction.user.id
        await interaction.channel.send(f"🟢 Ticket claimed by {interaction.user.mention}")
        await interaction.followup.send("✅ Ticket claimed.", ephemeral=True)

    # -------- CLOSE --------
    @discord.ui.button(label="🔒 Close", style=discord.ButtonStyle.secondary)
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)

        if not self.is_staff(interaction):
            return await interaction.followup.send("❌ Staff only.", ephemeral=True)

        await interaction.channel.set_permissions(
            interaction.guild.default_role,
            read_messages=False
        )

        await interaction.channel.send("🔒 Ticket closed.")
        await interaction.followup.send("✅ Ticket closed.", ephemeral=True)

    # -------- DELETE --------
    @discord.ui.button(label="🗑 Delete", style=discord.ButtonStyle.danger)
    async def delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)

        if not interaction.user.guild_permissions.administrator:
            return await interaction.followup.send("❌ Admin only.", ephemeral=True)

        await send_transcript(interaction.channel)
        await interaction.followup.send("🗑 Ticket deleted. Transcript saved.", ephemeral=True)
        await interaction.channel.delete()


# =================================================
# TRANSCRIPT SYSTEM
# =================================================
async def send_transcript(channel: discord.TextChannel):
    messages = []
    async for msg in channel.history(limit=None, oldest_first=True):
        time = msg.created_at.strftime("%Y-%m-%d %H:%M")
        messages.append(f"[{time}] {msg.author}: {msg.content}")

    data = "\n".join(messages)
    file = discord.File(io.BytesIO(data.encode()), filename=f"{channel.name}.txt")

    guild = channel.guild
    log_channel = guild.get_channel(TRANSCRIPT_CHANNEL_ID)

    if log_channel:
        await log_channel.send(f"📄 Transcript for {channel.name}", file=file)

    try:
        user_id = int(channel.topic)
        user = await guild.fetch_member(user_id)
        await user.send("📄 Your ticket transcript:", file=file)
    except:
        pass


# =================================================
# PANEL VIEW (MULTI BUTTON)
# =================================================
class TicketPanelView(discord.ui.View):
    def __init__(self, buttons: list):
        super().__init__(timeout=None)
        for label, emoji in buttons:
            self.add_item(TicketOpenButton(label, emoji))


class TicketOpenButton(discord.ui.Button):
    def __init__(self, label: str, emoji: str):
        super().__init__(
            label=label,
            style=discord.ButtonStyle.success,
            emoji=emoji
        )
        self.label_name = label

    async def callback(self, interaction: discord.Interaction):
        try:
            await interaction.response.send_modal(TicketModal(self.label_name))
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Error opening ticket:\n```{e}```",
                ephemeral=True
            )


# =================================================
# MAIN COG
# =================================================
class Tickets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="ticket_panel_multi",
        description="Create a ticket panel with multiple buttons"
    )
    @app_commands.describe(
        title="Panel title",
        description="Panel description",
        buttons="Format: Support,🎫|Report,⚠|Billing,💰",
        role="Role to tag",
        channel="Channel to send panel",
        imageurl="Image URL (optional)"
    )
    async def ticket_panel_multi(
        self,
        interaction: discord.Interaction,
        title: str,
        description: str,
        buttons: str,
        role: discord.Role,
        channel: discord.TextChannel,
        imageurl: str = None
    ):
        await interaction.response.defer(ephemeral=True)

        try:
            button_list = []
            for part in buttons.split("|"):
                if "," not in part:
                    return await interaction.followup.send(
                        "❌ Wrong format. Use: `Name,Emoji|Name,Emoji`",
                        ephemeral=True
                    )
                name, emoji = part.split(",", 1)
                button_list.append((name.strip(), emoji.strip()))

            embed = discord.Embed(title=title, description=description, color=discord.Color.blue())
            embed.set_footer(text="Click a button to open ticket")

            if imageurl:
                embed.set_image(url=imageurl)

            await channel.send(
                content=role.mention,
                embed=embed,
                view=TicketPanelView(button_list)
            )

            await interaction.followup.send(
                f"✅ Ticket panel created in {channel.mention}",
                ephemeral=True
            )

        except Exception as e:
            await interaction.followup.send(
                f"❌ Failed to create panel:\n```{e}```",
                ephemeral=True
            )


# =================================================
# SETUP
# =================================================
async def setup(bot: commands.Bot):
    bot.add_view(TicketPanelView([]))  # persistent buttons
    await bot.add_cog(Tickets(bot))
