# Copyright (C) 2021-present by Altruix@Github, < https://github.com/Altruix >.
#
# This file is part of < https://github.com/Altruix/Altruix > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/Altriux/Altruix/blob/main/LICENSE >
#
# All rights reserved.

import sys
import shlex
import asyncio
import traceback
from io import StringIO
from pprint import pprint
from Main import Altruix
from Main.core.types.client import AltruixTelegramClient as Client
from Main.core.types.message import Message
from Main.utils.command import resolve_command


p = print
pp = pprint


async def execute_py(c: Client, code: str, m: Message):
    namespace = {}
    exec(
        "async def __exec_py(c, m):"
        + "\n rm = getattr(m, 'reply_to_message', None)"
        + "\n message = m"
        + "\n client = Client = c"
        + "\n chat = getattr(m, 'chat', None)"
        + "\n user = getattr(m, 'from_user', None)"
        + "".join(f"\n {l}" for l in code.split("\n")),
        globals(),
        namespace,
    )
    return await namespace["__exec_py"](c, m)


async def eval_py(client: Client, code: str, m: Message) -> str:
    old_stderr = sys.stderr
    old_stdout = sys.stdout
    redirected_output = sys.stdout = StringIO()
    redirected_error = sys.stderr = StringIO()
    exc = None
    try:
        await execute_py(client, code, m)
    except Exception:
        exc = traceback.format_exc()
    stdout = redirected_output.getvalue()
    stderr = redirected_error.getvalue()
    sys.stdout = old_stdout
    sys.stderr = old_stderr

    if exc:
        evaluation = exc
    elif stderr:
        evaluation = stderr
    elif stdout:
        evaluation = stdout
    else:
        evaluation = Altruix.get_string("NO_OUTPUT") or "No output."
    return evaluation.strip()


async def exec_terminal(command: str):
    success = True
    return_code = 0
    cmd_args = shlex.split(command)
    output = ""
    if not cmd_args:
        return False, "No command provided.", 2
    cmd_args = resolve_command(cmd_args)
    try:
        process = await asyncio.create_subprocess_exec(
            *cmd_args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        return_code = process.returncode
        output += stdout.decode("utf-8", errors="ignore").strip()
        if stderr:
            output += "\n" + stderr.decode("utf-8", errors="ignore").strip()
        success = return_code == 0
    except Exception:
        success = False
        output += traceback.format_exc()
    return success, output, return_code


Altruix.run_cmd = exec_terminal
Altruix.eval_py = eval_py
