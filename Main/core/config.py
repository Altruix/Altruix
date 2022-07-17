# Copyright (C) 2021-present by Altruix@Github, < https://github.com/Altruix >.
#
# This file is part of < https://github.com/Altruix/Altruix > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/Altriux/Altruix/blob/main/LICENSE >
#
# All rights reserved.


import re
import dotenv
import asyncio
import logging
import pathlib
import contextlib
from os import getenv
from functools import wraps
from motor.core import AgnosticCollection
from asyncio.events import AbstractEventLoop
from typing import Any, List, Union, Optional
from .exceptions import NoDatabaseConnected, EnvVariableTypeError


dotenv.load_dotenv()


def digit_wrap(digit):
    with contextlib.suppress(Exception):
        return int(digit)
    return digit


class TGLIMITS(object):
    # Accounts
    MAX_USERNAME = 32
    MIN_USERNAME = 5
    FIRSTNAME = 64
    LASTNAME = 64

    # Messages
    MESSAGE_TEXT = 4096
    MEDIA_CAPTION_TEXT = 1024
    FILE_SIZE_LIMIT = 2  # GB


class BaseConfig(object):
    BOT_TOKEN = getenv("BOT_TOKEN")
    BOT_MODE = getenv("BOT_MODE", False)
    AUTOPOST_CACHE = {}
    CUSTOM_BOT_MEDIA = getenv("CUSTOM_BOT_MEDIA")
    OWNER_ID = (
        int(getenv("OWNER_ID"))
        if getenv("OWNER_ID") and getenv("OWNER_ID").isdigit()
        else None
    )
    LOAD_ENV_TO_DB = getenv("LOAD_ENV_TO_DB", False)
    CUSTOM_BT_START_MSG = getenv("CUSTOM_BT_START_MSG", "")
    SESSIONS = [i for i in getenv("SESSIONS", "").split(" ") if i != "" or None]
    API_ID = int(getenv("API_ID"))
    DISABLED_SUDO_CMD_LIST = []
    API_HASH = getenv("API_HASH")
    HEROKU_APP_NAME = getenv("HEROKU_APP_NAME")
    HELP_MENU_ROWS = int(getenv("HELP_MENU_ROWS", 6))
    HELP_MENU_COLUMNS = int(getenv("HELP_MENU_COLUMNS", 3))
    AUTOAPPROVE = getenv("AUTOAPPROVE", True)
    DEFAULT_REPO = "https://github.com/Altruix/Altruix"
    HEROKU_API_KEY = getenv("HEROKU_API_KEY")
    REPO = getenv("CUSTOM_REPO") or DEFAULT_REPO
    DEFAULT_PM_IMAGE = "./Main/assets/images/pmpermit.jpg"
    DEFAULT_PM_TEXT = """<b>Altruix's PM BOT</b>
<i>Hello, {mention}. Welcome to {mymention}'s PM. Please State your concern and wait for him to respond.</i>

<i>You currently <code>{warns}/{max_warns}</code> Warnings. If you end up exceeding warn limit you will be directly blocked until further notice!</i>
"""
    APPROVED_DICT: dict = {}
    CUSTOM_PM_TEXT: dict = {}
    UPDATE_ON_STARTUP = (
        False
        if (getenv("UPDATE_ON_STARTUP", "yes").lower() in ["n", "nope", "false"])
        else True
    )
    CUSTOM_PM_MEDIA: dict = {}
    PM_WARNS_DICT: dict = {}
    DB_NAME = "mongo"
    PM_MEDIA = getenv("PM_MEDIA")
    DB_URI = getenv("DB_URI")
    RESOURCE_SAVER = getenv("RESOURCE_SAVER") or "true"
    DEBUG = True if getenv("DEBUG", "false").lower() == "true" else False
    LOG_CHAT_ID = digit_wrap(getenv("LOG_CHAT_ID", None))
    PM_ENABLE = (
        False
        if (
            getenv("ENABLE_PM_PERMIT")
            and getenv("ENABLE_PM_PERMIT").lower() in ["false", "n", "no", "disable"]
        )
        else True
    )
    UB_LANG = getenv("UB_LANG")
    GEAR_THUMB = "https://telegra.ph/file/8ac4bcd5d2bd62f5f7a7a.png"
    SUDO_CMD_HANDLER = getenv("SUDO_CMD_HANDLER") or "!"
    CMD_HANDLER = getenv("CMD_HANDLER") or "."
    try:
        SUDO_USERS = [
            int(i) for i in getenv("SUDO_USERS", "").split(" ") if i.isdigit()
        ]
    except Exception:
        raise EnvVariableTypeError(Exception)

    ALIVE_MEDIA = getenv("ALIVE_MEDIA")

    def pop_session(self, index: int) -> Optional[str]:
        if len(self.SESSIONS) == 0:
            raise Exception("No sessions to pop")
        if index <= len(self.SESSIONS):
            for trials in range(5):
                try:
                    popped = self.SESSIONS.pop(index)
                    logging.info("Successfully Popped session.")
                    break
                except IndexError as e:
                    logging.warning(f"Index {index} is out of range. Retrying...")
                    if trials == 4:
                        raise Exception("Could not pop session") from e
                    continue
        else:
            print("\n")
            logging.error("Session index out of range.")
            quit(1)
        env_path = pathlib.Path().cwd().joinpath(".env")
        if not env_path.exists():
            return
        with open(env_path, "r") as f:
            raw_data = f.read()
        with open(env_path, "w") as f:
            if re.search(r"SESSIONS=(?:[^\r\n\t\f\v]+)?", raw_data):
                new_data = re.sub(
                    r"SESSIONS=(?:[^\r\n\t\f\v]+)?",
                    f"SESSIONS={' '.join(self.SESSIONS)}",
                    raw_data,
                )
            else:
                new_data = f'{raw_data}\nSESSIONS={" ".join(self.SESSIONS)}'
            f.write(new_data)
        logging.info("The unstable session was removed successfully")
        return popped

    def append_session(self, session: str) -> None:
        if session not in self.SESSIONS:
            env_path = pathlib.Path().cwd().joinpath(".env")
            if not env_path.exists():
                return
            self.SESSIONS.append(session)
            with open(env_path, "r") as f:
                raw_data = f.read()
            with open(env_path, "w") as f:
                new_data = re.sub(
                    r"SESSIONS=(?:[^\r\n\t\f\v]+)?",
                    f"SESSIONS={' '.join(self.SESSIONS)}",
                    raw_data,
                )
                f.write(new_data)
            logging.info("New session was successfully written to .env")
            return


def var_check(func):
    @wraps(func)
    async def var_check(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            raise EnvVariableTypeError(e) from e

    return var_check


class Config(BaseConfig):
    def __init__(
        self, env_col: AgnosticCollection = None, loop: AbstractEventLoop = None, **args
    ) -> None:
        if env_col is None:
            raise NoDatabaseConnected(
                "Please add database uri, So that the Userbot can function!"
            )
        self.env_col: AgnosticCollection = env_col
        self.loop = asyncio.get_event_loop() if loop is None else loop
        self.loop.run_until_complete(self.get_sudo())
        self.loop.run_until_complete(self.load_vars_from_db())
        self.loop.run_until_complete(self.load_envs_to_db())

    def digit_wrap(self, digit_: str) -> Union[str, int]:
        try:
            return int(digit_)
        except (ValueError, TypeError):
            return digit_

    async def load_envs_to_db(self):
        if env_ := await self.get_env("LOAD_ENV_TO_DB"):
            if env_.lower() == "true":
                for k in dir(BaseConfig):
                    v = getattr(BaseConfig, k)
                    if (
                        not callable(v)
                        and k
                        and k[:1] != "_"
                        and v is not None
                        and str(k).strip() not in [None, {}, [], "", " "]
                        and str(v).strip() not in [None, {}, [], "", " "]
                        and not str(k).lower().startswith("default")
                    ):
                        with contextlib.suppress(Exception):
                            await self.sync_env_to_db(
                                self.digit_wrap(k), self.digit_wrap(v)
                            )
                logging.info("Loaded ENV(s) to database!")

    async def load_vars_from_db(self):
        async for var in self.env_col.find({}):
            setattr(self, var.get("_id"), var.get("env_value"))

    async def get_env(self, env_key, as_list=False):
        env_key = env_key.strip().upper()
        return (
            await self.get_env_from_db(env_key)
            or self.get_env_(env_key, as_list)
            or getattr(self, env_key)
        )

    def get_env_(self, env_key, as_list):
        env_ = getenv(env_key)
        if env_ and as_list:
            return list(env_.split("|"))
        if env_ and "|" in env_:
            return list(env_.split("|"))
        return env_

    async def get_env_from_db(self, env_name):
        if var := await self.env_col.find_one({"_id": env_name}):
            self.__setattr__(env_name, var.get("env_value"))
            return (
                list(var.get("env_value"))
                if isinstance(var.get("env_value"), list)
                else var.get("env_value")
            )

    async def del_env_from_db(self, env_name):
        if await self.env_col.find_one({"_id": env_name}):
            await self.env_col.find_one_and_delete({"_id": env_name})
            return True
        return False

    async def add_env_to_db(
        self, env_name, update: Union[str, int, List[Any], dict], upsert: bool = False
    ) -> None:
        if self.DEBUG:
            logging.info("DEBUG mode is enabled, skipping db syncing...")
        elif isinstance(update, dict):
            await self.env_col.find_one_and_update(
                {"_id": "SUDO_USERS"}, update, upsert=upsert
            )
        else:
            await self.env_col.find_one_and_update(
                {"_id": env_name}, {"$set": {"env_value": update}}, upsert=upsert
            )

    async def add_element_to_list(self, env_name, value):
        if self.DEBUG:
            logging.info("DEBUG mode is enabled, skipping db syncing...")

        else:
            await self.env_col.find_one_and_update(
                {"_id": env_name}, {"$addToSet": {"env_value": value}}, upsert=True
            )

    async def pop_element_from_list(self, env_name, value):
        await self.env_col.find_one_and_update(
            {"_id": env_name}, {"$pull": {"env_value": value}}
        )

    async def unsync_env_to_db(self, env_name, env_value, upsert=False):
        if env_ := await self.get_env_from_db(env_name):
            if isinstance(env_value, list):
                for i in env_value:
                    if i in env_:
                        await self.env_col.find_one_and_update(
                            {"_id": env_name},
                            {"$pull": {"env_value": i}},
                            upsert=upsert,
                        )
            elif env_value in env_:
                return await self.env_col.find_one_and_update(
                    {"_id": env_name},
                    {"$pull": {"env_value": env_value}},
                    upsert=upsert,
                )

    async def sync_env_to_db(self, env_name, env_value, upsert=False, push_=False):
        if await self.get_env_from_db(env_name):
            if push_:
                if not isinstance(env_value, list):
                    return await self.env_col.find_one_and_update(
                        {"_id": env_name},
                        {"$push": {"env_value": env_value}},
                        upsert=upsert,
                    )
                for i in env_value:
                    await self.env_col.find_one_and_update(
                        {"_id": env_name},
                        {"$push": {"env_value": i}},
                        upsert=upsert,
                    )
            return await self.env_col.find_one_and_update(
                {"_id": env_name}, {"$set": {"env_value": env_value}}, upsert=upsert
            )
        if push_:
            env_value = [env_value]
        return await self.env_col.insert_one({"_id": env_name, "env_value": env_value})

    @var_check
    async def add_sudo(self, user_id: Union[int, str, List[Union[int, str]]]) -> None:
        if isinstance(user_id, int):
            user_id = [user_id]
        if isinstance(user_id, str):
            user_id = [int(user_id)]
        if isinstance(user_id, list):
            user_id = [int(i) for i in user_id]
        await self.add_env_to_db(
            "SUDO_USERS", {"$push": {"user_ids": {"$each": user_id}}}, upsert=True
        )

    @var_check
    async def get_sudo(self):
        users = []
        if var := await self.env_col.find_one({"_id": "SUDO_USERS"}):
            if var.get("user_ids"):
                users.extend([int(i) for i in var.get("user_ids")])
        if local_var := self.SUDO_USERS:
            users.extend(local_var)
            users = list(set(users))
            await self.add_env_to_db("SUDO_USERS", local_var)
        self.SUDO_USERS = users
        return users

    async def del_sudo(self, user_id):
        await self.env_col.find_one_and_update(
            {"_id": "SUDO_USERS"}, {"$pull": {"user_id": int(user_id)}}
        )
