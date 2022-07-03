# Copyright (C) 2021-present by Altruix@Github, < https://github.com/Altruix >.
#
# This file is part of < https://github.com/Altruix/Altruix > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/Altriux/Altruix/blob/main/LICENSE >
#
# All rights reserved.

import os
import math
import ffmpeg
from PIL import Image
from Main import Altruix
from typing import Union
from pyrogram import Client, raw
from pyrogram.file_id import FileId
from hachoir.parser import createParser
from ...core.types.message import Message
from ...utils.file_helpers import run_in_exc
from hachoir.metadata import extractMetadata
from pyrogram.types import Message as Rmessage
from pyrogram.errors.exceptions.bad_request_400 import PeerIdInvalid


@run_in_exc
def convertor_(input_file: str, w: int, h: int):
    out_file = f"{os.path.splitext(input_file)[0]}.webm"
    ffmpeg.input(input_file).output(
        out_file,
        vcodec="libvpx-vp9",
        pix_fmt="yuv420p",
        crf=28,
        preset="veryfast",
        vf=f"scale={h}:{w}",
        ss="0:00:00",
        to="0:00:03",
        loglevel="error",
    ).overwrite_output().run()
    if os.path.exists(input_file):
        os.remove(input_file)
    return out_file


async def convert_(input_file):
    w, h = await decide_file_dem(input_file)
    return await convertor_(input_file, w, h)


@run_in_exc
def decide_file_dem(input_file: str):
    metadata = extractMetadata(createParser(input_file))
    if metadata.has("width") and metadata.has("height"):
        if metadata.get("width") > metadata.get("height"):
            return (-2, 512)
        elif metadata.get("width") < metadata.get("height"):
            return (512, -2)
        return (512, 512)
    return (512, -2)


@Altruix.run_in_exc
def decode_file_id(file_id):
    file_id_ = FileId.decode(file_id)
    return raw.types.InputDocument(
        id=file_id_.media_id,
        access_hash=file_id_.access_hash,
        file_reference=file_id_.file_reference,
    )


async def getstickerfromcollection(name_: str):
    try:
        return await Altruix.bot.invoke(
            raw.functions.messages.GetStickerSet(
                stickerset=raw.types.InputStickerSetShortName(short_name=name_),
                hash=0,
            )
        )
    except Exception:
        return None


@Altruix.run_in_exc
def resize_image(image):
    im = Image.open(image)
    if (im.width and im.height) < 512:
        size1 = im.width
        size2 = im.height
        if im.width > im.height:
            scale = 512 / size1
            size1new = 512
            size2new = size2 * scale
        else:
            scale = 512 / size2
            size1new = size1 * scale
            size2new = 512
        size1new = math.floor(size1new)
        size2new = math.floor(size2new)
        sizenew = (size1new, size2new)
        im = im.resize(sizenew)
    else:
        maxsize = (512, 512)
        im.thumbnail(maxsize)
    file_name = "kenged_sticker.png"
    im.save(file_name, "PNG")
    if os.path.exists(image):
        os.remove(image)
    return file_name


cached_peer = {}


@Altruix.register_on_cmd(
    ["kang", "steal"],
    requires_reply=True,
    cmd_help={"help": "Kang any sticker with just a cmd!", "example": "kang 😁"},
)
async def kang_fun(c: Client, m: Union[Message, Rmessage]):
    pack_ = 0
    msg = await m.handle_message("PROCESSING")
    try:
        if m.from_user.id in cached_peer:
            peer_ = cached_peer.get(m.from_user.id) or cached_peer.get(m.from_user.id)
        else:
            peer_ = await Altruix.bot.resolve_peer(m.from_user.id)
            cached_peer[m.from_user.id] = peer_
    except (KeyError, PeerIdInvalid):
        return await msg.edit_msg(
            "START_YOUR_ASSISTANT", string_args=(Altruix.bot_info.username)
        )
    user_input = m.user_input
    emoji = user_input or "😁"
    if m.reply_to_message.sticker and m.reply_to_message.sticker.emoji:
        emoji = m.reply_to_message.sticker.emoji
    if m.reply_to_message.photo or (
        m.reply_to_message.document
        and c.guess_mime_type(m.reply_to_message.document.file_name).startswith(
            "image/"
        )
    ):
        photo_ = await m.reply_to_message.download()
        type_ = ""
        sticker_name = ""
        sticker_limit = 120
        new_photo = await resize_image(photo_)
        file_ = await Altruix.bot.upload_doc(new_photo, peer_)
    elif m.reply_to_message.video or m.reply_to_message.animation:
        down_ = await convert_(await m.reply_to_message.download())
        type_ = "webm"
        sticker_name = "VideoStickers"
        sticker_limit = 50
        file_ = await Altruix.bot.upload_doc(down_, peer_, force_file=True)
    elif m.reply_to_message.sticker:
        if m.reply_to_message.sticker.is_animated:
            type_ = "tgs"
            sticker_name = "Animated"
            sticker_limit = 50
            down_ = await m.reply_to_message.download()
            file_ = await Altruix.bot.upload_doc(down_, peer_, force_file=True)
        if m.reply_to_message.sticker.is_video:
            type_ = "webm"
            sticker_name = "VideoStickers"
            sticker_limit = 50
            down_ = await m.reply_to_message.download()
            file_ = await Altruix.bot.upload_doc(down_, peer_, force_file=True)
        else:
            type_ = ""
            sticker_name = ""
            sticker_limit = 120
            file_ = await decode_file_id(m.reply_to_message.sticker.file_id)
    else:
        return await msg.edit_msg("INVALID_REPLY")
    sticker = raw.types.InputStickerSetItem(document=file_, emoji=emoji)
    my_name = (
        f"@{m.from_user.username}"
        if m.from_user.username
        else f"{m.from_user.first_name}"
    )
    while True:
        pack_ += 1
        pack_m = f"altruix_{m.from_user.id}" + (
            f"_{sticker_name.lower()}" if sticker_name != "" else ""
        )
        pack_m += f"_{pack_}_by_{Altruix.bot_info.username}"
        title = f"{my_name}'s " + (
            f"{sticker_name.title()} " if sticker_name != "" else ""
        )
        title += f"Pack Vol {pack_}"
        stick_ = await getstickerfromcollection(pack_m)
        if not stick_:
            stick_ = await Altruix.bot.invoke(
                raw.functions.stickers.CreateStickerSet(
                    user_id=peer_,
                    title=title,
                    short_name=pack_m,
                    stickers=[sticker],
                    animated=type_ == "tgs",
                    videos=type_ == "webm",
                )
            )

            break
        elif stick_.set.count and stick_.set.count >= sticker_limit:
            await msg.edit_msg("MAX_STICKER_DONE", string_args=(title, pack_ + 1))
            continue
        else:
            await Altruix.bot.invoke(
                raw.functions.stickers.AddStickerToSet(
                    stickerset=raw.types.InputStickerSetShortName(
                        short_name=stick_.set.short_name
                    ),
                    sticker=sticker,
                )
            )
        break
    pack_m = f"https://t.me/addstickers/{pack_m}"
    await msg.edit_msg("STICKER_KANGED", string_args=(pack_m, title))


@Altruix.register_on_cmd(
    ["stickerpacks", "sp", "msp"],
    cmd_help={
        "help": "get all your packs that you have kanged.",
        "example": "sp -animated",
        "_args": {"animated": "Show animated packs", "vs": "Show video stickers"},
    },
)
async def get_pack_(c: Client, m: Message):
    msg = await m.handle_message("PROCESSING")
    if "-animated" in m.user_args:
        type_ = "Animated"
    elif "-vs" in m.user_args:
        type_ = "VideoStickers"
    else:
        type_ = ""
    str_type = f"{type_} " if type_ != "" else type_
    final_text = f"<b>Your {str_type}" + "Sticker Packs :</b> \n"
    pack_ = 0
    while True:
        pack_ += 1
        my_name = (
            f"@{m.from_user.username}"
            if m.from_user.username
            else f"{m.from_user.first_name}"
        )
        pack_m = f"altruix_{str(m.from_user.id)}" + (
            f"_{type_.lower()}" if type_ != "" else ""
        )
        pack_m += f"_{pack_}_by_{Altruix.bot_info.username}"
        title = f"{my_name}'s " + (f"{type_.title()} " if type_ != "" else "")
        title += f"Pack Vol {pack_}"
        stick_ = await getstickerfromcollection(pack_m)
        if pack_ == 1 and not stick_:
            final_text = None
            break
        if stick_:
            no_of_stickers = stick_.set.count
            pack_url = f"https://t.me/addstickers/{pack_m}"
            final_text += f"\n✪ <a href='{pack_url}'>{title}</a> [Sticker Count : {no_of_stickers}]"
            continue
        break
    if final_text is None:
        return await msg.edit_msg("NO_PACKS_FOUND")
    await msg.edit_msg(final_text)
