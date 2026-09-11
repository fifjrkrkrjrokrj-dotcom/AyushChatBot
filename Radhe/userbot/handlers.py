import re
import string
import asyncio
from pyrogram import Client, filters, enums
from pyrogram.handlers import MessageHandler
from pyrogram.types import Message

from Radhe.userbot.chatbot_engine import get_chatbot_response, clean_word
from Radhe.userbot.storage import accounts as ub_accounts
from Radhe import mongo, LOGGER


def _is_outgoing_or_self(message: Message, my_telegram_id: int) -> bool:
    """Check if the message was sent by the userbot itself or is outgoing."""
    if message.outgoing:
        return True
    if message.from_user and message.from_user.id == my_telegram_id:
        return True
    return False


def _is_other_connected_userbot(sender_id: int) -> bool:
    """Check if the sender is another connected userbot to prevent infinite inter-userbot loops."""
    for acc in ub_accounts.values():
        if acc.get("telegram_id") == sender_id:
            return True
    return False


def _check_group_mention_or_reply(message: Message, my_telegram_id: int, my_username: str) -> tuple[bool, str]:
    """
    Check if a group message mentions the userbot or is a direct reply to the userbot.
    Returns (should_respond: bool, cleaned_text: str).
    """
    text = message.text or message.caption or ""
    has_mention = False

    # 1. Check if direct reply to a message sent by this userbot
    if message.reply_to_message:
        replied = message.reply_to_message
        if replied.from_user and replied.from_user.id == my_telegram_id:
            has_mention = True
        elif replied.outgoing:
            has_mention = True

    # 2. Check message entities for mention or text_mention
    entities = message.entities or message.caption_entities or []
    mention_spans = []

    for entity in entities:
        if entity.type == enums.MessageEntityType.MENTION:
            start = entity.offset
            end = entity.offset + entity.length
            mention_word = text[start:end]
            if my_username and mention_word.lower() == f"@{my_username.lower()}":
                has_mention = True
                mention_spans.append((start, end))
        elif entity.type == enums.MessageEntityType.TEXT_MENTION:
            if entity.user and entity.user.id == my_telegram_id:
                has_mention = True
                mention_spans.append((entity.offset, entity.offset + entity.length))

    # 3. Fallback: check raw text for @username if username is set
    if not has_mention and my_username and f"@{my_username.lower()}" in text.lower():
        has_mention = True
        pattern = re.compile(rf"@{re.escape(my_username)}\b", re.IGNORECASE)
        for match in pattern.finditer(text):
            mention_spans.append(match.span())

    if not has_mention:
        return False, ""

    # Remove mention spans from text
    if mention_spans:
        char_list = list(text)
        for start, end in sorted(mention_spans, key=lambda x: x[0], reverse=True):
            char_list[start:end] = []
        cleaned_text = "".join(char_list).strip()
    else:
        cleaned_text = text.strip()

    return True, cleaned_text


async def register_userbot_handlers(client: Client, account_id: str):
    """
    Register incoming message handlers for a connected userbot client using direct MessageHandler.
    """

    async def group_autochat_handler(c: Client, message: Message):
        """Handle group messages: ONLY respond when mentioned or replied to."""
        account = ub_accounts.get(account_id)
        if not account:
            return

        # AutoChat ON/OFF check
        if not account.get("autochat", True):
            return

        my_id = account["telegram_id"]
        my_username = account.get("username", "")

        # Self-message / loop prevention
        if _is_outgoing_or_self(message, my_id):
            return
        if message.from_user and _is_other_connected_userbot(message.from_user.id):
            return
        if message.from_user and message.from_user.is_bot:
            return

        # Skip commands
        raw_text = message.text or message.caption or ""
        if raw_text.startswith(("/", "!", "?", ".")):
            return

        # Learn from replies between other users (not bot itself)
        if (
            mongo is not None
            and message.reply_to_message
            and message.reply_to_message.from_user
            and message.reply_to_message.from_user.id != my_id
            and not message.reply_to_message.outgoing
        ):
            replied_msg = message.reply_to_message
            if replied_msg.text:
                word_to_learn = clean_word(replied_msg.text) or replied_msg.text.strip().lower()
                chatai = mongo["Word"]["WordDb"]
                if word_to_learn and chatai is not None:
                    try:
                        if message.sticker:
                            existing = await chatai.find_one({"word": word_to_learn, "id": message.sticker.file_unique_id})
                            if not existing:
                                await chatai.insert_one({
                                    "word": word_to_learn,
                                    "text": message.sticker.file_id,
                                    "check": "sticker",
                                    "id": message.sticker.file_unique_id,
                                })
                        elif message.text:
                            existing = await chatai.find_one({"word": word_to_learn, "text": message.text.strip()})
                            if not existing:
                                await chatai.insert_one({
                                    "word": word_to_learn,
                                    "text": message.text.strip(),
                                    "check": "none",
                                })
                    except Exception:
                        pass

        # Check mention or reply-to
        should_respond, cleaned_text = _check_group_mention_or_reply(message, my_id, my_username)
        if not should_respond:
            return

        # Query MongoDB Word.WordDb engine
        sticker_id = message.sticker.file_unique_id if message.sticker else None
        response = await get_chatbot_response(cleaned_text, sticker_id=sticker_id)
        if not response:
            return

        # Reply to the message with configured delay
        delay = account.get("reply_delay", 0)
        try:
            if delay > 0:
                action = enums.ChatAction.CHOOSE_STICKER if response.get("sticker") else enums.ChatAction.TYPING
                asyncio.create_task(c.send_chat_action(message.chat.id, action))
                await asyncio.sleep(delay)

            if response.get("sticker"):
                await message.reply_sticker(
                    sticker=response["sticker"],
                    reply_to_message_id=message.id,
                )
            elif response.get("text"):
                await message.reply_text(
                    text=response["text"],
                    reply_to_message_id=message.id,
                )
        except Exception as e:
            LOGGER.error(f"⚠️ Userbot ({account_id}) group reply error: {e}")

    async def private_autochat_handler(c: Client, message: Message):
        """Handle private incoming messages when AutoChat is ON."""
        account = ub_accounts.get(account_id)
        if not account:
            return

        # AutoChat ON/OFF check
        if not account.get("autochat", True):
            return

        my_id = account["telegram_id"]

        # Self-message / loop prevention
        if _is_outgoing_or_self(message, my_id):
            return
        if message.from_user and _is_other_connected_userbot(message.from_user.id):
            return
        if message.from_user and message.from_user.is_bot:
            return

        # Skip commands
        raw_text = message.text or message.caption or ""
        if raw_text.startswith(("/", "!", "?", ".")):
            return

        # Query MongoDB Word.WordDb engine
        sticker_id = message.sticker.file_unique_id if message.sticker else None
        response = await get_chatbot_response(raw_text, sticker_id=sticker_id)
        if not response:
            return

        delay = account.get("reply_delay", 0)
        try:
            if delay > 0:
                action = enums.ChatAction.CHOOSE_STICKER if response.get("sticker") else enums.ChatAction.TYPING
                asyncio.create_task(c.send_chat_action(message.chat.id, action))
                await asyncio.sleep(delay)

            if response.get("sticker"):
                await message.reply_sticker(
                    sticker=response["sticker"],
                    reply_to_message_id=message.id,
                )
            elif response.get("text"):
                await message.reply_text(
                    text=response["text"],
                    reply_to_message_id=message.id,
                )
        except Exception as e:
            LOGGER.error(f"⚠️ Userbot ({account_id}) private reply error: {e}")

    # Register handlers directly on client using MessageHandler
    group_filter = filters.group & (filters.text | filters.sticker)
    private_filter = filters.private & (filters.text | filters.sticker)

    client.add_handler(MessageHandler(group_autochat_handler, group_filter), group=1)
    client.add_handler(MessageHandler(private_autochat_handler, private_filter), group=2)
    LOGGER.info(f"✅ Handlers registered successfully for userbot {account_id}")