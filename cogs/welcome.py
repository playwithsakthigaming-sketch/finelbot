import discord
from discord.ext import commands
from discord import app_commands
import aiosqlite
import os
from PIL import Image, ImageDraw, ImageFont, ImageSequence
from io import BytesIO

DB_NAME = "bot.db"

FONT_PATH = "fonts/CinzelDecorative-Bold.ttf"
DEFAULT_BG = "assets/welcome_bg.png"

# ================= FONT =================
def get_font(size):
    if not os.path.exists(FONT_PATH):
        raise FileNotFoundError(f"Font not found: {FONT_PATH}")
    return ImageFont.truetype(FONT_PATH, size)

# ================= IMAGE GENERATOR =================
async def generate_welcome_image(member: discord.Member, message: str, bg_path: str):
    bg = Image.open(bg_path)

    frames = []
    is_gif = getattr(bg, "is_animated", False)

    for frame in ImageSequence.Iterator(bg) if is_gif else [bg]:
        frame = frame.convert("RGBA").resize((900, 400))
        draw = ImageDraw.Draw(frame)

        # User avatar
        avatar_asset = member.display_avatar.with_size(128)
        avatar_bytes = await avatar_asset.read()
        avatar = Image.open(BytesIO(avatar_bytes)).resize((120,120)).convert("RGBA")
        frame.paste(avatar, (40, 140), avatar)

        # Server logo
        if member.guild.icon:
            icon_asset = member.guild.icon.with_size(128)
            icon_bytes = await icon_asset.read()
            icon = Image.open(BytesIO(icon_bytes)).resize((80,80)).convert("RGBA")
            frame.paste(icon, (780, 20), icon)

        text = message.format(user=member.name, server=member.guild.name)
        draw.text((200, 160), text, font=get_font(32), fill="white")

        frames.append(frame)

    buf = BytesIO()
    if is_gif:
        frames[0].save(
            buf,
            format="GIF",
            save_all=True,
            append_images=frames[1:],
            duration=bg.info.get("duration", 100),
            loop=0
        )
        fmt = "gif"
    else:
        frames[0].save(buf, format="PNG")
        fmt = "png"

    buf.seek(0)
    return buf, fmt

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
        mode: str,
        bg_path: str = DEFAULT_BG
    ):
        async with aiosqlite.connect(DB_NAME) as db:
            await db.execute("""
            INSERT OR REPLACE INTO guild_settings
            (guild_id, welcome_channel, welcome_role, welcome_message, welcome_bg, welcome_mode)
            VALUES (?, ?, ?, ?, ?, ?)
            """, (
                interaction.guild.id,
                channel.id,
                role.id,
                message,
                bg_path,
                mode
            ))
            await db.commit()

        await interaction.response.send_message("✅ Welcome system configured!", ephemeral=True)

    # ---------------- PREVIEW ----------------
    @app_commands.command(name="welcome_preview", description="Preview welcome message")
    @app_commands.checks.has_permissions(administrator=True)
    async def welcome_preview(self, interaction: discord.Interaction):
        async with aiosqlite.connect(DB_NAME) as db:
            cursor = await db.execute("""
            SELECT welcome_message, welcome_bg, welcome_mode
            FROM guild_settings WHERE guild_id=?
            """, (interaction.guild.id,))
            row = await cursor.fetchone()

        if not row:
            return await interaction.response.send_message("❌ Welcome not configured.", ephemeral=True)

        message, bg_path, mode = row

        if mode == "image":
            img, fmt = await generate_welcome_image(interaction.user, message, bg_path or DEFAULT_BG)
            await interaction.response.send_message(
                file=discord.File(img, f"welcome_preview.{fmt}"),
                ephemeral=True
            )

        elif mode == "embed":
            embed = discord.Embed(
                title="🎉 Welcome Preview",
                description=message.format(user=interaction.user.mention, server=interaction.guild.name),
                color=discord.Color.green()
            )
            embed.set_thumbnail(url=interaction.user.display_avatar.url)
            await interaction.response.send_message(embed=embed, ephemeral=True)

        else:
            await interaction.response.send_message(
                message.format(user=interaction.user.mention, server=interaction.guild.name),
                ephemeral=True
            )

    # ---------------- MEMBER JOIN ----------------
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        async with aiosqlite.connect(DB_NAME) as db:
            cursor = await db.execute("""
            SELECT welcome_channel, welcome_role, welcome_message, welcome_bg, welcome_mode
            FROM guild_settings WHERE guild_id=?
            """, (member.guild.id,))
            row = await cursor.fetchone()

        if not row:
            return

        channel_id, role_id, message, bg_path, mode = row
        channel = member.guild.get_channel(channel_id)

        # Auto role
        role = member.guild.get_role(role_id)
        if role:
            await member.add_roles(role)

        # DM welcome
        try:
            dm_text = (
                f"👋 Welcome to **{member.guild.name}**!\n\n"
                f"{message.format(user=member.name, server=member.guild.name)}\n\n"
                "Enjoy your stay 💖"
            )
            await member.send(dm_text)
        except:
            pass

        # Server welcome
        if mode == "image":
            img, fmt = await generate_welcome_image(member, message, bg_path or DEFAULT_BG)
            await channel.send(file=discord.File(img, f"welcome.{fmt}"))

        elif mode == "embed":
            embed = discord.Embed(
                title="🎉 Welcome!",
                description=message.format(user=member.mention, server=member.guild.name),
                color=discord.Color.green()
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.set_footer(text=f"Member #{member.guild.member_count}")
            await channel.send(embed=embed)

        else:
            await channel.send(message.format(user=member.mention, server=member.guild.name))

# ================= SETUP =================
async def setup(bot: commands.Bot):
    await bot.add_cog(Welcome(bot))
