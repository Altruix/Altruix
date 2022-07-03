# Copyright (C) 2021-present by Altruix@Github, < https://github.com/Altruix >.
#
# This file is part of < https://github.com/Altruix/Altruix > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/Altriux/Altruix/blob/main/LICENSE >
#
# All rights reserved.

__all__ = ["Essentials"]
import re
import time
import asyncio
import markdown
from bs4 import BeautifulSoup
from pyrogram.errors.exceptions import FloodWait, MessageNotModified


class _Essentials:
    def __init__(self):
        # virgin check, don't ask me what this is for :walks:
        self.initialized = True

    @staticmethod
    def md_to_text(raw_text: str) -> str:
        html = markdown.markdown(raw_text)
        soup = BeautifulSoup(html, features="html.parser")
        return soup.get_text()

    @staticmethod
    def clean_html(text: str) -> str:
        return re.sub(r"<[^>]*>", "", text)

    @staticmethod
    def get_readable_time(seconds: int) -> str:
        count = 0
        ping_time = ""
        time_list = []
        time_suffix_list = ["s", "m", "h", "days"]
        while count < 4:
            count += 1
            remainder, result = (
                divmod(
                    seconds,
                    60,
                )
                if count < 3
                else divmod(
                    seconds,
                    24,
                )
            )
            if seconds == 0 and remainder == 0:
                break
            time_list.append(int(result))
            seconds = int(remainder)
        for x in range(len(time_list)):
            time_list[x] = str(time_list[x]) + time_suffix_list[x]
        if len(time_list) == 4:
            ping_time += f"{time_list.pop()}, "
        time_list.reverse()
        ping_time += ":".join(time_list)
        return ping_time

    def humanbytes(self, size):
        if not size:
            return ""
        power = 2**10
        raised_to_pow = 0
        dict_power_n = {0: "", 1: "KB", 2: "MB", 3: "GB", 4: "TB"}
        while size > power:
            size /= power
            raised_to_pow += 1
        return f"{str(round(size, 2))} {dict_power_n[raised_to_pow]}"

    def time_formatter(self, milliseconds: int) -> str:
        seconds, milliseconds = divmod(milliseconds, 1000)
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        days, hours = divmod(hours, 24)
        tmp = (
            (f"{str(days)} Day(s), " if days else "")
            + (f"{str(hours)} Hour(s), " if hours else "")
            + (f"{str(minutes)} Minute(s), " if minutes else "")
            + (f"{str(seconds)} Second(s), " if seconds else "")
            + (f"{str(milliseconds)} Millisecond(s), " if milliseconds else "")
        )

        return tmp[:-2]

    async def progress(
        self, current, total, upload_or_download, start, message, file_name=None
    ):
        """Progress Bar For Showing Progress While Uploading / Downloading File - Normal"""
        now = time.time()
        diff = now - start
        if round(diff % 10.00) == 0 or current == total:
            percentage = current * 100 / total
            speed = current / diff
            elapsed_time = round(diff) * 1000
            if elapsed_time == 0:
                ...
            else:
                time_to_completion = round((total - current) / speed) * 1000
                estimated_total_time = elapsed_time + time_to_completion
                try:
                    await message.edit_msg(
                        "PROGRESS",
                        string_args=(
                            upload_or_download.upper(),
                            file_name or "Unknown",
                            upload_or_download.upper(),
                            self.humanbytes(current),
                            self.humanbytes(total),
                            percentage,
                            self.humanbytes(round(speed)),
                            self.time_formatter(estimated_total_time),
                        ),
                    )

                except FloodWait as e:
                    await asyncio.sleep(e.x + 2)
                    message._client.log(f"Sleeping for : {e.x} due to floodwaits!")
                except MessageNotModified:
                    pass


Essentials = _Essentials()
