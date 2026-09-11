import time
from Radhe import mongo, config

adminsdb = mongo["UserbotDB"]["bot_admins"] if mongo is not None else None


def is_owner(user_id: int) -> bool:
    """Check if the user is the bot owner."""
    if not config.OWNER_ID:
        return True
    try:
        return int(user_id) == int(config.OWNER_ID)
    except Exception:
        return False


async def is_admin(user_id: int) -> bool:
    """Check if the user is either the bot owner or an authorized bot admin."""
    if is_owner(user_id):
        return True
    if adminsdb is None:
        return False
    try:
        doc = await adminsdb.find_one({"user_id": int(user_id)})
        return doc is not None
    except Exception as e:
        print(f"⚠️ Error checking admin status for {user_id}: {e}")
        return False


async def add_admin(user_id: int, added_by: int = None, name: str = "", username: str = "") -> bool:
    """Add a new bot admin to MongoDB."""
    if adminsdb is None:
        return False
    try:
        await adminsdb.update_one(
            {"user_id": int(user_id)},
            {
                "$set": {
                    "user_id": int(user_id),
                    "added_by": int(added_by) if added_by else (int(config.OWNER_ID) if config.OWNER_ID else None),
                    "name": name or "",
                    "username": username or "",
                    "updated_at": time.time(),
                },
                "$setOnInsert": {
                    "added_at": time.time(),
                }
            },
            upsert=True
        )
        return True
    except Exception as e:
        print(f"⚠️ Error adding admin {user_id}: {e}")
        return False


async def remove_admin(user_id: int) -> bool:
    """Remove a bot admin from MongoDB."""
    if adminsdb is None:
        return False
    try:
        result = await adminsdb.delete_one({"user_id": int(user_id)})
        return result.deleted_count > 0
    except Exception as e:
        print(f"⚠️ Error removing admin {user_id}: {e}")
        return False


async def get_admins() -> list[dict]:
    """Get list of all authorized bot admins from MongoDB."""
    if adminsdb is None:
        return []
    admin_list = []
    try:
        async for admin in adminsdb.find({"user_id": {"$gt": 0}}):
            admin_list.append(admin)
    except Exception as e:
        print(f"⚠️ Error fetching admins: {e}")
    return admin_list


async def get_admin_ids() -> list[int]:
    """Get list of all admin user IDs."""
    admin_list = await get_admins()
    ids = [adm["user_id"] for adm in admin_list]
    if config.OWNER_ID and int(config.OWNER_ID) not in ids:
        ids.append(int(config.OWNER_ID))
    return ids
