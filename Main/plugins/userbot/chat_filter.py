# Copyright (C) 2021-present by Altruix@Github, < https://github.com/Altruix >.
#
# This file is part of < https://github.com/Altruix/Altruix > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/Altriux/Altruix/blob/main/LICENSE >
#
# All rights reserved.

import re
from Main import Altruix
from pyrogram import filters
from Main.core.config import BaseConfig
from Main.core.types.message import Message


filters_db = Altruix.db.make_collection("FILTERS")
LOG_CHAT = Altruix.log_chat


@Altruix.register_on_cmd(
    ["addfilter", "savefilter", "filter"],
    cmd_help={
        "help": "Add a filter to the chat.",
        "example": "addfilter <word> <reply to message>",
    },
    requires_reply=True,
)
async def add_filter(c: Altruix, m: Message):
    ms = await m.handle_message(Altruix.get_string("PROCESSING"))
    chat_id = m.chat.id
    msg = m.user_input.lower()
    my_id_ = c.myself.id
    res = await filters_db.find_one(
        {"keyword": msg, "chat_id": chat_id, "client_id": my_id_}
    )
    if m.reply_to_message.media:
        if not Altruix.log_chat:
            return await ms.edit_msg("ERROR_404_NO_LOG_CHAT")
        media = await m.reply_to_message.copy(Altruix.log_chat)
        (
            await filters_db.update_one(
                {"keyword": msg, "chat_id": chat_id, "client_id": my_id_},
                {"$set": {"reply": media.id}},
            )
            if res
            else await filters_db.insert_one(
                {
                    "keyword": msg,
                    "chat_id": chat_id,
                    "client_id": my_id_,
                    "reply": media.id,
                }
            )
        )
    else:
        reply = m.reply_to_message.text
        if res:
            if res["reply"] != reply:
                await filters_db.update_one(
                    {"keyword": msg, "chat_id": chat_id, "client_id": my_id_},
                    {"$set": {"reply": reply}},
                )
            return await ms.edit_msg("FILTER_EXISTS", string_args=(chat_id))
        await filters_db.insert_one(
            {"keyword": msg, "chat_id": chat_id, "client_id": my_id_, "reply": reply}
        )
    await ms.edit_msg(Altruix.get_string("FILTER_ADDED").format(msg))


@Altruix.register_on_cmd(
    ["delfilter", "remfilter"],
    cmd_help={
        "help": "remove a filter from the chat.",
        "example": "delfilter <word>",
    },
)
async def remove_filter(c: Altruix, m: Message):
    ms = await m.handle_message(Altruix.get_string("PROCESSING"))
    chat_id = m.chat.id
    msg = m.user_input.lower()
    _my_id = c.myself.id
    res = await filters_db.find_one(
        {"keyword": msg, "chat_id": chat_id, "client_id": _my_id}
    )
    if res:
        await filters_db.find_one_and_delete(
            {"keyword": msg, "chat_id": chat_id, "client_id": _my_id}
        )
        return await ms.edit_msg("FILTER_REMOVED", string_args=(res["keyword"]))
    await ms.edit_msg("FILTER_DONT_EXIST", string_args=(m.chat.first_name))


async def filter_check(_, c: Altruix, m: Message):
    if m and m.text and c and c.myself and c.myself.id and str(c.myself.id).isdigit():
        if f_ := await filters_db.find_one(
            {"keyword": m.text.lower(), "chat_id": m.chat.id, "client_id": c.myself.id}
        ):
            return bool(
                (
                    f_
                    and f_.get("client_id")
                    and str(f_.get("client_id")).isdigit()
                    and int(f_.get("client_id")) == int(c.myself.id)
                )
            )


@Altruix.register_on_cmd(
    ["listfilters", "filters"],
    cmd_help={
        "help": "list all filters in the chat.",
        "example": "listfilters",
    },
)
async def listfilters(c: Altruix, m: Message):
    ms = await m.handle_message(Altruix.get_string("PROCESSING"))
    chat_id = m.chat.id
    _my_id = c.myself.id
    res = await filters_db.find({"chat_id": chat_id, "client_id": _my_id}).to_list(None)
    if not res:
        return await ms.edit_msg("FILTER_LIST_EMPTY", string_args=(chat_id))
    to_reply = (
        "".join(f"• {i['keyword']} \n" for i in res)
        + f"\n<b>TOTAL FILTERS: {len(res)}</b>"
    )
    await ms.edit_msg("FILTER_LIST", string_args=(chat_id, to_reply))


@Altruix.register_on_cmd(
    ["delfilters", "delallfilters"],
    cmd_help={
        "help": "remove all filters from the chat.",
        "example": "delfilters",
    },
)
async def delfilters(c: Altruix, m: Message):
    ms = await m.handle_message(Altruix.get_string("PROCESSING"))
    chat_id = m.chat.id
    _my_id = c.myself.id
    if await filters_db.delete_many({"chat_id": chat_id, "client_id": _my_id}):
        await ms.edit_msg("FILTER_DELETED_ALL", string_args=(chat_id))
    else:
        await ms.edit_msg("FILTER_DONT_EXIST", string_args=(m.chat.first_name))


is_filtered = filters.create(func=filter_check, name="filter")


@Altruix.on_message(
    is_filtered & filters.incoming & ~filters.bot & (filters.text | filters.caption)
)
async def filter(c: Altruix, m: Message):
    _my_id = c.myself.id
    text_ = (m.text or m.caption).lower()
    all_filt = [
        key
        async for key in filters_db.find({"chat_id": m.chat.id, "client_id": _my_id})
    ]
    if not all_filt:
        return
    for filter_s in all_filt:
        pattern = r"( |^|[^\w])" + re.escape(filter_s.get("keyword")) + r"( |$|[^\w])"
        if re.search(pattern, text_, flags=re.IGNORECASE):
            reply = await filters_db.find_one(
                {
                    "keyword": filter_s.get("keyword"),
                    "chat_id": m.chat.id,
                    "client_id": _my_id,
                }
            )
            if str(reply["reply"]).isdigit():
                await c.copy_message(
                    m.chat.id,
                    LOG_CHAT,
                    int(reply["reply"]),
                    reply_to_message_id=m.id,
                )
            else:
                await m.reply(str(reply["reply"]), quote=True)
