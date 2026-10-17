# Copyright (C) 2021-present by Altruix@Github, < https://github.com/Altruix >.
#
# This file is part of < https://github.com/Altruix/Altruix > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/Altriux/Altruix/blob/main/LICENSE >
#
# All rights reserved.

import re
from Main import Altruix
from Main.core.types.client import AltruixTelegramClient as Client
from Main.core.types.message import Message
from Main.utils.custom_filters import create, Filter


@Altruix.register_on_cmd(
    ["addfilter", "savefilter", "filter"],
    cmd_help={
        "help": "Add filter(s) to the chat. Supports comma-separated bulk keywords.",
        "example": "addfilter word1, word2, word3 <reply to message>",
    },
    requires_reply=True,
    requires_input=True,
)
async def add_filter(c: Client, m: Message):
    ms = await m.handle_message("PROCESSING")
    if Altruix.db is None:
        return await ms.edit_msg("No database connected.")
    filters_db = Altruix.db.make_collection("FILTERS")
    chat_id = m.chat.id
    raw_input = m.user_input or ""
    keywords = [k.strip().lower() for k in raw_input.split(",") if k.strip()]
    if not keywords:
        return await ms.edit_msg("No keywords specified.")

    my_id_ = c.myself.id
    if m.reply_to_message and m.reply_to_message.file:
        if not Altruix.log_chat:
            return await ms.edit_msg("ERROR_404_NO_LOG_CHAT")
        saved = await c.send_message(Altruix.log_chat, m.reply_to_message)
        reply_val = str(saved.id)
    else:
        reply_val = m.reply_to_message.text if m.reply_to_message else ""

    added_count = 0
    updated_count = 0
    for kw in keywords:
        res = await filters_db.find_one(
            {"keyword": kw, "chat_id": chat_id, "client_id": my_id_}
        )
        if res:
            await filters_db.update_one(
                {"keyword": kw, "chat_id": chat_id, "client_id": my_id_},
                {"$set": {"reply": reply_val}},
            )
            updated_count += 1
        else:
            await filters_db.insert_one(
                {"keyword": kw, "chat_id": chat_id, "client_id": my_id_, "reply": reply_val}
            )
            added_count += 1

    kw_list = ", ".join(f"<code>{k}</code>" for k in keywords)
    if len(keywords) == 1:
        template = Altruix.get_string("FILTER_ADDED") or "Filter '{0}' added successfully."
        await ms.edit(template.format(keywords[0]))
    else:
        await ms.edit(
            f"✅ <b>Bulk Filters Saved:</b> {kw_list}\n"
            f"• <b>Added:</b> {added_count} | <b>Updated:</b> {updated_count}",
            parse_mode="html",
        )


@Altruix.register_on_cmd(
    ["delfilter", "remfilter"],
    cmd_help={
        "help": "Remove filter(s) from the chat. Supports comma-separated bulk keywords.",
        "example": "delfilter word1, word2, word3",
    },
    requires_input=True,
)
async def remove_filter(c: Client, m: Message):
    ms = await m.handle_message("PROCESSING")
    if Altruix.db is None:
        return await ms.edit_msg("No database connected.")
    filters_db = Altruix.db.make_collection("FILTERS")
    chat_id = m.chat.id
    raw_input = m.user_input or ""
    keywords = [k.strip().lower() for k in raw_input.split(",") if k.strip()]
    if not keywords:
        return await ms.edit_msg("No keywords specified.")

    my_id_ = c.myself.id
    removed = []
    not_found = []
    for kw in keywords:
        res = await filters_db.find_one_and_delete(
            {"keyword": kw, "chat_id": chat_id, "client_id": my_id_}
        )
        if res:
            removed.append(kw)
        else:
            not_found.append(kw)

    if len(keywords) == 1:
        if removed:
            return await ms.edit_msg("FILTER_REMOVED", string_args=(removed[0],))
        return await ms.edit_msg("FILTER_DONT_EXIST", string_args=(getattr(m.chat, "title", str(chat_id)),))

    res_parts = []
    if removed:
        res_parts.append(f"🗑️ <b>Removed {len(removed)} filter(s):</b> {', '.join(f'<code>{r}</code>' for r in removed)}")
    if not_found:
        res_parts.append(f"ℹ️ <b>Not found ({len(not_found)}):</b> {', '.join(f'<code>{n}</code>' for n in not_found)}")
    await ms.edit("\n".join(res_parts) if res_parts else "No filters processed.", parse_mode="html")


@Altruix.register_on_cmd(
    ["listfilters", "filters"],
    cmd_help={
        "help": "List all filters in the chat.",
        "example": "listfilters",
    },
)
async def listfilters(c: Client, m: Message):
    ms = await m.handle_message("PROCESSING")
    if Altruix.db is None:
        return await ms.edit_msg("No database connected.")
    filters_db = Altruix.db.make_collection("FILTERS")
    chat_id = m.chat.id
    my_id_ = c.myself.id
    res = [item async for item in filters_db.find({"chat_id": chat_id, "client_id": my_id_})]
    if not res:
        return await ms.edit_msg("FILTER_LIST_EMPTY", string_args=(chat_id,))
    to_reply = "".join(f"• {i['keyword']}\n" for i in res) + f"\n<b>TOTAL FILTERS: {len(res)}</b>"
    await ms.edit_msg("FILTER_LIST", string_args=(chat_id, to_reply))


@Altruix.register_on_cmd(
    ["delfilters", "delallfilters"],
    cmd_help={
        "help": "Remove all filters from the chat.",
        "example": "delfilters",
    },
)
async def delfilters(c: Client, m: Message):
    ms = await m.handle_message("PROCESSING")
    if Altruix.db is None:
        return await ms.edit_msg("No database connected.")
    filters_db = Altruix.db.make_collection("FILTERS")
    chat_id = m.chat.id
    my_id_ = c.myself.id
    deleted = await filters_db.delete_many({"chat_id": chat_id, "client_id": my_id_})
    if deleted.deleted_count > 0:
        await ms.edit_msg("FILTER_DELETED_ALL", string_args=(chat_id,))
    else:
        await ms.edit_msg("FILTER_DONT_EXIST", string_args=(getattr(m.chat, "title", str(chat_id)),))


async def filter_check(c: Client, m: Message) -> bool:
    if Altruix.db is None or not m.text:
        return False
    if m.out and not getattr(Altruix, "self_test_mode", False):
        return False
    if m.text.startswith(getattr(Altruix, "user_command_handler", ".")):
        return False
    filters_db = Altruix.db.make_collection("FILTERS")
    my_id = getattr(c.myself, "id", None)
    if not my_id:
        return False
    chat_id = m.chat_id or (getattr(m.chat, "id", None))
    doc = await filters_db.find_one({"keyword": m.text.lower(), "chat_id": chat_id, "client_id": my_id})
    return bool(doc)


@Altruix.on_message(create(filter_check))
async def filter_trigger_handler(c: Client, m: Message):
    if Altruix.db is None:
        return
    filters_db = Altruix.db.make_collection("FILTERS")
    my_id = c.myself.id
    doc = await filters_db.find_one({"keyword": m.text.lower(), "chat_id": m.chat.id, "client_id": my_id})
    if doc and doc.get("reply"):
        reply_val = doc["reply"]
        if str(reply_val).isdigit() and Altruix.log_chat:
            chat_target = await m.get_input_chat() if hasattr(m, "get_input_chat") else (m.chat_id or m.chat.id)
            await c.send_message(chat_target, await c.get_messages(Altruix.log_chat, ids=int(reply_val)), reply_to=m.id)
        else:
            await m.reply(str(reply_val))
