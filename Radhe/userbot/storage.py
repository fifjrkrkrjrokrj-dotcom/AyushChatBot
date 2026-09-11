import time
from Radhe import mongo, config

USERBOT_ACCOUNTS = mongo["UserbotDB"]["accounts"] if mongo is not None else None
USERBOT_SESSIONS = mongo["SessionDB"]["sessions"] if mongo is not None else None

# In-memory account state
# account_id -> {
#     "client": Client,
#     "telegram_id": int,
#     "username": str,
#     "name": str,
#     "phone": str,
#     "added_by": int,
#     "autochat": bool,
#     "reply_delay": int,
#     "speed_mode": str,
#     "status": str,
# }
accounts = {}


def _get_owner_id() -> int | None:
    if config.OWNER_ID:
        try:
            return int(config.OWNER_ID)
        except Exception:
            return None
    return None


async def get_served_accounts() -> list:
    """Get all userbot accounts from MongoDB."""
    if USERBOT_ACCOUNTS is None:
        return []
    accounts_list = []
    try:
        async for account in USERBOT_ACCOUNTS.find({"enabled": True}):
            if "added_by" not in account or not account["added_by"]:
                account["added_by"] = _get_owner_id()
            accounts_list.append(account)
    except Exception as e:
        print(f"⚠️ Error fetching served accounts: {e}")
    return accounts_list


async def get_accounts_by_user(user_id: int) -> list:
    """
    Get userbot accounts accessible by a specific user.
    If owner, returns all accounts.
    If admin, returns only accounts added by that admin.
    """
    from Radhe.database.admins import is_owner
    if is_owner(user_id):
        return await get_served_accounts()

    if USERBOT_ACCOUNTS is None:
        return []

    accounts_list = []
    try:
        async for account in USERBOT_ACCOUNTS.find({"enabled": True, "added_by": int(user_id)}):
            accounts_list.append(account)
    except Exception as e:
        print(f"⚠️ Error fetching accounts for user {user_id}: {e}")
    return accounts_list


async def get_account(account_id: str) -> dict:
    """Get a specific account by account_id."""
    if USERBOT_ACCOUNTS is None:
        return None
    try:
        acc = await USERBOT_ACCOUNTS.find_one({"account_id": account_id, "enabled": True})
        if acc and ("added_by" not in acc or not acc["added_by"]):
            acc["added_by"] = _get_owner_id()
        return acc
    except Exception as e:
        print(f"⚠️ Error getting account {account_id}: {e}")
        return None


async def add_account(account_data: dict):
    """Add or upsert a userbot account in MongoDB."""
    if USERBOT_ACCOUNTS is None:
        return None
    try:
        account_data["updated_at"] = time.time()
        if "added_by" not in account_data or not account_data["added_by"]:
            account_data["added_by"] = _get_owner_id()
        else:
            account_data["added_by"] = int(account_data["added_by"])

        return await USERBOT_ACCOUNTS.update_one(
            {"account_id": account_data["account_id"]},
            {"$set": account_data},
            upsert=True,
        )
    except Exception as e:
        print(f"⚠️ Error adding account {account_data.get('account_id')}: {e}")
        return None


async def update_account(account_id: str, update_data: dict):
    """Update an account's data in MongoDB."""
    if USERBOT_ACCOUNTS is None:
        return None
    try:
        update_data["updated_at"] = time.time()
        return await USERBOT_ACCOUNTS.update_one(
            {"account_id": account_id},
            {"$set": update_data}
        )
    except Exception as e:
        print(f"⚠️ Error updating account {account_id}: {e}")
        return None


async def remove_account(account_id: str):
    """Remove an account completely from MongoDB and delete its session."""
    if USERBOT_ACCOUNTS is None:
        return None
    try:
        await USERBOT_ACCOUNTS.delete_one({"account_id": account_id})
        if USERBOT_SESSIONS is not None:
            await USERBOT_SESSIONS.delete_one({"account_id": account_id})
        return True
    except Exception as e:
        print(f"⚠️ Error removing account {account_id}: {e}")
        return False


async def save_session(account_id: str, session_string: str):
    """Save or upsert a session string in MongoDB."""
    if USERBOT_SESSIONS is None:
        return None
    try:
        return await USERBOT_SESSIONS.update_one(
            {"account_id": account_id},
            {"$set": {"account_id": account_id, "session_string": session_string, "updated_at": time.time()}},
            upsert=True,
        )
    except Exception as e:
        print(f"⚠️ Error saving session for {account_id}: {e}")
        return None


async def get_session(account_id: str) -> str:
    """Get a session string from MongoDB."""
    if USERBOT_SESSIONS is None:
        return None
    try:
        session = await USERBOT_SESSIONS.find_one({"account_id": account_id})
        if session:
            return session.get("session_string")
    except Exception as e:
        print(f"⚠️ Error fetching session for {account_id}: {e}")
    return None


async def delete_session(account_id: str):
    """Delete a session string from MongoDB."""
    if USERBOT_SESSIONS is None:
        return None
    try:
        return await USERBOT_SESSIONS.delete_one({"account_id": account_id})
    except Exception as e:
        print(f"⚠️ Error deleting session for {account_id}: {e}")
        return None