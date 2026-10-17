# Copyright (C) 2021-present by Altruix@Github, < https://github.com/Altruix >.
#
# This file is part of < https://github.com/Altruix/Altruix > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/Altriux/Altruix/blob/main/LICENSE >
#
# All rights reserved.

import re
import html
from telethon import custom, functions
from Main import Altruix
from Main.core.decorators import log_errors, iuser_check
from Main.utils.custom_filters import filters
from Main.utils.inline_helper import is_owner_cb, is_owner


async def _render_pmpermit_panel():
    is_enabled = await Altruix.config.get_pm_sts()
    limit = await Altruix.config.get_pm_warn_limit()
    allow_contacts = await Altruix.config.get_pm_allow_contacts()
    custom_msg = await Altruix.config.get_pm_custom_msg()

    try:
        from Main.plugins.userbot.PM_Security import pm_permit_warning_cache
        pending_count = len(pm_permit_warning_cache)
    except Exception:
        pending_count = 0

    status_badge = "🟢 <b>ACTIVE & SCREENING</b>" if is_enabled else "🔴 <b>DISABLED</b>"
    contacts_badge = "✅ <b>ALLOWED (Bypass)</b>" if allow_contacts else "🛡️ <b>SCREENED</b>"
    msg_badge = "📝 <i>Customized</i>" if custom_msg else "📄 <i>Default Template</i>"

    text = (
        "🛡️ <b>Altruix PM Security Control Panel</b>\n\n"
        f"• <b>Status:</b> {status_badge}\n"
        f"• <b>Spam Warning Limit:</b> <code>{limit} Warnings</code> (Blocks on #{limit + 1})\n"
        f"• <b>Rule: Allow Contacts:</b> {contacts_badge}\n"
        f"• <b>Warning Message:</b> {msg_badge}\n"
        f"• <b>Pending In Queue:</b> <code>{pending_count} user(s)</code>\n\n"
        "<i>Tap buttons below to change policies, adjust limits (1-20), or mass approve:</i>"
    )

    toggle_label = "🔴 Turn OFF PM Permit" if is_enabled else "🟢 Turn ON PM Permit"
    contact_btn_label = "📇 Contacts: ALLOWED" if allow_contacts else "📇 Contacts: SCREENED"

    buttons = [
        [custom.Button.inline(toggle_label, b"pmsec_toggle")],
        [
            custom.Button.inline(contact_btn_label, b"pmsec_contacts"),
            custom.Button.inline(f"🔢 Set Limit ({limit})", b"pmsec_open_limits"),
        ],
        [
            custom.Button.inline("💬 View Message", b"pmsec_view_msg"),
            custom.Button.inline(f"✅ Mass Approve ({pending_count})", b"pmsec_mass_appr"),
        ],
        [
            custom.Button.inline("🧹 Reset Warnings", b"pmsec_reset"),
            custom.Button.inline("✖ Close", b"pmsec_close"),
        ],
    ]
    return text, buttons


async def _render_limits_panel():
    limit = await Altruix.config.get_pm_warn_limit()
    text = (
        "🔢 <b>Select PM Security Warning Limit</b>\n\n"
        "Choose how many warning messages a user receives before being automatically blocked.\n\n"
        f"• Current Active Limit: <b>{limit} Warnings</b>\n\n"
        "<i>Tap any number (1 - 20) below to set the limit:</i>"
    )
    buttons = []
    for r in range(4):
        row = []
        for c in range(1, 6):
            num = r * 5 + c
            label = f"✅ {num}" if num == limit else str(num)
            row.append(custom.Button.inline(label, f"pmsec_set_limit_{num}".encode("utf-8")))
        buttons.append(row)
    buttons.append([custom.Button.inline("🔙 Back to Control Panel", b"pmsec_main_panel")])
    return text, buttons


async def _render_msg_panel():
    custom_msg = await Altruix.config.get_pm_custom_msg()
    if custom_msg:
        status_text = f"<blockquote>{html.escape(custom_msg)}</blockquote>"
    else:
        status_text = "<i>(Currently using default template)</i>"

    text = (
        "💬 <b>PM Security Warning Message</b>\n\n"
        f"<b>Current Active Message:</b>\n{status_text}\n\n"
        "<i>To change your message, send:</i>\n"
        f"<code>{Altruix.user_command_handler}setpmmsg &lt;your custom message&gt;</code>"
    )
    buttons = [
        [custom.Button.inline("🔄 Reset to Default Template", b"pmsec_reset_msg")],
        [custom.Button.inline("🔙 Back to Control Panel", b"pmsec_main_panel")],
    ]
    return text, buttons


@Altruix.bot.on_inline_query(filters.regex(r"^pmpermit$"))
@log_errors
@iuser_check
async def pmpermit_inline_query_handler(c, iq):
    if not is_owner(iq.sender_id):
        return await iq.answer([], switch_pm="⛔ Access denied: PM Security is owner only.", switch_pm_param="auth")

    text, buttons = await _render_pmpermit_panel()
    builder = iq.builder
    res = builder.article(
        title="🛡️ PM Security Panel",
        description="Toggle PM security, set limits (1-20), custom message, and mass approve.",
        text=text,
        buttons=buttons,
        parse_mode="html",
    )
    await iq.answer([res], cache_time=0)


@Altruix.bot.on_callback_query(filters.regex(r"^pmsec_"))
@log_errors
async def pmsec_callback_handler(c, cb):
    if not is_owner_cb(cb):
        return await cb.answer("⛔ Access denied: Only the account owner can manage PM Security.", alert=True)

    data = cb.data.decode("utf-8") if isinstance(cb.data, bytes) else str(cb.data)

    if data == "pmsec_main_panel":
        text, buttons = await _render_pmpermit_panel()
        try:
            return await cb.edit(text, buttons=buttons, parse_mode="html")
        except Exception:
            return

    if data == "pmsec_open_limits":
        text, buttons = await _render_limits_panel()
        try:
            return await cb.edit(text, buttons=buttons, parse_mode="html")
        except Exception:
            return

    if data.startswith("pmsec_set_limit_"):
        new_limit = int(data.split("_")[-1])
        await Altruix.config.sync_env_to_db("PM_PERMIT_LIMIT", new_limit)
        await cb.answer(f"🔢 PM Warning limit set to {new_limit} warnings!", alert=False)
        text, buttons = await _render_limits_panel()
        try:
            return await cb.edit(text, buttons=buttons, parse_mode="html")
        except Exception:
            return

    if data == "pmsec_view_msg":
        text, buttons = await _render_msg_panel()
        try:
            return await cb.edit(text, buttons=buttons, parse_mode="html")
        except Exception:
            return

    if data == "pmsec_reset_msg":
        await Altruix.config.del_env_from_db("PM_PERMIT_CUSTOM_MSG")
        await cb.answer("🔄 Custom warning message reset to default!", alert=True)
        text, buttons = await _render_msg_panel()
        try:
            return await cb.edit(text, buttons=buttons, parse_mode="html")
        except Exception:
            return

    if data == "pmsec_toggle":
        current = await Altruix.config.get_pm_sts()
        new_val = not current
        await Altruix.config.sync_env_to_db("PM_PERMIT", new_val)
        status_str = "Enabled" if new_val else "Disabled"
        await cb.answer(f"🛡️ PM Security {status_str}!")

    elif data == "pmsec_contacts":
        current = await Altruix.config.get_pm_allow_contacts()
        new_val = not current
        await Altruix.config.sync_env_to_db("PM_PERMIT_ALLOW_CONTACTS", new_val)
        status_str = "Allowed (Bypass)" if new_val else "Screened"
        await cb.answer(f"📇 Saved Contacts: {status_str}!")

    elif data == "pmsec_mass_appr":
        try:
            from Main.plugins.userbot.PM_Security import pm_permit_warning_cache
            pending_ids = list(pm_permit_warning_cache.keys())
        except Exception:
            pending_ids = []

        if not pending_ids:
            return await cb.answer("ℹ️ No pending users waiting in warning queue.", alert=True)

        if Altruix.db is not None:
            pm_permit_col = Altruix.db.make_collection("pm_permit")
            for uid in pending_ids:
                await pm_permit_col.update_one({"user_id": uid}, {"$set": {"approved": True}}, upsert=True)

        count = len(pending_ids)
        try:
            from Main.plugins.userbot.PM_Security import pm_permit_warning_cache
            pm_permit_warning_cache.clear()
        except Exception:
            pass

        await cb.answer(f"✅ Successfully approved {count} pending user(s)!", alert=True)

    elif data == "pmsec_reset":
        try:
            from Main.plugins.userbot.PM_Security import pm_permit_warning_cache
            count = len(pm_permit_warning_cache)
            pm_permit_warning_cache.clear()
        except Exception:
            count = 0
        await cb.answer(f"🧹 Cleared warning count cache ({count} users reset)!", alert=True)

    elif data == "pmsec_close":
        try:
            await cb.delete()
        except (TypeError, Exception):
            try:
                await cb.edit("<i>PM Security panel closed.</i>", buttons=None, parse_mode="html")
            except Exception:
                pass
        return

    text, buttons = await _render_pmpermit_panel()
    try:
        await cb.edit(text, buttons=buttons, parse_mode="html")
    except Exception:
        pass


@Altruix.bot.on_inline_query(filters.regex(r"^pm_warn:(\d+)(?::(\d+):(\d+))?"))
@log_errors
async def pm_warn_inline_query_handler(c, iq):
    m = re.match(r"^pm_warn:(\d+)(?::(\d+):(\d+))?", iq.text)
    if not m:
        return
    target_id = int(m.group(1))
    warn_num = int(m.group(2)) if m.group(2) else 1
    limit = int(m.group(3)) if m.group(3) else await Altruix.config.get_pm_warn_limit()

    custom_msg = await Altruix.config.get_pm_custom_msg()

    if custom_msg:
        body = html.escape(custom_msg)
    else:
        body = (
            "<i>Hello there! I am currently away or busy.</i>\n"
            "Please state your reason for contacting in <b>one message</b> and wait for approval."
        )

    warn_str = f"⚠️ <b>Warning: {warn_num} of {limit}</b>"
    if warn_num >= limit:
        warn_str += " <i>(FINAL WARNING before automatic block)</i>"

    text = (
        "🤖 <b>Altruix PM Security Protection</b>\n\n"
        f"{body}\n\n"
        f"{warn_str}\n"
        "<i>Repeated messages will result in an automatic block.</i>"
    )

    buttons = [
        [
            custom.Button.inline("🛡️ Owner: Approve", f"pm_appr:{target_id}".encode("utf-8")),
            custom.Button.inline("🚫 Owner: Block", f"pm_block:{target_id}".encode("utf-8")),
        ]
    ]
    builder = iq.builder
    res = builder.article(
        title=f"⚠️ PM Warning ({warn_num}/{limit})",
        description=f"Warning {warn_num} of {limit} before auto-block.",
        text=text,
        buttons=buttons,
        parse_mode="html",
    )
    await iq.answer([res], cache_time=0)


@Altruix.bot.on_callback_query(filters.regex(r"^pm_(appr|block):(\d+)"))
@log_errors
async def pm_action_callback_handler(c, cb):
    sender_id = cb.sender_id
    if not is_owner(sender_id):
        return await cb.answer("⛔ Nice try! Only the account owner can approve or block contacts.", alert=True)

    m = re.match(r"^pm_(appr|block):(\d+)", cb.data.decode("utf-8") if isinstance(cb.data, bytes) else str(cb.data))
    if not m:
        return

    action = m.group(1)
    target_id = int(m.group(2))

    if action == "appr":
        if Altruix.db is not None:
            col = Altruix.db.make_collection("pm_permit")
            await col.update_one({"user_id": target_id}, {"$set": {"approved": True}}, upsert=True)
        try:
            from Main.plugins.userbot.PM_Security import pm_permit_warning_cache
            if target_id in pm_permit_warning_cache:
                del pm_permit_warning_cache[target_id]
        except Exception:
            pass
        await cb.answer("✅ User has been approved!", alert=True)
        await cb.edit(
            f"✅ <b>Contact Approved</b>\n\nUser <code>{target_id}</code> is now permitted to send direct messages.",
            parse_mode="html",
        )

    elif action == "block":
        if Altruix.db is not None:
            col = Altruix.db.make_collection("pm_permit")
            await col.update_one({"user_id": target_id}, {"$set": {"approved": False}}, upsert=True)
        try:
            from Main.plugins.userbot.PM_Security import pm_permit_warning_cache
            if target_id in pm_permit_warning_cache:
                del pm_permit_warning_cache[target_id]
        except Exception:
            pass

        try:
            for client in getattr(Altruix, "clients", []):
                peer = await client.get_input_entity(target_id)
                await client(functions.contacts.BlockRequest(id=peer))
                break
        except Exception:
            pass
        await cb.answer("🚫 Contact blocked.", alert=True)
        await cb.edit(
            f"🚫 <b>Contact Blocked</b>\n\nUser <code>{target_id}</code> has been blocked.",
            parse_mode="html",
        )
