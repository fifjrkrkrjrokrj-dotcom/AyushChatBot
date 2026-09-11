from os import getenv
from dotenv import load_dotenv

load_dotenv()

# Telegram API credentials
API_ID = int(getenv("API_ID", "22243185"))
API_HASH = getenv("API_HASH", "39d926a67155f59b722db787a23893ac")

# Bot configuration
BOT_TOKEN = getenv("BOT_TOKEN", None)
MONGO_URL = getenv("MONGO_URL", "mongodb+srv://ayushop:ayushop210@cluster0.gklnc.mongodb.net/?retryWrites=true&w=majority")

# Owner & Support info
OWNER_ID = int(getenv("OWNER_ID", "5311223486"))
SUPPORT_GRP = getenv("SUPPORT_GRP", "tmm_support_chat")
UPDATE_CHNL = getenv("UPDATE_CHNL", "FROZENTOOLS")
OWNER_USERNAME = getenv("OWNER_USERNAME", "moh_maya_official")

# Userbot configuration
USERBOT_AUTOCHAT_DEFAULT = getenv("USERBOT_AUTOCHAT_DEFAULT", "true").lower() == "true"

