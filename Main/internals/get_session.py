# Copyright (C) 2021-present by Altruix@Github, < https://github.com/Altruix >.
#
# This file is part of < https://github.com/Altruix/Altruix > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/Altriux/Altruix/blob/main/LICENSE >
#
# All rights reserved.

import re
import glob
import asyncio
import contextlib
from pathlib import Path
from Main import Altruix
from Main.utils.custom_filters import filters
from Main.core.decorators import log_errors
from telethon import custom


@Altruix.bot.on_message(filters.command("start", "/") & filters.private)
@log_errors
async def start_command_handler(c, m):
    payload = m.text.replace("/start", "").strip() if m.text else ""
    sender_id = getattr(m, "sender_id", None)
    if sender_id is None and hasattr(m, "from_user") and m.from_user:
        sender_id = getattr(m.from_user, "id", None)

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
        caption_template = Altruix.get_string("BOT_ST_MSG") or "Welcome {0}! {1}"
        caption = caption_template.format(mention, Altruix.config.CUSTOM_BT_START_MSG or "")

        start_buttons = []
        if sender_id in Altruix.auth_users:
            start_buttons.append([custom.Button.inline("📖 Help Menu", b"help#_cat?cat=all&page=0")])

        await m.reply_file(file, caption=caption, buttons=start_buttons or None, send_msg_if_file_invalid=True)

        if Altruix.training_wheels_protocol and (not m.from_user or m.from_user.id in Altruix.auth_users):
            buttons = [
                [
                    custom.Button.inline("Yes", b"session_yes"),
                    custom.Button.inline("No", b"session_no"),
                ]
            ]
            await m.reply(
                "You'll need to add a user session to activate userbot features.\n"
                "Do you have a Telethon string session already generated?",
                buttons=buttons,
            )
    elif payload == "add_session":
        buttons = [
            [
                custom.Button.inline("Yes", b"session_yes"),
                custom.Button.inline("No", b"session_no"),
            ]
        ]
        await m.reply(
            "Do you have a Telethon string session already generated?",
            buttons=buttons,
        )


@Altruix.bot.on_callback_query(filters.regex("^add_session"))
@log_errors
async def add_session_menu_cb_handler(c, cb):
    buttons = [
        [
            custom.Button.inline("Yes", b"session_yes"),
            custom.Button.inline("No", b"session_no"),
        ]
    ]
    await cb.edit(
        "Do you have a Telethon string session already generated?",
        buttons=buttons,
    )


@Altruix.bot.on_callback_query(filters.regex("^session_yes"))
@log_errors
async def add_session_yes_cb_handler(c, cb):
    await cb.answer()
    async with Altruix.bot.conversation(cb.chat_id, timeout=300) as conv:
        prompt = await conv.send_message(
            "Please send your Telethon string session.\n\n"
            "💡 You can generate one in terminal without risk of expired codes:\n"
            "<code>py -3 Main/scripts/session_gen.py</code>\n\n"
            "Use /cancel to cancel.",
            parse_mode="html",
        )
        session_resp = await conv.get_response(prompt)
        text = session_resp.raw_text.strip()
        if text.startswith("/cancel"):
            await conv.send_message("Session setup cancelled.")
            return

        match = re.search(r"(\S{100,600})", text)
        if not match:
            await conv.send_message("The string session format looks invalid. Please try again.")
            return

        session_str = match.group(1)
        status = await conv.send_message("Processing and connecting session...")
        try:
            new_client = await Altruix.add_session(session_str, status)
            if new_client:
                await conv.send_message("Session successfully added and connected!")
        except Exception as e:
            await status.edit(f"Failed to connect session: {e}")
