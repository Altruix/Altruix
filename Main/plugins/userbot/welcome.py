# Copyright (C) 2021-present by Altruix@Github, < https://github.com/Altruix >.
#
# This file is part of < https://github.com/Altruix/Altruix > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/Altriux/Altruix/blob/main/LICENSE >
#
# All rights reserved.


from Main import Altruix
from pyrogram import Client, filters
from Main.core.types.message import Message


welcome_db = Altruix.db.make_collection("WELCOME")


@Altruix.register_on_cmd(
    ["savewelcome", "addwelcome"],
    cmd_help={
        "help": "Save welcome message in a chat.",
        "example": "savewelcome Hello {first} , how are you?",
    },
    requires_reply=True,
)
async def add_welcome_cmd(c: Client, m: Message):
    reply_msg = m.reply_to_message
    if not Altruix.log_chat:
        return await m.handle_message("ERROR_404_NO_LOG_CHAT")
    save_welcome = await reply_msg.copy(int(Altruix.log_chat))
    if await welcome_db.find_one({"chat_id": m.chat.id, "client_id": c.myself.id}):
        await welcome_db.update_one(
            {"chat_id": m.chat.id, "client_id": c.myself.id},
            {"$set": {"msg_id": save_welcome.id}},
        )
    else:
        await welcome_db.insert_one(
            {
                "chat_id": m.chat.id,
                "msg_id": save_welcome.id,
                "client_id": c.myself.id,
            }
        )
    await m.handle_message("WELCOME_SAVED")


@Altruix.register_on_cmd(
    ["delwelcome", "rmwelcome"],
    cmd_help={
        "help": "Removes the welcome message saved i the chat.",
        "example": "rmwelcome",
    },
)
async def del_welcome_cmd(c: Client, m: Message):
    if not await welcome_db.find_one({"chat_id": m.chat.id, "client_id": c.myself.id}):
        return await m.handle_message("NO_WELCOME_SAVED")
    await welcome_db.delete_one({"chat_id": m.chat.id, "client_id": c.myself.id})
    await m.handle_message("WELCOME_REMOVED")


@Altruix.register_on_cmd(
    ["welcome", "welcomesettings"],
    cmd_help={
        "help": "Shows current welcome settings in the chat.",
        "example": "",
    },
)
async def welcome_settings_cmd(c: Client, m: Message):
    welcome_data = await welcome_db.find_one(
        {"chat_id": m.chat.id, "client_id": c.myself.id}
    )
    if not welcome_data or not Altruix.log_chat:
        return await m.handle_message("NO_WELCOME_SAVED")
    await m.handle_message("CURRENT_WELCOME")
    await c.copy_message(
        from_chat_id=int(Altruix.log_chat),
        chat_id=int(m.chat.id),
        id=welcome_data["msg_id"],
        reply_to_message_id=m.id,
    )


async def welcome_filter(filter, c: Client, m: Message):
    is_welcome_enabled = await welcome_db.find_one(
        {"chat_id": m.chat.id, "client_id": c.myself.id}
    )
    return bool(is_welcome_enabled)


async def is_media(message):
    return bool(
        (
            message.photo
            or message.video
            or message.document
            or message.audio
            or message.sticker
            or message.animation
            or message.voice
            or message.video_note
        )
    )


@Altruix.on_message(
    filters.create(welcome_filter) & filters.new_chat_members & filters.group
)
async def welcome_users(c: Client, m: Message):
    media = False
    welcome_data = await welcome_db.find_one(
        {"chat_id": m.chat.id, "client_id": c.myself.id}
    )
    welcome_message = await c.get_messages(Altruix.log_chat, welcome_data["msg_id"])
    if await is_media(welcome_message):
        text = welcome_message.caption or ""
        media = True
    else:
        text = welcome_message.text or ""
    if text != "":
        mention = m.new_chat_members[0].mention
        user_id = m.new_chat_members[0].id
        user_name = m.new_chat_members[0].username or "No Username"
        first_name = m.new_chat_members[0].first_name
        last_name = m.new_chat_members[0].last_name or "No Last Name"
        text = text.format(
            mention=mention,
            user_id=user_id,
            user_name=user_name,
            first_name=first_name,
            last_name=last_name,
        )
    if not media:
        await c.send_message(m.chat.id, text, reply_to_message_id=m.id)
    else:
        await welcome_message.copy(
            chat_id=int(m.chat.id),
            caption=text,
            reply_to_message_id=m.id,
        )
