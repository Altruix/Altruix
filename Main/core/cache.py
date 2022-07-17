# Copyright (C) 2021-present by Altruix@Github, < https://github.com/Altruix >.
#
# This file is part of < https://github.com/Altruix/Altruix > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/Altriux/Altruix/blob/main/LICENSE >
#
# All rights reserved.


import os
import logging
from ..utils.startup_helpers import custom_init


logger = logging.getLogger(__name__)


class Cache:
    def __init__(self, config, db, clients) -> None:
        self.config = config
        self.db = db
        self.clients = clients

    async def update_approved_list_on_startup(self):
        for client in self.clients:
            APPROVED_LIST = f"TO_PM_APPROVED_USERS_LIST_{client.myself.id}"
            if get_approved := await self.db.data_col.find_one(APPROVED_LIST):
                get_approved = get_approved.get("user_id")
            if get_approved:
                if not isinstance(get_approved, list):
                    get_approved = [get_approved]
                if not self.config.APPROVED_DICT.get(client.myself.id):
                    self.config.APPROVED_DICT[client.myself.id] = []
                self.config.APPROVED_DICT[client.myself.id] = get_approved
            if media_ := await self.config.get_env_from_db(
                f"PM_MEDIA_{client.myself.id}"
            ):
                self.config.CUSTOM_PM_MEDIA[client.myself.id] = media_
            if text_ := await self.config.get_env_from_db(
                f"PM_TEXT_{client.myself.id}"
            ):
                self.config.CUSTOM_PM_TEXT[client.myself.id] = text_
            if pm_limit_ := await self.config.get_env_from_db(
                f"PM_WARNS_COUNT_{client.myself.id}"
            ):
                self.config.PM_WARNS_DICT[client.myself.id] = int(pm_limit_)

    async def init_all_custom_files(self):
        path_ = "./cache/"
        if not os.path.exists(path_):
            os.makedirs(path_)
            logger.info("Created cache directory")
        if alive_media := await self.config.get_env("ALIVE_MEDIA"):
            await custom_init(alive_media, suffix_file="alive", to_path=path_)
        if pm_media := await self.config.get_env("PM_MEDIA"):
            await custom_init(pm_media, suffix_file="pmpermit", to_path=path_)
        if bot_st_media := await self.config.get_env("CUSTOM_BOT_MEDIA"):
            await custom_init(bot_st_media, suffix_file="bot_st_media", to_path=path_)

    async def update_auto_post_cache(self):
        auto_post_db = self.db.make_collection("auto_post_s")
        for client in self.clients:
            if not self.config.AUTOPOST_CACHE.get(client.myself.id):
                self.config.AUTOPOST_CACHE[client.myself.id] = {}
            async for adb in auto_post_db.find({"client_id": client.myself.id}):
                if adb and adb.get("from_chat") and adb.get("to_chat"):
                    if not self.config.AUTOPOST_CACHE[client.myself.id].get(
                        int(adb["from_chat"])
                    ):
                        self.config.AUTOPOST_CACHE[client.myself.id] = {
                            int(adb.get("from_chat")): [int(adb.get("to_chat"))]
                        }
                    else:
                        self.config.AUTOPOST_CACHE[client.myself.id][
                            int(adb["from_chat"])
                        ].append(int(adb["to_chat"]))
