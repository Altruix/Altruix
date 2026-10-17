# Copyright (C) 2021-present by Altruix@Github, < https://github.com/Altruix >.
#
# This file is part of < https://github.com/Altruix/Altruix > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/Altriux/Altruix/blob/main/LICENSE >
#
# All rights reserved.

import time
import asyncio
from Main import Altruix
from Main.utils.suppress import suppress_error
from Main.core.types.client import AltruixTelegramClient as Client
from Main.core.decorators import check_perm
from Main.core.types.message import Message
from Main.plugins.userbot.channel_utils import digit_wrap
from telethon import errors


@Altruix.register_on_cmd(
    "pin",
    cmd_help={"help": "Pin the reply message", "example": "pin (replying to message)"},
    requires_reply=True,
)
@check_perm("can_pin_messages")
async def pin(c: Client, msg: Message):
    _m = await msg.handle_message("PROCESSING")
    try:
        await c.pin_chat_message(msg.chat.id, msg.reply_to_message.id)
    except Exception as exception_:
        return await _m.edit_msg("UNABLE_TO_PIN", string_args=(exception_,))
    await _m.edit_msg("PINNED")


@Altruix.register_on_cmd(
    "unpin",
    cmd_help={
        "help": "Unpin the replied message",
        "example": "unpin (reply_to_message)",
    },
    requires_reply=True,
)
@check_perm("can_pin_messages")
async def unpin(c: Client, msg: Message):
    m = await msg.handle_message("PROCESSING")
    try:
        await c.unpin_chat_message(msg.chat.id, msg.reply_to_message.id)
    except Exception as exception_:
        return await m.edit_msg("UNABLE_TO_UNPIN", string_args=(exception_,))
    await m.edit_msg("UNPINNED")


@Altruix.register_on_cmd(
    "ban",
    cmd_help={
        "help": "Ban the user from the chat and restrict permissions",
        "example": "ban (reply|username|id)",
    },
    group_only=True,
)
@check_perm("can_restrict_members")
async def ban(c: Client, m: Message):
    ms = await m.handle_message("PROCESSING")
    user_, reason_, _ = m.get_user
    if not user_:
        return await ms.edit_msg("INVALID_USER")
    dur, input_dur = m.extract_time
    try:
        await c.edit_permissions(m.chat.id, digit_wrap(user_), view_messages=False, until_date=dur)
    except errors.UserAdminInvalidError:
        return await ms.edit_msg("NOT_PROPER_RIGHTS")
    except Exception as exception_:
        return await ms.edit_msg("UNABLE_TO_BAN", string_args=(exception_,))
    input_dur = input_dur or "Forever"
    user_obj = await c.get_users(user_)
    await ms.edit_msg(
        "BANNED_USER",
        string_args=(
            getattr(user_obj, "mention", str(user_)),
            reason_ or "Not specified",
            input_dur,
        ),
    )


@Altruix.register_on_cmd(
    "unban",
    cmd_help={
        "help": "Unban a user from the chat and restore permissions",
        "example": "unban (reply|username|id)",
    },
    group_only=True,
)
@check_perm("can_restrict_members")
async def unban(c: Client, m: Message):
    ms = await m.handle_message("PROCESSING")
    user_, reason, is_chnnl = m.get_user
    if not user_:
        return await ms.edit_msg("INVALID_USER")
    try:
        await c.edit_permissions(m.chat.id, digit_wrap(user_), view_messages=True)
    except errors.UserAdminInvalidError:
        return await ms.edit_msg("NOT_PROPER_RIGHTS")
    except Exception as exception_:
        return await ms.edit_msg("UNABLE_TO_BAN", string_args=(exception_,))
    u_ser = await c.get_users(user_)
    await ms.edit_msg("UNBANNED_USER", string_args=(getattr(u_ser, "mention", str(user_)),))


@Altruix.register_on_cmd(
    "mute",
    cmd_help={
        "help": "Disallow a user to send messages in the chat",
        "example": "mute (reply|username|id)",
    },
    group_only=True,
)
@check_perm("can_restrict_members")
async def mute(c: Client, m: Message):
    ms = await m.handle_message("PROCESSING")
    user_, reason_, is_chnnl = m.get_user
    if not user_:
        return await ms.edit_msg("INVALID_USER")
    dur, input_dur = m.extract_time
    try:
        await c.edit_permissions(m.chat.id, digit_wrap(user_), send_messages=False, until_date=dur)
    except errors.UserAdminInvalidError:
        return await ms.edit_msg(Altruix.get_string("NOT_PROPER_RIGHTS") or "Not proper admin rights.")
    except Exception as exception_:
        return await ms.edit_msg(
            Altruix.get_string("UNABLE_TO_MUTE", string_args=(exception_,)) or f"Unable to mute: {exception_}"
        )
    user_info = await c.get_users(user_)
    input_dur = input_dur or "Forever"
    await ms.edit_msg(
        "MUTED_USER",
        string_args=(getattr(user_info, "mention", str(user_)), reason_ or "Not specified", input_dur),
    )


@Altruix.register_on_cmd(
    "unmute",
    cmd_help={
        "help": "Re-allow user to message in the chat",
        "example": "unmute (reply/username/id)",
    },
    group_only=True,
)
@check_perm("can_restrict_members")
async def unmute(c: Client, m: Message):
    ms = await m.handle_message("PROCESSING")
    user_, reason_, is_chnnl = m.get_user
    if not user_:
        return await ms.edit_msg("INVALID_USER")
    try:
        await c.edit_permissions(m.chat.id, digit_wrap(user_), send_messages=True)
    except errors.UserAdminInvalidError:
        return await ms.edit_msg("NOT_PROPER_RIGHTS")
    except Exception as exception_:
        return await ms.edit_msg("UNABLE_TO_UNMUTE", string_args=(exception_,))
    user_info = await c.get_users(user_)
    await ms.edit_msg("UNMUTED_USER", string_args=(getattr(user_info, "mention", str(user_)),))


@Altruix.register_on_cmd(
    "kick",
    cmd_help={
        "help": "Kick the user from the chat",
        "example": "kick (reply|username|id)",
    },
    group_only=True,
)
@check_perm("can_restrict_members")
async def kick(c: Client, m: Message):
    ms = await m.handle_message("PROCESSING")
    user_, reason_, is_chnnl = m.get_user
    if not user_:
        return await ms.edit_msg("INVALID_USER")
    try:
        await c.kick_participant(m.chat.id, digit_wrap(user_))
    except errors.UserAdminInvalidError:
        return await ms.edit_msg("NOT_PROPER_RIGHTS")
    except Exception as exception_:
        return await ms.edit_msg("UNABLE_TO_KICK", string_args=(exception_,))
    user_info = await c.get_users(user_)
    await ms.edit_msg(
        "KICKED_USER",
        string_args=(getattr(user_info, "mention", str(user_)), reason_ or "Not specified"),
    )


@Altruix.register_on_cmd(
    "promote",
    cmd_help={
        "help": "Promote a user in the group chat",
        "example": "promote (username | reply to user)",
    },
    group_only=True,
    disallow_if_sender_is_channel=True,
)
@check_perm("can_promote_members")
async def promote(c: Client, m: Message):
    ms = await m.handle_message("PROCESSING")
    user_, __, _ = m.get_user
    args = m.user_args
    if not user_:
        return await ms.edit_msg("INVALID_USER")

    admin_title = args.title or "Admin"
    try:
        await c.edit_admin(
            m.chat.id,
            digit_wrap(user_),
            change_info=True,
            post_messages=True,
            edit_messages=True,
            delete_messages=True,
            ban_users=True,
            invite_users=True,
            pin_messages=True,
            add_admins=False,
            manage_call=True,
            title=admin_title,
        )
    except Exception as e:
        return await ms.edit_msg("PROMOTE_FAILED", string_args=(e,))
    user_info = await c.get_users(user_)
    await ms.edit_msg("PROMOTED", string_args=(getattr(user_info, "mention", str(user_)), admin_title))


@Altruix.register_on_cmd(
    "demote",
    cmd_help={
        "help": "Demote a user in the group chat",
        "example": "demote (username | reply to user)",
    },
    group_only=True,
    disallow_if_sender_is_channel=True,
)
@check_perm("can_promote_members")
async def demote(c: Client, m: Message):
    ms = await m.handle_message("PROCESSING")
    user_, a_title, is_chnnl = m.get_user
    if not user_:
        return await ms.edit_msg("INVALID_USER")
    try:
        await c.edit_admin(m.chat.id, digit_wrap(user_), is_admin=False)
    except Exception as e:
        return await ms.edit_msg("DEMOTE_FAILED", string_args=(e,))
    user_info = await c.get_users(user_)
    await ms.edit_msg("DEMOTED", string_args=(getattr(user_info, "mention", str(user_)),))


@Altruix.register_on_cmd(
    ["del", "delete"],
    cmd_help={
        "help": "Delete the replied message",
        "example": "del (reply to message)",
    },
    requires_reply=True,
)
async def delete_cmd(c: Client, m: Message):
    start_time = time.time()
    ms = await m.handle_message("PROCESSING")
    reply_id = m.reply_to_message.id if m.reply_to_message else None
    if reply_id:
        await c.delete_messages(m.chat.id, [reply_id])
        elapsed = round((time.time() - start_time) * 1000, 2)
        await ms.edit_msg("DEL_SUCCESS_TRUE", string_args=(elapsed,))
    else:
        await ms.edit_msg("DEL_SUCCESS_FALSE")
    await asyncio.sleep(2)
    with suppress_error(msg="Deleting del status message"):
        await ms.delete()


@Altruix.register_on_cmd(
    "purge",
    cmd_help={
        "help": "Purge messages in the group chat",
        "example": "purge (replying to start message)",
    },
    requires_reply=True,
)
@check_perm("can_delete_messages")
async def purge(c: Client, m: Message):
    start_time = time.time()
    ms = await m.handle_message("PROCESSING")
    start_id = m.reply_to_message.id
    end_id = m.id
    ids = [i for i in range(start_id, end_id) if i not in (m.id, ms.id)]
    if ids:
        # Telethon delete_messages accepts list of message IDs
        for chunk in [ids[i : i + 100] for i in range(0, len(ids), 100)]:
            await c.delete_messages(m.chat.id, chunk)
    time_taken = round((time.time() - start_time) * 1000, 2)
    await ms.edit_msg("PURGED", string_args=(time_taken, len(ids)))
    await asyncio.sleep(2)
    with suppress_error(msg="Deleting purge status message"):
        await ms.delete()
