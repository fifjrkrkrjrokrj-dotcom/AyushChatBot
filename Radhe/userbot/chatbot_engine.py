import random
import string
from Radhe import mongo, LOGGER


def clean_word(word: str) -> str:
    """Normalize a word for MongoDB search."""
    if not word:
        return ""
    return word.strip().lower().strip(string.punctuation)


async def get_chatbot_response(text: str = None, sticker_id: str = None) -> dict:
    """
    Search the MongoDB Word.WordDb for a matching response.
    Returns a dict with {'text': ..., 'check': 'none'} or {'sticker': ..., 'check': 'sticker'},
    or None if no match is found.
    """
    if mongo is None:
        return None

    try:
        chatai = mongo["Word"]["WordDb"]
        if chatai is None:
            return None

        # 1. Sticker query
        if sticker_id:
            cursor = chatai.find({"word": sticker_id})
            data = await cursor.to_list(length=50)
            if data:
                pick = random.choice(data)
                if pick.get("check") == "sticker":
                    return {"sticker": pick.get("text"), "check": "sticker"}
                elif pick.get("text"):
                    return {"text": pick.get("text"), "check": "none"}

        if not text:
            return None

        raw_text = text.strip()
        if not raw_text:
            return None

        lower_text = raw_text.lower()
        cleaned = clean_word(raw_text)

        # 2. Exact & cleaned sentence queries
        search_queries = []
        search_queries.append(raw_text)
        if lower_text not in search_queries:
            search_queries.append(lower_text)
        if cleaned and cleaned not in search_queries:
            search_queries.append(cleaned)

        cursor = chatai.find({"word": {"$in": search_queries}})
        data = await cursor.to_list(length=100)

        # 3. Fallback: individual word matching if sentence didn't match
        if not data:
            word_tokens = [
                clean_word(w)
                for w in raw_text.split()
                if len(clean_word(w)) >= 2
            ]
            if word_tokens:
                cursor = chatai.find({"word": {"$in": word_tokens}})
                data = await cursor.to_list(length=100)

        if not data:
            return None

        # Pick random response
        pick = random.choice(data)

        if pick.get("check") == "sticker":
            return {"sticker": pick.get("text"), "check": "sticker"}
        elif pick.get("text"):
            return {"text": pick.get("text"), "check": "none"}

        return None

    except Exception as e:
        LOGGER.error(f"⚠️ Error fetching chatbot response: {e}")
        return None