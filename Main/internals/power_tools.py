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
from pyrogram import Client, filters
from Main.core.types.message import Message
from Main.core.decorators import iuser_check, inline_check
from pyrogram.types import (
    Message, InlineQuery, CallbackQuery, InlineKeyboardButton,
    InlineKeyboardMarkup, InputTextMessageContent, InlineQueryResultArticle)


@Altruix.bot.on_callback_query(filters.regex("^(restart|reload)_confirm"))
@iuser_check
async def restart_cb_handler(_, cb: CallbackQuery):
    await cb.answer("Hang on..", show_alert=True)
    _type = cb.matches[0].group(1)
    if _type == "restart":
        text = "<i>A fresh restart will be initiated in a few seconds.</i>"
        soft = False
    else:
        text = "<i>The reloading will be initiated in a few seconds.</i>"
        soft = True
    await cb.edit_message_text(text)
    await Altruix.reboot(soft, last_msg=cb)


@Altruix.bot.on_callback_query(filters.regex("^(restart|reload)_cancel"))
@iuser_check
async def restart_cb_handler(c: Client, cb: CallbackQuery):
    await cb.answer("Alright", show_alert=True)
    _type = cb.matches[0].group(1)
    soft = _type != "restart"
    await cb.edit_message_text(
        f"<i>Aborted {'reload' if soft else 'restart'}.</i>",
    )


@Altruix.bot.on_message(
    filters.command(["restart", "reload"], "/") & filters.user(Altruix.config.OWNER_ID)
)
async def restart_command_handler(_, m: Message):
    reload_only = m.command[0] == "reload"
    await m.reply(
        f"<b>Are you sure about {'reloading' if reload_only else 'restarting'} Altruix?</b>\n\n<i>This will stop all the ongoing processes and the {'reload' if reload_only else 'restart'} will take some time.</i>",
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "Yes", f"{'reload' if reload_only else 'restart'}_confirm"
                    ),
                    InlineKeyboardButton(
                        "No", f"{'reload' if reload_only else 'restart'}_cancel"
                    ),
                ]
            ]
        ),
    )


@Altruix.bot.on_inline_query(filters.regex("^(restart|reload)"))
@iuser_check
async def ping_inline_handler(_, iq: InlineQuery):
    soft = iq.query.lower() == "reload"
    await iq.answer(
        [
            InlineQueryResultArticle(
                id=1,
                title=f"{'Reload' if soft else 'Restart'} confirmation mesage",
                description=Altruix.get_string(
                    "INTERNAL_FUNCTION", args=pf["ping_emoji2"]
                ),
                input_message_content=InputTextMessageContent(
                    f"<b>Are you sure about {'reloading' if soft else 'restarting'} Altruix?</b>\n\n<i>This will stop all the ongoing processes and the restart will take some time.</i>",
                ),
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                "Yes", f"{'reload' if soft else 'restart'}_confirm"
                            ),
                            InlineKeyboardButton(
                                "No", f"{'reload' if soft else 'restart'}_cancel"
                            ),
                        ]
                    ]
                ),
            )
        ],
        cache_time=0,
        is_personal=True,
        switch_pm_text="Internal Function",
        switch_pm_parameter="inline_help",
    )


@Altruix.register_on_cmd(
    ["restart", "reload"],
    bot_mode_unsupported=True,
    cmd_help={
        "help": "Restarts the userbot",
        "example": "restart",
        "user_args": {
            "r": "Just reloads the plugins instead of performing a full restart."
        },
    },
)
@inline_check
async def restart_ub_cmd(c: Client, m: Message):
    reload = m.command == "reload"
    rm = m.reply_to_message
    results = await c.get_inline_bot_results(
        Altruix.bot_info.username, "reload" if reload else "restart"
    )
    await asyncio.gather(
        *[
            c.send_inline_bot_result(
                chat_id=m.chat.id,
                query_id=results.query_id,
                result_id=results.results[0].id,
                reply_to_message_id=rm.id if rm else m.id,
            ),
            m.delete_if_self(),
        ]
    )
