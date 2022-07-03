# Copyright (C) 2021-present by Altruix@Github, < https://github.com/Altruix >.
#
# This file is part of < https://github.com/Altruix/Altruix > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/Altriux/Altruix/blob/main/LICENSE >
#
# All rights reserved.


import os
import random
import string
import asyncio
import multiprocessing
from functools import wraps
from concurrent.futures.thread import ThreadPoolExecutor


executor = ThreadPoolExecutor(max_workers=multiprocessing.cpu_count() * 5)


def run_in_exc(func_):
    @wraps(func_)
    async def wrapper(*args, **kwargs):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(executor, lambda: func_(*args, **kwargs))

    return wrapper


@run_in_exc
def make_file_from_text(input_: str, file_name=None, file_suffix=".txt"):
    letters = string.ascii_lowercase
    file_name = (
        file_name or "".join(random.choice(letters) for _ in range(5)) + file_suffix
    )

    if os.path.exists(file_name):
        os.remove(file_name)
    open(file_name, "w", encoding="utf-8").write(input_)
    return file_name


@run_in_exc
def rename_file(file_name, new_file_name):
    if not os.path.exists(file_name):
        return False
    os.rename(file_name, new_file_name)
    if not os.path.exists(new_file_name):
        return False
    return True


@run_in_exc
def make_folder(folder_name=None):
    letters = string.ascii_letters
    folder_name = folder_name or "".join(random.choice(letters) for _ in range(5))
    if os.path.exists(folder_name):
        os.remove(folder_name)
    os.makedirs(folder_name)
    return os.path.exists(folder_name)
