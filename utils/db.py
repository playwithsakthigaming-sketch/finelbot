from supabase import create_client
import os

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ======================
# INIT DB (no create tables here, done in Supabase SQL)
# ======================
async def init_db():
    print("✅ Supabase connected")


# ======================
# COINS FUNCTIONS
# ======================
async def get_coins(user_id: int):
    data = supabase.table("coins").select("*").eq("user_id", user_id).execute()
    if data.data:
        return data.data[0]["balance"]
    return 0


async def add_coins(user_id: int, amount: int):
    existing = supabase.table("coins").select("*").eq("user_id", user_id).execute()

    if existing.data:
        supabase.table("coins").update(
            {"balance": existing.data[0]["balance"] + amount}
        ).eq("user_id", user_id).execute()
    else:
        supabase.table("coins").insert(
            {"user_id": user_id, "balance": amount}
        ).execute()


# ======================
# WELCOME CONFIG
# ======================
async def set_welcome_config(guild_id, channel, role, message, thumbnail):
    supabase.table("welcome_config").upsert({
        "guild_id": guild_id,
        "welcome_channel": channel,
        "welcome_role": role,
        "welcome_message": message
    }).execute()


async def get_welcome_config(guild_id):
    res = supabase.table("welcome_config").select("*").eq("guild_id", guild_id).execute()
    if res.data:
        return res.data[0]
    return None


# ======================
# PAYMENTS
# ======================
async def save_payment(invoice_id, user_id, rupees, coins, timestamp):
    supabase.table("payments").insert({
        "invoice_id": invoice_id,
        "user_id": user_id,
        "rupees": rupees,
        "coins": coins,
        "timestamp": timestamp
    }).execute()
