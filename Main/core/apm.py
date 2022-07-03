# Copyright (C) 2021-present by Altruix@Github, < https://github.com/Altruix >.
#
# This file is part of < https://github.com/Altruix/Altruix > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/Altriux/Altruix/blob/main/LICENSE >
#
# All rights reserved.
#

import os
import json
import httpx
import shutil
import tarfile
import aiofiles
import contextlib
from typing import Union
from traceback import format_exc
from types import SimpleNamespace
from pyrogram.types import Message
from Main.core.exceptions import (
    Package404, AlreadyInstalled, InvalidPackageToUpdate)


apt_available = True

try:
    import apt
except (ImportError):
    apt_available = False


class APM:
    def __init__(self, Altruix) -> None:
        self.base_url = "https://engine-production-d3fb.up.railway.app/"
        self.package_path = "./Main/plugins/custom_app/"
        self.Altruix = Altruix
        self.tmp_package = "./Main/plugins/temp_app/"
        self.httpx_client = httpx.AsyncClient()

    async def make_req(self, path: str, params: dict = None) -> Union[int, str]:
        if params is None:
            params = {}
        url = self.base_url + path
        req = await self.httpx_client.get(url, params=params)
        await req.aclose()
        return req.status_code, req.text

    async def install_apt_packages(self, package: str):
        if not apt_available:
            return self.Altruix.log(
                "APT : not available. Try again or install binary file manually!", 40
            )
        whoami = await self.Altruix.run_cmd_async("whoami")
        if whoami[0] != "root":
            return self.Altruix.log(
                "APT : root access not available. Try again running the userbot with sudo!",
                40,
            )
        cache = apt.Cache()
        cache.update()
        cache.open()
        if os.path.exists(package):
            async with aiofiles.open(package, "r") as f:
                packages = f.readlines()
        else:
            packages = [package]
        for package in packages:
            try:
                pkg = cache[package]
            except KeyError:
                self.Altruix.log(f"Package : {package} not found!")
                continue
            if pkg.is_installed:
                self.Altruix.log("Package already available - skipping!", 10)
                continue
            try:
                pkg.mark_install()
                cache.commit()
            except Exception:
                self.Altruix.log(
                    f"An exception was raised while trying to install package {package} : {str(format_exc())}",
                    20,
                )
                continue
        self.Altruix.log("All required packages installed!")

    def dictify(self, text: str) -> dict:
        with contextlib.suppress(Exception):
            return json.loads(text)

    def mk_dir(self, dir_path, remove_dir=False):
        if remove_dir and os.path.exists(dir_path):
            os.rmdir(dir_path)
        return os.makedirs(dir_path)

    async def get_package_info(self, package_name: str):
        resp, json_resp = await self.make_req(
            "getPluginInfo", params={"name": package_name}
        )
        if resp != 200:
            return None
        if json_resp:
            return (
                json.loads(json_resp, object_hook=lambda d: SimpleNamespace(**d))
            ).result

    async def write_file(self, package_name):
        url = f"{self.base_url}getPlugin"
        req = await self.httpx_client.get(url, params={"name": package_name})
        if not os.path.exists(self.tmp_package):
            self.mk_dir(self.tmp_package)
        file_ = os.path.join(self.tmp_package, package_name)
        if os.path.exists(f"{file_}.tar.gz"):
            os.remove(f"{file_}.tar.gz")
        async with aiofiles.open(f"{file_}.tar.gz", "wb") as f:
            await f.write(req.content)
        await req.aclose()
        return f"{file_}.tar.gz"

    async def unzip_and_load(
        self, app_path: str, plugin_name: str, msg: Message = None
    ):
        to_unzip = os.path.join(self.package_path, plugin_name)
        if not os.path.exists(to_unzip):
            self.mk_dir(to_unzip, True)
        file = tarfile.open(app_path, "r:gz")
        file.extractall(to_unzip)
        file.close()
        if msg:
            await msg.edit_msg("LOADING_PACKAGE")
        if os.path.exists(app_path):
            os.remove(app_path)
        req_file_path = os.path.join(to_unzip, "requirements.txt")
        apt_req_file_path = os.path.join(to_unzip, "apt_req.txt")
        if os.path.exists(apt_req_file_path):
            if apt_available:
                try:
                    self.install_apt_packages(req_file_path)
                except Exception:
                    if msg:
                        await msg.edit_msg("PACKAGE_APT_NOT_AVAILABLE")
                    return self.Altruix.log(
                        f"Package install failed : This package requires apt with sudo permissions! \n : {format_exc()}",
                        40,
                    )
            else:
                if msg:
                    await msg.edit_msg("PACKAGE_APT_NOT_AVAILABLE")
                return self.Altruix.log(
                    "Package install failed : This package requires apt with sudo permissions!",
                    40,
                )
        if os.path.exists(req_file_path) or (req_file_path := os.path.exists(os.path.join(to_unzip, "req.txt"))):
            if msg:
                await msg.edit_msg("INSTALLING_PACKAGE_REQUIREMENTS")
            await self.Altruix.run_cmd_async(
                f"pip3 install --no-cache-dir -r {req_file_path}"
            )
        await self.Altruix.load_from_directory(f"{to_unzip}/*.py", msg=msg)

    async def install_package(self, package_name: str, msg=None):
        resp = await self.get_package_info(package_name)
        plugin_path = os.path.join(self.package_path, package_name)
        if os.path.exists(plugin_path):
            raise AlreadyInstalled("Package is Already installed and working.")
        if not resp:
            raise Package404("Package Not found. Invalid Package Stated.")
        file_path = await self.write_file(package_name)
        await self.unzip_and_load(file_path, package_name, msg)
        return resp

    async def uninstall_package(self, package_name: str, msg):
        plugin_path = os.path.join(self.package_path, package_name)
        if os.path.exists(plugin_path):
            shutil.rmtree(plugin_path)
            await self.Altruix.reboot(last_msg=msg)
            return True
        return False

    async def update_package(self, package_name: str):
        resp = await self.get_package_info(package_name)
        if not resp:
            raise InvalidPackageToUpdate(
                "Looks like you are trying to update a package that doesn't exists"
            )
        if os.path.exists(self.package_path):
            plugin_path = os.path.join(self.package_path, package_name)
            if os.path.exists(plugin_path):
                os.rmdir(plugin_path)
        return await self.install_package(package_name)
