# Copyright (C) 2021-present by Altruix@Github, < https://github.com/Altruix >.
#
# This file is part of < https://github.com/Altruix/Altruix > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/Altriux/Altruix/blob/main/LICENSE >
#
# All rights reserved.

import re
import asyncio
import logging
import contextlib
from Main import Altruix
from Main.utils.suppress import suppress_error
from Main.core.decorators import log_errors
from Main.utils.custom_filters import filters
from telethon import errors, functions, types
from telethon.sessions import StringSession
from Main.core.types.client import AltruixTelegramClient


async def client_session(api_id: int, api_hash: str) -> AltruixTelegramClient:
    return AltruixTelegramClient(StringSession(), api_id=int(api_id), api_hash=str(api_hash))


@Altruix.bot.on_callback_query(filters.regex("^session_no"))
@log_errors
async def add_session_cb_handler(_, cb):
    with suppress_error(msg="Deleting session_no callback message"):
        await cb.delete()

    api_id = Altruix.config.API_ID
    api_hash = Altruix.config.API_HASH

    if not api_id or not api_hash:
        await Altruix.bot.send_message(cb.chat_id, "API_ID or API_HASH is not set in config.")
        return

    # Wait for phone number via conversation
    async with Altruix.bot.conversation(cb.chat_id, timeout=120) as conv:
        phone_prompt = await conv.send_message(
            "Alright... Please send your phone number with country code (e.g. +1234567890).\n\n"
            "Use /cancel to cancel the current operation."
        )
        resp = await conv.get_response(phone_prompt)
        phone_number = resp.raw_text.strip()
        if phone_number == "/cancel":
            await conv.send_message("Current process was cancelled.")
            return

        process_msg = await conv.send_message("Connecting to Telegram...")
        app = await client_session(api_id, api_hash)
        await app.connect()

        try:
            sent_code = await app.send_code_request(phone_number)
        except errors.FloodWaitError as e:
            await process_msg.edit(f"Floodwait: please wait {e.seconds} seconds.")
            await app.disconnect()
            return
        except errors.PhoneNumberInvalidError:
            await process_msg.edit("Invalid phone number format. Please check and try again.")
            await app.disconnect()
            return
        except errors.ApiIdInvalidError:
            await process_msg.edit("Invalid API ID or Hash.")
            await app.disconnect()
            return

        code_prompt = await conv.send_message(
            "Code sent!\n\n"
            "⚠️ <b>CRITICAL TELEGRAM NOTICE:</b> Telegram's security scanner automatically cancels login codes sent as plain numbers in chat.\n\n"
            "To prevent your code from expiring, <b>send it with letters between each number</b>:\n"
            "👉 If your code is <code>12345</code>, send: <code>x1x2x3x4x5</code> or <code>1a2b3c4d5</code>\n\n"
            "<i>(Or send /cancel and generate your session securely in terminal: <code>py -3 Main/scripts/session_gen.py</code>)</i>",
            parse_mode="html",
        )
        code_resp = await conv.get_response(code_prompt)
        raw_code = code_resp.raw_text.strip()
        if raw_code == "/cancel":
            await conv.send_message("Action cancelled.")
            await app.disconnect()
            return

        code_text = "".join(re.findall(r"\d", raw_code))
        if not code_text:
            await conv.send_message("No valid digits found in your input. Process cancelled.")
            await app.disconnect()
            return

        try:
            await app.sign_in(phone_number, code=code_text, phone_code_hash=sent_code.phone_code_hash)
        except errors.SessionPasswordNeededError:
            pwd_prompt = await conv.send_message("Account has 2FA enabled. Please enter your password:")
            pwd_resp = await conv.get_response(pwd_prompt)
            if pwd_resp.raw_text == "/cancel":
                await conv.send_message("Action cancelled.")
                await app.disconnect()
                return
            try:
                await app.sign_in(password=pwd_resp.raw_text.strip())
            except Exception as e:
                await conv.send_message(f"Password verification failed: {e}")
                await app.disconnect()
                return
        except Exception as e:
            await conv.send_message(f"Login failed: {e}\n\n💡 Try generating your session in terminal via: <code>py -3 Main/scripts/session_gen.py</code>", parse_mode="html")
            await app.disconnect()
            return

        session_str = app.session.save()
        with suppress_error(msg="Sending string session to me"):
            await app.send_message(
                "me",
                f"**Altruix Telethon String Session**\n\n`{session_str}`\n\n"
                "Keep this safe! Do not share it.",
            )
        await app.disconnect()

        status_msg = await conv.send_message("Session generated! Registering with Altruix...")
        await Altruix.add_session(session_str, status_msg)
