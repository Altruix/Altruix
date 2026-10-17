# Copyright (C) 2021-present by Altruix@Github, < https://github.com/Altruix >.
#
# This file is part of < https://github.com/Altruix/Altruix > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/Altriux/Altruix/blob/main/LICENSE >
#
# All rights reserved.

import re
import contextlib
from Main.utils.suppress import suppress_error
from typing import List, Tuple, Any
from Main import Altruix
from Main.utils.custom_filters import filters
from Main.core.decorators import log_errors
from telethon import custom


settings_menu_buttons = [
    [
        custom.Button.inline("Sessions", b"sessions_list_1"),
        custom.Button.inline("Configs", b"configs_home"),
    ],
]


@Altruix.bot.on_callback_query(filters.regex("configs_home"))
@log_errors
async def configs_menu_cb_handler(c, cb):
    await cb.answer("This feature will be added soon!", alert=True)


@Altruix.bot.on_callback_query(filters.regex("settings_menu"))
@log_errors
async def settings_menu_cb_handler(c, cb):
    text = Altruix.get_string("SETTINGS_TEXT") or "<b>Settings</b>"
    await cb.edit(text, buttons=settings_menu_buttons, parse_mode="html")


def arrange_buttons(array: list, no: int = 5) -> List:
    n = int(no)
    return [array[i * n : (i + 1) * n] for i in range((len(array) + n - 1) // n)]


def get_sessions_buttons(page: int = 1) -> Tuple[List[Any], bool, int]:
    per_page = 9
    buttons = [
        custom.Button.inline(
            str(getattr(i.myself, "first_name", f"Session {index + 1}")),
            f"session_info_{index}_{page}".encode("utf-8"),
        )
        for index, i in enumerate(Altruix.clients)
    ] + [custom.Button.inline("➕ Add a session", b"add_session")]
    len_buttons = len(buttons)
    pages = arrange_buttons(buttons, per_page)
    if not pages or page > len(pages):
        return [], False, 1
    return pages[page - 1], len(pages) > page, len(pages)


@Altruix.bot.on_message(filters.command("settings", "/"))
@log_errors
async def settings_command_handler(c, m):
    if m.sender_id not in Altruix.auth_users:
        return
    text = Altruix.get_string("SETTINGS_TEXT") or "<b>Settings</b>"
    await m.reply(text, buttons=settings_menu_buttons, parse_mode="html")


@Altruix.bot.on_callback_query(filters.regex(r"sessions_list_(\d+)$"))
@log_errors
async def sessions_menu_cb_handler(c, cb):
    await cb.answer()
    match = re.search(r"sessions_list_(\d+)$", cb.data.decode("utf-8") if isinstance(cb.data, bytes) else str(cb.data))
    page = int(match.group(1)) if match else 1
    buttons, has_next, total_pages = get_sessions_buttons(page)
    grid = arrange_buttons(buttons, 3)
    last_col = []
    if page > 1:
        last_col.append(custom.Button.inline("Previous", f"sessions_list_{page - 1}".encode("utf-8")))
    last_col.append(custom.Button.inline(f"🔙 [{page}/{total_pages or 1}]", b"settings_menu"))
    if has_next:
        last_col.append(custom.Button.inline("Next", f"sessions_list_{page + 1}".encode("utf-8")))
    grid.append(last_col)
    await cb.edit("Sessions", buttons=grid)


@Altruix.bot.on_callback_query(filters.regex(r"session_info_(\d+)_(\d+)$"))
@log_errors
async def sessions_info_cb_handler(c, cb):
    await cb.answer()
    data_str = cb.data.decode("utf-8") if isinstance(cb.data, bytes) else str(cb.data)
    match = re.search(r"session_info_(\d+)_(\d+)$", data_str)
    if not match:
        return
    index = int(match.group(1))
    page = int(match.group(2))
    if index >= len(Altruix.clients):
        await cb.answer("Session no longer available.", alert=True)
        return
    session_info = Altruix.clients[index].myself
    txt = (
        f"<b>Session info</b>\n\n"
        f"<b>First name:</b> {getattr(session_info, 'first_name', '')}\n"
        f"<b>Last name:</b> {getattr(session_info, 'last_name', '')}\n"
        f"<b>Username:</b> @{getattr(session_info, 'username', 'None')}\n"
        f"<b>Is Bot:</b> <code>{getattr(session_info, 'bot', False)}</code>\n"
        f"<b>Is SCAM:</b> <code>{getattr(session_info, 'scam', False)}</code>"
    )
    bttns = [
        [
            custom.Button.inline("🔄 Refresh data", f"refresh_session_info_{index}".encode("utf-8")),
            custom.Button.inline("🔗 Unlink (Remove)", f"unlink_session_{index}".encode("utf-8")),
        ],
        [
            custom.Button.inline("🔙 Back", f"sessions_list_{page}".encode("utf-8")),
        ],
    ]
    await cb.edit(txt, buttons=bttns, parse_mode="html")


@Altruix.bot.on_callback_query(filters.regex(r"refresh_session_info_(\d+)$"))
@log_errors
async def refresh_session_info_cb_handler(c, cb):
    data_str = cb.data.decode("utf-8") if isinstance(cb.data, bytes) else str(cb.data)
    match = re.search(r"refresh_session_info_(\d+)$", data_str)
    if match:
        index = int(match.group(1))
        if index < len(Altruix.clients):
            Altruix.clients[index].myself = await Altruix.clients[index].get_me()
    await cb.answer("Data refreshed!", alert=True)


@Altruix.bot.on_callback_query(filters.regex(r"unlink_session_(\d+)$"))
@log_errors
async def unlink_session_cb_handler(c, cb):
    data_str = cb.data.decode("utf-8") if isinstance(cb.data, bytes) else str(cb.data)
    match = re.search(r"unlink_session_(\d+)$", data_str)
    if not match:
        return
    index = int(match.group(1))
    if index >= len(Altruix.clients):
        await cb.answer("Session already removed or not found.", alert=True)
        return

    client_to_remove = Altruix.clients.pop(index)
    with suppress_error(msg="Disconnecting removed client session"):
        await client_to_remove.disconnect()

    Altruix.config.pop_session(index)
    await cb.answer("Session unlinked and removed successfully!", alert=True)

    # Return to sessions menu
    buttons, _, total_pages = get_sessions_buttons(1)
    grid = arrange_buttons(buttons, 3)
    grid.append([custom.Button.inline("🔙 [1/1]", b"settings_menu")])
    await cb.edit("Sessions", buttons=grid)
