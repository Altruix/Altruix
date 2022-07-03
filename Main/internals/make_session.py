# Copyright (C) 2021-present by Altruix@Github, < https://github.com/Altruix >.
#
# This file is part of < https://github.com/Altruix/Altruix > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/Altriux/Altruix/blob/main/LICENSE >
#
# All rights reserved.


import asyncio
import contextlib
import logging
from Main import Altruix
from pyrogram import Client, filters
from pyrogram.types import (
    Message, ForceReply, CallbackQuery, KeyboardButton, ReplyKeyboardMarkup,
    ReplyKeyboardRemove)
from pyrogram.errors import (
    FloodWait, ApiIdInvalid, UsernameInvalid, PhoneCodeExpired,
    PhoneCodeInvalid, UsernameOccupied, PhoneNumberInvalid,
    UsernameNotModified, SessionPasswordNeeded)


async def client_session(api_id, api_hash):
    return Client(
        "new_session", api_id=int(api_id), api_hash=str(api_hash), in_memory=True
    )


@Altruix.bot.on_callback_query(filters.regex("^session_no"))
async def add_session_cb_handler(_, cb: CallbackQuery):
    with contextlib.suppress(Exception):
        await cb.message.delete()
    await cb.message.reply(
        "Alright... Please share your contact with me for fetching your phone number.\n<i>This instance of Altruix solely belongs to you so you don't have to worry over your data.</i>\n\nUse /cancel to cancel the current operation.",
        reply_markup=ReplyKeyboardMarkup(
            [[KeyboardButton("Share Contact", request_contact=True)]],
            resize_keyboard=True,
            one_time_keyboard=True,
        ),
    )
    while True:
        response: Message = await cb.from_user.listen(timeout=60)
        if response.contact:
            phone_number = response.contact.phone_number
            Altruix.log(f"{phone_number=}", level=logging.DEBUG)
            break
        elif response.text == "/cancel":
            await cb.message.reply(
                "Current process was canceled.", reply_markup=ReplyKeyboardRemove()
            )
            return
        await response.reply("invalid message type. Please try again.", quote=True)
    process_msg = await response.reply(
        "<i>Please wait till I make a session for this account!</i>"
    )

    try:
        app = await client_session(
            api_id=Altruix.config.API_ID, api_hash=Altruix.config.API_HASH
        )
    except Exception as err:
        await process_msg.reply(f"Something went wrong!\n{err}")
        await process_msg.delete()
        return
    try:
        await app.connect()
    except ConnectionError:
        await app.disconnect()
        await app.connect()
    try:
        sent_code = await app.send_code(phone_number)
    except FloodWait as e:
        await process_msg.reply(
            f"Couldn't create a session!.\nYou have a floodwait of <code>{e.x} seconds</code>."
        )
        await process_msg.delete()
        return
    except PhoneNumberInvalid:
        await process_msg.reply(
            "Telegram says that the phone number that you've given in invalid.\nhmm... strange"
        )
        await process_msg.delete()
        return
    except ApiIdInvalid:
        await process_msg.reply(
            "Telegram says that the API ID that you've given in invalid.\nhmm... strange"
        )
        await process_msg.delete()
        return
    ans = await cb.from_user.ask(
        "Now, Send me your code in the format <code>1-2-3-4-5</code> and not <code>12345</code>",
        reply_markup=ForceReply(selective=True),
    )
    await process_msg.delete()
    if ans.text == "/cancel":
        await process_msg.reply("Cancelled the current action!", quote=True)
        return
    try:
        await app.sign_in(phone_number, sent_code.phone_code_hash, ans.text)
    except SessionPasswordNeeded:
        await asyncio.sleep(3)
        ans = await cb.from_user.ask(
            "The entered Telegram Number is protected with 2FA. Please enter your second factor authentication code.\n<i>This message will only be used for generating your string session, and will never be used for any other purposes than for which it is asked.</i>",
            reply_markup=ForceReply(selective=True),
            filters=filters.text,
        )
        if ans.text == "/cancel":
            await process_msg.reply("Cancelled the current action!", quote=True)
            return
        try:
            await app.check_password(ans.text)
        except Exception as err:
            await ans.reply(f"Something went wrong!\n{err}")
            return
    except PhoneCodeInvalid:
        await ans.reply("The code you sent seems Invalid, Try again.")
        return
    except PhoneCodeExpired:
        await ans.reply("The Code you sent seems Expired. Try again.")
        return
    if (await app.get_me()).username is None:
        ask_name = await cb.from_user.ask(
            "Perfect! now send me a username for this account without '@'\nYou can also /skip this step",
            reply_markup=ForceReply(selective=True),
        )
        while True:
            try:
                if ask_name.text.lower == "/skip":
                    break
                username = ask_name.text.replace(" ", "_")[:32].lstrip("@")
                if len(username) < 5:
                    await cb.from_user.ask("This username too short.. send again")
                else:
                    await app.set_username(username=username)
                    break
            except UsernameOccupied:
                ask_name = await cb.from_user.ask(
                    "This username is occupied.. send again"
                )
            except UsernameInvalid:
                ask_name = await cb.from_user.ask(
                    "This username is invalid.. send again"
                )
            except UsernameNotModified:
                break
    try:
        app_session = await app.export_session_string()
    except Exception:
        Altruix.log(level=40)
        await ans.reply("Something went wrong!")
        return
    await app.send_message(
        "me",
        f"<b>The session for this account.</b>\n<code>{app_session}</code>\n\n<b>Note:</b> Do not share this session with anyone. With this, they can easily login to your account.\n(c) @AltruixUB",
    )
    status_msg = await process_msg.reply("<code>Processing..</code>")
    try:
        await Altruix.add_session(app_session, status_msg)
    except Exception:
        Altruix.log(level=40)
        await status_msg.edit("Something went wrong!")
