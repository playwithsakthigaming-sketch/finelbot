import discord
from discord.ext import commands, tasks
from discord import app_commands
from supabase import create_client
import os, json, time, shutil
from typing import List

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
ADMIN_ID = int(os.getenv("ADMIN_ID"))  # your Discord ID

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

BACKUP_DIR = "backups"
MAX_BACKUPS = 10  # auto delete old backups

TABLES = [
    "coins",
    "premium",
    "welcome_config",
    "tickets",
    "payments",
    "coupons",
    "announcements"
]

os.makedirs(BACKUP_DIR, exist_ok=True)


# =========================
# UTILS
# =========================
def get_backup_files() -> List[str]:
    files = sorted(os.listdir(BACKUP_DIR), reverse=True)
    return files


def create_backup_file():
    data = {}
    for table in TABLES:
        res = supabase.table(table).select("*").execute()
        data[table] = res.data

    filename = f"backup_{int(time.time())}.json"
    path = os.path.join(BACKUP_DIR, filename)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

    return path


def restore_backup_file(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    for table in TABLES:
        supabase.table(table).delete().neq("id", 0).execute()
        if data.get(table):
            supabase.table(table).insert(data[table]).execute()


def cleanup_old_backups():
    files = get_backup_files()
    if len(files) > MAX_BACKUPS:
        for f in files[MAX_BACKUPS:]:
            os.remove(os.path.join(BACKUP_DIR, f))


# =========================
# DROPDOWN
# =========================
class BackupSelect(discord.ui.Select):
    def __init__(self, files):
        options = [
            discord.SelectOption(label=f, value=f)
            for f in files
        ]
        super().__init__(placeholder="Select backup file", options=options)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            f"⚠️ Are you sure to restore `{self.values[0]}`?",
            view=RestoreConfirmView(self.values[0]),
            ephemeral=True
        )


class BackupSelectView(discord.ui.View):
    def __init__(self, files):
        super().__init__(timeout=60)
        self.add_item(BackupSelect(files))


# =========================
# CONFIRM BUTTONS
# =========================
class RestoreConfirmView(discord.ui.View):
    def __init__(self, filename):
        super().__init__(timeout=30)
        self.filename = filename

    @discord.ui.button(label="✅ Confirm Restore", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, _):
        try:
            restore_backup_file(os.path.join(BACKUP_DIR, self.filename))
            await interaction.response.send_message("✅ Backup restored successfully")
        except Exception as e:
            await interaction.response.send_message(f"❌ Restore failed: {e}")

    @discord.ui.button(label="❌ Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, _):
        await interaction.response.send_message("❌ Restore cancelled", ephemeral=True)


# =========================
# COG
# =========================
class Backup(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.auto_backup.start()

    # ================= AUTO BACKUP (1 HOUR) =================
    @tasks.loop(hours=1)
    async def auto_backup(self):
        try:
            path = create_backup_file()
            cleanup_old_backups()
            print(f"💾 Auto backup created: {path}")
        except Exception as e:
            admin = self.bot.get_user(ADMIN_ID)
            if admin:
                await admin.send(f"❌ Backup failed: {e}")

    @auto_backup.before_loop
    async def before_backup(self):
        await self.bot.wait_until_ready()

    # ================= MANUAL BACKUP =================
    @app_commands.command(name="backup_now", description="Create database backup now")
    @app_commands.checks.has_permissions(administrator=True)
    async def backup_now(self, interaction: discord.Interaction):
        try:
            path = create_backup_file()
            size = os.path.getsize(path) // 1024
            cleanup_old_backups()

            await interaction.response.send_message(
                f"✅ Backup created\n📁 File: `{os.path.basename(path)}`\n📦 Size: `{size} KB`",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(f"❌ Backup failed: {e}", ephemeral=True)

    # ================= RESTORE BACKUP =================
    @app_commands.command(name="restore_backup", description="Restore database from backup")
    @app_commands.checks.has_permissions(administrator=True)
    async def restore_backup(self, interaction: discord.Interaction):
        files = get_backup_files()

        if not files:
            return await interaction.response.send_message("❌ No backups found", ephemeral=True)

        await interaction.response.send_message(
            "Select a backup file:",
            view=BackupSelectView(files),
            ephemeral=True
        )


# =========================
# SETUP
# =========================
async def setup(bot: commands.Bot):
    await bot.add_cog(Backup(bot))
