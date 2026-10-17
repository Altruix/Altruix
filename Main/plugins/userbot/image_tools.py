# Copyright (C) 2021-present by Altruix@Github, < https://github.com/Altruix >.
#
# This file is part of < https://github.com/Altruix/Altruix > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/Altriux/Altruix/blob/main/LICENSE >
#
# All rights reserved.

import os
import time
from os import remove
from Main import Altruix
from random import choice
from os.path import exists
from pathlib import Path
from Main.core.types import AltruixTelegramClient as Client, Message
from time import perf_counter as pc
from PIL import Image, ImageDraw, ImageFont


colours = [
    (255, 0, 0),
    (255, 64, 0),
    (255, 128, 0),
    (255, 191, 0),
    (255, 255, 0),
    (191, 255, 0),
    (128, 255, 0),
    (64, 255, 0),
    (0, 255, 0),
    (0, 255, 64),
    (0, 255, 128),
    (0, 255, 191),
    (0, 255, 255),
    (0, 191, 255),
    (0, 128, 255),
    (0, 64, 255),
    (0, 0, 255),
    (64, 0, 255),
    (128, 0, 255),
    (191, 0, 255),
    (255, 0, 255),
    (255, 0, 191),
    (255, 0, 128),
    (255, 0, 64),
    (255, 0, 0),
]


def isValidRGB(RGB):
    RGB = RGB.split(" ")
    if len(RGB) < 3:
        return False, ()
    R, G, B = RGB[0], RGB[1], RGB[2]
    if (not R.isnumeric()) | (not G.isnumeric()) | (not B.isnumeric()):
        return False, ()
    R, G, B = int(R), int(G), int(B)
    if R < 0 or R > 255:
        return False, ()
    if G < 0 or G > 255:
        return False, ()
    if B < 0 or B > 255:
        return False, ()
    return True, (R, G, B)


def splitter(input_):
    input_ = input_.split("|")
    len_ = len(input_)
    if len_ == 1:
        return (
            ("Altruix", 500, choice(colours))
            if input_[0] == ""
            else (input_[0], 500, choice(colours))
        )
    elif len_ == 2:
        if input_[0] == "":
            return "Altruix", 500, choice(colours)
        if input_[1].isnumeric():
            return input_[0], int(input_[1]), choice(colours)
        return input_[0], 500, choice(colours)
    if input_[0] == "":
        return "Altruix", 500, choice(colours)
    if not input_[1].isnumeric():
        return (
            input_[0],
            500,
            isValidRGB(input_[2])[1] if isValidRGB(input_[2]) else choice(colours),
        )
    return (
        input_[0],
        int(input_[1]),
        isValidRGB(input_[2])[1] if isValidRGB(input_[2]) else choice(colours),
    )


@Altruix.register_on_cmd(
    ["logo"],
    cmd_help={
        "help": "Makes logo frong given text.",
        "example": "logo Altruix|1000|255 0 102",
    },
)
async def logo(c: Client, m: Message):
    start_ = pc()
    await m.handle_message("PROCESSING")
    text, size, RGB = splitter(m.user_input or "")
    asset_dir = Path(__file__).resolve().parents[2] / "assets"
    img = Image.open(asset_dir / "images" / "blank_black.png")
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype(asset_dir / "fonts" / "Streamster.ttf", size)
    img_w, img_h = img.size
    try:
        bbox = draw.textbbox((0, 0), text, font=font)
        w_, h_ = bbox[2] - bbox[0], bbox[3] - bbox[1]
    except AttributeError:
        w_, h_ = draw.textsize(text, font)
    h_ += int(h_ * 0.25)
    temp_dir = os.path.abspath("./temp")
    os.makedirs(temp_dir, exist_ok=True)
    file_name = os.path.join(temp_dir, f"logo-{int(time.time() * 1000)}.png")
    img.save(file_name, "png")
    try:
        rm = await m.get_reply_message() if hasattr(m, "get_reply_message") else None
        reply_to = rm.id if rm else (m.reply_to_msg_id or None)
        msg = await c.send_file(
            m.chat_id,
            file=file_name,
            caption=f"Took <code>{round(pc()-start_, 2)}</code>s.",
            reply_to=reply_to,
        )
        await m.delete()
    finally:
        if exists(file_name):
            remove(file_name)
