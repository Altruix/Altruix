# Copyright (C) 2021-present by Altruix@Github, < https://github.com/Altruix >.
#
# This file is part of < https://github.com/Altruix/Altruix > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/Altriux/Altruix/blob/main/LICENSE >
#
# All rights reserved.


from Main import Altruix
from pyrogram import filters
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup


@Altruix.bot.on_message(filters.command("add", "/"))
async def add_session_command_handler(_, m: Message):
    if m.from_user.id not in Altruix.auth_users:
        return await m.reply_text("Hey, I'm just a bot. Powered by @AltruixUB.")
    await m.reply(
        "Do you have the string session already generated?.",
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("Yes", callback_data="session_yes"),
                    InlineKeyboardButton("No", callback_data="session_no"),
                ]
            ]
        ),
    )
