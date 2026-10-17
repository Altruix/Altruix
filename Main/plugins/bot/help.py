# Copyright (C) 2021-present by Altruix@Github, < https://github.com/Altruix >.
#
# This file is part of < https://github.com/Altruix/Altruix > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/Altriux/Altruix/blob/main/LICENSE >
#
# All rights reserved.

import re
import html
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
async def get_help_menu(category: str = "all", page: int = 0):
    main_plugins, loaded_plugins = Altruix.get_plugins_by_category()
    all_plugins = sorted(list(Altruix._command_help_message_data.keys()))

    if category == "main":
        target_plugins = main_plugins
    elif category == "loaded":
        target_plugins = loaded_plugins
    else:
        category = "all"
        target_plugins = all_plugins

    cat_tabs = [
        custom.Button.inline(
            f"• 📦 Main ({len(main_plugins)}) •" if category == "main" else f"📦 Main ({len(main_plugins)})",
            b"help#_cat?cat=main&page=0",
        ),
        custom.Button.inline(
            f"• 🧩 Loaded ({len(loaded_plugins)}) •" if category == "loaded" else f"🧩 Loaded ({len(loaded_plugins)})",
            b"help#_cat?cat=loaded&page=0",
        ),
        custom.Button.inline(
            f"• 🌐 All ({len(all_plugins)}) •" if category == "all" else f"🌐 All",
            b"help#_cat?cat=all&page=0",
        ),
    ]

    ikb = [
        custom.Button.inline(
            f"{'📦' if Altruix.get_plugin_category(p) == 'main' else '🧩'} {p.replace('_', ' ').title()}",
            f"help#{p}?cat={category}&page={page}".encode("utf-8"),
        )
        for p in target_plugins
    ]

    rows = getattr(Altruix.config, "HELP_MENU_ROWS", 6) or 6
    columns = getattr(Altruix.config, "HELP_MENU_COLUMNS", 3) or 3
    chunked = [ikb[i : i + columns] for i in range(0, len(ikb), columns)]
    pages = [chunked[i : i + rows] for i in range(0, len(chunked), rows)]

    if not pages:
        pages = [[]]

    page = max(0, min(page, len(pages) - 1))
    current_grid = list(pages[page])

    # Insert category switcher as the first row
    current_grid.insert(0, cat_tabs)

    # Append pagination if multiple pages
    if len(pages) > 1:
        page_buttons = [
            custom.Button.inline(
                f"> {i + 1} <" if i == page else str(i + 1),
                f"help#_page?cat={category}&page={i}".encode("utf-8"),
            )
            for i in range(len(pages))
        ]
        if len(page_buttons) > 6:
            start_idx = max(0, min(page - 2, len(page_buttons) - 5))
            page_buttons = page_buttons[start_idx : start_idx + 5]
        current_grid.append(page_buttons)

    # Append Control buttons & Close
    current_grid.append([
        custom.Button.inline("🏠 Main Menu", b"bot_start_menu"),
        custom.Button.inline("⚙️ Settings", b"panel_refresh"),
        custom.Button.inline("✖ Close", b"close_help"),
    ])
    return current_grid


@log_errors
async def get_plugin_data(plugin: str, page: int = 0, category: str = "all"):
    p_name = plugin.lower()
    cat = Altruix.get_plugin_category(p_name)
    badge = "📦 Core / Main Plugin" if cat == "main" else "🧩 Loaded / Extra Plugin"
    text = (
        f"<b>Help for</b> <code>{p_name}</code>  <i>[{badge}]</i>\n\n"
        f"{Altruix._command_help_message_data[p_name].strip()}"
    )
    buttons = [
        [
            custom.Button.inline("🔙 Back", f"help#_page?cat={category}&page={page}".encode("utf-8")),
            custom.Button.inline("🏠 Main Menu", b"bot_start_menu"),
        ]
    ]
    return text, buttons


@Altruix.bot.on_callback_query(filters.regex("close_help"))
@log_errors
@iuser_check
async def close_help(c, cq):
    await cq.edit(
        "<b>Help Menu Closed 🔐</b>",
        buttons=[
            [
                custom.Button.inline("Re-Open", b"re_open"),
                custom.Button.inline("🏠 Main Menu", b"bot_start_menu"),
            ]
        ],
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
        buttons = await get_help_menu(category="all", page=0)
        result = builder.article(
            title="Help Menu",
            text=help_text,
            parse_mode="html",
            buttons=buttons,
        )
        await iq.answer([result])
    elif plugin.lower() in Altruix._command_help_message_data:
        p_text, p_buttons = await get_plugin_data(plugin.lower(), page=0, category="all")
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
    buttons = await get_help_menu(category="all", page=0)
    await cq.edit(help_text, buttons=buttons, parse_mode="html")


@Altruix.bot.on_callback_query(filters.regex(r"^help(?:#([a-zA-Z0-9_]+)(?:\?(.*))?)?$"))
@log_errors
@iuser_check
async def help_callback(c, cq):
    data_str = cq.data.decode("utf-8") if isinstance(cq.data, bytes) else str(cq.data)
    match = re.search(r"^help(?:#([a-zA-Z0-9_]+)(?:\?(.*))?)?$", data_str)
    if not match or not match.group(1):
        buttons = await get_help_menu(category="all", page=0)
        return await cq.edit(help_text, buttons=buttons, parse_mode="html")

    text = match.group(1)
    query_str = match.group(2) or ""
    params = dict(item.split("=", 1) for item in query_str.split("&") if "=" in item)
    category = params.get("cat", "all")
    page = int(params.get("page", 0)) if params.get("page", "").isdigit() else 0

    if text in ("_page", "_cat"):
        buttons = await get_help_menu(category=category, page=page)
        return await cq.edit(help_text, buttons=buttons, parse_mode="html")

    if text.lower() not in Altruix._command_help_message_data:
        return await cq.answer(Altruix.get_string("PLUGIN_404") or "Plugin not found")

    p_text, p_buttons = await get_plugin_data(text, page=page, category=category)
    await cq.edit(p_text, buttons=p_buttons, parse_mode="html")


@Altruix.bot.on_message(filters.command(["help"], prefixes="/"))
@log_errors
async def bot_help_message_handler(c, m):
    sender_id = getattr(m, "sender_id", None)
    if not sender_id or sender_id not in Altruix.auth_users:
        if getattr(m, "is_private", False):
            return await m.reply("⚠️ <i>You are not authorized to use this bot.</i>", parse_mode="html")
        return

    raw_text = getattr(m, "text", "") or getattr(m, "raw_text", "") or ""
    parts = raw_text.split(None, 1)
    plugin = parts[1].strip().lower() if len(parts) > 1 else None

    if not plugin:
        buttons = await get_help_menu(category="all", page=0)
        await m.reply(help_text, buttons=buttons, parse_mode="html")
    elif plugin in Altruix._command_help_message_data:
        p_text, p_buttons = await get_plugin_data(plugin, page=0, category="all")
        await m.reply(p_text, buttons=p_buttons, parse_mode="html")
    else:
        await m.reply(f"<i>Help for</i> <code>{html.escape(plugin)}</code> <i>was not found!</i>", parse_mode="html")
