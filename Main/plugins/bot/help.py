# Copyright (C) 2021-present by Altruix@Github, < https://github.com/Altruix >.
#
# This file is part of < https://github.com/Altruix/Altruix > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/Altriux/Altruix/blob/main/LICENSE >
#
# All rights reserved.

import re
import telethon
from Main import Altruix
from typing import Optional
from platform import python_version
from Main.utils.custom_filters import filters
from Main.core.decorators import log_errors, iuser_check
from telethon import custom


help_text = f"""<b><u>Altruix Help Menu</u></b>
<b>Userbot version:</b> <code>V{Altruix.__version__}</code>
<b>Telethon version:</b> <code>V{telethon.__version__}</code>
<b>Python version:</b> <code>V{python_version()}</code>"""
cache_help_menu = None
multi_pages = False


@log_errors
async def get_help_menu(return_all: bool = False):
    global cache_help_menu
    global multi_pages
    if cache_help_menu:
        if multi_pages and not return_all:
            return cache_help_menu[0]
        return cache_help_menu
    plugins = sorted(list(Altruix._command_help_message_data.keys()))
    ikb = [
        custom.Button.inline(
            plugin.replace("_", " ").title(),
            f"help#{plugin}".encode("utf-8"),
        )
        for plugin in plugins
    ]
    rows = Altruix.config.HELP_MENU_ROWS
    columns = Altruix.config.HELP_MENU_COLUMNS
    buttons = [ikb[i : i + columns] for i in range(0, len(ikb), columns)]
    if len(buttons) > rows:
        buttons = [buttons[i : i + rows] for i in range(0, len(buttons), rows)]
        multi_pages = True
    if multi_pages:
        new_pages = []
        for index, page in enumerate(buttons):
            updated_page = []
            for row in page:
                new_row = []
                for btn in row:
                    data = getattr(btn, "data", None) or getattr(getattr(btn, "type", None), "data", b"")
                    new_data = (data.decode("utf-8") if isinstance(data, bytes) else str(data)) + f"?page={index}"
                    new_row.append(custom.Button.inline(btn.text, new_data.encode("utf-8")))
                updated_page.append(new_row)
            page_buttons = [
                custom.Button.inline(f"> {i + 1} <" if i == index else str(i + 1), f"help#_page?page={i}".encode("utf-8"))
                for i in range(len(buttons))
            ]
            updated_page.append(page_buttons)
            updated_page.append([custom.Button.inline("Close", b"close_help")])
            new_pages.append(updated_page)
        buttons = new_pages
    cache_help_menu = buttons
    if multi_pages and not return_all:
        return cache_help_menu[0]
    return cache_help_menu


@log_errors
async def get_plugin_data(plugin: str, number: int = 0):
    text = f"<b>Help for</b> <code>{plugin}</code>\n\n{Altruix._command_help_message_data[plugin.lower()].strip()}"
    buttons = [[custom.Button.inline("Back", f"help#_page?page={number}".encode("utf-8"))]]
    return text, buttons


@Altruix.bot.on_callback_query(filters.regex("close_help"))
@log_errors
@iuser_check
async def close_help(c, cq):
    await cq.edit(
        "<b>Help Menu Closed 🔐</b>",
        buttons=[[custom.Button.inline("Re-Open", b"re_open")]],
        parse_mode="html",
    )


@Altruix.bot.on_inline_query(filters.regex(r"^change_lang", flags=re.IGNORECASE))
@log_errors
@iuser_check
async def reload_language(c, iq):
    bttns = [
        [
            custom.Button.inline(
                Altruix.all_lang_strings[lang].get("def", lang).title(),
                f"reload_lang_{lang}".encode("utf-8"),
            )
        ]
        for lang in Altruix.all_lang_strings.keys()
    ]
    builder = iq.builder
    result = builder.article(
        title="Change Altruix default language",
        text="<b>Altruix Language Setup Wizard</b>\n<b>Click a language available below to change Altruix's default language</b>",
        parse_mode="html",
        buttons=bttns,
    )
    await iq.answer([result])


@Altruix.bot.on_callback_query(filters.regex(r"^reload_lang_(.*)"))
@log_errors
@iuser_check
async def change_lang(c, cb):
    data_str = cb.data.decode("utf-8") if isinstance(cb.data, bytes) else str(cb.data)
    match = re.search(r"^reload_lang_(.*)", data_str)
    if not match:
        return
    lang = match.group(1)
    if lang not in Altruix.all_lang_strings.keys():
        return await cb.answer(Altruix.get_string("INVALID_LANG_SELECTED") or "Invalid language", alert=True)
    if lang == Altruix.selected_lang:
        return await cb.answer(Altruix.get_string("LANG_IN_USE") or "Language already in use")
    Altruix.selected_lang = lang
    await Altruix.config.add_env_to_db("UB_LANG", lang)
    return await cb.answer(Altruix.get_string("LANG_SELECTED") or "Language selected!")


@Altruix.bot.on_inline_query(filters.regex(r"^help ?(.+)?", flags=re.IGNORECASE))
@log_errors
@iuser_check
async def help_inline(c, iq):
    text = iq.text or ""
    parts = text.split(None, 1)
    plugin = parts[1].strip() if len(parts) > 1 else None
    builder = iq.builder

    if not plugin:
        buttons = await get_help_menu()
        result = builder.article(
            title="Help Menu",
            text=help_text,
            parse_mode="html",
            buttons=buttons,
        )
        await iq.answer([result])
    elif plugin.lower() in Altruix._command_help_message_data:
        p_text, p_buttons = await get_plugin_data(plugin.lower())
        result = builder.article(
            title=f"Help Module for {plugin}",
            text=p_text,
            parse_mode="html",
            buttons=[[custom.Button.inline("Go to help menu", b"re_open")]],
        )
        await iq.answer([result])
    else:
        result = builder.article(
            title="Plugin not found!",
            text=f"Help for {plugin} was not found!",
        )
        await iq.answer([result])


@Altruix.bot.on_callback_query(filters.regex(r"^re_open"))
@log_errors
@iuser_check
async def re_help(c, cq):
    buttons = await get_help_menu()
    await cq.edit(help_text, buttons=buttons, parse_mode="html")


@Altruix.bot.on_callback_query(filters.regex(r"^help(?:#(\w+)(?:\?page=(\d+))?)?$"))
@log_errors
@iuser_check
async def help_callback(c, cq):
    data_str = cq.data.decode("utf-8") if isinstance(cq.data, bytes) else str(cq.data)
    match = re.search(r"^help(?:#(\w+)(?:\?page=(\d+))?)?$", data_str)
    if not match or not match.group(1):
        buttons = await get_help_menu()
        return await cq.edit(help_text, buttons=buttons, parse_mode="html")
    text = match.group(1)
    number = int(match.group(2)) if match.group(2) else 0
    if text == "_page":
        buttons = await get_help_menu(return_all=True)
        return await cq.edit(help_text, buttons=buttons[number], parse_mode="html")
    if text.lower() not in Altruix._command_help_message_data:
        return await cq.answer(Altruix.get_string("PLUGIN_404") or "Plugin not found")
    p_text, p_buttons = await get_plugin_data(text, number)
    await cq.edit(p_text, buttons=p_buttons, parse_mode="html")
