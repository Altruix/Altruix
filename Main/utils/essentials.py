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
import logging
from bs4 import BeautifulSoup
from telethon import errors
from typing import Union

logger = logging.getLogger("altruix.essentials")


class _Essentials:
    def __init__(self):
        self.initialized = True

    @staticmethod
    def md_to_text(raw_text: str) -> str:
        html_content = markdown.markdown(raw_text)
        soup = BeautifulSoup(html_content, features="html.parser")
        return soup.get_text()

    @staticmethod
    def clean_html(text: str) -> str:
        return re.sub(r"<[^>]*>", "", text)

    @staticmethod
    def get_readable_time(seconds: int) -> str:
        seconds = int(seconds)
        count = 0
        ping_time = ""
        time_list = []
        time_suffix_list = ["s", "m", "h", "days"]
        while count < 4:
            count += 1
            remainder, result = (
                divmod(seconds, 60)
                if count < 3
                else divmod(seconds, 24)
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
        return ping_time or "0s"

    def humanbytes(self, size: Union[int, float]) -> str:
        if not size:
            return "0 B"
        power = 2**10
        raised_to_pow = 0
        dict_power_n = {0: "B", 1: "KB", 2: "MB", 3: "GB", 4: "TB"}
        size_f = float(size)
        while size_f >= power and raised_to_pow < 4:
            size_f /= power
            raised_to_pow += 1
        return f"{round(size_f, 2)} {dict_power_n[raised_to_pow]}"

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
        return tmp[:-2] if tmp else "0s"

    async def progress(
        self, current, total, upload_or_download, start, message, file_name=None
    ):
        """Progress Bar For Showing Progress While Uploading / Downloading File"""
        now = time.time()
        diff = now - start
        if diff < 0.1:
            return
        if round(diff % 5.0) == 0 or current == total:
            percentage = current * 100 / total if total else 0
            speed = current / diff if diff > 0 else 0
            elapsed_time = round(diff) * 1000
            time_to_completion = round((total - current) / speed) * 1000 if speed > 0 else 0
            estimated_total_time = elapsed_time + time_to_completion
            try:
                await message.edit_msg(
                    "PROGRESS",
                    string_args=(
                        str(upload_or_download).upper(),
                        file_name or "Unknown",
                        str(upload_or_download).upper(),
                        self.humanbytes(current),
                        self.humanbytes(total),
                        percentage,
                        self.humanbytes(round(speed)),
                        self.time_formatter(estimated_total_time),
                    ),
                )
            except errors.FloodWaitError as e:
                logger.warning(f"Sleeping for {e.seconds}s due to floodwait")
                await asyncio.sleep(e.seconds + 2)
            except errors.MessageNotModifiedError:
                pass
            except Exception:
                pass


Essentials = _Essentials()
