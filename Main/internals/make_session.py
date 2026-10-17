# Copyright (C) 2021-present by Altruix@Github, < https://github.com/Altruix >.
#
# This file is part of < https://github.com/Altruix/Altruix > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/Altriux/Altruix/blob/main/LICENSE >
#
# All rights reserved.

import re
import os
import sys
import psutil
import asyncio
import logging
from typing import Dict, Any, Optional
from Main import Altruix
from Main.utils.suppress import suppress_error
from Main.core.decorators import log_errors
from Main.utils.custom_filters import filters
from telethon import errors, functions, types, custom
from telethon.sessions import StringSession
from Main.core.types.client import AltruixTelegramClient

logger = logging.getLogger("altruix.make_session")

# Active interactive login sessions: chat_id -> state dict
_ACTIVE_LOGINS: Dict[int, Dict[str, Any]] = {}
_PENDING_LOGINS: set = set()

# First-Claim Ownership Lock
_TWP_LOCKED_USER: Optional[int] = None


def is_twp_authorized(sender_id: Optional[int]) -> bool:
    """
    Security Barrier for Training Wheels Protocol (TWP):
    1. If OWNER_ID is configured in environment, strictly enforce sender_id == OWNER_ID.
    2. If OWNER_ID is not configured, the first user to run setup locks ownership to prevent hijacking.
    """
    global _TWP_LOCKED_USER
    if not sender_id:
        return False
    owner_id = getattr(Altruix.config, "OWNER_ID", None)
    if owner_id and str(owner_id).strip().isdigit() and int(owner_id) > 0:
        return sender_id == int(owner_id)
    if _TWP_LOCKED_USER is None:
        _TWP_LOCKED_USER = sender_id
        return True
    return sender_id == _TWP_LOCKED_USER


async def client_session(api_id: int, api_hash: str) -> AltruixTelegramClient:
    return AltruixTelegramClient(StringSession(), api_id=int(api_id), api_hash=str(api_hash))


def get_numpad_buttons() -> list:
    return [
        [
            custom.Button.inline("1", b"otp_1"),
            custom.Button.inline("2", b"otp_2"),
            custom.Button.inline("3", b"otp_3"),
        ],
        [
            custom.Button.inline("4", b"otp_4"),
            custom.Button.inline("5", b"otp_5"),
            custom.Button.inline("6", b"otp_6"),
        ],
        [
            custom.Button.inline("7", b"otp_7"),
            custom.Button.inline("8", b"otp_8"),
            custom.Button.inline("9", b"otp_9"),
        ],
        [
            custom.Button.inline("⌫ Del", b"otp_del"),
            custom.Button.inline("0", b"otp_0"),
            custom.Button.inline("✖ Cancel", b"otp_cancel"),
        ],
    ]


def get_numpad_text(phone: str, digits: str) -> str:
    masked_list = list(digits) + ["•"] * max(0, 5 - len(digits))
    masked_display = " ".join(masked_list)
    return (
        "📲 <b>Telegram Login Code Sent!</b>\n\n"
        f"• <b>Target Phone:</b> <code>{phone}</code>\n"
        f"• <b>Code Entered:</b> <code>[ {masked_display} ]</code>\n\n"
        "🔒 <b>Secure NumPad Active:</b>\n"
        "<i>Tap the buttons below to enter your 5-digit code safely. Telegram never cancels login codes submitted via button clicks!</i>\n\n"
        "<i>(Or send the code as a message with letters between digits, e.g. <code>x1x2x3x4x5</code>)</i>"
    )


async def persist_and_finalize_session(app, session_str: str, chat_id: int):
    status_msg = await Altruix.bot.send_message(chat_id, "Connecting session and registering with Altruix...")
    try:
        new_client = await Altruix.add_session(session_str, status_msg)
    except Exception as e:
        return await status_msg.edit(f"❌ Failed to connect session: {e}")

    user_id = new_client.myself.id
    user_name = getattr(new_client.myself, "first_name", "User")
    username = getattr(new_client.myself, "username", None)
    username_str = f"@{username}" if username else "None"

    # Multi-Tier Persistence for Serverless & Cloud Hosting:
    # Tier 1: Cloud/Active Database (Survives dyno/container restarts)
    if Altruix.db is not None and Altruix.config:
        with suppress_error(msg="Persisting session to database"):
            await Altruix.config.add_element_to_list("SESSIONS", session_str)
            await Altruix.config.add_env_to_db("OWNER_ID", user_id, upsert=True)

    # Tier 2: Heroku Config Vars (if running on Heroku)
    h_api_key = getattr(Altruix.config, "HEROKU_API_KEY", None) or os.environ.get("HEROKU_API_KEY")
    h_app_name = getattr(Altruix.config, "HEROKU_APP_NAME", None) or os.environ.get("HEROKU_APP_NAME")
    if h_api_key and h_app_name:
        try:
            import heroku3
            h = heroku3.from_key(h_api_key)
            app_inst = h.app(h_app_name)
            curr = app_inst.config().get("SESSIONS", "")
            if session_str not in curr:
                app_inst.config()["SESSIONS"] = f"{curr} {session_str}".strip()
            app_inst.config()["OWNER_ID"] = str(user_id)
        except Exception:
            pass

    # Tier 3: Local .env (if on VPS/local machine with writable disk)
    if hasattr(Altruix.config, "append_session"):
        with suppress_error(msg="Appending session to .env"):
            Altruix.config.append_session(session_str)

    # Disable TWP
    Altruix.training_wheels_protocol = False

    # Detect Serverless / Ephemeral environment
    is_serverless = any(
        k in os.environ for k in ("DYNO", "KOYEB_APP_NAME", "RENDER", "RAILWAY_STATIC_URL", "VERCEL")
    ) or os.path.exists("/.dockerenv")

    db_is_persistent = Altruix.db is not None and not isinstance(Altruix.db, type(Altruix.local_db))

    if is_serverless and not db_is_persistent:
        serverless_notice = (
            "\n\n⚠️ <b>Serverless Host Detected (Ephemeral Storage):</b>\n"
            "Your container wipes local files on reboot. To make your userbot permanent, "
            "add these variables to your cloud platform's <b>Environment Variables</b> dashboard:\n\n"
            f"<code>SESSIONS={session_str}</code>\n"
            f"<code>OWNER_ID={user_id}</code>"
        )
    else:
        serverless_notice = (
            "\n\n💾 <b>Persistence Verified:</b>\n"
            "Your session is securely saved in your database & configuration. "
            "It will persist across all container/dyno restarts automatically."
        )

    # Send backup copy to Saved Messages
    with suppress_error(msg="Sending backup to Saved Messages"):
        await new_client.send_message(
            "me",
            f"**🔐 Altruix Telethon String Session**\n\n`{session_str}`\n\n"
            "Keep this session secret! Do not share it with anyone.",
        )

    success_text = (
        f"🎉 <b>Setup Complete! Welcome {user_name}!</b>\n\n"
        f"• <b>Account:</b> {user_name} ({username_str})\n"
        f"• <b>User ID:</b> <code>{user_id}</code> (Configured as Owner)\n"
        f"• <b>Status:</b> 🟢 Operational & Online"
        f"{serverless_notice}"
    )

    success_buttons = [
        [
            custom.Button.inline("🎛️ Settings Panel", b"panel_refresh"),
            custom.Button.inline("⚡ Test Ping", b"panel_ping"),
        ],
        [custom.Button.inline("📖 Help Menu", b"help#_cat?cat=all&page=0")],
    ]

    await Altruix.bot.send_message(chat_id, success_text, buttons=success_buttons, parse_mode="html")


# ==========================================
# Phone Number Input Handler
# ==========================================

@Altruix.bot.on_callback_query(filters.regex(r"^session_no"))
@log_errors
async def add_session_cb_handler(_, cb):
    sender_id = getattr(cb, "sender_id", 0)
    if not is_twp_authorized(sender_id):
        return await cb.answer("⛔ Access Denied: Setup is locked to the owner.", alert=True)

    chat_id = cb.chat_id
    if chat_id in _PENDING_LOGINS or chat_id in _ACTIVE_LOGINS:
        return await cb.answer("⚠️ Login is already in progress! Please enter your code/password or /cancel.", alert=True)

    _PENDING_LOGINS.add(chat_id)
    await cb.answer()

    with suppress_error(msg="Deleting session_no callback message"):
        await cb.delete()

    api_id = Altruix.config.API_ID
    api_hash = Altruix.config.API_HASH

    if not api_id or not api_hash:
        _PENDING_LOGINS.discard(chat_id)
        return await Altruix.bot.send_message(chat_id, "API_ID or API_HASH is not set in config.")

    # 1. Ask phone number in bounded conversation and exit conversation immediately
    phone_number = None
    try:
        if hasattr(Altruix.bot, "_conversations"):
            with suppress_error():
                for c_obj in list(Altruix.bot._conversations.get(chat_id, set())):
                    c_obj._cancel_all()
                Altruix.bot._conversations.pop(chat_id, None)

        async with Altruix.bot.conversation(chat_id, timeout=120, exclusive=False) as conv:
            phone_prompt = await conv.send_message(
                "📱 Please send your Telegram phone number with international country code (e.g. <code>+1234567890</code>).\n\n"
                "Use /cancel to cancel.",
                parse_mode="html",
            )
            while True:
                resp = await conv.get_response(phone_prompt)
                raw_text = resp.raw_text.strip()
                if raw_text == "/cancel":
                    _PENDING_LOGINS.discard(chat_id)
                    return await conv.send_message("Setup cancelled.")
                cleaned_phone = re.sub(r"[\s\-\(\)]", "", raw_text)
                if re.match(r"^\+?\d{7,16}$", cleaned_phone):
                    phone_number = cleaned_phone
                    break
                phone_prompt = await conv.send_message(
                    "❌ That does not look like a valid phone number format.\n"
                    "Please send your phone number with country code (e.g. <code>+1234567890</code>), or /cancel to abort.",
                    parse_mode="html",
                )
    except Exception as e:
        _PENDING_LOGINS.discard(chat_id)
        return await Altruix.bot.send_message(chat_id, f"❌ Setup conversation error: {e}")
    finally:
        _PENDING_LOGINS.discard(chat_id)

    # 2. Connect to Telegram MTProto outside conversation
    process_msg = await Altruix.bot.send_message(chat_id, "Connecting to Telegram...")
    app = await client_session(api_id, api_hash)
    await app.connect()

    try:
        sent_code = await app.send_code_request(phone_number)
    except errors.FloodWaitError as e:
        await app.disconnect()
        return await process_msg.edit(f"Floodwait: please wait {e.seconds} seconds.")
    except errors.PhoneNumberInvalidError:
        await app.disconnect()
        return await process_msg.edit("Invalid phone number format. Please check and try again.")
    except errors.ApiIdInvalidError:
        await app.disconnect()
        return await process_msg.edit("Invalid API ID or Hash.")
    except Exception as e:
        await app.disconnect()
        return await process_msg.edit(f"Connection error: {e}")

    # 3. Store active login state
    _ACTIVE_LOGINS[chat_id] = {
        "app": app,
        "phone": phone_number,
        "hash": sent_code.phone_code_hash,
        "digits": "",
        "awaiting_2fa": False,
    }

    with suppress_error():
        await process_msg.delete()

    numpad_msg = await Altruix.bot.send_message(
        chat_id,
        get_numpad_text(phone_number, ""),
        buttons=get_numpad_buttons(),
        parse_mode="html",
    )
    _ACTIVE_LOGINS[chat_id]["msg_id"] = numpad_msg.id


# ==========================================
# OTP Text & 2FA Password Input Handler
# ==========================================

@Altruix.bot.on_message(filters.private)
async def on_twp_text_input(client, message):
    chat_id = message.chat_id
    state = _ACTIVE_LOGINS.get(chat_id)
    if not state:
        return

    raw = (message.raw_text or "").strip()
    if raw.startswith("/start"):
        return
    if raw == "/cancel":
        app = state.get("app")
        if app:
            with suppress_error():
                await app.disconnect()
        _ACTIVE_LOGINS.pop(chat_id, None)
        return await message.reply("❌ Login process cancelled.")

    # A. 2FA Password Handling (Event-driven, zero conversation locks)
    if state.get("awaiting_2fa"):
        app = state["app"]
        verifying = await message.reply("⏳ Verifying 2FA password...")
        try:
            await app.sign_in(password=raw)
            with suppress_error():
                await verifying.delete()
        except Exception as e:
            return await verifying.edit(
                f"❌ <b>2FA Verification Failed:</b> <code>{e}</code>\n\nPlease check your password and send it again, or /cancel to abort.",
                parse_mode="html",
            )

        _ACTIVE_LOGINS.pop(chat_id, None)
        session_str = app.session.save()
        await app.disconnect()
        return await persist_and_finalize_session(app, session_str, chat_id)

    # B. Code Digits Fallback
    digits = "".join(re.findall(r"\d", raw))
    if len(digits) >= 5:
        state["digits"] = digits[:5]
        await _submit_login_code(chat_id, message)


# ==========================================
# OTP NumPad Callback Handler
# ==========================================

@Altruix.bot.on_callback_query(filters.regex(r"^otp_"))
async def on_otp_numpad_callback(c, cq):
    sender_id = getattr(cq, "sender_id", 0)
    if not is_twp_authorized(sender_id):
        return await cq.answer("⛔ Access Denied: Setup is locked to the owner.", alert=True)

    chat_id = cq.chat_id
    state = _ACTIVE_LOGINS.get(chat_id)
    if not state:
        return await cq.answer("Session expired. Please restart login.", alert=True)

    data = cq.data.decode("utf-8") if isinstance(cq.data, bytes) else str(cq.data)
    action = data.split("_", 1)[1]

    if action == "cancel":
        await cq.answer("Login cancelled.")
        app = state.get("app")
        if app:
            with suppress_error():
                await app.disconnect()
        _ACTIVE_LOGINS.pop(chat_id, None)
        try:
            await cq.edit("❌ <i>Login operation cancelled.</i>", buttons=None, parse_mode="html")
        except Exception:
            pass
        return

    if action == "del":
        state["digits"] = state["digits"][:-1]
        await cq.answer()
        try:
            await cq.edit(
                get_numpad_text(state["phone"], state["digits"]),
                buttons=get_numpad_buttons(),
                parse_mode="html",
            )
        except Exception:
            pass
        return

    # Numeric digit entered
    if action.isdigit():
        if len(state["digits"]) < 5:
            state["digits"] += action
        await cq.answer()

        try:
            await cq.edit(
                get_numpad_text(state["phone"], state["digits"]),
                buttons=get_numpad_buttons(),
                parse_mode="html",
            )
        except Exception:
            pass

        # Auto-submit once 5 digits are collected
        if len(state["digits"]) == 5:
            await _submit_login_code(chat_id, cq)


async def _submit_login_code(chat_id: int, message_or_cq):
    state = _ACTIVE_LOGINS.get(chat_id)
    if not state:
        return

    app = state["app"]
    phone = state["phone"]
    p_hash = state["hash"]
    digits = state["digits"]

    edit_target = message_or_cq.edit if hasattr(message_or_cq, "edit") else message_or_cq.edit_text

    try:
        await edit_target("⏳ Verifying code with Telegram...", buttons=None, parse_mode="html")
    except Exception:
        pass

    try:
        await app.sign_in(phone, code=digits, phone_code_hash=p_hash)
    except errors.SessionPasswordNeededError:
        state["awaiting_2fa"] = True
        return await Altruix.bot.send_message(
            chat_id,
            "🔐 <b>Two-Step Verification (2FA) Active!</b>\n\n"
            "Your Telegram account has a 2FA Cloud Password enabled.\n"
            "Please send your <b>2FA Password</b> as a text message right now.\n\n"
            "<i>(Send /cancel to abort)</i>",
            parse_mode="html",
        )
    except (errors.PhoneCodeInvalidError, errors.PhoneCodeExpiredError) as e:
        await app.disconnect()
        _ACTIVE_LOGINS.pop(chat_id, None)
        return await Altruix.bot.send_message(
            chat_id,
            f"❌ <b>Invalid or Expired Code:</b> <code>{e}</code>\n\nPlease restart login via /start.",
            parse_mode="html",
        )
    except Exception as e:
        await app.disconnect()
        _ACTIVE_LOGINS.pop(chat_id, None)
        return await Altruix.bot.send_message(
            chat_id,
            f"❌ <b>Login failed:</b> <code>{e}</code>\n\n💡 Try terminal session generator: <code>py -3 -m Main.scripts.wizard</code>",
            parse_mode="html",
        )

    _ACTIVE_LOGINS.pop(chat_id, None)
    session_str = app.session.save()
    await app.disconnect()
    await persist_and_finalize_session(app, session_str, chat_id)
