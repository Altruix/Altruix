# Copyright (C) 2021-present by Altruix@Github, < https://github.com/Altruix >.
#
# This file is part of < https://github.com/Altruix/Altruix > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/Altriux/Altruix/blob/main/LICENSE >
#
# All rights reserved.

from os import remove
from Main import Altruix
from random import choice
from os.path import exists
from pyrogram import Client
from time import perf_counter as pc
from Main.core.types.message import Message
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
            ("AltruiX", 500, choice(colours))
            if input_[0] == ""
            else (input_[0], 500, choice(colours))
        )
    elif len_ == 2:
        if input_[0] == "":
            return "AltruiX", 500, choice(colours)
        if input_[1].isnumeric():
            return input_[0], int(input_[1]), choice(colours)
        return input_[0], 500, choice(colours)
    if input_[0] == "":
        return "AltruiX", 500, choice(colours)
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
        "example": "logo AltruiX|1000|255 0 102",
    },
)
async def logo(c: Client, m: Message):
    start_ = pc()
    await m.handle_message("PROCESSING")
    text, size, RGB = splitter(m.user_input or "")
    img = Image.open("./Main/assets/images/blank_black.png")
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype("./Main/assets/fonts/Streamster.ttf", size)
    img_w, img_h = img.size
    w_, h_ = draw.textsize(text, font)
    h_ += int(h_ * 0.25)
    draw.text(((img_w - w_) / 2, (img_h - h_) / 2), text, RGB, font)
    file_name = f"logo-{start_}.png"
    img.save(file_name, "png")
    if m.reply_to_message:
        msg = await c.send_document(
            m.chat.id,
            document=file_name,
            file_name="logo.png",
            reply_to_message_id=m.reply_to_message.id,
        )
    else:
        msg = await c.send_document(m.chat.id, document=file_name, file_name="logo.png")
    await m.delete()
    if exists(file_name):
        remove(file_name)
    await msg.edit_msg(f"Took <code>{round(pc()-start_, 2)}</code>s.")
