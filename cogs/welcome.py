import discord
from discord.ext import commands
from discord import app_commands
import aiosqlite
import os
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO

DB_NAME = "bot.db"

FONT_PATH = "fonts/CinzelDecorative-Bold.ttf"
DEFAULT_BG = "assets/welcome_bg.png"

# ================= FONT =================
def get_font(size):
    return ImageFont.truetype(FONT_PATH, size)

# ================= IMAGE GENERATOR =================
async def generate_welcome_image(member: discord.Member, message: str, bg_path: str):
    bg = Image.open(bg_path).convert("RGB").resize((900, 400))
    draw = ImageDraw.Draw(bg)

    # User avatar
    avatar_asset = member.display_avatar.with_size(128)
    avatar_bytes = await avatar_asset.read()
    avatar = Image.open(BytesIO(avatar_bytes)).resize((120, 120)).convert("RGBA")
    bg.paste(avatar, (40, 140), avatar)

    text = message.format(user=member.name, server=member.guild.name)
    draw.text((200, 170), text, font=get_font(32), fill="white")

    buf = BytesIO()
    bg.save(buf, "PNG")
    buf.seek(0)
    return buf

# ================= COG =================
class Welcome(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ---------------- SETUP ----------------
    @app_commands.command(name="welcome_setup", description="Setup welcome system")
    @app_commands.checks.has_permissions(administrator=True)
    async def welcome_setup(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        role: discord.Role,
        message: str,
        mode: str,  # text/embed/image
        bg_path: str = DEFAULT_BG
    ):
        if mode not in ["text", "embed", "image"]:
            return await interaction.response.send_message(
                "❌ Mode must be text, embed, or image", ephemeral=True
            )

        async with aiosqlite.connect(DB_NAME) as db:
            await db.execute("""
            INSERT OR REPLACE INTO guild_settings
            (guild_id, welcome_channel, welcome_role, welcome_message, welcome_mode, welcome_bg)
            VALUES (?, ?, ?, ?, ?, ?)
            """, (
                interaction.guild.id,
                channel.id,
                role.id,
                message,
                mode,
                bg_path
            ))
            await db.commit()

        await interaction.response.send_message("✅ Welcome system configured!", ephemeral=True)

    # ---------------- PREVIEW ----------------
    @app_commands.command(name="welcome_preview", description="Preview welcome message")
    @app_commands.checks.has_permissions(administrator=True)
    async def welcome_preview(self, interaction: discord.Interaction):
        async with aiosqlite.connect(DB_NAME) as db:
            cursor = await db.execute("""
            SELECT welcome_message, welcome_mode, welcome_bg
            FROM guild_settings WHERE guild_id=?
            """, (interaction.guild.id,))
            row = await cursor.fetchone()

        if not row:
            return await interaction.response.send_message("❌ Welcome not configured.", ephemeral=True)

        message, mode, bg_path = row

        if mode == "image":
            img = await generate_welcome_image(interaction.user, message, bg_path or DEFAULT_BG)
            await interaction.response.send_message(
                file=discord.File(img, "welcome_preview.png"),
                ephemeral=True
            )

        elif mode == "embed":
            embed = discord.Embed(
                title="🎉 Welcome Preview",
                description=message.format(
                    user=interaction.user.mention,
                    server=interaction.guild.name
                ),
                color=discord.Color.green()
            )
            embed.set_thumbnail(url=interaction.user.display_avatar.url)
            await interaction.response.send_message(embed=embed, ephemeral=True)

        else:
            await interaction.response.send_message(
                message.format(
                    user=interaction.user.mention,
                    server=interaction.guild.name
                ),
                ephemeral=True
            )

    # ---------------- MEMBER JOIN ----------------
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        async with aiosqlite.connect(DB_NAME) as db:
            cursor = await db.execute("""
            SELECT welcome_channel, welcome_role, welcome_message, welcome_mode, welcome_bg
            FROM guild_settings WHERE guild_id=?
            """, (member.guild.id,))
            row = await cursor.fetchone()

        if not row:
            return

        channel_id, role_id, message, mode, bg_path = row
        channel = member.guild.get_channel(channel_id)

        # Auto role
        role = member.guild.get_role(role_id)
        if role:
            try:
                await member.add_roles(role)
            except:
                pass

        # DM welcome
        try:
            dm_msg = (
                f"👋 Welcome to **{member.guild.name}**!\n\n"
                f"{message.format(user=member.name, server=member.guild.name)}\n\n"
                "Enjoy your stay 💖"
            )
            await member.send(dm_msg)
        except:
            pass

        if not channel:
            return

        if mode == "image":
            img = await generate_welcome_image(member, message, bg_path or DEFAULT_BG)
            await channel.send(file=discord.File(img, "welcome.png"))

        elif mode == "embed":
            embed = discord.Embed(
                title="🎉 Welcome!",
                description=message.format(
                    user=member.mention,
                    server=member.guild.name
                ),
                color=discord.Color.green()
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            await channel.send(embed=embed)

        else:
            await channel.send(
                message.format(
                    user=member.mention,
                    server=member.guild.name
                )
            )

# ---------------- SETUP ----------------
async def setup(bot: commands.Bot):
    await bot.add_cog(Welcome(bot))
