# Copyright (C) 2021-present by Altruix@Github, < https://github.com/Altruix >.
#
# This file is part of < https://github.com/Altruix/Altruix > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/Altriux/Altruix/blob/main/LICENSE >
#
# All rights reserved.

import os
import random
import requests
from PIL import Image
from Main import Altruix
from pyrogram import Client
from bs4 import BeautifulSoup
from json import loads as j_loads
from requests import post as r_post
from time import perf_counter as pc
from urllib import parse as u_parse
from Main.core.types.message import Message
from os import path as o_path, remove as rmv
from Main.utils.file_helpers import run_in_exc


@Altruix.register_on_cmd(
    ["reverse", "ris", "gris", "grs", "gis"],
    cmd_help={
        "help": "Reverses replied image on (Google | Yahoo).",
        "example": "reverse (reply to photo | sticker | image)",
        "user_args": {"yandex": "Use yandex as a method to reverse search"},
    },
    requires_reply=True,
)
async def reverse_search_func_(c: Client, m: Message):
    start = pc()
    rm = m.reply_to_message
    msg = await m.handle_message("PROCESSING")
    if (
        rm.photo
        or (rm.sticker and not rm.sticker.is_animated)
        or (
            rm.document
            and c.guess_mime_type(rm.document.file_name).startswith("image/")
        )
    ):
        photo = await m.reply_to_message.download("reverse_.png")
        if m.user_args and (all(item in ["-yandex", "-y"] for item in m.user_args)):
            img_search_url = await reverse_search_in_yandex(photo).parse()
            if not img_search_url:
                return await msg.edit_msg(
                    "YANDEX_FAILED", string_args=("Results not found!")
                )
            end = pc()
            await msg.edit_msg(
                "YANDEX_RESULT",
                string_args=(img_search_url, round(end - start, 2)),
                disable_web_page_preview=True,
            )
            return rmv(photo)
        else:
            img_r = reverse_search_in_google(photo)
            fetch_url = await img_r.reverse()
            if not fetch_url:
                return await msg.edit_msg(
                    "<code>Given image not found on Google.</code>"
                )
            if fetch_url.get("best_guess") and fetch_url.get("similar_images"):
                await msg.edit_msg("GOOGLE_LOOKING")
            else:
                return await msg.edit_msg("GOOGLE_NOT_FOUND")
            end = pc()
            return await msg.edit_msg(
                "GOOGLE_RESULT",
                string_args=(
                    fetch_url,
                    fetch_url["best_guess"],
                    fetch_url["similar_images"],
                    fetch_url["url"],
                    round(end - start, 2),
                ),
                disable_web_page_preview=True,
            )
    await msg.edit_msg("INVALID_REPLY")


user_agent = random.choice(
    [
        "Mozilla/5.0 (Linux; Android 6.0.1; SM-G920V Build/MMB29K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/52.0.2743.98 Mobile Safari/537.36",
        "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:77.0) Gecko/20100101 Firefox/77.0",
    ]
)
user_agent = {"User-agent": user_agent}


def convert_to_png(img_path):
    name = "google_.png"
    if os.path.exists(name):
        os.remove(name)
    try:
        image = Image.open(img_path)
    except OSError:
        return None
    image.save(name, "PNG")
    image.close()
    return name


class reverse_search_in_yandex:
    def __init__(self, photo) -> None:
        self.photo = photo

    @run_in_exc
    def parse(self):
        photo = self.photo
        photo = convert_to_png(photo)
        if photo is None:
            return None
        search_URL = "https://yandex.com/images/search"
        files = {"upfile": ("blob", open(photo, "rb"), "image/jpeg")}
        parameters = {
            "rpt": "imageview",
            "format": "json",
            "request": '{"blocks":[{"block":"b-page_type_search-by-image__link"}]}',
        }
        response = r_post(search_URL, params=parameters, files=files)
        if response.status_code == 400:
            return None
        if response.status_code == 429:
            return None
        if not response.headers:
            return None
        query_string = j_loads(response.content)["blocks"][0]["params"]["url"]
        return f"{search_URL}?{query_string}"


class reverse_search_in_google:
    def __init__(self, photo) -> None:
        self.photo = photo

    async def reverse(self):
        url = await self.get_img_search_result()
        if not url:
            return None
        return await self.ParseSauce(url)

    @run_in_exc
    def get_img_search_result(self):
        img = self.photo
        name = convert_to_png(img)
        if name is None:
            return None
        if o_path.exists(img):
            rmv(img)
        searchUrl = "https://www.google.com/searchbyimage/upload"
        multipart = {"encoded_image": (name, open(name, "rb"))}
        response = r_post(searchUrl, files=multipart, allow_redirects=False)
        if o_path.exists(name):
            rmv(name)
        if response.status_code == 400:
            return None
        return response.headers.get("Location")

    @run_in_exc
    def ParseSauce(self, url_):
        url_ = f"{url_}&preferences?hl=en&fg=1#languages"
        results = {}
        source_s = requests.get(url_, headers=user_agent)
        soup = BeautifulSoup(str(source_s.text), "html.parser")
        for similar_image in soup.find_all("input", {"class": "gLFyf"}):
            if similar_image.get("value"):
                url = "https://www.google.com/search?tbm=isch&q=" + u_parse.quote_plus(
                    similar_image.get("value")
                )
                results["similar_images"] = url
        for best in soup.find_all("div", {"class": "r5a77d"}):
            results["best_guess"] = best.get_text()
        results["url"] = url_
        return results
