import aiosqlite

async def init_db():
    async with aiosqlite.connect("bot.db") as db:

        await db.execute("CREATE TABLE IF NOT EXISTS coins (user_id INTEGER PRIMARY KEY, balance INTEGER DEFAULT 0)")
        await db.execute("CREATE TABLE IF NOT EXISTS premium (user_id INTEGER PRIMARY KEY, tier TEXT, expires INTEGER)")
        await db.execute("CREATE TABLE IF NOT EXISTS levels (user_id INTEGER, guild_id INTEGER, xp INTEGER DEFAULT 0, level INTEGER DEFAULT 1, PRIMARY KEY(user_id,guild_id))")
        await db.execute("CREATE TABLE IF NOT EXISTS user_themes (user_id INTEGER PRIMARY KEY, theme TEXT DEFAULT 'default')")
        await db.execute("CREATE TABLE IF NOT EXISTS tickets (channel_id INTEGER PRIMARY KEY, user_id INTEGER, created_at INTEGER, claimed_by INTEGER)")
        await db.execute("CREATE TABLE IF NOT EXISTS ticket_transcripts (ticket_id INTEGER, message TEXT, author INTEGER, timestamp INTEGER)")
        await db.execute("CREATE TABLE IF NOT EXISTS payments (invoice_id TEXT PRIMARY KEY, user_id INTEGER, rupees INTEGER, coins INTEGER, timestamp INTEGER)")
        await db.execute("CREATE TABLE IF NOT EXISTS guild_settings (guild_id INTEGER PRIMARY KEY, welcome_channel INTEGER, welcome_role INTEGER, goodbye_channel INTEGER)")
        await db.execute("CREATE TABLE IF NOT EXISTS youtube_alerts (guild_id INTEGER PRIMARY KEY, youtube_channel TEXT, discord_channel INTEGER)")

        await db.commit()
