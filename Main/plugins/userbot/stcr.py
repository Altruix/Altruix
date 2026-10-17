# Copyright (C) 2021-present by Altruix@Github, < https://github.com/Altruix >.
#
# This file is part of < https://github.com/Altruix/Altruix > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/Altriux/Altruix/blob/main/LICENSE >
#
# All rights reserved.

import os
import time
import math
import shutil
import asyncio
from PIL import Image
from Main import Altruix
from typing import Union, Optional, Tuple
from telethon import functions, types, errors, utils
from Main.core.types import AltruixTelegramClient as Client
from Main.core.types.message import Message
from Main.utils.file_helpers import run_in_exc
from Main.utils.suppress import suppress_error

TEMP_DIR = os.path.abspath("./temp")
os.makedirs(TEMP_DIR, exist_ok=True)


@run_in_exc
def convertor_(input_file: str, w: int, h: int) -> str:
    """Convert raw video to webm sticker using ffmpeg if installed."""
    if not shutil.which("ffmpeg"):
        raise RuntimeError("FFmpeg is not installed on this system.")
    import subprocess
    out_file = f"{os.path.splitext(input_file)[0]}.webm"
    cmd = [
        "ffmpeg", "-y",
        "-ss", "0:00:00", "-to", "0:00:03",
        "-i", input_file,
        "-vf", f"scale={h}:{w}",
        "-c:v", "libvpx-vp9",
        "-pix_fmt", "yuv420p",
        "-crf", "28",
        "-loglevel", "error",
        out_file,
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if os.path.exists(input_file):
        os.remove(input_file)
    return out_file


async def convert_(input_file: str) -> str:
    w, h = await decide_file_dem(input_file)
    return await convertor_(input_file, w, h)


@run_in_exc
def decide_file_dem(input_file: str) -> Tuple[int, int]:
    try:
        from hachoir.parser import createParser
        from hachoir.metadata import extractMetadata
        metadata = extractMetadata(createParser(input_file))
        if metadata and metadata.has("width") and metadata.has("height"):
            if metadata.get("width") > metadata.get("height"):
                return (-2, 512)
            elif metadata.get("width") < metadata.get("height"):
                return (512, -2)
            return (512, 512)
    except Exception:
        pass
    return (512, -2)


async def getstickerfromcollection(name_: str):
    try:
        target_client = Altruix.bot or (Altruix.clients[0] if Altruix.clients else None)
        if not target_client:
            return None
        return await target_client.invoke(
            functions.messages.GetStickerSetRequest(
                stickerset=types.InputStickerSetShortName(short_name=name_),
                hash=0,
            )
        )
    except Exception:
        return None


@Altruix.run_in_exc
def resize_image(image_path: str) -> str:
    """Resize photo to fit Telegram sticker dimensions (512x512 max, one side exactly 512)."""
    if not image_path or not os.path.exists(image_path):
        raise ValueError(f"Invalid image file for sticker conversion: {image_path}")
    im = Image.open(image_path)
    if im.width < 512 and im.height < 512:
        if im.width > im.height:
            scale = 512 / im.width
            sizenew = (512, math.floor(im.height * scale))
        else:
            scale = 512 / im.height
            sizenew = (math.floor(im.width * scale), 512)
        im = im.resize(sizenew, Image.Resampling.LANCZOS)
    else:
        im.thumbnail((512, 512), Image.Resampling.LANCZOS)

    out_file = os.path.join(TEMP_DIR, f"kanged_sticker_{int(time.time() * 1000)}.png")
    im.save(out_file, "PNG")
    if os.path.exists(image_path) and image_path != out_file:
        os.remove(image_path)
    return out_file


cached_peer = {}


@Altruix.register_on_cmd(
    ["kang", "steal"],
    requires_reply=True,
    cmd_help={
        "help": "Kang any sticker (static, animated, or video) or photo into your pack!",
        "example": "kang 😁",
        "user_args": [
            {"arg": "pack", "help": "Custom pack name volume.", "requires_input": True},
        ],
    },
)
async def kang_fun(c: Client, m: Message):
    msg = await m.handle_message("PROCESSING")
    if not Altruix.bot or not getattr(Altruix, "bot_info", None):
        return await msg.edit_msg("❌ Assistant bot is not active. Please set <code>BOT_TOKEN</code> to use kang.")

    user_id = m.sender_id or (getattr(m.from_user, "id", None) if m.from_user else getattr(c.myself, "id", 0))
    bot_username = getattr(Altruix.bot_info, "username", "AssistantBot")

    if user_id in cached_peer:
        peer_ = cached_peer.get(user_id)
    else:
        try:
            peer_ = await Altruix.bot.resolve_peer(user_id)
        except Exception:
            try:
                bot_entity = await c.get_entity(bot_username)
                await c.send_message(bot_entity, "/start")
                await asyncio.sleep(1)
                peer_ = await Altruix.bot.resolve_peer(user_id)
            except Exception:
                return await msg.edit_msg(
                    "START_YOUR_ASSISTANT", string_args=(bot_username)
                )
        cached_peer[user_id] = peer_

    rm = m.reply_to_message or (await m.get_reply_message() if hasattr(m, "get_reply_message") else None)
    if not rm:
        return await msg.edit_msg("INVALID_REPLY")

    user_input = m.user_input.strip() if m.user_input else ""
    emoji = user_input or "😁"

    # Identify media type
    doc = getattr(rm.media, "document", None) or getattr(rm, "document", None)
    is_sticker = bool(getattr(rm, "sticker", None)) or (
        bool(doc) and any(
            isinstance(attr, types.DocumentAttributeSticker)
            for attr in getattr(doc, "attributes", [])
        )
    )

    # Auto-extract sticker emoji if not manually specified
    if is_sticker and not user_input and doc:
        for attr in getattr(doc, "attributes", []):
            if isinstance(attr, types.DocumentAttributeSticker) and attr.alt:
                emoji = attr.alt
                break

    temp_cleanup_files = []
    file_ = None

    try:
        # CASE 1: Replied message is ALREADY A STICKER (Static, Animated, or Video)
        # MTProto allows passing the existing InputDocument directly without re-uploading or FFmpeg!
        if is_sticker and doc:
            file_ = types.InputDocument(
                id=doc.id,
                access_hash=doc.access_hash,
                file_reference=doc.file_reference,
            )

        # CASE 2: Replied message is a PHOTO or static IMAGE DOCUMENT
        elif (
            rm.photo
            or (rm.document and getattr(rm, "file", None) and getattr(rm.file, "mime_type", "").startswith("image/"))
        ):
            temp_dl = os.path.join(TEMP_DIR, f"raw_photo_{int(time.time() * 1000)}.jpg")
            photo_path = await c.download_media(rm, file=temp_dl)
            if not photo_path or not os.path.exists(photo_path):
                return await msg.edit_msg("Failed to download image from replied message.")
            temp_cleanup_files.append(photo_path)
            resized = await resize_image(photo_path)
            temp_cleanup_files.append(resized)
            file_ = await Altruix.bot.upload_doc(resized, peer_)

        # CASE 3: Replied message is a raw non-sticker VIDEO or GIF
        elif rm.video or (rm.document and getattr(rm, "file", None) and getattr(rm.file, "mime_type", "").startswith("video/")):
            if not shutil.which("ffmpeg"):
                return await msg.edit_msg(
                    "❌ <b>FFmpeg is required</b> to convert raw videos/GIFs into video stickers.\n\n"
                    "<i>Note: You can already kang any existing sticker (animated, video, or static) directly without FFmpeg!</i>"
                )
            temp_vid = os.path.join(TEMP_DIR, f"raw_vid_{int(time.time() * 1000)}.mp4")
            dl_path = await c.download_media(rm, file=temp_vid)
            if not dl_path or not os.path.exists(dl_path):
                return await msg.edit_msg("Failed to download video file.")
            temp_cleanup_files.append(dl_path)
            converted = await convert_(dl_path)
            temp_cleanup_files.append(converted)
            file_ = await Altruix.bot.upload_doc(converted, peer_, force_file=True)

        elif doc:
            file_ = types.InputDocument(
                id=doc.id,
                access_hash=doc.access_hash,
                file_reference=doc.file_reference,
            )
        else:
            return await msg.edit_msg("❌ <b>Unsupported media.</b> Please reply to a sticker, photo, image, or video.")

        sticker = types.InputStickerSetItem(document=file_, emoji=emoji)

        from_user = m.from_user
        username = getattr(from_user, "username", None) if from_user else getattr(c.myself, "username", None)
        first_name = getattr(from_user, "first_name", None) if from_user else getattr(c.myself, "first_name", "User")
        my_name = f"@{username}" if username else f"{first_name}"
        user_num_id = user_id or getattr(c.myself, "id", 0)

        # Telegram supports mixed sticker sets (static, animated, and video in the same pack)
        sticker_limit = 120
        pack_ = 0

        while True:
            pack_ += 1
            pack_m = f"altruix_{user_num_id}_{pack_}_by_{bot_username}"
            title = f"{my_name}'s Pack Vol {pack_}"

            stick_ = await getstickerfromcollection(pack_m)
            if not stick_:
                await Altruix.bot.invoke(
                    functions.stickers.CreateStickerSetRequest(
                        user_id=utils.get_input_user(peer_),
                        title=title,
                        short_name=pack_m,
                        stickers=[sticker],
                    )
                )
                break
            count_val = getattr(getattr(stick_, "set", None), "count", None)
            if isinstance(count_val, int) and count_val >= sticker_limit:
                continue
            else:
                try:
                    await Altruix.bot.invoke(
                        functions.stickers.AddStickerToSetRequest(
                            stickerset=types.InputStickerSetShortName(
                                short_name=stick_.set.short_name
                            ),
                            sticker=sticker,
                        )
                    )
                    break
                except (
                    errors.StickersTooMuchError,
                    errors.StickerpackStickersTooMuchError,
                    errors.StickerPngNopngError,
                    errors.StickerTgsNotgsError,
                    errors.StickerVideoNowebmError,
                ):
                    # If older pack cannot accept this type or reached limit, advance to next volume
                    continue

        pack_url = f"https://t.me/addstickers/{pack_m}"
        await msg.edit_msg("STICKER_KANGED", string_args=(pack_url, title))

    finally:
        for f in temp_cleanup_files:
            if os.path.exists(f):
                with suppress_error(msg="Cleaning up temporary sticker file"):
                    os.remove(f)


@Altruix.register_on_cmd(
    ["stickerpacks", "sp", "msp"],
    cmd_help={
        "help": "Get all your sticker packs that you have kanged.",
        "example": "sp",
    },
)
async def get_pack_(c: Client, m: Message):
    msg = await m.handle_message("PROCESSING")
    final_text = "<b>Your Sticker Packs:</b>\n"
    pack_ = 0
    from_user = m.from_user
    username = getattr(from_user, "username", None) if from_user else getattr(c.myself, "username", None)
    first_name = getattr(from_user, "first_name", None) if from_user else getattr(c.myself, "first_name", "User")
    my_name = f"@{username}" if username else f"{first_name}"
    user_num_id = getattr(from_user, "id", None) or m.sender_id or getattr(c.myself, "id", 0)
    bot_username = getattr(Altruix.bot_info, "username", "AssistantBot") if Altruix.bot_info else "AssistantBot"

    found_any = False
    while True:
        pack_ += 1
        pack_m = f"altruix_{user_num_id}_{pack_}_by_{bot_username}"
        title = f"{my_name}'s Pack Vol {pack_}"
        stick_ = await getstickerfromcollection(pack_m)
        if not stick_:
            # Also check legacy named packs
            stick_legacy = await getstickerfromcollection(f"altruix_{user_num_id}_animated_{pack_}_by_{bot_username}")
            if stick_legacy:
                stick_ = stick_legacy
                pack_m = f"altruix_{user_num_id}_animated_{pack_}_by_{bot_username}"
                title = f"{my_name}'s Animated Pack Vol {pack_}"

        if not stick_:
            break

        found_any = True
        no_of_stickers = stick_.set.count
        pack_url = f"https://t.me/addstickers/{pack_m}"
        final_text += f"\n✪ <a href='{pack_url}'>{title}</a> [Stickers: <code>{no_of_stickers}</code>]"

    if not found_any:
        return await msg.edit_msg("NO_PACKS_FOUND")
    await msg.edit_msg(final_text)
