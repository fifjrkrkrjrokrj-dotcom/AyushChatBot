import random
import asyncio
import string
from Abg.chat_status import adminsOnly

from pyrogram import Client, filters
from pyrogram.enums import ChatAction
from pyrogram.types import InlineKeyboardMarkup, Message

from Radhe import Radhe, mongo
from Radhe.database import RADHE
from Radhe.modules.helpers import CHATBOT_ON


# Automatically create index on startup to optimize search times
async def create_indexes():
    if mongo is not None:
        try:
            chatai = mongo["Word"]["WordDb"]
            await chatai.create_index("word")
        except Exception as e:
            print("Failed to create index:", e)

# Schedule background task to run index creation if loop is running
try:
    loop = asyncio.get_running_loop()
    loop.create_task(create_indexes())
except RuntimeError:
    pass


def clean_word(word: str) -> str:
    if not word:
        return ""
    # Strip whitespace, lowercase, and strip punctuation from start/end
    return word.strip().lower().strip(string.punctuation)


@Radhe.on_cmd("chatbot", group_only=True)
@adminsOnly("can_delete_messages")
async def chaton_(_, m: Message):
    await m.reply_text(
        f"ᴄʜᴀᴛ: {m.chat.title}\n**ᴄʜᴏᴏsᴇ ᴀɴ ᴏᴩᴛɪᴏɴ ᴛᴏ ᴇɴᴀʙʟᴇ/ᴅɪsᴀʙʟᴇ ᴄʜᴀᴛʙᴏᴛ.**",
        reply_markup=InlineKeyboardMarkup(CHATBOT_ON),
    )


@Radhe.on_message(
    (filters.text | filters.sticker) & ~filters.private & ~filters.bot,
    group=4,
)
async def chatbot_group(client: Client, message: Message):
    try:
        if message.text and message.text.startswith(("!", "/", "?", "@", "#")):
            return
    except Exception:
        pass

    if mongo is None or RADHE is None:
        return

    # Check if chatbot is disabled in this group
    is_RADHE = await RADHE.find_one({"chat_id": message.chat.id})
    if is_RADHE:
        return

    chatai = mongo["Word"]["WordDb"]

    # Learn from replies between other users (not bot itself)
    if (
        message.reply_to_message
        and message.reply_to_message.from_user
        and message.reply_to_message.from_user.id != client.id
    ):
        replied_msg = message.reply_to_message
        if replied_msg.text:
            word_to_learn = clean_word(replied_msg.text)
            if not word_to_learn:
                word_to_learn = replied_msg.text.strip().lower()

            if word_to_learn:
                # Learn sticker reply
                if message.sticker:
                    existing = await chatai.find_one(
                        {
                            "word": word_to_learn,
                            "id": message.sticker.file_unique_id,
                        }
                    )
                    if not existing:
                        await chatai.insert_one(
                            {
                                "word": word_to_learn,
                                "text": message.sticker.file_id,
                                "check": "sticker",
                                "id": message.sticker.file_unique_id,
                            }
                        )
                
                # Learn text reply
                elif message.text:
                    existing = await chatai.find_one(
                        {"word": word_to_learn, "text": message.text.strip()}
                    )
                    if not existing:
                        await chatai.insert_one(
                            {
                                "word": word_to_learn,
                                "text": message.text.strip(),
                                "check": "none",
                            }
                        )

    # Reply logic (Matches all formats and search queries)
    search_queries = []
    if message.text:
        raw_text = message.text.strip()
        search_queries.append(raw_text)
        
        lower_text = raw_text.lower()
        if lower_text not in search_queries:
            search_queries.append(lower_text)
            
        cleaned = clean_word(raw_text)
        if cleaned and cleaned not in search_queries:
            search_queries.append(cleaned)
    elif message.sticker:
        search_queries.append(message.sticker.file_unique_id)

    if not search_queries:
        return

    cursor = chatai.find({"word": {"$in": search_queries}})
    data = await cursor.to_list(length=100)
    if data:
        # Run typing action in the background to avoid delay in sending the message
        asyncio.create_task(client.send_chat_action(message.chat.id, ChatAction.TYPING))
        pick = random.choice(data)
        if pick.get("check") == "sticker":
            await message.reply_sticker(pick["text"])
        else:
            await message.reply_text(pick["text"])


@Radhe.on_message(
    (filters.text | filters.sticker) & filters.private & ~filters.bot,
    group=4,
)
async def chatbot_private(client: Client, message: Message):
    try:
        if message.text and message.text.startswith(("!", "/", "?", "@", "#")):
            return
    except Exception:
        pass

    if mongo is None:
        return

    chatai = mongo["Word"]["WordDb"]

    search_queries = []
    if message.text:
        raw_text = message.text.strip()
        search_queries.append(raw_text)
        
        lower_text = raw_text.lower()
        if lower_text not in search_queries:
            search_queries.append(lower_text)
            
        cleaned = clean_word(raw_text)
        if cleaned and cleaned not in search_queries:
            search_queries.append(cleaned)
    elif message.sticker:
        search_queries.append(message.sticker.file_unique_id)

    if not search_queries:
        return

    cursor = chatai.find({"word": {"$in": search_queries}})
    data = await cursor.to_list(length=100)
    if data:
        # Run typing action in the background to avoid delay in sending the message
        asyncio.create_task(client.send_chat_action(message.chat.id, ChatAction.TYPING))
        pick = random.choice(data)
        if pick.get("check") == "sticker":
            await message.reply_sticker(pick["text"])
        else:
            await message.reply_text(pick["text"])
