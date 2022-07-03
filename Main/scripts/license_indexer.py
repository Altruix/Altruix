# Copyright (C) 2021-present by Altruix@Github, < https://github.com/Altruix >.
#
# This file is part of < https://github.com/Altruix/Altruix > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/Altriux/Altruix/blob/main/LICENSE >
#
# All rights reserved.

import os
import sys
import time
import asyncio
import pathlib
import aiofiles
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


def file_list(path, lisT):
    for filepath in pathlib.Path(path).glob("**/*.*"):
        if os.path.isdir(filepath):
            file_list(filepath, lisT)
        elif os.path.isfile(filepath):
            if filepath not in lisT:
                lisT.append(filepath.absolute())
    return lisT


str_license_ = """# Copyright (C) 2021-present by Altruix@Github, < https://github.com/Altruix >.
#
# This file is part of < https://github.com/Altruix/Altruix > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/Altriux/Altruix/blob/main/LICENSE >
#
# All rights reserved."""

if sys.__stdin__.isatty():
    if not (license_ := input("Enter license header : \n")):
        license_ = str_license_
else:
    license_ = str_license_


async def licence_file(file_path, len_files):
    file_as_read = await aiofiles.open(file_path, "r")
    file_content = await file_as_read.read()
    if not file_content.startswith(license_):
        len_files += 1
        final_ = license_ + "\n\n" + file_content
        open_file_as_writer = await aiofiles.open(file_path, "w")
        await open_file_as_writer.write(final_)
        await open_file_as_writer.close()
        print("\033[92m" + f"Added Licence to : {str(file_path)}")
    else:
        print("\033[93m", f"Skipping : {file_path}")
    await file_as_read.close()


@run_in_exc
def get_file_path():
    if sys.__stdin__.isatty():
        file_path = input(
            "\033[31m" + "Enter Folder Path Containing your Python Files : \n"
        )
    else:
        file_path = os.getenv("TO_INDEX") or "."
    if not os.path.isdir(file_path):
        while not os.path.isdir(file_path):
            file_path = input(
                "Try Again : [IS_NOT_A_DIR] Give me Valid Path. (n - to stop)\n"
            )
            if file_path == "n":
                print("Closing Script. Please Halt.")
                exit(1)
    return file_path


async def do_it():
    file_path = await get_file_path()
    lisT = []
    start_time = await (run_in_exc(time.perf_counter))()
    files_ = [i for i in file_list(file_path, lisT) if str(i).endswith(".py")]
    len_files = 0
    await asyncio.gather(*[licence_file(i, len_files) for i in files_])
    end_time = await (run_in_exc(time.perf_counter))()
    ms = round((end_time - start_time) * 1000, 2)
    print(
        "\033[96m"
        + f"Tasked Completed in {ms} ms - Added Licence header in {len_files} Files."
    )


loop = asyncio.new_event_loop()
loop.run_until_complete(do_it())
