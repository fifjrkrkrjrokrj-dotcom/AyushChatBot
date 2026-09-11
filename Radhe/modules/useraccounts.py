import re
import time
from pyrogram import filters, enums
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from Radhe import Radhe, LOGGER, config
from Radhe.userbot.storage import (
    get_served_accounts,
    get_account,
    accounts as ub_accounts,
)
from Radhe.userbot.manager import userbot_manager
from Radhe.userbot.auth import (
    pending_auth,
    start_login_flow,
    process_otp_input,
    process_2fa_input,
)


def _is_owner(user_id: int) -> bool:
    """Check if the user is the bot owner."""
    if not config.OWNER_ID:
        return True
    try:
        return int(user_id) == int(config.OWNER_ID)
    except Exception:
        return False


def _mask_phone(phone: str) -> str:
    """Mask phone number for safe display (e.g. +91********10)."""
    if not phone:
        return "—"
    phone_clean = phone.strip()
    if len(phone_clean) <= 6:
        return phone_clean
    prefix = phone_clean[:3]
    suffix = phone_clean[-2:]
    return f"{prefix}********{suffix}"


def _format_speed_label(mode: str, delay: int) -> str:
    """Format speed mode for display."""
    if mode == "fast" or delay == 0:
        return "⚡ Fast (0s)"
    elif mode == "medium" or delay == 5:
        return f"⏱ Medium ({delay}s)"
    elif mode == "slow" or delay == 10:
        return f"🐢 Slow ({delay}s)"
    else:
        return f"⚙️ Custom ({delay}s)"


async def _build_main_dashboard() -> tuple[str, InlineKeyboardMarkup]:
    """Build the main list of all connected userbots."""
    accounts_list = await get_served_accounts()

    if not accounts_list:
        text = (
            "👥 **USERBOT MANAGEMENT DASHBOARD**\n\n"
            "📦 **No userbot accounts connected.**\n\n"
            "Click **[ ➕ Add Userbot ]** below to link your Telegram account."
        )
        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Add Userbot", callback_data="ub_add")],
            [InlineKeyboardButton("🔄 Refresh", callback_data="ub_main_refresh")],
        ])
        return text, markup

    text = (
        "👥 **USERBOT MANAGEMENT DASHBOARD**\n\n"
        f"📦 **Connected Accounts:** `{len(accounts_list)}`\n\n"
        "Select a userbot below to open its dedicated settings & controls:"
    )

    keyboard_rows = []
    for index, acc in enumerate(accounts_list, 1):
        account_id = acc["account_id"]
        in_mem = ub_accounts.get(account_id, {})

        name = in_mem.get("name", acc.get("name", "Unknown"))
        username = in_mem.get("username", acc.get("username", ""))
        user_tag = f"@{username}" if username else f"#{index}"

        autochat_state = in_mem.get("autochat", acc.get("autochat", True))
        status_icon = "🟢" if autochat_state else "🔴"

        btn_text = f"👤 {index}. {name} ({user_tag}) • {status_icon}"
        keyboard_rows.append([InlineKeyboardButton(btn_text, callback_data=f"ub_panel:{account_id}")])

    keyboard_rows.append([
        InlineKeyboardButton("➕ Add Userbot", callback_data="ub_add"),
        InlineKeyboardButton("🔄 Refresh", callback_data="ub_main_refresh"),
    ])

    return text, InlineKeyboardMarkup(keyboard_rows)


async def _build_userbot_panel(account_id: str) -> tuple[str, InlineKeyboardMarkup]:
    """Build dedicated management panel for a single userbot."""
    acc = await get_account(account_id)
    if not acc:
        return "❌ Userbot account not found.", InlineKeyboardMarkup([
            [InlineKeyboardButton("↩️ Back to Accounts", callback_data="ub_back_main")]
        ])

    in_mem = ub_accounts.get(account_id, {})
    telegram_id = in_mem.get("telegram_id", acc.get("telegram_id", 0))
    username = in_mem.get("username", acc.get("username", ""))
    username_str = f"@{username}" if username else "—"
    name = in_mem.get("name", acc.get("name", "Unknown"))
    phone_masked = _mask_phone(in_mem.get("phone", acc.get("phone", "")))

    is_connected = account_id in ub_accounts and ub_accounts[account_id].get("status") == "CONNECTED"
    status_str = "🟢 Connected" if is_connected else "🔴 Disconnected"

    autochat_state = in_mem.get("autochat", acc.get("autochat", True))
    autochat_label = "🟢 ON" if autochat_state else "🔴 OFF"
    autochat_btn_text = "🔴 Turn AutoChat OFF" if autochat_state else "🟢 Turn AutoChat ON"

    delay = in_mem.get("reply_delay", acc.get("reply_delay", 0))
    speed_mode = in_mem.get("speed_mode", acc.get("speed_mode", "fast"))
    speed_label = _format_speed_label(speed_mode, delay)

    panel_text = (
        f"👤 **Userbot Panel: {name}**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 **ID:** `{telegram_id}`\n"
        f"👤 **Username:** {username_str}\n"
        f"📱 **Phone:** `{phone_masked}`\n"
        f"📊 **Connection:** {status_str}\n"
        f"🤖 **AutoChat:** {autochat_label}\n"
        f"⚡ **Reply Speed:** {speed_label}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━"
    )

    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton(autochat_btn_text, callback_data=f"ub_toggle:{account_id}")],
        [
            InlineKeyboardButton("⚡ Speed Settings", callback_data=f"ub_speed:{account_id}"),
            InlineKeyboardButton("🔄 Restart", callback_data=f"ub_restart:{account_id}"),
        ],
        [
            InlineKeyboardButton("ℹ️ Info", callback_data=f"ub_info:{account_id}"),
            InlineKeyboardButton("🗑 Remove", callback_data=f"ub_remove:{account_id}"),
        ],
        [InlineKeyboardButton("↩️ Back to Accounts List", callback_data="ub_back_main")],
    ])

    return panel_text, markup


async def _build_speed_menu(account_id: str) -> tuple[str, InlineKeyboardMarkup]:
    """Build speed configuration menu for a userbot."""
    acc = await get_account(account_id)
    if not acc:
        return "❌ Userbot account not found.", InlineKeyboardMarkup([
            [InlineKeyboardButton("↩️ Back", callback_data="ub_back_main")]
        ])

    in_mem = ub_accounts.get(account_id, {})
    name = in_mem.get("name", acc.get("name", "Userbot"))
    username = in_mem.get("username", acc.get("username", ""))
    username_str = f"@{username}" if username else ""

    delay = in_mem.get("reply_delay", acc.get("reply_delay", 0))
    speed_mode = in_mem.get("speed_mode", acc.get("speed_mode", "fast"))
    current_speed_str = _format_speed_label(speed_mode, delay)

    speed_text = (
        f"⚡ **Reply Speed Settings: {name}** {username_str}\n\n"
        f"📊 **Current Speed:** `{current_speed_str}`\n\n"
        "Choose how fast this userbot responds:\n"
        "• ⚡ **Fast**: Instant reply (0s delay)\n"
        "• ⏱ **Medium**: 5s delay (human pace)\n"
        "• 🐢 **Slow**: 10s delay (relaxed pace)\n"
        "• ⚙️ **Custom**: Enter custom delay in seconds\n"
        "━━━━━━━━━━━━━━━━━━━━━━"
    )

    markup = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⚡ Fast (0s)", callback_data=f"ub_setspeed:{account_id}:fast"),
            InlineKeyboardButton("⏱ Medium (5s)", callback_data=f"ub_setspeed:{account_id}:medium"),
        ],
        [
            InlineKeyboardButton("🐢 Slow (10s)", callback_data=f"ub_setspeed:{account_id}:slow"),
            InlineKeyboardButton("⚙️ Custom Delay", callback_data=f"ub_setspeed:{account_id}:custom"),
        ],
        [InlineKeyboardButton(f"↩️ Back to {name}", callback_data=f"ub_panel:{account_id}")],
    ])

    return speed_text, markup


# ---------- Command Handler ----------

@Radhe.on_cmd("useraccounts")
async def useraccounts_cmd(_, m: Message):
    """Owner-only command to open the userbot management dashboard."""
    if not _is_owner(m.from_user.id):
        return await m.reply("❌ You are not authorized to use this command.")

    if m.chat.type != enums.ChatType.PRIVATE:
        return await m.reply("❌ This command works only in private chat with the bot.")

    text, markup = await _build_main_dashboard()
    await m.reply_text(text, reply_markup=markup, disable_web_page_preview=True)


# ---------- Callback Query Handlers (Group -1 to ensure priority) ----------

@Radhe.on_callback_query(filters.regex(r"^ub_"), group=-1)
async def useraccounts_callbacks(_, query: CallbackQuery):
    """Handle all useraccounts dashboard inline callbacks."""
    if not _is_owner(query.from_user.id):
        return await query.answer("❌ Unauthorized", show_alert=True)

    data = query.data

    # Main Dashboard / Refresh
    if data in ("ub_main_refresh", "ub_back_main"):
        text, markup = await _build_main_dashboard()
        try:
            await query.message.edit_text(text, reply_markup=markup, disable_web_page_preview=True)
        except Exception:
            pass
        await query.answer("🔄 Dashboard refreshed")
        return

    # Open Individual Userbot Panel
    if data.startswith("ub_panel:"):
        account_id = data.split(":", 1)[1]
        text, markup = await _build_userbot_panel(account_id)
        try:
            await query.message.edit_text(text, reply_markup=markup, disable_web_page_preview=True)
        except Exception:
            pass
        await query.answer()
        return

    # Add New Userbot
    if data == "ub_add":
        pending_auth[query.from_user.id] = {
            "step": "phone",
            "created_at": time.time(),
        }
        await query.message.edit_text(
            "📱 **Add New Userbot**\n\n"
            "Please send your Telegram phone number with country code.\n\n"
            "Example: `+919876543210`\n\n"
            "Send /cancel to cancel this operation.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ Cancel", callback_data="ub_cancel_auth")]
            ])
        )
        await query.answer()
        return

    if data == "ub_cancel_auth":
        pending_auth.pop(query.from_user.id, None)
        text, markup = await _build_main_dashboard()
        await query.message.edit_text(text, reply_markup=markup, disable_web_page_preview=True)
        await query.answer("❌ Operation cancelled")
        return

    # Toggle AutoChat
    if data.startswith("ub_toggle:"):
        account_id = data.split(":", 1)[1]
        new_state = await userbot_manager.toggle_autochat(account_id)
        state_str = "ON" if new_state else "OFF"
        await query.answer(f"✅ AutoChat is now {state_str}!", show_alert=True)
        text, markup = await _build_userbot_panel(account_id)
        try:
            await query.message.edit_text(text, reply_markup=markup, disable_web_page_preview=True)
        except Exception:
            pass
        return

    # Open Speed Menu
    if data.startswith("ub_speed:"):
        account_id = data.split(":", 1)[1]
        text, markup = await _build_speed_menu(account_id)
        try:
            await query.message.edit_text(text, reply_markup=markup, disable_web_page_preview=True)
        except Exception:
            pass
        await query.answer()
        return

    # Set Speed Presets
    if data.startswith("ub_setspeed:"):
        parts = data.split(":")
        account_id = parts[1]
        mode = parts[2]

        if mode == "fast":
            await userbot_manager.set_speed(account_id, delay=0, mode="fast")
            await query.answer("⚡ Fast mode set! (Instant reply)", show_alert=True)
            text, markup = await _build_speed_menu(account_id)
            await query.message.edit_text(text, reply_markup=markup, disable_web_page_preview=True)
            return

        elif mode == "medium":
            await userbot_manager.set_speed(account_id, delay=5, mode="medium")
            await query.answer("⏱ Medium mode set! (5s delay)", show_alert=True)
            text, markup = await _build_speed_menu(account_id)
            await query.message.edit_text(text, reply_markup=markup, disable_web_page_preview=True)
            return

        elif mode == "slow":
            await userbot_manager.set_speed(account_id, delay=10, mode="slow")
            await query.answer("🐢 Slow mode set! (10s delay)", show_alert=True)
            text, markup = await _build_speed_menu(account_id)
            await query.message.edit_text(text, reply_markup=markup, disable_web_page_preview=True)
            return

        elif mode == "custom":
            pending_auth[query.from_user.id] = {
                "step": "custom_delay",
                "account_id": account_id,
                "created_at": time.time(),
            }
            await query.message.edit_text(
                "⚙️ **Enter Custom Reply Delay**\n\n"
                "Please send the delay in seconds (e.g. `3`, `7`, `15`, `30`).\n\n"
                "Send /cancel to cancel.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("❌ Cancel", callback_data=f"ub_speed:{account_id}")]
                ])
            )
            await query.answer()
            return

    # Restart Userbot
    if data.startswith("ub_restart:"):
        account_id = data.split(":", 1)[1]
        await query.answer("🔄 Restarting userbot...", show_alert=False)
        success = await userbot_manager.restart_account(account_id)
        if success:
            await query.answer("✅ Userbot restarted successfully!", show_alert=True)
        else:
            await query.answer("❌ Failed to restart userbot. Session may be expired.", show_alert=True)
        text, markup = await _build_userbot_panel(account_id)
        try:
            await query.message.edit_text(text, reply_markup=markup, disable_web_page_preview=True)
        except Exception:
            pass
        return

    # Account Info
    if data.startswith("ub_info:"):
        account_id = data.split(":", 1)[1]
        acc = await get_account(account_id)
        if not acc:
            await query.answer("❌ Account not found", show_alert=True)
            return

        in_mem = ub_accounts.get(account_id, {})
        telegram_id = in_mem.get("telegram_id", acc.get("telegram_id", 0))
        username = in_mem.get("username", acc.get("username", ""))
        name = in_mem.get("name", acc.get("name", "Unknown"))
        phone_masked = _mask_phone(in_mem.get("phone", acc.get("phone", "")))
        is_conn = account_id in ub_accounts and ub_accounts[account_id].get("status") == "CONNECTED"
        status_str = "🟢 Connected" if is_conn else "🔴 Disconnected"
        autochat_state = in_mem.get("autochat", acc.get("autochat", True))
        autochat_str = "ON" if autochat_state else "OFF"
        delay = in_mem.get("reply_delay", acc.get("reply_delay", 0))
        speed_mode = in_mem.get("speed_mode", acc.get("speed_mode", "fast"))
        speed_label = _format_speed_label(speed_mode, delay)

        info_text = (
            "👤 **Userbot Account Info**\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🆔 **Telegram ID:** `{telegram_id}`\n"
            f"👤 **Username:** @{username if username else '—'}\n"
            f"📛 **Name:** {name}\n"
            f"📱 **Phone:** `{phone_masked}`\n"
            f"📊 **Connection:** {status_str}\n"
            f"🤖 **AutoChat:** {autochat_str}\n"
            f"⚡ **Speed:** {speed_label}\n"
            "━━━━━━━━━━━━━━━━━━━━━━"
        )
        info_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"↩️ Back to {name}", callback_data=f"ub_panel:{account_id}")]
        ])
        await query.message.edit_text(info_text, reply_markup=info_markup, disable_web_page_preview=True)
        await query.answer()
        return

    # Remove Confirmation
    if data.startswith("ub_remove:"):
        account_id = data.split(":", 1)[1]
        acc = await get_account(account_id)
        name = acc.get("name", "this userbot") if acc else "this userbot"

        confirm_text = (
            f"⚠️ **Are you sure you want to remove {name}?**\n\n"
            "Its Pyrogram client will be stopped and its session will be deleted."
        )
        confirm_markup = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Confirm Remove", callback_data=f"ub_rm_confirm:{account_id}"),
                InlineKeyboardButton("❌ Cancel", callback_data=f"ub_panel:{account_id}"),
            ]
        ])
        await query.message.edit_text(confirm_text, reply_markup=confirm_markup)
        await query.answer()
        return

    # Remove Confirmed
    if data.startswith("ub_rm_confirm:"):
        account_id = data.split(":", 1)[1]
        await userbot_manager.remove_account(account_id)
        await query.answer("🗑 Userbot removed successfully!", show_alert=True)
        text, markup = await _build_main_dashboard()
        try:
            await query.message.edit_text(text, reply_markup=markup, disable_web_page_preview=True)
        except Exception:
            pass
        return


# ---------- Owner Private Message Handler (Auth Flow & Custom Delay) ----------

@Radhe.on_message(filters.private & ~filters.bot & ~filters.forwarded, group=-1)
async def userbot_auth_messages_handler(_, m: Message):
    """Handle owner's auth messages (Phone, OTP, 2FA, Custom Delay input)."""
    owner_id = m.from_user.id
    if not _is_owner(owner_id):
        m.continue_propagation()
        return

    if owner_id not in pending_auth:
        m.continue_propagation()
        return

    text = (m.text or "").strip()

    # Allow owner to cancel with /cancel
    if text == "/cancel":
        flow = pending_auth.pop(owner_id, None)
        if flow and "account_id" in flow:
            text_p, markup_p = await _build_userbot_panel(flow["account_id"])
            await m.reply("❌ Custom delay setting cancelled.", reply_markup=markup_p)
        else:
            text_m, markup_m = await _build_main_dashboard()
            await m.reply("❌ Operation cancelled.", reply_markup=markup_m)
        m.stop_propagation()
        return

    flow = pending_auth[owner_id]
    step = flow.get("step")

    # Step: Custom Delay input
    if step == "custom_delay":
        account_id = flow.get("account_id")
        if not re.fullmatch(r"^\d+$", text):
            await m.reply("❌ Please enter a valid positive number in seconds (e.g. `3`, `8`, `20`):")
            m.stop_propagation()
            return

        delay = int(text)
        if delay < 0 or delay > 300:
            await m.reply("❌ Please enter a delay between 0 and 300 seconds:")
            m.stop_propagation()
            return

        pending_auth.pop(owner_id, None)
        await userbot_manager.set_speed(account_id, delay=delay, mode="custom")
        await m.reply(f"✅ **Custom delay set to {delay} seconds!**")

        text_panel, markup_panel = await _build_userbot_panel(account_id)
        await m.reply_text(text_panel, reply_markup=markup_panel, disable_web_page_preview=True)
        m.stop_propagation()
        return

    # Step: Phone number received
    if step == "phone":
        progress_msg = await m.reply("⏳ Connecting to Telegram and sending OTP code...")
        success, response = await start_login_flow(owner_id, text)
        await progress_msg.edit_text(response)
        m.stop_propagation()
        return

    # Step: OTP received in ONE SINGLE MESSAGE (e.g. "1 2 3 4 5")
    if step == "otp":
        progress_msg = await m.reply("⏳ Verifying OTP...")
        success, status, result = await process_otp_input(owner_id, text)

        if success and status == "SUCCESS":
            acc_info = result
            success_card = (
                "✅ **Userbot connected successfully!**\n\n"
                f"👤 **Name:** {acc_info.get('name')}\n"
                f"🆔 **ID:** `{acc_info.get('telegram_id')}`\n"
                f"🔗 **Username:** @{acc_info.get('username') or '—'}\n"
                f"🟢 **Status:** Connected\n"
                f"🤖 **AutoChat:** ON\n\n"
                "Opening userbot settings panel..."
            )
            await progress_msg.edit_text(success_card)

            # Show individual panel for new userbot
            p_text, p_markup = await _build_userbot_panel(acc_info["account_id"])
            await m.reply_text(p_text, reply_markup=p_markup, disable_web_page_preview=True)

        elif status == "2FA_REQUIRED":
            await progress_msg.edit_text(result)

        elif status == "INVALID_FORMAT":
            await progress_msg.edit_text(result)

        elif status == "INVALID_OTP":
            await progress_msg.edit_text(result)

        else:
            await progress_msg.edit_text(str(result))

        m.stop_propagation()
        return

    # Step: 2FA Password received
    if step == "2fa":
        progress_msg = await m.reply("⏳ Verifying 2FA password...")
        success, status, result = await process_2fa_input(owner_id, text)

        if success and status == "SUCCESS":
            acc_info = result
            success_card = (
                "✅ **Userbot connected successfully!**\n\n"
                f"👤 **Name:** {acc_info.get('name')}\n"
                f"🆔 **ID:** `{acc_info.get('telegram_id')}`\n"
                f"🔗 **Username:** @{acc_info.get('username') or '—'}\n"
                f"🟢 **Status:** Connected\n"
                f"🤖 **AutoChat:** ON\n\n"
                "Opening userbot settings panel..."
            )
            await progress_msg.edit_text(success_card)

            # Show individual panel for new userbot
            p_text, p_markup = await _build_userbot_panel(acc_info["account_id"])
            await m.reply_text(p_text, reply_markup=p_markup, disable_web_page_preview=True)

        else:
            await progress_msg.edit_text(str(result))

        m.stop_propagation()
        return

    m.continue_propagation()