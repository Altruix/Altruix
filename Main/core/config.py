# Copyright (C) 2021-present by Altruix@Github, < https://github.com/Altruix >.
#
# This file is part of < https://github.com/Altruix/Altruix > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/Altriux/Altruix/blob/main/LICENSE >
#
# All rights reserved.

from __future__ import annotations

import os
import re
import dotenv
import logging
import pathlib
import contextlib
from functools import wraps
from typing import Any, List, Union, Optional
from asyncio.events import AbstractEventLoop

from .exceptions import NoDatabaseConnected, EnvVariableTypeError

dotenv.load_dotenv()
logger = logging.getLogger("altruix.config")


def digit_wrap(digit: Any) -> Union[int, Any]:
    if digit is None:
        return None
    with contextlib.suppress(Exception):
        val = str(digit).strip()
        if val.lstrip("-").isdigit():
            return int(val)
    return digit


class TGLIMITS:
    # Accounts
    MAX_USERNAME = 32
    MIN_USERNAME = 5
    FIRSTNAME = 64
    LASTNAME = 64

    # Messages
    MESSAGE_TEXT = 4096
    MEDIA_CAPTION_TEXT = 1024
    FILE_SIZE_LIMIT = 2  # GB


class BaseConfig:
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    BOT_MODE = os.getenv("BOT_MODE", "false").lower() in {"true", "yes", "enable", "1"}
    AUTOPOST_CACHE: dict = {}
    CUSTOM_BOT_MEDIA = os.getenv("CUSTOM_BOT_MEDIA")
    OWNER_ID = (
        int(os.getenv("OWNER_ID"))
        if os.getenv("OWNER_ID") and os.getenv("OWNER_ID").strip().lstrip("-").isdigit()
        else 0
    )
    LOAD_ENV_TO_DB = os.getenv("LOAD_ENV_TO_DB", "false").lower() in {"true", "yes", "1"}
    CUSTOM_BT_START_MSG = os.getenv("CUSTOM_BT_START_MSG", "")
    SESSIONS = [i for i in os.getenv("SESSIONS", "").split(" ") if i.strip()]
    API_ID = (
        int(os.getenv("API_ID"))
        if os.getenv("API_ID") and os.getenv("API_ID").strip().isdigit()
        else 0
    )
    DISABLED_SUDO_CMD_LIST: List[str] = []
    API_HASH = os.getenv("API_HASH", "")
    HEROKU_APP_NAME = os.getenv("HEROKU_APP_NAME")
    HELP_MENU_ROWS = int(os.getenv("HELP_MENU_ROWS", 6)) if str(os.getenv("HELP_MENU_ROWS", "6")).isdigit() else 6
    HELP_MENU_COLUMNS = int(os.getenv("HELP_MENU_COLUMNS", 3)) if str(os.getenv("HELP_MENU_COLUMNS", "3")).isdigit() else 3

    DEFAULT_REPO = "https://github.com/Altruix/Altruix"
    HEROKU_API_KEY = os.getenv("HEROKU_API_KEY")
    REPO = os.getenv("CUSTOM_REPO") or DEFAULT_REPO

    UPDATE_ON_STARTUP = os.getenv("UPDATE_ON_STARTUP", "false").strip().lower() in {
        "true", "yes", "1", "on"
    }
    DB_NAME = os.getenv("DB_NAME", "Altruix")
    DB_URI = os.getenv("DB_URI")
    RESOURCE_SAVER = os.getenv("RESOURCE_SAVER") or "true"
    DEBUG = os.getenv("DEBUG", "false").lower() == "true"
    LOG_CHAT_ID = digit_wrap(os.getenv("LOG_CHAT_ID", None))
    UB_LANG = os.getenv("UB_LANG")
    SUDO_CMD_HANDLER = os.getenv("SUDO_CMD_HANDLER") or "!"
    CMD_HANDLER = os.getenv("CMD_HANDLER") or "."
    SUDO_USERS: List[int] = [
        int(i)
        for i in os.getenv("SUDO_USERS", "").split(" ")
        if i.strip().lstrip("-").isdigit()
    ]

    ALIVE_MEDIA = os.getenv("ALIVE_MEDIA")
    LOAD_XTRA_PLUGINS = os.getenv("LOAD_XTRA_PLUGINS", "true").lower() in {"true", "yes", "1", "enable"}
    XTRA_PLUGINS_REPOS: List[str] = [
        r.strip() for r in re.split(r"[, ]+", os.getenv("XTRA_PLUGINS_REPOS", "https://github.com/Altruix/XtraPlugins")) if r.strip()
    ]

    def reload_from_env(self) -> None:
        """Dynamically load or reload all environment variables into this config instance."""
        self.BOT_TOKEN = os.getenv("BOT_TOKEN")
        self.BOT_MODE = os.getenv("BOT_MODE", "false").lower() in {"true", "yes", "enable", "1"}
        self.CUSTOM_BOT_MEDIA = os.getenv("CUSTOM_BOT_MEDIA")
        self.OWNER_ID = (
            int(os.getenv("OWNER_ID"))
            if os.getenv("OWNER_ID") and os.getenv("OWNER_ID").strip().lstrip("-").isdigit()
            else 0
        )
        self.LOAD_ENV_TO_DB = os.getenv("LOAD_ENV_TO_DB", "false").lower() in {"true", "yes", "1"}
        self.CUSTOM_BT_START_MSG = os.getenv("CUSTOM_BT_START_MSG", "")
        self.SESSIONS = [i for i in os.getenv("SESSIONS", "").split(" ") if i.strip()]
        self.API_ID = (
            int(os.getenv("API_ID"))
            if os.getenv("API_ID") and os.getenv("API_ID").strip().isdigit()
            else 0
        )
        self.DISABLED_SUDO_CMD_LIST = []
        self.API_HASH = os.getenv("API_HASH", "")
        self.HEROKU_APP_NAME = os.getenv("HEROKU_APP_NAME")
        self.HELP_MENU_ROWS = int(os.getenv("HELP_MENU_ROWS", 6)) if str(os.getenv("HELP_MENU_ROWS", "6")).isdigit() else 6
        self.HELP_MENU_COLUMNS = int(os.getenv("HELP_MENU_COLUMNS", 3)) if str(os.getenv("HELP_MENU_COLUMNS", "3")).isdigit() else 3
        self.DEFAULT_REPO = "https://github.com/Altruix/Altruix"
        self.HEROKU_API_KEY = os.getenv("HEROKU_API_KEY")
        self.REPO = os.getenv("CUSTOM_REPO") or self.DEFAULT_REPO
        self.UPDATE_ON_STARTUP = os.getenv("UPDATE_ON_STARTUP", "false").strip().lower() in {
            "true", "yes", "1", "on"
        }
        self.DB_NAME = os.getenv("DB_NAME", "Altruix")
        self.DB_URI = os.getenv("DB_URI")
        self.RESOURCE_SAVER = os.getenv("RESOURCE_SAVER") or "true"
        self.DEBUG = os.getenv("DEBUG", "false").lower() == "true"
        self.LOG_CHAT_ID = digit_wrap(os.getenv("LOG_CHAT_ID", None))
        self.UB_LANG = os.getenv("UB_LANG")
        self.SUDO_CMD_HANDLER = os.getenv("SUDO_CMD_HANDLER") or "!"
        self.CMD_HANDLER = os.getenv("CMD_HANDLER") or "."
        self.SUDO_USERS = [
            int(i)
            for i in os.getenv("SUDO_USERS", "").split(" ")
            if i.strip().lstrip("-").isdigit()
        ]
        self.ALIVE_MEDIA = os.getenv("ALIVE_MEDIA")
        self.LOAD_XTRA_PLUGINS = os.getenv("LOAD_XTRA_PLUGINS", "true").lower() in {"true", "yes", "1", "enable"}
        self.XTRA_PLUGINS_REPOS = [
            r.strip() for r in re.split(r"[, ]+", os.getenv("XTRA_PLUGINS_REPOS", "https://github.com/Altruix/XtraPlugins")) if r.strip()
        ]

    def digit_wrap(self, digit_: Any) -> Union[str, int]:
        return digit_wrap(digit_)

    async def get_env(self, env_key: str, as_list: bool = False) -> Any:
        env_key = env_key.strip().upper()
        env_ = os.getenv(env_key)
        if env_ and as_list:
            return list(env_.split("|"))
        if env_ and "|" in env_:
            return list(env_.split("|"))
        if env_ is not None:
            return env_
        return getattr(self, env_key, None)

    def pop_session(self, index: int) -> Optional[str]:
        if len(self.SESSIONS) == 0:
            raise ValueError("No sessions to pop")
        if index < len(self.SESSIONS):
            popped = self.SESSIONS.pop(index)
            logger.info("Successfully popped session.")
        else:
            logger.error("Session index out of range.")
            return None

        env_path = pathlib.Path.cwd().joinpath(".env")
        if not env_path.exists():
            return popped
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                raw_data = f.read()
            with open(env_path, "w", encoding="utf-8") as f:
                if re.search(r"SESSIONS=(?:[^\r\n\t\f\v]+)?", raw_data):
                    new_data = re.sub(
                        r"SESSIONS=(?:[^\r\n\t\f\v]+)?",
                        f"SESSIONS={' '.join(self.SESSIONS)}",
                        raw_data,
                    )
                else:
                    new_data = f'{raw_data}\nSESSIONS={" ".join(self.SESSIONS)}'
                f.write(new_data)
            logger.info("Session removed from .env")
        except Exception as e:
            logger.warning("Failed to update .env: %s", e)
        return popped

    def append_session(self, session: str) -> None:
        if session not in self.SESSIONS:
            self.SESSIONS.append(session)
            env_path = pathlib.Path.cwd().joinpath(".env")
            if not env_path.exists():
                return
            try:
                with open(env_path, "r", encoding="utf-8") as f:
                    raw_data = f.read()
                with open(env_path, "w", encoding="utf-8") as f:
                    if re.search(r"SESSIONS=(?:[^\r\n\t\f\v]+)?", raw_data):
                        new_data = re.sub(
                            r"SESSIONS=(?:[^\r\n\t\f\v]+)?",
                            f"SESSIONS={' '.join(self.SESSIONS)}",
                            raw_data,
                        )
                    else:
                        new_data = f'{raw_data}\nSESSIONS={" ".join(self.SESSIONS)}'
                    f.write(new_data)
                logger.info("New session successfully appended to .env")
            except Exception as e:
                logger.warning("Failed to append session to .env: %s", e)


def var_check(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            raise EnvVariableTypeError(e) from e

    return wrapper


class Config(BaseConfig):
    def __init__(
        self,
        env_col: Optional[Any] = None,
        loop: Optional[AbstractEventLoop] = None,
        executor: Optional[Any] = None,
        **args,
    ) -> None:
        self.env_col = env_col
        self.loop = loop
        self._executor = executor
        self.reload_from_env()

    async def init_db_vars(self) -> None:
        if self.env_col is not None:
            await self.get_sudo()
            await self.load_vars_from_db()
            await self.load_envs_to_db()

    def digit_wrap(self, digit_: Any) -> Union[str, int]:
        return digit_wrap(digit_)

    async def load_envs_to_db(self) -> None:
        if self.env_col is None:
            return
        if env_ := await self.get_env("LOAD_ENV_TO_DB"):
            if str(env_).lower() in {"true", "yes", "1"}:
                for k in dir(BaseConfig):
                    v = getattr(BaseConfig, k)
                    if (
                        not callable(v)
                        and k
                        and not k.startswith("_")
                        and v is not None
                        and str(k).strip() not in {"", " "}
                        and not str(k).lower().startswith("default")
                    ):
                        with contextlib.suppress(Exception):
                            await self.sync_env_to_db(k, v)
                logger.info("Loaded environment variables to database!")

    async def load_vars_from_db(self) -> None:
        if self.env_col is None:
            return
        if not hasattr(self, "_env_cache"):
            self._env_cache = {}
        try:
            async for var in self.env_col.find({}):
                k = var.get("_id")
                v = var.get("env_value")
                setattr(self, k, v)
                self._env_cache[k] = v
        except Exception as e:
            logger.warning("Error loading vars from DB: %s", e)

    async def get_env(self, env_key: str, as_list: bool = False) -> Any:
        env_key = env_key.strip().upper()
        if not hasattr(self, "_env_cache"):
            self._env_cache = {}
        if env_key in self._env_cache:
            val = self._env_cache[env_key]
            if as_list and not isinstance(val, (list, tuple)):
                return [val] if val is not None else []
            return list(val) if as_list and isinstance(val, (list, tuple)) else val

        from_db = await self.get_env_from_db(env_key)
        if from_db is not None:
            self._env_cache[env_key] = from_db
            return list(from_db) if as_list and isinstance(from_db, (list, tuple)) else from_db

        from_env = self.get_env_(env_key, as_list)
        if from_env is not None:
            self._env_cache[env_key] = from_env
            return from_env

        attr_val = getattr(self, env_key, None)
        if attr_val is not None:
            self._env_cache[env_key] = attr_val
        return attr_val

    def get_env_(self, env_key: str, as_list: bool) -> Any:
        env_ = os.getenv(env_key)
        if env_ and as_list:
            return list(env_.split("|"))
        if env_ and "|" in env_:
            return list(env_.split("|"))
        return env_

    async def get_env_from_db(self, env_name: str) -> Any:
        if self.env_col is None:
            return None
        try:
            if var := await self.env_col.find_one({"_id": env_name}):
                val = var.get("env_value")
                res = list(val) if isinstance(val, list) else val
                if not hasattr(self, "_env_cache"):
                    self._env_cache = {}
                self._env_cache[env_name] = res
                return res
        except Exception:
            pass
        return None

    async def del_env_from_db(self, env_name: str) -> bool:
        if hasattr(self, "_env_cache") and env_name in self._env_cache:
            del self._env_cache[env_name]
        if self.env_col is None:
            return False
        try:
            if await self.env_col.find_one({"_id": env_name}):
                await self.env_col.find_one_and_delete({"_id": env_name})
                return True
        except Exception:
            pass
        return False

    async def unsync_env_to_db(self, env_name: str, values: Any) -> List[Any]:
        """Remove one or more values from a list-valued environment setting."""
        if self.env_col is None or self.DEBUG:
            return []
        current = await self.get_env_from_db(env_name)
        if current is None:
            return []
        current_values = current if isinstance(current, list) else [current]
        remove_values = values if isinstance(values, (list, tuple, set)) else [values]
        remove_keys = {str(value).strip().casefold() for value in remove_values}
        remaining = [
            value for value in current_values
            if str(value).strip().casefold() not in remove_keys
        ]
        if remaining == current_values:
            return remaining
        if remaining:
            await self.add_env_to_db(env_name, remaining, upsert=True)
        else:
            await self.del_env_from_db(env_name)
        return remaining

    async def add_env_to_db(
        self, env_name: str, update: Union[str, int, List[Any], dict], upsert: bool = False
    ) -> None:
        if hasattr(self, "_env_cache"):
            self._env_cache.pop(env_name, None)
        if self.DEBUG:
            logger.info("DEBUG mode enabled, skipping DB syncing...")
            return
        if self.env_col is None:
            return
        if isinstance(update, dict):
            await self.env_col.find_one_and_update(
                {"_id": "SUDO_USERS"}, update, upsert=upsert
            )
        else:
            await self.env_col.find_one_and_update(
                {"_id": env_name}, {"$set": {"env_value": update}}, upsert=upsert
            )

    async def add_element_to_list(self, env_name: str, value: Any) -> None:
        if hasattr(self, "_env_cache"):
            self._env_cache.pop(env_name, None)
        if self.DEBUG:
            logger.info("DEBUG mode enabled, skipping DB syncing...")
            return
        if self.env_col is None:
            return
        await self.env_col.find_one_and_update(
            {"_id": env_name}, {"$addToSet": {"env_value": value}}, upsert=True
        )

    async def pop_element_from_list(self, env_name: str, value: Any) -> None:
        if hasattr(self, "_env_cache"):
            self._env_cache.pop(env_name, None)
        if self.env_col is None:
            return
        await self.env_col.find_one_and_update(
            {"_id": env_name}, {"$pull": {"env_value": value}}
        )

    async def sync_env_to_db(
        self, env_name: str, env_value: Any, upsert: bool = False, push_: bool = False
    ) -> Any:
        if self.env_col is None:
            return None
        existing = await self.get_env_from_db(env_name)
        if push_:
            current = existing if isinstance(existing, list) else ([] if existing is None else [existing])
            incoming = env_value if isinstance(env_value, list) else [env_value]
            updated = list(current)
            for item in incoming:
                if item not in updated:
                    updated.append(item)
            return await self.env_col.find_one_and_update(
                {"_id": env_name}, {"$set": {"env_value": updated}}, upsert=True
            )
        if existing is not None:
            return await self.env_col.find_one_and_update(
                {"_id": env_name}, {"$set": {"env_value": env_value}}, upsert=upsert
            )
        return await self.env_col.insert_one({"_id": env_name, "env_value": env_value})

    @var_check
    async def add_sudo(self, user_id: Union[int, str, List[Union[int, str]]]) -> None:
        if isinstance(user_id, int):
            user_id = [user_id]
        elif isinstance(user_id, str):
            user_id = [int(user_id)]
        elif isinstance(user_id, list):
            user_id = [int(i) for i in user_id]
        await self.add_env_to_db(
            "SUDO_USERS", {"$push": {"user_ids": {"$each": user_id}}}, upsert=True
        )

    @var_check
    async def get_sudo(self) -> List[int]:
        users: List[int] = []
        if self.env_col is not None:
            try:
                if var := await self.env_col.find_one({"_id": "SUDO_USERS"}):
                    if var.get("user_ids"):
                        users.extend([int(i) for i in var.get("user_ids")])
            except Exception:
                pass
        if local_var := self.SUDO_USERS:
            users.extend(local_var)
            users = list(set(users))
            if self.env_col is not None:
                with contextlib.suppress(Exception):
                    await self.add_env_to_db("SUDO_USERS", local_var)
        self.SUDO_USERS = users
        return users

    async def del_sudo(self, user_id: Union[int, str]) -> None:
        if self.env_col is None:
            return
        await self.env_col.find_one_and_update(
            {"_id": "SUDO_USERS"}, {"$pull": {"user_ids": int(user_id)}}
        )

    async def get_pm_sts(self) -> bool:
        val = await self.get_env("PM_PERMIT")
        return bool(val and str(val).lower() in {"true", "yes", "1", "on"})

    async def get_pm_warn_limit(self) -> int:
        val = await self.get_env("PM_PERMIT_LIMIT")
        try:
            limit = int(val) if val is not None else 3
            return max(1, min(limit, 20))
        except Exception:
            return 3

    async def get_pm_custom_msg(self) -> Optional[str]:
        val = await self.get_env("PM_PERMIT_CUSTOM_MSG")
        return str(val) if val and str(val).strip() else None

    async def get_pm_allow_contacts(self) -> bool:
        val = await self.get_env("PM_PERMIT_ALLOW_CONTACTS")
        if val is None:
            return True
        return str(val).lower() in {"true", "yes", "1", "on"}

