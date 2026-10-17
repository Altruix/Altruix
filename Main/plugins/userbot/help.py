# Copyright (C) 2021-present by Altruix@Github, < https://github.com/Altruix >.
#
# This file is part of < https://github.com/Altruix/Altruix > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/Altriux/Altruix/blob/main/LICENSE >
#
# All rights reserved.

import html
import asyncio
import logging
from difflib import get_close_matches
from telethon import errors

from Main import Altruix
from Main.core.types import AltruixTelegramClient as Client
from Main.core.types.message import Message

logger = logging.getLogger("altruix.help")


@Altruix.register_on_cmd(
    ["lang", "language", "set language"], bot_mode_unsupported=True
)
async def lang_modify(c: Client, m: Message):
    rm = m.reply_to_message
    if not getattr(Altruix, "bot_info", None):
        return await m.handle_message("Assistant bot is not configured or running.")
    try:
        results = await c.get_inline_bot_results(Altruix.bot_info.username, "change_lang")
        if results:
            await results[0].click(m.chat.id, reply_to=rm.id if rm else m.id)
            return await m.delete_if_self()
    except Exception as e:
        logger.warning(f"Language modify inline failed: {e}")
        return await m.handle_message(f"Failed to open language wizard: {e}")


@Altruix.register_on_cmd(
    ["help"],
    bot_mode_unsupported=True,
    cmd_help={
        "help": "Display the interactive inline help menu or text help for a specific plugin.",
        "example": "help or help -basic or help paste",
        "user_args": [
            {
                "arg": "basic",
                "help": "Force text-based help menu without invoking inline assistant bot.",
                "requires_input": False,
            }
        ],
    },
)
async def help_normal(c: Client, m: Message):
    cmd_lists = Altruix._command_help_message_data
    user_input = m.user_input
    chat = m.chat_id or (getattr(m.chat, "id", None))
    rm = m.reply_to_message or (await m.get_reply_message() if hasattr(m, "get_reply_message") else None)
    is_bot = getattr(c.myself, "bot", getattr(c.myself, "is_bot", False)) if getattr(c, "myself", None) else False

    bot_reason = None

    if is_bot:
        bot_reason = "Running as bot account, skipping inline menu."
    elif "-basic" in m.user_args:
        bot_reason = "Flag -basic passed, using text menu."
    elif not getattr(Altruix, "bot_info", None):
        bot_reason = "Assistant bot is not running (BOT_TOKEN missing, invalid, or assistant failed to login)."
        logger.warning(f"[.help] {bot_reason}")
    else:
        bot_username = getattr(Altruix.bot_info, "username", None)
        if not bot_username:
            bot_reason = "Assistant bot has no public username set."
            logger.warning(f"[.help] {bot_reason}")
        else:
            try:
                results = await c.get_inline_bot_results(bot_username, "help")
                if results:
                    await results[0].click(chat, reply_to=rm.id if rm else m.id)
                    return await m.delete_if_self()
                else:
                    bot_reason = f"Inline query to @{bot_username} returned 0 results. Check bot authorization and inline handlers."
                    logger.warning(f"[.help] {bot_reason}")
            except errors.BotInlineDisabledError:
                bot_reason = "BotInlineDisabledError: Inline mode is disabled for the assistant bot on Telegram."
                logger.warning(f"[.help] {bot_reason} Attempting auto-setup via @BotFather...")
                try:
                    from Main.internals.set_inline import set_inline_in_botfather
                    await set_inline_in_botfather(c)
                    await asyncio.sleep(1)
                    results = await c.get_inline_bot_results(bot_username, "help")
                    if results:
                        await results[0].click(chat, reply_to=rm.id if rm else m.id)
                        return await m.delete_if_self()
                except Exception as exc:
                    bot_reason = f"Auto-setting inline on @BotFather failed: {exc}. Please send /setinline to @BotFather manually."
                    logger.warning(f"[.help] {bot_reason}")
            except errors.ChatSendInlineForbiddenError:
                bot_reason = "ChatSendInlineForbiddenError: Inline bots are forbidden by permissions in this chat."
                logger.warning(f"[.help] {bot_reason}")
            except errors.YouBlockedUserError:
                bot_reason = f"YouBlockedUserError: You have blocked your assistant bot @{bot_username}."
                logger.warning(f"[.help] {bot_reason}")
            except Exception as e:
                bot_reason = f"Inline help failed ({e.__class__.__name__}): {e}"
                logger.error(f"[.help] {bot_reason}", exc_info=True)

    # Text menu fallback or direct plugin help
    notice = f"⚠️ <i>Inline menu unavailable: {html.escape(bot_reason)}</i>\n\n" if bot_reason and "-basic" not in m.user_args and not is_bot else ""

    if user_input and cmd_lists.get(user_input.lower()):
        await m.handle_message(
            f"{notice}<b>Help for</b> <code>{user_input}</code>\n\n{cmd_lists[user_input.lower()].strip()}"
        )
    elif not user_input:
        cmd_list = f"{notice}<i><b>Plugins Available:</b></i>\n\n"
        for plugins in sorted(cmd_lists.keys()):
            cmd_list += f"<code>{plugins}</code>  "
        cmd_list += f"\n\n<i>Use</i> <code>{Altruix.user_command_handler}help &lt;plugin&gt;</code> <i>to know more!</i>"
        await m.handle_message(cmd_list)
    else:
        matches = get_close_matches(user_input.lower(), cmd_lists.keys(), n=4, cutoff=0.3)
        if matches:
            preds = ", ".join(f"<code>{i}</code>" for i in matches)
            return await m.handle_message(
                f"{notice}<i>Command not found in the list, did you mean?</i> : {preds}"
            )
        await m.handle_message(f"{notice}<i>This command is not in the command list!</i>")
