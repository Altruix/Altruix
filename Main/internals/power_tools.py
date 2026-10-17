# Copyright (C) 2021-present by Altruix@Github, < https://github.com/Altruix >.
#
# This file is part of < https://github.com/Altruix/Altruix > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/Altriux/Altruix/blob/main/LICENSE >
#
# All rights reserved.

import asyncio
from Main import Altruix
from style import ping_format as pf
from Main.utils.custom_filters import filters
from Main.core.decorators import log_errors, iuser_check, inline_check
from telethon import custom


@Altruix.bot.on_callback_query(filters.regex(r"^(restart|reload)_confirm"))
@log_errors
@iuser_check
async def restart_cb_handler(_, cb):
    await cb.answer("Hang on...", alert=True)
    data = cb.data.decode("utf-8") if isinstance(cb.data, bytes) else str(cb.data)
    soft = data.startswith("reload")
    text = f"<i>{'Reload' if soft else 'Restart'} initiated.</i>"
    await cb.edit(text, parse_mode="html")
    await Altruix.reboot(soft=soft, last_msg=cb) if hasattr(Altruix, "reboot") else None


@Altruix.bot.on_callback_query(filters.regex(r"^(restart|reload)_cancel"))
@log_errors
@iuser_check
async def restart_cancel_cb_handler(_, cb):
    await cb.answer("Aborted", alert=True)
    await cb.edit("<i>Operation cancelled.</i>", parse_mode="html")


@Altruix.bot.on_message(filters.command(["restart", "reload"], "/"))
@log_errors
async def restart_command_handler(_, m):
    if m.sender_id != Altruix.config.OWNER_ID:
        return
    text = m.text or ""
    reload_only = "reload" in text.lower()
    buttons = [
        [
            custom.Button.inline("Yes", b"reload_confirm" if reload_only else b"restart_confirm"),
            custom.Button.inline("No", b"reload_cancel" if reload_only else b"restart_cancel"),
        ]
    ]
    await m.reply(
        f"<b>Are you sure about {'reloading' if reload_only else 'restarting'} Altruix?</b>",
        buttons=buttons,
        parse_mode="html",
    )


@Altruix.register_on_cmd(
    "restart",
    bot_mode_unsupported=True,
    cmd_help={
        "help": "Restarts the userbot",
        "example": "restart",
        "user_args": [
            {
                "arg": "soft",
                "help": "Just reloads the plugins instead of performing a full restart.",
                "requires_input": False,
            },
        ],
    },
)
async def restart_ub_cmd(c, m):
    reload = m.user_args and "soft" in m.user_args
    await m.handle_message(f"Initiating {'reload' if reload else 'restart'}...")
    if hasattr(Altruix, "reboot"):
        await Altruix.reboot(soft=reload, last_msg=m)
