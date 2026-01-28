from supabase import create_client
import os, time

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

async def init_db():
    print("✅ Supabase connected")

# ===== COINS =====
async def get_coins(user_id):
    res = supabase.table("coins").select("*").eq("user_id", user_id).execute()
    return res.data[0]["balance"] if res.data else 0

async def set_coins(user_id, balance):
    supabase.table("coins").upsert({
        "user_id": user_id,
        "balance": balance
    }).execute()

# ===== PREMIUM =====
async def set_premium(user_id, tier, days):
    supabase.table("premium").upsert({
        "user_id": user_id,
        "tier": tier,
        "expires": int(time.time()) + days * 86400
    }).execute()

async def get_premium(user_id):
    res = supabase.table("premium").select("*").eq("user_id", user_id).execute()
    return res.data[0] if res.data else None

# ===== WELCOME =====
async def set_welcome(guild_id, channel, role, message, thumb):
    supabase.table("welcome_config").upsert({
        "guild_id": guild_id,
        "welcome_channel": channel,
        "welcome_role": role,
        "welcome_message": message,
        "thumbnail_url": thumb
    }).execute()

async def get_welcome(guild_id):
    res = supabase.table("welcome_config").select("*").eq("guild_id", guild_id).execute()
    return res.data[0] if res.data else None

# ===== TICKETS =====
async def create_ticket(channel_id, user_id, category):
    supabase.table("tickets").insert({
        "channel_id": channel_id,
        "user_id": user_id,
        "claimed_by": None,
        "category": category,
        "created_at": int(time.time())
    }).execute()
