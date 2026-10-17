# Copyright (C) 2021-present by Altruix@Github, < https://github.com/Altruix >.
#
# This file is part of < https://github.com/Altruix/Altruix > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/Altriux/Altruix/blob/main/LICENSE >
#
# All rights reserved.

import contextlib
import html
from telethon import functions
from Main import Altruix
from Main.utils.suppress import suppress_error
from Main.core.types.client import AltruixTelegramClient as Client
from Main.core.types.message import Message
from Main.utils.custom_filters import filters


pm_permit_warning_cache = {}
__last_message_cache = {}


@Altruix.register_on_cmd(
    "approve",
    bot_mode_unsupported=True,
    cmd_help={
        "help": "Approves the targeted user or mass approves all pending users with -a.",
        "example": "approve @username or approve -a",
        "user_args": [
            {"arg": "a", "help": "Mass approves all pending users currently warned.", "requires_input": False},
        ],
    },
)
async def approve_user_pm_permit_func(c: Client, m: Message):
    if "-a" in m.user_args or m.user_input.strip() == "-a":
        return await mass_approve_func(c, m)

    msg = await m.handle_message("PROCESSING")
    user_ = m.chat_id or getattr(m.chat, "id", None)
    if not await Altruix.config.get_pm_sts():
        return await m.edit("<code>PM permit is disabled</code>", parse_mode="html")

    if not (getattr(m, "is_private", False) or getattr(m.chat, "type", "") == "private"):
        user_, _, is_channel = m.get_user
        if is_channel or not user_:
            return await msg.edit_msg("INVALID_USER")

    try:
        user_obj = await c.get_users(user_)
    except Exception:
        user_obj = None

    if not user_obj:
        return await msg.edit_msg("INVALID_USER")

    user_id = user_obj.id
    if Altruix.db is not None:
        pm_permit_col = Altruix.db.make_collection("pm_permit")
        user_info = await pm_permit_col.find_one({"user_id": user_id})
        if not user_info:
            await pm_permit_col.insert_one({"user_id": user_id, "approved": True})
        else:
            if user_info.get("approved", False):
                return await msg.edit_msg("ALREADY_APPROVED")
            await pm_permit_col.update_one({"user_id": user_id}, {"$set": {"approved": True}})

    if user_id in pm_permit_warning_cache:
        del pm_permit_warning_cache[user_id]

    mention = getattr(user_obj, "mention", str(user_id))
    await msg.edit_msg("APPROVED", string_args=(mention,))


@Altruix.register_on_cmd(
    ["massapprove", "approveall"],
    bot_mode_unsupported=True,
    cmd_help={
        "help": "Mass approves all users who are currently waiting in PM permit warning queue.",
        "example": "massapprove",
    },
)
async def mass_approve_func(c: Client, m: Message):
    msg = await m.handle_message("Processing mass approval...")
    if not await Altruix.config.get_pm_sts():
        return await msg.edit("<code>PM permit is disabled</code>", parse_mode="html")

    pending_ids = list(pm_permit_warning_cache.keys())
    if not pending_ids:
        return await msg.edit("ℹ️ <i>No pending users in PM permit warning queue.</i>", parse_mode="html")

    if Altruix.db is not None:
        pm_permit_col = Altruix.db.make_collection("pm_permit")
        for uid in pending_ids:
            await pm_permit_col.update_one({"user_id": uid}, {"$set": {"approved": True}}, upsert=True)

    count = len(pending_ids)
    pm_permit_warning_cache.clear()
    await msg.edit(f"✅ <b>Mass Approval Complete:</b> Approved <code>{count}</code> pending user(s).", parse_mode="html")


@Altruix.register_on_cmd(
    "disapprove",
    bot_mode_unsupported=True,
    cmd_help={
        "help": "Disapproves the targeted user!",
        "example": "disapprove @username",
    },
)
async def disapprove_user_pm_permit_func(c: Client, m: Message):
    msg = await m.handle_message("PROCESSING")
    user_ = m.chat_id or getattr(m.chat, "id", None)
    if not await Altruix.config.get_pm_sts():
        if Altruix.log_chat:
            await c.send_message(
                Altruix.log_chat,
                "**#DISAPPROVE**\n\nStatus: `Can't Disapprove!`\n\n**Reason:** `PM Security is Disabled!`",
            )
        return

    if not (getattr(m, "is_private", False) or getattr(m.chat, "type", "") == "private"):
        user_, _, is_channel = m.get_user
        if is_channel or not user_:
            return await msg.edit_msg("INVALID_USER")

    try:
        user_obj = await c.get_users(user_)
    except Exception:
        user_obj = None

    if not user_obj:
        return await msg.edit_msg("INVALID_USER")

    user_id = user_obj.id
    if Altruix.db is not None:
        pm_permit_col = Altruix.db.make_collection("pm_permit")
        await pm_permit_col.update_one({"user_id": user_id}, {"$set": {"approved": False}}, upsert=True)

    mention = getattr(user_obj, "mention", str(user_id))
    await msg.edit_msg("DIS_APPROVED", string_args=(mention,))


@Altruix.register_on_cmd(
    ["setpmlimit", "pmlimit", "pmwarnlimit"],
    bot_mode_unsupported=True,
    requires_input=True,
    cmd_help={
        "help": "Set the spam warning threshold before a sender is automatically blocked.",
        "example": "setpmlimit 5",
    },
)
async def set_pm_limit_func(c: Client, m: Message):
    raw_input = m.user_input.strip()
    if not raw_input.isdigit():
        return await m.handle_message("⚠️ Please provide a valid positive integer limit (e.g. <code>.setpmlimit 5</code>).")

    limit = int(raw_input)
    if limit < 1 or limit > 20:
        return await m.handle_message("⚠️ Warning limit must be between 1 and 20.")

    await Altruix.config.sync_env_to_db("PM_PERMIT_LIMIT", limit)
    await m.handle_message(f"🔢 <b>PM Security Warning Limit:</b> Set to <code>{limit}</code> warnings before auto-block.")


@Altruix.register_on_cmd(
    ["setpmmsg", "pmmsg", "custompmmsg"],
    bot_mode_unsupported=True,
    cmd_help={
        "help": "Set or view a custom warning message for PM permit.",
        "example": "setpmmsg Hello! Please drop your reason in one message.",
    },
)
async def set_pm_msg_func(c: Client, m: Message):
    new_msg = m.user_input.strip()
    if not new_msg:
        current = await Altruix.config.get_pm_custom_msg()
        if current:
            return await m.handle_message(
                f"💬 <b>Current Custom PM Message:</b>\n\n<blockquote>{html.escape(current)}</blockquote>\n\n"
                f"<i>Use</i> <code>{Altruix.user_command_handler}resetpmmsg</code> <i>to restore the default template.</i>"
            )
        else:
            return await m.handle_message(
                "💬 <b>PM Warning Message:</b> Default template is currently active.\n"
                f"<i>Provide text to set a custom one:</i> <code>{Altruix.user_command_handler}setpmmsg &lt;text&gt;</code>"
            )

    await Altruix.config.sync_env_to_db("PM_PERMIT_CUSTOM_MSG", new_msg)
    await m.handle_message(
        f"✅ <b>Custom PM Warning Message Saved:</b>\n\n<blockquote>{html.escape(new_msg)}</blockquote>"
    )


@Altruix.register_on_cmd(
    ["resetpmmsg", "delpmmsg"],
    bot_mode_unsupported=True,
    cmd_help={
        "help": "Reset PM warning message back to the default template.",
        "example": "resetpmmsg",
    },
)
async def reset_pm_msg_func(c: Client, m: Message):
    await Altruix.config.del_env_from_db("PM_PERMIT_CUSTOM_MSG")
    await m.handle_message("🔄 <b>Custom PM Warning Message Reset:</b> Restored default template.")


@Altruix.register_on_cmd(
    ["pmcontacts", "pmcontact"],
    bot_mode_unsupported=True,
    cmd_help={
        "help": "Configure whether mutual/saved contacts automatically bypass PM Permit.",
        "example": "pmcontacts on or pmcontacts off",
    },
)
async def pm_contacts_rule_func(c: Client, m: Message):
    arg = m.user_input.strip().lower()
    if arg in {"on", "yes", "true", "enable", "1"}:
        new_val = True
    elif arg in {"off", "no", "false", "disable", "0"}:
        new_val = False
    else:
        current = await Altruix.config.get_pm_allow_contacts()
        new_val = not current

    await Altruix.config.sync_env_to_db("PM_PERMIT_ALLOW_CONTACTS", new_val)
    status_text = "ENABLED (Saved contacts bypass PM Permit)" if new_val else "DISABLED (All contacts screened)"
    await m.handle_message(f"📇 <b>Contact Auto-Allow Policy:</b> <code>{status_text}</code>")


@Altruix.register_on_cmd(
    ["resetpmwarns", "clearpmwarns"],
    bot_mode_unsupported=True,
    cmd_help={
        "help": "Clears the active in-memory PM warning counts.",
        "example": "resetpmwarns",
    },
)
async def reset_pm_warns_func(c: Client, m: Message):
    count = len(pm_permit_warning_cache)
    pm_permit_warning_cache.clear()
    await m.handle_message(f"🧹 <b>PM Warning Cache Cleared:</b> Reset warning counters for <code>{count}</code> user(s).")


@Altruix.register_on_cmd(
    "pmpermit",
    bot_mode_unsupported=True,
    cmd_help={
        "help": "Displays the interactive PM Security panel or changes PM permit rules.",
        "example": "pmpermit or pmpermit -y or pmpermit -n",
        "user_args": [
            {"arg": "y", "help": "Enables Pm Permit.", "requires_input": False},
            {"arg": "n", "help": "Disables Pm Permit.", "requires_input": False},
            {"arg": "basic", "help": "View text summary without bot inline widget.", "requires_input": False},
        ],
    },
)
async def pm_permit_command_handler(c: Client, m: Message):
    user_args = m.user_args
    if "n" in user_args:
        await Altruix.config.sync_env_to_db("PM_PERMIT", False)
        if Altruix.log_chat:
            await c.send_message(Altruix.log_chat, "**#Pm Permit**\n\nStatus: `Disabled`")
        return await m.handle_message("🛡️ <b>PM Security Status:</b> <code>Disabled</code>")
    elif "y" in user_args:
        await Altruix.config.sync_env_to_db("PM_PERMIT", True)
        if Altruix.log_chat:
            await c.send_message(Altruix.log_chat, "**#Pm Permit**\n\nStatus: `Enabled`")
        return await m.handle_message("🛡️ <b>PM Security Status:</b> <code>Enabled</code>")

    is_bot = (
        (getattr(c, "myself", None) and getattr(c.myself, "bot", False))
        or (getattr(Altruix, "bot_info", None) and getattr(c, "myself", None) and c.myself.id == Altruix.bot_info.id)
    )
    if is_bot:
        from Main.plugins.bot.pm_security_inline import _render_pmpermit_panel
        text, buttons = await _render_pmpermit_panel()
        return await m.reply(text, buttons=buttons, parse_mode="html")

    if "-basic" not in user_args and "-text" not in user_args:
        try:
            from Main.utils.inline_helper import send_inline_widget
            if await send_inline_widget(c, m, "pmpermit"):
                return
        except Exception:
            pass

    status_enabled = await Altruix.config.get_pm_sts()
    limit = await Altruix.config.get_pm_warn_limit()
    allow_contacts = await Altruix.config.get_pm_allow_contacts()
    custom_msg = await Altruix.config.get_pm_custom_msg()
    pending = len(pm_permit_warning_cache)

    text = (
        "🛡️ <b>Altruix PM Security Summary</b>\n\n"
        f"• <b>Status:</b> <code>{'🟢 Enabled' if status_enabled else '🔴 Disabled'}</code>\n"
        f"• <b>Warning Limit:</b> <code>{limit} Warnings</code> (Auto-block on #{limit + 1})\n"
        f"• <b>Allow Contacts:</b> <code>{'✅ Yes (Bypass)' if allow_contacts else '❌ No (Screened)'}</code>\n"
        f"• <b>Custom Message:</b> <code>{'Configured' if custom_msg else 'Default Template'}</code>\n"
        f"• <b>Pending In Queue:</b> <code>{pending} user(s)</code>\n\n"
        f"<i>Tip: Use</i> <code>{Altruix.user_command_handler}setpmlimit &lt;int&gt;</code>, "
        f"<code>{Altruix.user_command_handler}setpmmsg &lt;text&gt;</code>, "
        f"<code>{Altruix.user_command_handler}pmcontacts &lt;on|off&gt;</code>, "
        f"<i>or</i> <code>{Altruix.user_command_handler}massapprove</code>."
    )
    await m.handle_message(text)


@Altruix.on_message(
    filters.private & filters.outgoing,
    group=4,
    bot_mode_unsupported=True,
)
async def pm_permit_outgoing_listener(c: Client, m: Message):
    """If I message someone in private chat, automatically approve them in PM permit!"""
    if not await Altruix.config.get_pm_sts():
        return
    chat_id = m.chat_id or getattr(m.chat, "id", None)
    if not chat_id or chat_id in {777000, 42777}:
        return
    if Altruix.db is not None:
        pm_permit_col = Altruix.db.make_collection("pm_permit")
        await pm_permit_col.update_one({"user_id": chat_id}, {"$set": {"approved": True}}, upsert=True)
    if chat_id in pm_permit_warning_cache:
        del pm_permit_warning_cache[chat_id]


@Altruix.on_message(
    filters.private & ~filters.group & ~filters.channel & ~filters.outgoing,
    group=3,
    bot_mode_unsupported=True,
)
async def pm_permit_new_message_listener_handler(c: Client, m: Message):
    if not await Altruix.config.get_pm_sts():
        return

    # Exclude outgoing messages
    if getattr(m, "out", False):
        return

    # Exclude self accounts & owner
    self_ids = set()
    if hasattr(c, "myself") and c.myself:
        self_ids.add(c.myself.id)
    for cl in getattr(Altruix, "clients", []):
        if hasattr(cl, "myself") and cl.myself:
            self_ids.add(cl.myself.id)
    if Altruix.config.OWNER_ID:
        self_ids.add(Altruix.config.OWNER_ID)

    sender_id = m.sender_id or (getattr(m.from_user, "id", None) if hasattr(m, "from_user") else None)
    if not sender_id or sender_id in self_ids:
        return

    # Exclude Telegram official service notifications
    if sender_id in {777000, 42777}:
        return

    # Exclude Sudo users
    sudo_users = await Altruix.config.get_sudo()
    if sender_id in sudo_users:
        return

    # Fetch real sender entity to check bot / contact / verified status
    sender_obj = None
    try:
        if hasattr(m, "get_sender"):
            sender_obj = await m.get_sender()
    except Exception:
        pass

    if not sender_obj:
        try:
            sender_obj = await c.get_entity(sender_id)
        except Exception:
            pass

    if sender_obj:
        # Exclude bots completely!
        if getattr(sender_obj, "bot", False) or getattr(sender_obj, "is_bot", False):
            return
        # Exclude verified official accounts
        if getattr(sender_obj, "verified", False):
            return
        # Rule: Contact / Mutual Contact auto-allow
        if await Altruix.config.get_pm_allow_contacts():
            if getattr(sender_obj, "contact", False) or getattr(sender_obj, "mutual_contact", False):
                return

    # Check Database for approval status
    if Altruix.db is not None:
        pm_permit_col = Altruix.db.make_collection("pm_permit")
        user_info = await pm_permit_col.find_one({"user_id": sender_id})
        if user_info and user_info.get("approved", False):
            return

    # Rule: "If I DM someone first / previous outgoing message in history"
    try:
        history = await c.get_messages(sender_id, limit=7)
        if any(getattr(msg, "out", False) for msg in history):
            # We already spoke or initiated conversation -> auto-approve in DB!
            if Altruix.db is not None:
                await pm_permit_col.update_one({"user_id": sender_id}, {"$set": {"approved": True}}, upsert=True)
            return
    except Exception:
        pass

    # Dynamic spam warning limit
    pm_warns_count = await Altruix.config.get_pm_warn_limit()
    current_warns = pm_permit_warning_cache.get(sender_id, 0)

    if current_warns >= pm_warns_count:
        # Limit reached -> block user
        with suppress_error(msg="Blocking user on max PM warns"):
            if sender_id in pm_permit_warning_cache:
                del pm_permit_warning_cache[sender_id]
            input_peer = await c.get_input_entity(sender_id)
            await c(functions.contacts.BlockRequest(id=input_peer))
        await m.reply_msg("PM_PERMIT_ALREADY_WARNED")
        return

    # Advance warning count
    new_warn_count = current_warns + 1
    pm_permit_warning_cache[sender_id] = new_warn_count

    # Log to log_chat when a new user arrives in PM
    if current_warns == 0 and Altruix.log_chat:
        with suppress_error(msg="Logging new PM user to log chat"):
            sender_name = "Unknown User"
            sender_username = ""
            if sender_obj:
                fn = getattr(sender_obj, "first_name", "") or ""
                ln = getattr(sender_obj, "last_name", "") or ""
                sender_name = f"{fn} {ln}".strip() or "Unknown User"
                if getattr(sender_obj, "username", None):
                    sender_username = f"@{sender_obj.username}"

            raw_txt = (getattr(m, "text", None) or getattr(m, "raw_text", None) or "[Media / Attachment]")
            snippet = raw_txt[:300] + ("..." if len(raw_txt) > 300 else "")

            log_text = (
                "📬 <b>#NEW_PM_CONTACT</b>\n\n"
                f"• <b>User:</b> <a href=\"tg://user?id={sender_id}\">{html.escape(sender_name)}</a>\n"
                f"• <b>User ID:</b> <code>{sender_id}</code>\n"
                + (f"• <b>Username:</b> {sender_username}\n" if sender_username else "")
                + f"• <b>Message:</b>\n<blockquote>{html.escape(snippet)}</blockquote>\n\n"
                f"🛡️ <i>PM Security: Warning 1/{pm_warns_count} issued</i>"
            )

            sent = False
            if hasattr(Altruix, "_raw_bot") and Altruix._raw_bot is not None:
                try:
                    await Altruix._raw_bot.send_message(Altruix.log_chat, log_text, parse_mode="html")
                    sent = True
                except Exception:
                    pass
            if not sent:
                try:
                    await c.send_message(Altruix.log_chat, log_text, parse_mode="html")
                except Exception:
                    pass

    out = None
    try:
        from Main.utils.inline_helper import is_inline_available
        if is_inline_available() and getattr(Altruix, "bot_info", None):
            bot_username = getattr(Altruix.bot_info, "username", None)
            if bot_username:
                # Pass user_id, current warn number, and total limit!
                results = await c.get_inline_bot_results(
                    bot_username, f"pm_warn:{sender_id}:{new_warn_count}:{pm_warns_count}"
                )
                if results and len(results) > 0:
                    chat_target = m.chat_id or getattr(m.chat, "id", None)
                    out = await results[0].click(chat_target, reply_to=m.id)
    except Exception:
        out = None

    if not out:
        custom_msg = await Altruix.config.get_pm_custom_msg()
        warn_badge = f"⚠️ <b>Warning: {new_warn_count} / {pm_warns_count}</b>"
        if custom_msg:
            text = (
                f"🤖 <b>Altruix PM Security Protection</b>\n\n"
                f"{custom_msg}\n\n"
                f"{warn_badge} <i>before automatic block.</i>"
            )
        else:
            text = (
                "<i>Hello there, this is an automated security message. I am currently away or busy.</i>\n"
                "Please state your reason for messaging in <b>one message</b> and wait for approval.\n\n"
                f"{warn_badge} <i>before automatic block.</i>"
            )
        out = await m.reply(text, parse_mode="html")

    if sender_id in __last_message_cache:
        with suppress_error(msg="Deleting previous PM permit warning"):
            await __last_message_cache[sender_id].delete()
    __last_message_cache[sender_id] = out
