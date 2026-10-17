# Copyright (C) 2021-present by Altruix@Github, < https://github.com/Altruix >.
#
# This file is part of < https://github.com/Altruix/Altruix > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/Altriux/Altruix/blob/main/LICENSE >
#
# All rights reserved.

"""
reactions.py — Telegram Message Reactions
Supports emoji reactions and custom emoji reactions (Premium).
Commands: .react, .unreact, .reacstats
"""

from Main import Altruix
from telethon import functions, types
from Main.core.types import AltruixTelegramClient as Client, Message


@Altruix.register_on_cmd(
    ["react", "reaction"],
    cmd_help={
        "help": "React to a replied message with an emoji.",
        "example": "react 👍",
        "user_args": [
            {"arg": "big", "help": "Use a big reaction (Premium).", "requires_input": False},
        ],
    },
    requires_reply=True,
)
async def react_to_message(c: Client, m: Message):
    rm = m.reply_to_message or (await m.get_reply_message() if hasattr(m, "get_reply_message") else None)
    if not rm:
        return await m.handle_message("INVALID_REPLY")

    emoji = m.user_input.strip() if m.user_input else "👍"
    add_to_recent = not (m.user_args and "big" in m.user_args)

    try:
        await c(functions.messages.SendReactionRequest(
            peer=await c.get_input_entity(m.chat_id),
            msg_id=rm.id,
            reaction=[types.ReactionEmoji(emoticon=emoji)],
            add_to_recent=add_to_recent,
        ))
        await m.delete_if_self()
    except Exception as e:
        await m.handle_message("REACTIONS_FAILED", string_args=(str(e),))


@Altruix.register_on_cmd(
    ["unreact", "unreaxt", "removereact"],
    cmd_help={
        "help": "Remove your reaction from a replied message.",
        "example": "unreact",
    },
    requires_reply=True,
)
async def remove_reaction(c: Client, m: Message):
    rm = m.reply_to_message or (await m.get_reply_message() if hasattr(m, "get_reply_message") else None)
    if not rm:
        return await m.handle_message("INVALID_REPLY")

    try:
        await c(functions.messages.SendReactionRequest(
            peer=await c.get_input_entity(m.chat_id),
            msg_id=rm.id,
            reaction=[],  # Empty list removes reactions
        ))
        await m.delete_if_self()
    except Exception as e:
        await m.handle_message("REACTIONS_FAILED", string_args=(str(e),))


@Altruix.register_on_cmd(
    ["reactstats", "reacstats", "reactions"],
    cmd_help={
        "help": "Show reaction statistics for a replied message.",
        "example": "reactstats",
    },
    requires_reply=True,
)
async def get_reaction_stats(c: Client, m: Message):
    rm = m.reply_to_message or (await m.get_reply_message() if hasattr(m, "get_reply_message") else None)
    if not rm:
        return await m.handle_message("INVALID_REPLY")

    # Get the fresh message with reactions
    full_msg = await c.get_messages(m.chat_id, ids=rm.id)
    if not full_msg:
        return await m.handle_message("REACTIONS_EMPTY")

    reactions = getattr(full_msg, "reactions", None)

    if not reactions or not reactions.results:
        return await m.handle_message("REACTIONS_EMPTY")

    text = "<b>📊 Reaction Stats:</b>\n\n"
    total = 0
    for result in reactions.results:
        r = result.reaction
        emoji = getattr(r, "emoticon", "?")
        count = result.count
        chosen = " ✓" if result.chosen_order is not None else ""
        text += f"  {emoji} — <b>{count}</b>{chosen}\n"
        total += count
    text += f"\n<b>Total:</b> {total}"

    await m.handle_message(text)
