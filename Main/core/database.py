# Copyright (C) 2021-present by Altruix@Github, < https://github.com/Altruix >.
#
# This file is part of < https://github.com/Altruix/Altruix > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/Altriux/Altruix/blob/main/LICENSE >
#
# All rights reserved.

import os
import certifi
import ujson as json
from os import path
from typing import Any, Dict, Optional
from motor.motor_asyncio import AsyncIOMotorClient
from motor.core import AgnosticDatabase, AgnosticCollection


class MongoDB:
    def __init__(self, uri):
        self.tlsca_ = certifi.where()
        self._client = AsyncIOMotorClient(uri, tlsCAFile=self.tlsca_)
        self._db_name: AgnosticDatabase = self._client["Altruix"]
        self.settings_col: AgnosticCollection = self._db_name["SETTINGS"]
        self.data_col: AgnosticCollection = self._db_name["DATA"]
        self.user_col: AgnosticCollection = self._db_name["USERS"]
        self.env_col: AgnosticCollection = self._db_name["ENV"]
        self.stickers_col: AgnosticCollection = self._db_name["STICKERS"]

    async def ping(self):
        return await self._db_name.command("ping")

    def make_collection(self, name: str) -> AgnosticCollection:
        return self._db_name[name]


class LocalDatabase:
    def __init__(self, file_path="db.json"):
        self.path = file_path
        if not path.exists(file_path):
            self.data = {}
            self.save()
        try:
            self.data = json.load(open(self.path))
        except ValueError:
            os.remove(file_path)
            self.data = {}
        self.save()

    def add_to_col(self, col_name: str, data: Dict[Any, Any]) -> None:
        if not self.data.get(col_name):
            self.data[col_name] = {}
        self.data[col_name].update(data)
        self.save()
        return

    def get_from_col(
        self, col_name: str, key: str, pop: bool = True
    ) -> Optional[Dict[Any, Any]]:
        if self.data.get(col_name) and self.data[col_name].get(key):
            if not pop:
                return self.data[col_name][key]
            value = self.data[col_name].pop(key)
            self.save()
            return value
        return None

    def save(self) -> None:
        with open(self.path, "w+") as _file:
            json.dump(self.data, _file, indent=4)
            _file.close()
