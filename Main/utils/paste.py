# Copyright (C) 2021-present by Altruix@Github, < https://github.com/Altruix >.
#
# This file is part of < https://github.com/Altruix/Altruix > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/Altriux/Altruix/blob/main/LICENSE >
#
# All rights reserved.

import httpx
import random
import contextlib
from json import JSONDecodeError
from typing import List, Tuple, Optional, Union


class Paste:
    def __init__(
        self,
        text: Union[str, bytes] = None,
        title: str = None,
        author: str = None,
        file_ext: str = None,
        service: str = None,
    ) -> None:
        self.httpx = httpx.AsyncClient(timeout=15.0, follow_redirects=True)
        self.text: Union[str, bytes] = text
        self.title: str = title
        self.author: str = author
        self.file_ext: str = file_ext
        self.service: str = service

    def _get_text(self) -> str:
        if isinstance(self.text, bytes):
            return self.text.decode("utf-8", errors="ignore")
        return str(self.text or "")

    async def to_spacebin(self) -> Tuple[Optional[str], Optional[str]]:
        url = "https://spaceb.in/api/"
        try:
            r = await self.httpx.post(url, json={"content": self._get_text()})
            if r.status_code == 200:
                data = r.json()
                doc_id = data.get("payload", {}).get("id")
                if doc_id:
                    return "spacebin", f"https://spaceb.in/{doc_id}"
        except (KeyError, TypeError, TimeoutError, JSONDecodeError, httpx.HTTPError):
            pass
        return None, None

    async def to_dpaste(self) -> Tuple[Optional[str], Optional[str]]:
        url = "https://dpaste.org/api/"
        payload = {"content": self._get_text(), "format": "json", "expiry_days": 14}
        if self.title:
            payload["title"] = self.title
        try:
            r = await self.httpx.post(url, data=payload)
            if r.status_code == 200:
                data = r.json()
                if "url" in data:
                    return "dpaste", data["url"]
        except (KeyError, TypeError, TimeoutError, JSONDecodeError, httpx.HTTPError):
            pass
        return None, None

    async def to_pasters(self) -> Tuple[Optional[str], Optional[str]]:
        url = "https://paste.rs/"
        try:
            r = await self.httpx.post(url, content=self._get_text())
            if r.status_code in (200, 201):
                link = r.text.strip()
                if link.startswith("http"):
                    return "paste.rs", link
        except (KeyError, TypeError, TimeoutError, JSONDecodeError, httpx.HTTPError):
            pass
        return None, None

    async def to_cnet(self) -> Tuple[Optional[str], Optional[str]]:
        url = "https://paste.c-net.org/"
        try:
            r = await self.httpx.post(url, content=self._get_text())
            if r.status_code == 200:
                link = r.text.strip()
                if link.startswith("http"):
                    return "c-net", link
        except (KeyError, TypeError, TimeoutError, JSONDecodeError, httpx.HTTPError):
            pass
        return None, None

    async def paste(self) -> Tuple[Optional[str], Optional[str]]:
        service, paste_url = None, None
        if not self.service:
            available_functions = [
                getattr(self, m)
                for m in dir(self)
                if not m.startswith("__")
                and m.startswith("to_")
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
        return sorted([
            m.removeprefix("to_")
            for m in dir(self)
            if not m.startswith("__") and m.startswith("to_") and callable(getattr(self, m))
        ])

    def __repr__(self) -> str:
        return f"Paste(text={self.text}, title={self.title}, author={self.author}, file_ext={self.file_ext})"
