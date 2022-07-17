# Copyright (C) 2021-present by Altruix@Github, < https://github.com/Altruix >.
#
# This file is part of < https://github.com/Altruix/Altruix > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/Altriux/Altruix/blob/main/LICENSE >
#
# All rights reserved.

from Main import Altruix
from pyrogram import Client
from Main.core.types.message import Message


bcast_db = Altruix.db.make_collection("Broadcast")


@Altruix.register_on_cmd(
    ["badd", "broadcastadd", "bcastadd"],
    bot_mode_unsupported=True,
    cmd_help={
        "help": "Add the chat to the db",
        "example": "badd <chatid>",
    },
)
async def bcast_add(c: Client, m: Message):
    msg = await m.handle_message("PROCESSING")
    my_id = c.myself.id
    if m.user_input:
        chat_id = m.user_input
        if not chat_id.isdigit():
            return await msg.edit("Invalid chat id")
    else:
        chat_id = m.chat.id
    check = await bcast_db.find_one({"chat_id": int(chat_id), "client_id": my_id})
    if check:
        return await msg.edit("This chat is already in database.")
    await bcast_db.insert_one({"chat_id": int(chat_id), "client_id": my_id})
    await msg.edit(f"Added <code>{chat_id}</code> to the database")


@Altruix.register_on_cmd(
    ["bremove", "brm", "broadcastremove", "broadcastrm", "bcastrm", "bcastremove"],
    bot_mode_unsupported=True,
    cmd_help={
        "help": "Remove the chat from the db",
        "example": "bcastrm <chatid>",
    },
)
async def bcast_remove(c: Client, m: Message):
    msg = await m.handle_message("PROCESSING")
    if m.user_input:
        chat_id = m.user_input
        if not chat_id.isdigit():
            return await msg.edit("Invalid chat id")
    else:
        chat_id = m.chat.id
    check = await bcast_db.find_one({"chat_id": int(chat_id), "client_id": c.myself.id})
    if not check:
        return await msg.edit("This chat is not in the db")
    await bcast_db.delete_one({"chat_id": int(chat_id), "client_id": c.myself.id})
    await msg.edit(f"Deleted <code>{chat_id}</code> from the database")


@Altruix.register_on_cmd(
    ["bcast", "broadcast"],
    bot_mode_unsupported=True,
    cmd_help={
        "help": "To broadcast the replied message",
        "example": "bcast <replyt_o_msg>",
    },
    requires_reply=True,
)
async def broadcast(c: Client, m: Message):
    success = 0
    err = 0
    msg = await m.handle_message("PROCESSING")
    chats = []
    async for x in bcast_db.find({"client_id": c.myself.id}):
        chats.append(x["chat_id"])
    if not chats:
        return await msg.edit("No chats saved in db")
    for chat in chats:
        try:
            await c.copy_message(
                chat_id=int(chat),
                from_chat_id=m.chat.id,
                message_id=m.reply_to_message.id,
            )
            success += 1
        except Exception:
            Altruix.log()
            err += 1
    await msg.edit(
        f"Succesfully broadcasted in <code>{success}</code> chats and errors in <code>{err}</code> chats!"
    )
