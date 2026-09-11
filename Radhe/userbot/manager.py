import asyncio
import time
from pyrogram import Client
from Radhe import config, mongo, LOGGER
from Radhe.userbot.storage import (
    USERBOT_ACCOUNTS,
    USERBOT_SESSIONS,
    accounts as ub_accounts,
    get_served_accounts,
    get_account,
    add_account,
    update_account,
    remove_account,
    save_session,
    get_session,
)


class AccountManager:
    """Manages multiple userbot accounts lifecycle and settings."""

    def __init__(self):
        self.cleanup_task = None

    async def startup(self):
        """Load all enabled userbot accounts from MongoDB on application startup."""
        accounts_list = await get_served_accounts()
        LOGGER.info(f"Loading {len(accounts_list)} userbot account(s)...")

        for account_doc in accounts_list:
            account_id = account_doc.get("account_id")
            try:
                await self._restore_account(account_doc)
            except Exception as e:
                LOGGER.error(f"⚠️ Failed to restore userbot account {account_id}: {e}")
                await update_account(account_id, {"status": "ERROR"})

        # Start background cleanup task for expired auth flows
        from Radhe.userbot.auth import cleanup_expired_flows
        self.cleanup_task = asyncio.create_task(self._periodic_cleanup())

    async def _restore_account(self, account_doc: dict):
        """Restore and connect a single userbot account from persistent session."""
        account_id = account_doc["account_id"]
        telegram_id = account_doc.get("telegram_id")
        username = account_doc.get("username", "")
        name = account_doc.get("name", "")
        phone = account_doc.get("phone", "")
        autochat = account_doc.get("autochat", config.USERBOT_AUTOCHAT_DEFAULT)
        reply_delay = account_doc.get("reply_delay", 0)
        speed_mode = account_doc.get("speed_mode", "fast")

        session_string = await get_session(account_id)
        if not session_string:
            LOGGER.warning(f"⚠️ No session found for userbot account {account_id}")
            await update_account(account_id, {"status": "AUTH_REQUIRED"})
            return

        client = Client(
            name=account_id,
            api_id=config.API_ID,
            api_hash=config.API_HASH,
            session_string=session_string,
            in_memory=True,
        )

        try:
            await client.start()
            me = await client.get_me()

            ub_accounts[account_id] = {
                "client": client,
                "telegram_id": me.id,
                "username": me.username or username,
                "name": name or f"{me.first_name or ''} {me.last_name or ''}".strip(),
                "phone": phone,
                "autochat": autochat,
                "reply_delay": reply_delay,
                "speed_mode": speed_mode,
                "status": "CONNECTED",
            }

            # Update MongoDB status
            await update_account(account_id, {
                "status": "CONNECTED",
                "username": me.username or username,
                "name": ub_accounts[account_id]["name"],
            })

            # Register message handlers
            from Radhe.userbot.handlers import register_userbot_handlers
            await register_userbot_handlers(client, account_id)

            LOGGER.info(f"✅ Userbot {ub_accounts[account_id]['name']} ({account_id}) connected successfully!")

        except Exception as e:
            LOGGER.error(f"❌ Error starting userbot {account_id}: {e}")
            await update_account(account_id, {"status": "ERROR"})

    async def toggle_autochat(self, account_id: str) -> bool:
        """Toggle AutoChat state for an account in-memory and in MongoDB."""
        account_doc = await get_account(account_id)
        current_state = config.USERBOT_AUTOCHAT_DEFAULT

        if account_id in ub_accounts:
            current_state = ub_accounts[account_id].get("autochat", True)
        elif account_doc:
            current_state = account_doc.get("autochat", True)

        new_state = not current_state

        if account_id in ub_accounts:
            ub_accounts[account_id]["autochat"] = new_state

        await update_account(account_id, {"autochat": new_state})
        return new_state

    async def set_speed(self, account_id: str, delay: int, mode: str):
        """Set reply speed and delay for a userbot."""
        if account_id in ub_accounts:
            ub_accounts[account_id]["reply_delay"] = delay
            ub_accounts[account_id]["speed_mode"] = mode
        await update_account(account_id, {"reply_delay": delay, "speed_mode": mode})

    async def restart_account(self, account_id: str) -> bool:
        """Restart a userbot account using its saved session."""
        account_doc = await get_account(account_id)
        if not account_doc:
            return False

        # Stop current client if active
        if account_id in ub_accounts:
            client = ub_accounts[account_id].get("client")
            if client:
                try:
                    await client.stop()
                except Exception:
                    pass
            ub_accounts.pop(account_id, None)

        # Restore from database
        try:
            await self._restore_account(account_doc)
            return account_id in ub_accounts and ub_accounts[account_id].get("status") == "CONNECTED"
        except Exception as e:
            LOGGER.error(f"⚠️ Error restarting account {account_id}: {e}")
            return False

    async def remove_account(self, account_id: str) -> bool:
        """Remove a userbot account completely."""
        if account_id in ub_accounts:
            client = ub_accounts[account_id].get("client")
            if client:
                try:
                    await client.stop()
                except Exception:
                    pass
            ub_accounts.pop(account_id, None)

        await remove_account(account_id)
        return True

    async def _periodic_cleanup(self):
        """Periodically clean up expired login flows."""
        from Radhe.userbot.auth import cleanup_expired_flows
        while True:
            try:
                await asyncio.sleep(60)
                await cleanup_expired_flows()
            except Exception:
                pass

    async def stop(self):
        """Stop all userbot clients on shutdown."""
        if self.cleanup_task:
            self.cleanup_task.cancel()

        for account_id, data in list(ub_accounts.items()):
            client = data.get("client")
            if client:
                try:
                    await client.stop()
                except Exception:
                    pass
        ub_accounts.clear()


userbot_manager = AccountManager()