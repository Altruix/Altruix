# Copyright (C) 2021-present by Altruix@Github, < https://github.com/Altruix >.
#
# This file is part of < https://github.com/Altruix/Altruix > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/Altriux/Altruix/blob/main/LICENSE >
#
# All rights reserved.

"""
selftest.py — Single-Account Testing Suite & Diagnostic Tools
Allows testing chat filters, blacklists, and AFK triggers using a single Telegram account
without needing a second account.
"""

import time
from Main import Altruix
from Main.core.types import AltruixTelegramClient as Client, Message
from Main.utils.essentials import Essentials


@Altruix.register_on_cmd(
    ["selftest", "testmode"],
    cmd_help={
        "help": "Toggle single-account self-test mode to test filters, blacklist, and AFK without a 2nd account.",
        "example": "selftest on",
        "user_args": [
            {"arg": "on", "help": "Enable self-test mode (allows own messages to trigger filters/blacklist).", "requires_input": False},
            {"arg": "off", "help": "Disable self-test mode (returns to standard production mode).", "requires_input": False},
            {"arg": "status", "help": "Show current self-test mode state.", "requires_input": False},
        ],
    },
)
async def toggle_selftest_cmd(c: Client, m: Message):
    arg = (m.user_input or "").lower().strip()
    if not arg and m.user_args:
        if "on" in m.user_args:
            arg = "on"
        elif "off" in m.user_args:
            arg = "off"
        elif "status" in m.user_args:
            arg = "status"

    if arg == "on":
        Altruix.self_test_mode = True
        return await m.handle_message(
            "<b>🧪 Self-Test Mode: <code>ENABLED</code></b>\n\n"
            "You can now test userbot triggers with your <b>own single account</b>:\n"
            "• <b>Filters:</b> Type any saved filter keyword to see the auto-reply.\n"
            "• <b>Blacklist:</b> Type any blacklisted word to see it auto-deleted.\n"
            "• <b>AFK:</b> Mention yourself while AFK to see your AFK response.\n\n"
            f"<i>Type <code>{Altruix.user_command_handler}selftest off</code> when finished.</i>"
        )
    elif arg == "off":
        Altruix.self_test_mode = False
        return await m.handle_message(
            "<b>🧪 Self-Test Mode: <code>DISABLED</code></b>\n\n"
            "Userbot has returned to standard operating mode.\n"
            "Your own messages will no longer trigger filters or blacklist."
        )
    else:
        current = "ENABLED" if getattr(Altruix, "self_test_mode", False) else "DISABLED"
        return await m.handle_message(
            f"<b>🧪 Self-Test Mode Status:</b> <code>{current}</code>\n\n"
            f"• Use <code>{Altruix.user_command_handler}selftest on</code> to enable.\n"
            f"• Use <code>{Altruix.user_command_handler}selftest off</code> to disable."
        )


@Altruix.register_on_cmd(
    ["test", "diagnose"],
    cmd_help={
        "help": "Run diagnostic health checks on your userbot and simulate triggers.",
        "example": "test filter <keyword>",
        "user_args": [
            {"arg": "filter", "help": "Simulate and test a filter keyword in the current chat.", "requires_input": True},
            {"arg": "bl", "help": "Check if a word is blacklisted in the current chat.", "requires_input": True},
            {"arg": "afk", "help": "Preview your active AFK auto-response without waiting for a mention.", "requires_input": False},
            {"arg": "db", "help": "Run read/write latency benchmarks on local database.", "requires_input": False},
        ],
    },
)
async def test_diagnose_cmd(c: Client, m: Message):
    sub = (m.user_input or "").strip()
    chat_id = m.chat_id or (getattr(m.chat, "id", None))
    my_id = getattr(c.myself, "id", 0)

    # 1. Test Filter simulation
    if sub.startswith("filter"):
        keyword = sub.replace("filter", "", 1).strip().lower()
        if not keyword:
            return await m.handle_message(f"Usage: <code>{Altruix.user_command_handler}test filter &lt;keyword&gt;</code>")
        if Altruix.db is None:
            return await m.handle_message("Database is not initialized.")
        filters_db = Altruix.db.make_collection("FILTERS")
        doc = await filters_db.find_one({"keyword": keyword, "chat_id": chat_id, "client_id": my_id})
        if doc:
            reply_val = doc.get("reply", "No reply set")
            return await m.handle_message(
                f"<b>✅ Filter Match Found:</b>\n"
                f"• <b>Keyword:</b> <code>{keyword}</code>\n"
                f"• <b>Chat ID:</b> <code>{chat_id}</code>\n"
                f"• <b>Auto-Reply:</b> <code>{reply_val}</code>"
            )
        return await m.handle_message(
            f"<b>❌ No Filter Match:</b>\nKeyword <code>{keyword}</code> is not saved in this chat.\n"
            f"Save one with: <code>{Altruix.user_command_handler}filter {keyword} &lt;reply text&gt;</code>"
        )

    # 2. Test Blacklist check
    if sub.startswith("bl") or sub.startswith("blacklist"):
        parts = sub.split(None, 1)
        word = parts[1].strip().lower() if len(parts) > 1 else ""
        if not word:
            return await m.handle_message(f"Usage: <code>{Altruix.user_command_handler}test bl &lt;word&gt;</code>")
        if Altruix.db is None:
            return await m.handle_message("Database is not initialized.")
        bl_db = Altruix.db.make_collection("BLACKLIST")
        record = await bl_db.find_one({"chat_id": chat_id, "client_id": my_id})
        if record and "words" in record and word in record["words"]:
            action = record.get("action", "delete")
            return await m.handle_message(
                f"<b>⚠️ Word is Blacklisted:</b>\n"
                f"• <b>Word:</b> <code>{word}</code>\n"
                f"• <b>Action:</b> <code>{action}</code>\n"
                f"• <b>Chat:</b> <code>{chat_id}</code>"
            )
        return await m.handle_message(f"<b>✅ Word is Allowed:</b> <code>{word}</code> is not blacklisted.")

    # 3. Test AFK status
    if sub == "afk" or (m.user_args and "afk" in m.user_args):
        if Altruix.db is None:
            return await m.handle_message("Database not available.")
        rec = await Altruix.db.settings_col.find_one({"_id": "AFK", "client_id": my_id})
        if rec:
            afk_time = rec.get("afk_time", int(time.time()))
            dur = Essentials.get_readable_time(time.time() - afk_time)
            reason = rec.get("reason", "No reason")
            return await m.handle_message(
                f"<b>💤 AFK Status: ACTIVE</b>\n"
                f"• <b>Duration:</b> {dur}\n"
                f"• <b>Reason:</b> {reason}\n"
                f"• <b>Auto-reply preview:</b> <i>I am currently AFK ({dur}): {reason}</i>"
            )
        return await m.handle_message("<b>AFK Status: INACTIVE</b> (You are currently active).")

    # 4. General System Diagnostics
    start_t = time.perf_counter()
    await c.get_me()
    api_lat = round((time.perf_counter() - start_t) * 1000, 1)

    db_start = time.perf_counter()
    if Altruix.db:
        await Altruix.db.settings_col.find_one({"_id": "HEALTH_CHECK"})
    db_lat = round((time.perf_counter() - db_start) * 1000, 1)

    uptime = Essentials.get_readable_time(time.time() - Altruix.start_time)
    test_mode = "ENABLED" if getattr(Altruix, "self_test_mode", False) else "DISABLED"
    plugins_count = len(Altruix._command_help_message_data)
    user_name = getattr(c.myself, "first_name", "User")

    report = (
        f"<b>🛠 Altruix System Diagnostics:</b>\n\n"
        f"• <b>User Account:</b> {user_name} (<code>{my_id}</code>)\n"
        f"• <b>Telegram MTProto Latency:</b> <code>{api_lat} ms</code>\n"
        f"• <b>Database Latency:</b> <code>{db_lat} ms</code>\n"
        f"• <b>System Uptime:</b> <code>{uptime}</code>\n"
        f"• <b>Loaded Plugins:</b> <code>{plugins_count}</code>\n"
        f"• <b>Self-Test Mode:</b> <code>{test_mode}</code>\n\n"
        f"💡 <i>Tip: Run <code>{Altruix.user_command_handler}selftest on</code> to test triggers with your own account!</i>"
    )
    await m.handle_message(report)
