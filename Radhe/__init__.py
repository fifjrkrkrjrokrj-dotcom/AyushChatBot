import sys
import logging 
import time
from Abg import patch

from motor.motor_asyncio import AsyncIOMotorClient as MongoCli
import pyrogram.utils
from pyrogram import Client
from pyrogram.enums import ParseMode

# Patch Pyrogram for 64-bit Telegram Channel IDs (> 2 billion)
pyrogram.utils.MIN_CHANNEL_ID = -1009999999999
pyrogram.utils.MIN_CHAT_ID = -999999999999

import config

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

logging.basicConfig(
    format="[%(asctime)s - %(levelname)s] - %(name)s - %(message)s",
    datefmt="%d-%b-%y %H:%M:%S",
    handlers=[
        logging.FileHandler("log.txt", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
    level=logging.INFO,
)

logging.getLogger("pyrogram").setLevel(logging.ERROR)
LOGGER = logging.getLogger(__name__)
boot = time.time()

# MongoDB initialization
if not config.MONGO_URL:
    LOGGER.warning("⚠️ MONGO_URL environment variable is missing! MongoDB features will not work.")
    mongo = None
    db = None
else:
    mongo = MongoCli(config.MONGO_URL)
    db = mongo.Anonymous

OWNER = int(config.OWNER_ID) if config.OWNER_ID else None



class Radhe(Client):
    def __init__(self):
        super().__init__(
            name="Radhe",
            api_id=config.API_ID,
            api_hash=config.API_HASH,
            lang_code="en",
            bot_token=config.BOT_TOKEN,
            in_memory=True,
            parse_mode=ParseMode.DEFAULT,
        )
        self.id = None
        self.name = "Radhe"
        self.username = None
        self.mention = ""

    async def start(self):
        await super().start()
        self.id = self.me.id
        self.name = self.me.first_name + " " + (self.me.last_name or "")
        self.username = self.me.username
        self.mention = self.me.mention

    async def stop(self):
        await super().stop()


Radhe = Radhe()
