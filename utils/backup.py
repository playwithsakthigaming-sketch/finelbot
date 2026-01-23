import shutil
import time
import os

def backup_db():
    if not os.path.exists("bot.db"):
        return
    ts = time.strftime("%Y%m%d_%H%M")
    shutil.copyfile("bot.db", f"backup_bot_{ts}.db")
