import discord
from discord.ext import commands
from discord import app_commands
import aiohttp, io, aiosqlite
from PIL import Image, ImageDraw, ImageFont

DB_NAME = "bot.db"

DEFAULT_BG = "https://i.imgur.com/zvWTUVu.png"  # change if you want


class Welcome(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ================= SETUP COMMAND =================
    @app_commands.command(name="set_welcome", description="Setup welcome system")
    @app_commands.describe(
        channel="Welcome channel",
        role="Auto role",
        message="Welcome message (use {user})",
        background_url="Background image URL (optional)"
    )
    async def set_welcome(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        role: discord.Role,
        message: str,
        background_url: str = None
    ):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ Admin only.", ephemeral=True)

        await interaction.response.defer(ephemeral=True)

        async with aiosqlite.connect(DB_NAME) as db:
            await db.execute("""
                INSERT OR REPLACE INTO guild_settings
                (guild_id, welcome_channel, welcome_role, welcome_message, welcome_bg, welcome_mode)
                VALUES (?,?,?,?,?,?)
            """, (
                interaction.guild.id,
                channel.id,
                role.id,
                message,
                background_url,
                "image"
            ))
            await db.commit()

        await interaction.followup.send("✅ Welcome system updated.")

    # ================= MEMBER JOIN =================
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        async with aiosqlite.connect(DB_NAME) as db:
            async with db.execute("""
                SELECT welcome_channel, welcome_role, welcome_message, welcome_bg
                FROM guild_settings WHERE guild_id=?
            """, (member.guild.id,)) as cursor:
                data = await cursor.fetchone()

        if not data:
            return

        channel_id, role_id, message, bg_url = data

        channel = member.guild.get_channel(channel_id)
        role = member.guild.get_role(role_id)

        if not channel:
            return

        # Auto role
        if role:
            await member.add_roles(role)

        # Generate image
        image = await self.generate_welcome_image(member, bg_url)

        file = discord.File(image, filename="welcome.png")

        embed = discord.Embed(
            title="🎉 Welcome!",
            description=message.replace("{user}", member.mention),
            color=discord.Color.green()
        )

        embed.set_image(url="attachment://welcome.png")

        # Server logo top right
        if member.guild.icon:
            embed.set_thumbnail(url=member.guild.icon.url)

        await channel.send(embed=embed, file=file)

    # ================= IMAGE GENERATOR =================
    async def generate_welcome_image(self, member: discord.Member, bg_url: str):
        if not bg_url:
            bg_url = DEFAULT_BG

        async with aiohttp.ClientSession() as session:
            async with session.get(bg_url) as resp:
                bg_bytes = await resp.read()

            async with session.get(member.display_avatar.url) as resp:
                avatar_bytes = await resp.read()

            if member.guild.icon:
                async with session.get(member.guild.icon.url) as resp:
                    logo_bytes = await resp.read()
            else:
                logo_bytes = None

        bg = Image.open(io.BytesIO(bg_bytes)).resize((800, 300)).convert("RGBA")
        avatar = Image.open(io.BytesIO(avatar_bytes)).resize((150, 150)).convert("RGBA")

        # Paste avatar LEFT
        bg.paste(avatar, (30, 75))

        # Paste server logo TOP RIGHT
        if logo_bytes:
            logo = Image.open(io.BytesIO(logo_bytes)).resize((100, 100)).convert("RGBA")
            bg.paste(logo, (670, 20), logo)

        draw = ImageDraw.Draw(bg)

        try:
            font = ImageFont.truetype("arial.ttf", 40)
        except:
            font = ImageFont.load_default()

        draw.text((220, 120), f"Welcome {member.name}!", font=font, fill="white")

        buffer = io.BytesIO()
        bg.save(buffer, format="PNG")
        buffer.seek(0)
        return buffer


async def setup(bot):
    await bot.add_cog(Welcome(bot))
