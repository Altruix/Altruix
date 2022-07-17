# Copyright (C) 2021-present by Altruix@Github, < https://github.com/Altruix >.
#
# This file is part of < https://github.com/Altruix/Altruix > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/Altriux/Altruix/blob/main/LICENSE >
#
# All rights reserved.


import re
import pyrogram
from Main import Altruix
from typing import Optional
from platform import python_version
from pyrogram import Client, filters
from Main.core.decorators import log_errors, iuser_check
from pyrogram.types import (
    InlineQuery, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup,
    InputTextMessageContent, InlineQueryResultArticle)


help_text = f"""<b><u>Altruix Help Menu</u></b>
<b>Userbot version :</b> <code>V{Altruix.__version__}</code>
<b>Pyrogram version :</b> <code>V{pyrogram.__version__} </code>
<b>Python version :</b> <code>V{python_version()}</code>"""
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
    plugins = sorted(list(Altruix.CLIST.keys()))
    ikb = [
        InlineKeyboardButton(
            plugin.replace("_", " ").title(), callback_data=f"help#{plugin}"
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
        for page in buttons:
            index = buttons.index(page)
            for i in page:
                for j in i:
                    j.callback_data += f"#{index}"
            page_buttons = [
                InlineKeyboardButton(str(i + 1), callback_data=f"help#_page#{i}")
                for i in range(len(buttons))
            ]
            for i in page_buttons:
                if i.text == str(index + 1):
                    i.text = f"☞ {i.text} ☜"
            page.append(page_buttons)
            page.append([InlineKeyboardButton("Close", "close_help")])
    cache_help_menu = buttons
    if multi_pages and not return_all:
        return cache_help_menu[0]
    return cache_help_menu


@log_errors
async def get_plugin_data(plugin: str, number: int = 0):
    text = f"<b>Help for</b> <code>{plugin}</code>\n\n{Altruix.CLIST[plugin.lower()].strip()}"
    buttons = InlineKeyboardMarkup(
        [[InlineKeyboardButton("Back", callback_data=f"help#_page#{number}")]]
    )
    return text, buttons


@Altruix.bot.on_callback_query(filters.regex("close_help"))
@log_errors
@iuser_check
async def close_help(c: Client, cq: CallbackQuery):
    await cq.edit_message_text(
        "<b>Help Menu Closed 🔐</b>",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("Re-Open", "re_open")]]
        ),
    )


@Altruix.bot.on_inline_query(filters.regex("^change_lang", flags=re.IGNORECASE))
@log_errors
@iuser_check
async def reload_language(c: Client, iq: InlineQuery):
    bttns = [
        [
            InlineKeyboardButton(
                Altruix.all_lang_strings[lang].get("def").title() or lang.title(),
                f"reload_lang_{lang}",
            )
        ]
        for lang in Altruix.all_lang_strings.keys()
    ]
    await iq.answer(
        results=[
            InlineQueryResultArticle(
                title="Change Altruix default language",
                input_message_content=InputTextMessageContent(
                    "<b>Altruix Language Set-up Wizard</b> \n<b>Click a language available below to change Altruix's default langauge</b>"
                ),
                reply_markup=InlineKeyboardMarkup(bttns),
            )
        ]
    )


@Altruix.bot.on_callback_query(filters.regex("^reload_lang_(.*)"))
@log_errors
@iuser_check
async def change_lang(c: Client, cb: CallbackQuery):
    lang = cb.matches[0].group(1)
    if lang not in Altruix.all_lang_strings.keys():
        return await cb.answer(
            Altruix.get_string("INVALID_LANG_SELECTED"), cache_time=0, show_alert=True
        )
    if lang == Altruix.selected_lang:
        return await cb.answer(Altruix.get_string("LANG_IN_USE"))
    Altruix.selected_lang = lang
    await Altruix.config.add_env_to_db("UB_LANG", lang)
    return await cb.answer(Altruix.get_string("LANG_SELECTED"))


@Altruix.bot.on_inline_query(filters.regex("^help ?(.+)?", flags=re.IGNORECASE))
@log_errors
@iuser_check
async def help(_: Client, iq: InlineQuery):
    plugin: Optional[str] = iq.matches[0].group(1)
    if not plugin:
        buttons = await get_help_menu()
        await iq.answer(
            results=[
                InlineQueryResultArticle(
                    title="Help Menu",
                    input_message_content=InputTextMessageContent(help_text),
                    reply_markup=InlineKeyboardMarkup(buttons),
                )
            ]
        )
    elif plugin.strip() in Altruix.CLIST:
        text, _ = await get_plugin_data(plugin.lower())
        await iq.answer(
            results=[
                InlineQueryResultArticle(
                    title=f"Help Module for {plugin}",
                    input_message_content=InputTextMessageContent(text),
                    reply_markup=InlineKeyboardMarkup(
                        [[InlineKeyboardButton("Goto help menu", "help")]]
                    ),
                )
            ]
        )
    else:
        await iq.answer(
            results=[
                InlineQueryResultArticle(
                    title="Plugin not found!",
                    input_message_content=InputTextMessageContent(
                        f"Help for {plugin} is not found!"
                    ),
                )
            ]
        )


@Altruix.bot.on_callback_query(filters.regex("^re_open"))
@log_errors
@iuser_check
async def re_help(c: Client, cq: CallbackQuery):
    buttons = await get_help_menu()
    await cq.edit_message_text(help_text, reply_markup=InlineKeyboardMarkup(buttons))


@Altruix.bot.on_callback_query(filters.regex("^help"))
@log_errors
@iuser_check
async def help_callback(_: Client, cq: CallbackQuery):
    data = cq.data.lower().split("#")
    data.pop(0)
    if not data:
        buttons = await get_help_menu()
        return await cq.edit_message_text(
            help_text, reply_markup=InlineKeyboardMarkup(buttons)
        )
    text = data[0]
    number = int(data[1])
    if text == "_page":
        buttons = await get_help_menu(return_all=True)
        return await cq.edit_message_text(
            help_text, reply_markup=InlineKeyboardMarkup(buttons[number])
        )
    if text.lower() not in Altruix.CLIST.keys():
        return await cq.answer(Altruix.get_string("PLUGIN_404"))
    text, buttons = await get_plugin_data(text, number)
    await cq.edit_message_text(text, reply_markup=buttons)
