# Copyright (C) 2021-present by Altruix@Github, < https://github.com/Altruix >.
#
# This file is part of < https://github.com/Altruix/Altruix > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/Altriux/Altruix/blob/main/LICENSE >
#
# All rights reserved.

import re
from telethon import custom
from Main import Altruix
from Main.core.decorators import log_errors, iuser_check
from Main.utils.custom_filters import filters
from Main.utils.inline_helper import is_owner_cb, is_owner


async def _render_sudo_menu(c):
    sudos = await Altruix.config.get_sudo() or []
    if not sudos:
        text = (
            "👑 <b>Sudo Users Management</b>\n\n"
            "<i>No sudo users currently authorized.</i>\n\n"
            "To grant sudo access, use:\n"
            "<code>.addsudo @username</code>"
        )
        buttons = [
            [custom.Button.inline("🔄 Refresh", b"sudo_refresh")],
            [custom.Button.inline("✖ Close", b"sudo_close")],
        ]
        return text, buttons

    lines = [
        "👑 <b>Sudo Users Management Panel</b>\n",
        f"<b>Authorized Users ({len(sudos)}):</b>\n",
    ]

    buttons = []
    for uid in sudos:
        try:
            user_ent = await c.get_entity(int(uid))
            name = getattr(user_ent, "first_name", "") or str(uid)
            uname = f"@{user_ent.username}" if getattr(user_ent, "username", None) else f"ID: {uid}"
            lines.append(f"• <b>{name}</b> (<code>{uname}</code>)")
            btn_label = f"❌ Revoke {name[:14]}"
        except Exception:
            lines.append(f"• User ID: <code>{uid}</code>")
            btn_label = f"❌ Revoke {uid}"

        buttons.append([custom.Button.inline(btn_label, f"sudo_rm:{uid}".encode("utf-8"))])

    lines.append("\n<i>💡 Tap any revoke button below to remove sudo privileges instantly:</i>")
    buttons.append([
        custom.Button.inline("🔄 Refresh", b"sudo_refresh"),
        custom.Button.inline("✖ Close", b"sudo_close"),
    ])
    return "\n".join(lines), buttons


@Altruix.bot.on_inline_query(filters.regex(r"^listsudo$"))
@log_errors
@iuser_check
async def listsudo_inline_query_handler(c, iq):
    if not is_owner(iq.sender_id):
        return await iq.answer([], switch_pm="⛔ Access denied: Sudo management is owner only.", switch_pm_param="auth")

    text, buttons = await _render_sudo_menu(c)
    builder = iq.builder
    res = builder.article(
        title="👑 Sudo Users Management",
        description="View and revoke authorized sudo users with one tap.",
        text=text,
        buttons=buttons,
        parse_mode="html",
    )
    await iq.answer([res], cache_time=0)


@Altruix.bot.on_callback_query(filters.regex(r"^sudo_"))
@log_errors
async def sudo_callback_handler(c, cb):
    if not is_owner_cb(cb):
        return await cb.answer("⛔ Access denied: Only primary bot owner can manage sudo users.", alert=True)

    data = cb.data.decode("utf-8") if isinstance(cb.data, bytes) else str(cb.data)

    if data.startswith("sudo_rm:"):
        target_uid = int(data.split(":")[1])
        await Altruix.config.del_sudo(target_uid)
        await cb.answer(f"❌ Revoked sudo privileges for {target_uid}!", alert=True)

    elif data == "sudo_refresh":
        await cb.answer("🔄 Sudo list refreshed!")

    elif data == "sudo_close":
        try:
            await cb.delete()
        except (TypeError, Exception):
            try:
                await cb.edit("<i>Sudo management panel closed.</i>", buttons=None, parse_mode="html")
            except Exception:
                pass
        return

    text, buttons = await _render_sudo_menu(c)
    try:
        await cb.edit(text, buttons=buttons, parse_mode="html")
    except Exception:
        pass

