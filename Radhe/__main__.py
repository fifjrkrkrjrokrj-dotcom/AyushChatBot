import os
import asyncio
import importlib
from threading import Thread
from flask import Flask

from pyrogram import idle

from Radhe import LOGGER, Radhe
from Radhe.modules import ALL_MODULES
from Radhe.userbot import userbot_manager

# ─────────────────────────────────────
# 1️⃣ Flask app (Render ke liye REQUIRED)
# ─────────────────────────────────────
app = Flask(__name__)

@app.route("/")
def home():
    return "✅ Radhe Bot is Alive!"

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

# ─────────────────────────────────────
# 2️⃣ Pyrogram Bot Starter
# ─────────────────────────────────────
async def start_bot():
    try:
        await Radhe.start()
    except Exception as ex:
        LOGGER.error(ex)
        quit(1)

    for module in ALL_MODULES:
        importlib.import_module("Radhe.modules." + module)

    LOGGER.info(f"@{Radhe.username} Started Successfully")

    # Startup recovery for userbot accounts
    try:
        await userbot_manager.startup()
        LOGGER.info("✅ Multi-Userbot Manager Initialized Successfully")
    except Exception as ex:
        LOGGER.error(f"⚠️ Userbot Manager Startup Error: {ex}")

    await idle()

    # Graceful stop on shutdown
    try:
        await userbot_manager.stop()
    except Exception:
        pass

# ─────────────────────────────────────
# 3️⃣ Start Flask + Bot Together
# ─────────────────────────────────────
if __name__ == "__main__":
    Thread(target=run_flask, daemon=True).start()   # Flask server (Render port bind)
    asyncio.get_event_loop().run_until_complete(start_bot())
