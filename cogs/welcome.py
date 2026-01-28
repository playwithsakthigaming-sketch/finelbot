import discord
from discord.ext import commands
from discord import app_commands
import aiosqlite

DB_NAME = "bot.db"

class Welcome(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # =========================
    # CREATE TABLE
    # =========================
    async def create_table(self):
        async with aiosqlite.connect(DB_NAME) as db:
            await db.execute("""
            CREATE TABLE IF NOT EXISTS welcome_config (
                guild_id INTEGER PRIMARY KEY,
                welcome_channel INTEGER,
                autorole INTEGER,
                message TEXT,
                thumbnail_url TEXT
            )
            """)
            await db.commit()

    # =========================
    # /welcome_setup
    # =========================
    @app_commands.command(name="welcome_setup", description="Setup welcome system")
    @app_commands.checks.has_permissions(administrator=True)
    async def welcome_setup(
        self,
        interaction: discord.Interaction,
        welcome_channel: discord.TextChannel,
        autorole: discord.Role,
        message: str,
        thumbnail_url: str
    ):
        await interaction.response.defer(ephemeral=True)
        await self.create_table()

        async with aiosqlite.connect(DB_NAME) as db:
            await db.execute("""
            INSERT OR REPLACE INTO welcome_config
            VALUES (?, ?, ?, ?, ?)
            """, (
                interaction.guild.id,
                welcome_channel.id,
                autorole.id,
                message,
                thumbnail_url
            ))
            await db.commit()

        await interaction.followup.send("✅ Welcome system configured successfully!")

    # =========================
    # /welcome_remove
    # =========================
    @app_commands.command(name="welcome_remove", description="Disable welcome system")
    @app_commands.checks.has_permissions(administrator=True)
    async def welcome_remove(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        async with aiosqlite.connect(DB_NAME) as db:
            await db.execute("DELETE FROM welcome_config WHERE guild_id=?", (interaction.guild.id,))
            await db.commit()

        await interaction.followup.send("❌ Welcome system removed!")

    # =========================
    # /welcome_preview
    # =========================
    @app_commands.command(name="welcome_preview", description="Preview welcome message")
    async def welcome_preview(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        async with aiosqlite.connect(DB_NAME) as db:
            cursor = await db.execute("""
            SELECT welcome_channel, autorole, message, thumbnail_url
            FROM welcome_config WHERE guild_id=?
            """, (interaction.guild.id,))
            data = await cursor.fetchone()

        if not data:
            return await interaction.followup.send("❌ Welcome system not set.")

        embed = self.build_embed(interaction.user, interaction.guild, data)
        await interaction.followup.send(embed=embed)

    # =========================
    # MEMBER JOIN EVENT
    # =========================
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        await self.create_table()

        async with aiosqlite.connect(DB_NAME) as db:
            cursor = await db.execute("""
            SELECT welcome_channel, autorole, message, thumbnail_url
            FROM welcome_config WHERE guild_id=?
            """, (member.guild.id,))
            data = await cursor.fetchone()

        if not data:
            return

        channel_id, role_id, message, thumb_url = data
        channel = member.guild.get_channel(channel_id)
        role = member.guild.get_role(role_id)

        # Auto role
        if role:
            try:
                await member.add_roles(role)
            except:
                pass

        embed = self.build_embed(member, member.guild, data)

        # DM user
        try:
            await member.send(embed=embed)
        except:
            pass

        # Send in welcome channel
        if channel:
            await channel.send(embed=embed)

    # =========================
    # EMBED BUILDER
    # =========================
    def build_embed(self, member: discord.Member, guild: discord.Guild, data):
        channel_id, role_id, message, thumb_url = data

        embed = discord.Embed(
            title="🚚 Welcome To Our Server 🚛",
            description=(
                f"👤 **{member.mention}**\n\n"
                f"{message.format(user=member.mention, server=guild.name)}\n\n"
                f"— **{guild.name} Management Team**\n"
                f"Welcome to the convoy! 🚛"
            ),
            color=discord.Color.green()
        )

        embed.set_author(name=member.name, icon_url=member.display_avatar.url)

        if thumb_url:
            embed.set_thumbnail(url=thumb_url)

        embed.set_footer(text=f"Member #{guild.member_count}")
        return embed


# =========================
# SETUP
# =========================
async def setup(bot: commands.Bot):
    await bot.add_cog(Welcome(bot))
