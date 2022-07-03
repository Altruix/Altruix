# Copyright (C) 2021-present by Altruix@Github, < https://github.com/Altruix >.
#
# This file is part of < https://github.com/Altruix/Altruix > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/Altriux/Altruix/blob/main/LICENSE >
#
# All rights reserved.

from json import JSONDecodeError
import httpx
import random
import contextlib
from typing import Set, List, Union

class Paste:
    def __init__(
        self,
        text: str = None,
        title: str = None,
        author: str = None,
        file_ext: str = None,
        service: str = None,
    ) -> None:
        self.httpx = httpx.AsyncClient()
        self.text: Union[str, bytes] = text
        self.title: str = title
        self.author: str = author
        self.file_ext: str = file_ext
        self.service: str = service

    async def to_nekobin(self) -> Set[Union[str, None]]:
        url = "https://nekobin.com/api/documents/"
        data = {
            "content": self.text,
            "title": self.title,
            "author": self.author,
        }
        resp = await self.httpx.post(url, json=data)
        try:
            data = resp.json()
            return "nekobin", f"https://nekobin.com/{data['result']['key']}"
        except (KeyError, TypeError, TimeoutError, JSONDecodeError):
            return None, None

    async def to_spacebin(self) -> Set[Union[str, None]]:
        url = "https://spaceb.in/api/v1/documents"
        data = {"content": self.text, "extension": "txt"}
        r = await self.httpx.post(url, data=data)
        try:
            data = r.json()
            return "spacebin", f'https://spaceb.in/{data["payload"]["id"]}'
        except (KeyError, TypeError, TimeoutError, JSONDecodeError):
            return None, None

    async def to_hastebin(self) -> Set[Union[str, None]]:
        r = await self.httpx.post("https://hastebin.com/documents", data=self.text)
        try:
            data = r.json()
            return "hastebin", f'https://hastebin.com/{data["key"]}'
        except (KeyError, TypeError, TimeoutError, JSONDecodeError):
            return None, None

    async def paste(self) -> Set[Union[str, None]]:
        service, paste_url = None, None
        if not self.service:
            available_functions = [
                getattr(self, m)
                for m in dir(self)
                if not m.startswith("__")
                and m.startswith("to")
                and callable(getattr(self, m))
            ]
            while paste_url is None and available_functions:
                _ = random.choice(available_functions)
                available_functions.remove(_)
                service, paste_url = await _()
        elif self.service not in self.all_bins:
            raise ValueError(f'"{self.service}" is not a valid paste service!')
        else:
            service, paste_url = await getattr(self, f"to_{self.service}")()
        with contextlib.suppress(Exception):
            await self.httpx.aclose()
        return service, paste_url

    @property
    def all_bins(self) -> List[str]:
        return [
            m.strip("to_")
            for m in dir(self)
            if not m.startswith("__") and m.startswith("to")
        ]

    def __repr__(self) -> str:
        return f"Paste(text={self.text}, title={self.title}, author={self.author}, file_ext={self.file_ext})"
