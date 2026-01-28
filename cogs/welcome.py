import discord
from discord.ext import commands
from discord import app_commands
from supabase import create_client, Client
import os
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# 🔗 YOUR LOGO IMAGE
LOGO_URL = "https://files.catbox.moe/c1lm6g.png"


class Welcome(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ---------------- SETUP ----------------
    @app_commands.command(name="welcome_setup", description="Setup welcome system (embed only)")
    @app_commands.checks.has_permissions(administrator=True)
    async def welcome_setup(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        role: discord.Role,
        message: str
    ):
        await interaction.response.defer(ephemeral=True)

        try:
            data = {
                "guild_id": interaction.guild.id,
                "welcome_channel": channel.id,
                "welcome_role": role.id,
                "welcome_message": message
            }

            supabase.table("guild_settings").upsert(data).execute()

            await interaction.followup.send(
                "✅ Welcome system configured!\n"
                "`{user}` = username\n"
                "`{server}` = server name"
            )

        except Exception as e:
            await interaction.followup.send(f"❌ Error: {e}")

    # ---------------- PREVIEW ----------------
    @app_commands.command(name="welcome_preview", description="Preview welcome embed")
    @app_commands.checks.has_permissions(administrator=True)
    async def welcome_preview(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        try:
            res = supabase.table("guild_settings") \
                .select("welcome_message") \
                .eq("guild_id", interaction.guild.id) \
                .execute()

            if not res.data:
                return await interaction.followup.send("❌ Welcome not configured.")

            message = res.data[0]["welcome_message"]

            embed = discord.Embed(
                title="🎉 Welcome!",
                description=message.format(
                    user=interaction.user.name,
                    server=interaction.guild.name
                ),
                color=discord.Color.gold()
            )

            embed.set_thumbnail(url=interaction.user.display_avatar.url)
            embed.set_image(url=LOGO_URL)

            await interaction.followup.send(
                content=interaction.user.mention,
                embed=embed
            )

        except Exception as e:
            await interaction.followup.send(f"❌ Error: {e}")

    # ---------------- MEMBER JOIN ----------------
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        try:
            res = supabase.table("guild_settings") \
                .select("*") \
                .eq("guild_id", member.guild.id) \
                .execute()

            if not res.data:
                return

            data = res.data[0]
            channel_id = data["welcome_channel"]
            role_id = data["welcome_role"]
            message = data["welcome_message"]

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
                await member.send(
                    message.format(
                        user=member.name,
                        server=member.guild.name
                    )
                )
            except:
                pass

            if not channel:
                return

            embed = discord.Embed(
                title="🎉 Welcome!",
                description=message.format(
                    user=member.name,
                    server=member.guild.name
                ),
                color=discord.Color.gold()
            )

            embed.set_thumbnail(url=member.display_avatar.url)
            embed.set_image(url=LOGO_URL)
            embed.set_footer(text=f"Member #{member.guild.member_count}")

            await channel.send(
                content=member.mention,
                embed=embed
            )

        except Exception as e:
            print("Welcome error:", e)


async def setup(bot: commands.Bot):
    await bot.add_cog(Welcome(bot))
