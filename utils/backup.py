import shutil
import time
import os

def backup_db():
    if not os.path.exists("bot.db"):
        return

    os.makedirs("db_backups", exist_ok=True)

    ts = time.strftime("%Y%m%d_%H%M%S")
    backup_path = f"db_backups/bot_{ts}.db"

    shutil.copyfile("bot.db", backup_path)
