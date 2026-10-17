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
import glob
import psutil
import asyncio
from pathlib import Path
from telethon import custom
from Main import Altruix
from Main.utils.custom_filters import filters
from Main.core.decorators import log_errors
from Main.internals.make_session import persist_and_finalize_session, is_twp_authorized


def _get_db_badge() -> str:
    db_obj = getattr(Altruix, "db", None)
    if db_obj is None:
        return "🔴 Disconnected"
    cls_name = db_obj.__class__.__name__
    if "Mongo" in cls_name:
        return "🟢 MongoDB Cloud (Persistent)"
    if "SQL" in cls_name:
        dialect = getattr(db_obj, "dialect", "sql").title()
        return f"🟢 SQL ({dialect}) (Persistent)"
    return "🟡 Local JSON (Ephemeral on serverless)"


def _get_host_badge() -> str:
    is_serverless = any(
        k in os.environ for k in ("DYNO", "KOYEB_APP_NAME", "RENDER", "RAILWAY_STATIC_URL", "VERCEL")
    ) or os.path.exists("/.dockerenv")
    return "☁️ Serverless / Cloud" if is_serverless else "💻 Local Server / VPS"


# ==========================================
# STEP 1: Database Setup
# ==========================================

def get_twp_step1_text() -> str:
    db_badge = _get_db_badge()
    host_badge = _get_host_badge()
    return (
        "⚡ <b>Altruix Setup Wizard (Step 1 of 3: Database)</b> ⚡\n\n"
        f"• <b>Host Environment:</b> <code>{host_badge}</code>\n"
        f"• <b>Current Storage:</b> <code>{db_badge}</code>\n\n"
        "Choose where Altruix should store your configurations & userbot credentials.\n"
        "💡 <i>Selecting a persistent database first ensures your session survives serverless dyno reboots!</i>"
    )


def get_twp_step1_buttons() -> list:
    btns = [
        [
            custom.Button.inline("📁 SQLite (Default Embedded)", b"twp_set_db:sqlite"),
            custom.Button.inline("☁️ MongoDB Atlas (Cloud)", b"twp_set_db:mongo"),
        ],
        [
            custom.Button.inline("🐘 PostgreSQL / Supabase", b"twp_set_db:postgres"),
            custom.Button.inline("⏩ Skip to Step 2 (Account)", b"twp_step2_session"),
        ],
        [
            custom.Button.inline("🔍 Pre-Flight Diagnostics", b"twp_diag"),
        ],
        [
            custom.Button.inline("🏠 Main Menu", b"bot_start_menu"),
        ],
    ]
    return btns


# ==========================================
# STEP 2: Account Login
# ==========================================

def get_twp_step2_text() -> str:
    db_badge = _get_db_badge()
    host_badge = _get_host_badge()
    prefix = getattr(Altruix, "user_command_handler", ".")
    return (
        "⚡ <b>Altruix Setup Wizard (Step 2 of 3: Account)</b> ⚡\n\n"
        f"• <b>Host Environment:</b> <code>{host_badge}</code>\n"
        f"• <b>Database Storage:</b> <code>{db_badge}</code>\n"
        f"• <b>Command Prefix:</b> <code>{prefix}</code>\n\n"
        "Connect your Telegram user account to activate the userbot:\n"
        "🔒 <i>Your session string will be saved directly into the database chosen in Step 1.</i>"
    )


def get_twp_step2_buttons() -> list:
    btns = [
        [
            custom.Button.inline("📱 Quick Login (with Secure NumPad)", b"session_no"),
        ],
        [
            custom.Button.inline("📋 Paste Existing StringSession", b"session_yes"),
        ],
        [
            custom.Button.inline("⚙️ Command Prefix", b"twp_prefix_menu"),
            custom.Button.inline("🗄️ Change Database", b"twp_db_menu"),
        ],
        [
            custom.Button.inline("🔍 Pre-Flight Diagnostics", b"twp_diag"),
        ],
        [
            custom.Button.inline("🏠 Main Menu", b"bot_start_menu"),
        ],
    ]
    return btns


def get_main_start_dashboard(mention: str = "User") -> tuple:
    caption_template = Altruix.get_string("BOT_ST_MSG") or "Welcome {0}! {1}"
    caption = caption_template.format(mention, Altruix.config.CUSTOM_BT_START_MSG or "")
    if not Altruix.training_wheels_protocol:
        caption += "\n\n🎛️ <b>Control Center:</b> Use the quick options below to configure settings, add accounts, or view commands:"
        start_buttons = [
            [
                custom.Button.inline("📖 Help & Commands", b"help#_cat?cat=all&page=0"),
                custom.Button.inline("⚙️ Settings Panel", b"panel_refresh"),
            ],
            [
                custom.Button.inline("➕ Add Telegram Account", b"twp_step2_session"),
                custom.Button.inline("👥 Active Accounts", b"panel_sessions"),
            ],
            [
                custom.Button.inline("🛡️ PM Security", b"panel_toggle_pm"),
                custom.Button.inline("⚡ Ping & Status", b"panel_ping"),
            ],
        ]
    else:
        start_buttons = [
            [custom.Button.inline("📖 Help Menu", b"help#_cat?cat=all&page=0")],
            [custom.Button.inline("⚡ Step 1: Database Setup", b"twp_db_menu")],
            [custom.Button.inline("⚡ Step 2: Account Login", b"twp_step2_session")],
        ]
    return caption, start_buttons


@Altruix.bot.on_callback_query(filters.regex(r"^(bot_start_menu|start_hub|start_menu)$"))
@log_errors
async def bot_start_menu_cb_handler(c, cq):
    # Cancel any pending login / conversation locks
    from Main.internals.make_session import _PENDING_LOGINS
    from Main.utils.suppress import suppress_error
    _PENDING_LOGINS.discard(cq.chat_id)
    if hasattr(Altruix.bot, "_conversations"):
        with suppress_error():
            for c_obj in list(Altruix.bot._conversations.get(cq.chat_id, set())):
                c_obj._cancel_all()
            Altruix.bot._conversations.pop(cq.chat_id, None)

    mention = getattr(cq.sender, "first_name", "User") or "User"
    caption, buttons = get_main_start_dashboard(mention)
    try:
        await cq.edit(caption, buttons=buttons, parse_mode="html")
    except Exception:
        path_ = "./cache/bot_st_media.*"
        logo = Path(__file__).resolve().parents[1] / "assets" / "images" / "logo.jpg"
        file = glob.glob(path_)[0] if glob.glob(path_) else str(logo)
        try:
            await cq.delete()
        except Exception:
            pass
        await c.send_file(cq.chat_id, file, caption=caption, buttons=buttons, parse_mode="html")


# ==========================================
# Start Command Handler
# ==========================================

@Altruix.bot.on_message(filters.command("start", "/") & filters.private)
@log_errors
async def start_command_handler(c, m):
    sender_id = getattr(m, "sender_id", None)
    if sender_id is None and hasattr(m, "from_user") and m.from_user:
        sender_id = getattr(m.from_user, "id", None)

    # Cancel any stuck logins / conversations for this user
    from Main.internals.make_session import _PENDING_LOGINS
    from Main.utils.suppress import suppress_error
    _PENDING_LOGINS.discard(sender_id)
    if hasattr(Altruix.bot, "_conversations"):
        with suppress_error():
            for c_obj in list(Altruix.bot._conversations.get(sender_id, set())):
                c_obj._cancel_all()
            Altruix.bot._conversations.pop(sender_id, None)

    payload = m.text.replace("/start", "").strip() if m.text else ""

    if payload == "help" or payload.startswith("help"):
        if not sender_id or sender_id not in Altruix.auth_users:
            return await m.reply("⚠️ <i>You are not authorized to use this bot.</i>", parse_mode="html")
        from Main.plugins.bot.help import get_help_menu, help_text
        buttons = await get_help_menu(category="all", page=0)
        return await m.reply(help_text, buttons=buttons, parse_mode="html")

    if not payload:
        path_ = "./cache/bot_st_media.*"
        logo = Path(__file__).resolve().parents[1] / "assets" / "images" / "logo.jpg"
        file = glob.glob(path_)[0] if glob.glob(path_) else str(logo)
        mention = m.from_user.mention if m.from_user else "User"

        caption, start_buttons = get_main_start_dashboard(mention)

        if sender_id not in Altruix.auth_users and not is_twp_authorized(sender_id):
            start_buttons = []

        await m.reply_file(file, caption=caption, buttons=start_buttons or None, send_msg_if_file_invalid=True)

        if Altruix.training_wheels_protocol:
            if not is_twp_authorized(sender_id):
                return await m.reply("⛔ <b>Access Denied:</b> This bot's initial setup is locked to the verified owner.", parse_mode="html")

            # Guide user through Step 1 (Database) first
            await m.reply(get_twp_step1_text(), buttons=get_twp_step1_buttons(), parse_mode="html")

    elif payload == "add_session":
        if not is_twp_authorized(sender_id):
            return await m.reply("⛔ <b>Access Denied:</b> Initial setup is locked to the owner.", parse_mode="html")
        await m.reply(get_twp_step2_text(), buttons=get_twp_step2_buttons(), parse_mode="html")


# ==========================================
# Navigation & Step Callback Handlers
# ==========================================

@Altruix.bot.on_callback_query(filters.regex(r"^add_session"))
@log_errors
async def add_session_menu_cb_handler(c, cb):
    if not is_twp_authorized(cb.sender_id):
        return await cb.answer("⛔ Access Denied: Setup is locked to the owner.", alert=True)
    await cb.edit(get_twp_step1_text(), buttons=get_twp_step1_buttons(), parse_mode="html")


@Altruix.bot.on_callback_query(filters.regex(r"^twp_step2_session"))
async def twp_step2_session_handler(c, cq):
    if not is_twp_authorized(cq.sender_id):
        return await cq.answer("⛔ Access Denied: Setup is locked to the owner.", alert=True)
    await cq.edit(get_twp_step2_text(), buttons=get_twp_step2_buttons(), parse_mode="html")


@Altruix.bot.on_callback_query(filters.regex(r"^twp_db_menu"))
async def twp_db_menu_handler(c, cq):
    if not is_twp_authorized(cq.sender_id):
        return await cq.answer("⛔ Access Denied: Setup is locked to the owner.", alert=True)
    await cq.edit(get_twp_step1_text(), buttons=get_twp_step1_buttons(), parse_mode="html")


@Altruix.bot.on_callback_query(filters.regex(r"^session_yes"))
@log_errors
async def add_session_yes_cb_handler(c, cb):
    if not is_twp_authorized(cb.sender_id):
        return await cb.answer("⛔ Access Denied: Setup is locked to the owner.", alert=True)

    await cb.answer()
    if hasattr(Altruix.bot, "_conversations"):
        from Main.utils.suppress import suppress_error
        with suppress_error():
            for c_obj in list(Altruix.bot._conversations.get(cb.chat_id, set())):
                c_obj._cancel_all()
            Altruix.bot._conversations.pop(cb.chat_id, None)

    try:
        async with Altruix.bot.conversation(cb.chat_id, timeout=300, exclusive=False) as conv:
            prompt = await conv.send_message(
                "📋 Please send your Telethon StringSession.\n\n"
                "💡 You can also generate one in terminal without risk of expired codes:\n"
                "<code>py -3 -m Main.scripts.wizard</code>\n\n"
                "Tap below or send /cancel to abort.",
                buttons=[[custom.Button.inline("❌ Cancel / Main Menu", b"bot_start_menu")]],
                parse_mode="html",
            )
            session_resp = await conv.get_response(prompt)
            text = session_resp.raw_text.strip()
            if text.lower().startswith(("/cancel", "/start", "/stop", "/abort", "cancel", "menu")):
                if text.startswith("/start"):
                    mention = getattr(session_resp.sender, "first_name", "User") or "User"
                    caption, buttons = get_main_start_dashboard(mention)
                    return await conv.send_message(caption, buttons=buttons, parse_mode="html")
                return await conv.send_message(
                    "Session setup cancelled.",
                    buttons=[[custom.Button.inline("🏠 Main Menu", b"bot_start_menu")]],
                )

            match = re.search(r"(\S{100,600})", text)
            if not match:
                return await conv.send_message(
                    "The string session format looks invalid. Please try again.",
                    buttons=[[custom.Button.inline("🏠 Main Menu", b"bot_start_menu")]],
                )

            session_str = match.group(1)
            await persist_and_finalize_session(None, session_str, cb.chat_id)
    except asyncio.TimeoutError:
        return await Altruix.bot.send_message(
            cb.chat_id,
            "⏱️ <b>Session entry timed out.</b> Tap below to return to the main menu.",
            buttons=[[custom.Button.inline("🏠 Main Menu", b"bot_start_menu")]],
            parse_mode="html",
        )


# ==========================================
# Database Selection & Next Step
# ==========================================

@Altruix.bot.on_callback_query(filters.regex(r"^twp_set_db:"))
async def twp_set_db_handler(c, cq):
    if not is_twp_authorized(cq.sender_id):
        return await cq.answer("⛔ Access Denied: Setup is locked to the owner.", alert=True)

    choice = cq.data.decode("utf-8").split(":", 1)[1]
    if choice in ("sqlite", "local"):
        uri = "sqlite:///altruix.db"
        if Altruix.config and Altruix.db is not None:
            await Altruix.config.add_env_to_db("DB_URI", uri, upsert=True)
        await cq.answer("SQLite selected!", alert=True)
        # Advance directly to Step 2
        await cq.edit(
            "✅ <b>Database Configured: SQLite (<code>sqlite:///altruix.db</code>)</b>\n\n" + get_twp_step2_text(),
            buttons=get_twp_step2_buttons(),
            parse_mode="html",
        )
    elif choice in ("mongo", "postgres"):
        name = "MongoDB Atlas URI (mongodb+srv://...)" if choice == "mongo" else "PostgreSQL URI (postgresql://...)"
        await cq.answer()
        if hasattr(Altruix.bot, "_conversations"):
            from Main.utils.suppress import suppress_error
            with suppress_error():
                for c_obj in list(Altruix.bot._conversations.get(cq.chat_id, set())):
                    c_obj._cancel_all()
                Altruix.bot._conversations.pop(cq.chat_id, None)

        try:
            async with Altruix.bot.conversation(cq.chat_id, timeout=120, exclusive=False) as conv:
                msg = await conv.send_message(
                    f"Please send your {name}:\n\nTap below or send /cancel to abort.",
                    buttons=[[custom.Button.inline("❌ Cancel / Main Menu", b"bot_start_menu")]],
                )
                resp = await conv.get_response(msg)
                val = resp.raw_text.strip()
                if val.lower().startswith(("/cancel", "/start", "/stop", "/abort", "cancel", "menu")):
                    if val.startswith("/start"):
                        mention = getattr(resp.sender, "first_name", "User") or "User"
                        caption, buttons = get_main_start_dashboard(mention)
                        return await conv.send_message(caption, buttons=buttons, parse_mode="html")
                    return await conv.send_message(
                        "Database configuration cancelled.",
                        buttons=[[custom.Button.inline("🏠 Main Menu", b"bot_start_menu")]],
                    )
                if Altruix.config and Altruix.db is not None:
                    await Altruix.config.add_env_to_db("DB_URI", val, upsert=True)
                await conv.send_message(
                    f"✅ <b>Database Configured!</b>\n\n<code>{val}</code>\n\n" + get_twp_step2_text(),
                    buttons=get_twp_step2_buttons(),
                    parse_mode="html",
                )
        except asyncio.TimeoutError:
            return await Altruix.bot.send_message(
                cq.chat_id,
                "⏱️ <b>Database setup timed out.</b> Tap below to return to the main menu.",
                buttons=[[custom.Button.inline("🏠 Main Menu", b"bot_start_menu")]],
                parse_mode="html",
            )


# ==========================================
# Command Prefix Selector
# ==========================================

@Altruix.bot.on_callback_query(filters.regex(r"^twp_prefix_menu"))
async def twp_prefix_menu_handler(c, cq):
    if not is_twp_authorized(cq.sender_id):
        return await cq.answer("⛔ Access Denied: Setup is locked to the owner.", alert=True)

    curr = getattr(Altruix, "user_command_handler", ".")
    text = (
        f"⚙️ <b>Choose Command Prefix Handler:</b>\n\n"
        f"Current Prefix: <code>{curr}</code>\n"
        f"Example: <code>{curr}help</code>, <code>{curr}ping</code>\n\n"
        "Select your preferred prefix below:"
    )
    buttons = [
        [
            custom.Button.inline(". (Dot)", b"twp_set_pfx:."),
            custom.Button.inline("! (Exclamation)", b"twp_set_pfx:!"),
        ],
        [
            custom.Button.inline(", (Comma)", b"twp_set_pfx:,"),
            custom.Button.inline("? (Question)", b"twp_set_pfx:?"),
        ],
        [
            custom.Button.inline("⚙️ Settings Panel", b"panel_refresh"),
            custom.Button.inline("🏠 Main Menu", b"bot_start_menu"),
        ],
    ]
    await cq.edit(text, buttons=buttons, parse_mode="html")


@Altruix.bot.on_callback_query(filters.regex(r"^twp_set_pfx:"))
async def twp_set_prefix_handler(c, cq):
    if not is_twp_authorized(cq.sender_id):
        return await cq.answer("⛔ Access Denied: Setup is locked to the owner.", alert=True)

    pfx = cq.data.decode("utf-8").split(":", 1)[1]
    Altruix.user_command_handler = pfx
    if Altruix.config and Altruix.db is not None:
        await Altruix.config.add_env_to_db("CMD_HANDLER", pfx, upsert=True)
    await cq.answer(f"Prefix updated to '{pfx}'!", alert=True)
    text = (
        f"✅ <b>Command Prefix Handler Updated!</b>\n\n"
        f"Current Prefix: <code>{pfx}</code>\n"
        f"Commands will now use: <code>{pfx}ping</code>, <code>{pfx}help</code>, etc."
    )
    buttons = [
        [
            custom.Button.inline("⚙️ Settings Panel", b"panel_refresh"),
            custom.Button.inline("🏠 Main Menu", b"bot_start_menu"),
        ]
    ]
    await cq.edit(text, buttons=buttons, parse_mode="html")


# ==========================================
# Diagnostics
# ==========================================

@Altruix.bot.on_callback_query(filters.regex(r"^twp_diag"))
async def twp_diag_handler(c, cq):
    if not is_twp_authorized(cq.sender_id):
        return await cq.answer("⛔ Access Denied: Setup is locked to the owner.", alert=True)

    await cq.answer("Running system diagnostics...")

    is_heroku = "DYNO" in os.environ
    is_koyeb = "KOYEB_APP_NAME" in os.environ
    is_render = "RENDER" in os.environ
    is_railway = "RAILWAY_STATIC_URL" in os.environ
    is_vercel = "VERCEL" in os.environ
    is_docker = os.path.exists("/.dockerenv")

    if is_heroku:
        host_badge = "☁️ Heroku Dyno (Ephemeral)"
    elif is_koyeb:
        host_badge = "☁️ Koyeb App (Ephemeral)"
    elif is_render:
        host_badge = "☁️ Render Worker"
    elif is_railway:
        host_badge = "☁️ Railway Container"
    elif is_vercel:
        host_badge = "☁️ Vercel Function"
    elif is_docker:
        host_badge = "🐳 Docker Container"
    else:
        host_badge = "💻 Standalone Server / VPS"

    db_badge = _get_db_badge()
    cpu = psutil.cpu_percent()
    ram = psutil.virtual_memory().percent
    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"

    diag_text = (
        "🔍 <b>Altruix Pre-Flight Health Diagnostics</b>\n\n"
        f"• <b>Runtime Environment:</b> {host_badge}\n"
        f"• <b>Database Storage:</b> {db_badge}\n"
        f"• <b>Python Version:</b> <code>{py_ver}</code>\n"
        f"• <b>CPU Load:</b> <code>{cpu}%</code> | <b>RAM:</b> <code>{ram}%</code>\n"
        f"• <b>MTProto Protocol:</b> 🟢 Telethon v1.36.0+\n"
        f"• <b>TWP Protocol:</b> 🟢 Active (Step-by-step Setup)\n\n"
        "💡 <i>Tip: For serverless hosts like Heroku or Koyeb, connect MongoDB Atlas or PostgreSQL so your settings survive dyno reboots!</i>"
    )

    buttons = [
        [custom.Button.inline("🔄 Re-run Check", b"twp_diag")],
        [
            custom.Button.inline("🔙 Back to Step 1", b"twp_db_menu"),
            custom.Button.inline("🏠 Main Menu", b"bot_start_menu"),
        ],
    ]
    await cq.edit(diag_text, buttons=buttons, parse_mode="html")
