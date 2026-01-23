import aiosqlite

DB_NAME = "bot.db"

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:

        # =================================================
        # SQLITE SAFETY PRAGMAS (VERY IMPORTANT)
        # =================================================
        await db.execute("PRAGMA journal_mode=WAL;")
        await db.execute("PRAGMA synchronous=NORMAL;")
        await db.execute("PRAGMA foreign_keys=ON;")

        # =================================================
        # COINS / ECONOMY
        # =================================================
        await db.execute("""
        CREATE TABLE IF NOT EXISTS coins (
            user_id INTEGER PRIMARY KEY,
            balance INTEGER DEFAULT 0
        )
        """)

        # =================================================
        # PREMIUM SYSTEM
        # =================================================
        await db.execute("""
        CREATE TABLE IF NOT EXISTS premium (
            user_id INTEGER PRIMARY KEY,
            tier TEXT,
            expires INTEGER
        )
        """)

        # =================================================
        # LEVELS / XP
        # =================================================
        await db.execute("""
        CREATE TABLE IF NOT EXISTS levels (
            user_id INTEGER,
            guild_id INTEGER,
            xp INTEGER DEFAULT 0,
            level INTEGER DEFAULT 1,
            PRIMARY KEY (user_id, guild_id)
        )
        """)

        # =================================================
        # THEMES
        # =================================================
        await db.execute("""
        CREATE TABLE IF NOT EXISTS user_themes (
            user_id INTEGER PRIMARY KEY,
            theme TEXT DEFAULT 'default'
        )
        """)

        # =================================================
        # TICKETS
        # =================================================
        await db.execute("""
        CREATE TABLE IF NOT EXISTS tickets (
            channel_id INTEGER PRIMARY KEY,
            user_id INTEGER,
            created_at INTEGER,
            claimed_by INTEGER
        )
        """)

        await db.execute("""
        CREATE TABLE IF NOT EXISTS ticket_transcripts (
            ticket_id INTEGER,
            message TEXT,
            author INTEGER,
            timestamp INTEGER
        )
        """)

        # =================================================
        # PAYMENTS / INVOICES
        # =================================================
        await db.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            invoice_id TEXT PRIMARY KEY,
            user_id INTEGER,
            rupees INTEGER,
            coins INTEGER,
            timestamp INTEGER
        )
        """)

        # =================================================
        # GUILD SETTINGS
        # =================================================
        await db.execute("""
        CREATE TABLE IF NOT EXISTS guild_settings (
            guild_id INTEGER PRIMARY KEY,
            welcome_channel INTEGER,
            welcome_role INTEGER,
            goodbye_channel INTEGER,
            modlog_channel INTEGER
        )
        """)

        # ---- SAFE ALTER TABLE FOR NEW WELCOME FEATURES ----
        for column, col_type in [
            ("welcome_message", "TEXT"),
            ("welcome_bg", "TEXT"),
            ("welcome_mode", "TEXT")
        ]:
            try:
                await db.execute(
                    f"ALTER TABLE guild_settings ADD COLUMN {column} {col_type}"
                )
            except aiosqlite.OperationalError:
                pass

        # =================================================
        # WARNINGS / MODERATION
        # =================================================
        await db.execute("""
        CREATE TABLE IF NOT EXISTS warnings (
            user_id INTEGER,
            guild_id INTEGER,
            count INTEGER DEFAULT 0,
            PRIMARY KEY (user_id, guild_id)
        )
        """)

        # =================================================
        # YOUTUBE ALERTS
        # =================================================
        await db.execute("""
        CREATE TABLE IF NOT EXISTS youtube_alerts (
            guild_id INTEGER PRIMARY KEY,
            youtube_channel TEXT,
            discord_channel INTEGER
        )
        """)

        # =================================================
        # COUPONS
        # =================================================
        await db.execute("""
        CREATE TABLE IF NOT EXISTS coupons (
            code TEXT PRIMARY KEY,
            type TEXT,
            value INTEGER,
            max_uses INTEGER,
            used INTEGER DEFAULT 0,
            expires INTEGER
        )
        """)

        await db.commit()        # COUPONS
        # =================================================
        await db.execute("""
        CREATE TABLE IF NOT EXISTS coupons (
            code TEXT PRIMARY KEY,
            type TEXT,
            value INTEGER,
            max_uses INTEGER,
            used INTEGER DEFAULT 0,
            expires INTEGER
        )
        """)

        await db.commit()            max_uses INTEGER,
            used INTEGER DEFAULT 0,
            expires INTEGER
        )
        """)

        await db.commit()
