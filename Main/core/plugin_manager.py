# Copyright (C) 2021-present by Altruix@Github, < https://github.com/Altruix >.
#
# This file is part of < https://github.com/Altruix/Altruix > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/Altriux/Altruix/blob/main/LICENSE >
#
# All rights reserved.

"""
Altruix Plugin Manager (APM v2)
================================
Supports loading plugins from multiple providers:
  - local: from filesystem paths
  - github: from GitHub repositories (raw or releases)
  - url: from any direct URL
  - registry: from the Altruix plugin registry

Manifest format (plugin.json):
{
    "name": "my_plugin",
    "version": "1.0.0",
    "description": "Does something cool",
    "author": "YourName",
    "provider": "github",
    "source": "username/repo",
    "branch": "main",
    "entry": "my_plugin.py",
    "dependencies": ["httpx", "pillow"],
    "apt_dependencies": []
}
"""

from __future__ import annotations

import os
import sys
import glob
import json
import shutil
import asyncio
import hashlib
import logging
import tarfile
import zipfile
import importlib
import importlib.util
import contextlib
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, field, asdict

import aiofiles
import httpx

logger = logging.getLogger("altruix.apm")

ALTRUIX_REGISTRY_URL = "https://raw.githubusercontent.com/Altruix/plugin-registry/main/registry.json"
GITHUB_RAW_BASE = "https://raw.githubusercontent.com/{repo}/{branch}/{path}"
GITHUB_ARCHIVE_BASE = "https://github.com/{repo}/archive/refs/heads/{branch}.zip"


@dataclass
class PluginManifest:
    name: str
    version: str = "0.0.1"
    description: str = ""
    author: str = "Unknown"
    provider: str = "local"       # local | github | url | registry
    source: str = ""              # repo "user/repo", URL, or registry name
    branch: str = "main"
    entry: str = ""               # main .py file
    dependencies: List[str] = field(default_factory=list)
    apt_dependencies: List[str] = field(default_factory=list)
    enabled: bool = True
    checksum: Optional[str] = None

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "PluginManifest":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class PluginProvider:
    """Base class for plugin providers."""
    name: str = "base"

    async def fetch(self, manifest: PluginManifest, dest_dir: Path) -> Path:
        raise NotImplementedError

    async def resolve(self, source: str) -> Optional[PluginManifest]:
        return None


class LocalProvider(PluginProvider):
    """Load a plugin from the local filesystem."""
    name: str = "local"

    async def fetch(self, manifest: PluginManifest, dest_dir: Path) -> Path:
        src = Path(manifest.source)
        if not src.exists():
            raise FileNotFoundError(f"Local plugin path not found: {src}")
        dest = dest_dir / manifest.name
        dest.mkdir(parents=True, exist_ok=True)
        if src.is_file():
            shutil.copy2(src, dest / src.name)
        else:
            shutil.copytree(src, dest, dirs_exist_ok=True)
        return dest


class GithubProvider(PluginProvider):
    """Download and install a plugin from a GitHub repository."""

    def __init__(self, repo_url_or_client: Optional[Union[str, httpx.AsyncClient]] = None, **kwargs) -> None:
        if isinstance(repo_url_or_client, str):
            self.repo_url = repo_url_or_client
            self.repo_name = repo_url_or_client.rstrip("/").split("/")[-1]
            self.name = f"github:{self.repo_name}"
            self._client = kwargs.get("client") or httpx.AsyncClient(timeout=30.0, follow_redirects=True)
        else:
            self.repo_url = ""
            self.repo_name = ""
            self.name = "github"
            self._client = repo_url_or_client or httpx.AsyncClient(timeout=30.0, follow_redirects=True)

    @staticmethod
    def _normalize_repo(source: str) -> str:
        s = source.strip()
        for prefix in ("https://github.com/", "http://github.com/", "git@github.com:"):
            if s.startswith(prefix):
                s = s[len(prefix):]
                break
        s = s.rstrip("/")
        if s.endswith(".git"):
            s = s[:-4]
        return s

    async def fetch(self, manifest: PluginManifest, dest_dir: Path) -> Path:
        repo = self._normalize_repo(manifest.source)
        branch = manifest.branch or "main"
        dest = dest_dir / manifest.name
        dest.mkdir(parents=True, exist_ok=True)

        if manifest.entry:
            # Fetch single file
            url = GITHUB_RAW_BASE.format(repo=repo, branch=branch, path=manifest.entry)
            resp = await self._client.get(url)
            resp.raise_for_status()
            file_dest = dest / Path(manifest.entry).name
            async with aiofiles.open(file_dest, "wb") as f:
                await f.write(resp.content)
            return file_dest
        else:
            # Download whole repo archive as zip
            url = GITHUB_ARCHIVE_BASE.format(repo=repo, branch=branch)
            resp = await self._client.get(url)
            resp.raise_for_status()
            zip_path = dest / f"{manifest.name}.zip"
            async with aiofiles.open(zip_path, "wb") as f:
                await f.write(resp.content)
            # Safe extract
            with zipfile.ZipFile(zip_path, "r") as z:
                dest_resolved = dest.resolve()
                for member in z.namelist():
                    target = (dest / member).resolve()
                    if not str(target).startswith(str(dest_resolved)):
                        raise ValueError(f"Directory traversal detected in archive: {member}")
                z.extractall(dest)
            zip_path.unlink(missing_ok=True)
            return dest

    async def resolve(self, source: str) -> Optional[PluginManifest]:
        """Try to fetch plugin.json from repo root."""
        clean_repo = self._normalize_repo(source)
        try:
            url = GITHUB_RAW_BASE.format(repo=clean_repo, branch="main", path="plugin.json")
            resp = await self._client.get(url, timeout=10.0)
            if resp.status_code == 200:
                data = resp.json()
                data["source"] = clean_repo
                data["provider"] = "github"
                return PluginManifest.from_dict(data)
        except Exception as e:
            logger.debug(f"Could not resolve manifest from {source}: {e}")
        return None


class URLProvider(PluginProvider):
    """Download a plugin from a direct URL (zip or .py)."""

    def __init__(self, client: Optional[httpx.AsyncClient] = None) -> None:
        self._client = client or httpx.AsyncClient(timeout=60.0, follow_redirects=True)

    async def fetch(self, manifest: PluginManifest, dest_dir: Path) -> Path:
        url = manifest.source
        resp = await self._client.get(url)
        resp.raise_for_status()
        dest = dest_dir / manifest.name
        dest.mkdir(parents=True, exist_ok=True)

        filename = url.split("/")[-1].split("?")[0] or f"{manifest.name}.py"
        file_path = dest / filename

        async with aiofiles.open(file_path, "wb") as f:
            await f.write(resp.content)

        if filename.endswith(".zip"):
            with zipfile.ZipFile(file_path, "r") as z:
                z.extractall(dest)
            file_path.unlink(missing_ok=True)
        elif filename.endswith(".tar.gz"):
            with tarfile.open(file_path, "r:gz") as t:
                t.extractall(dest)
            file_path.unlink(missing_ok=True)

        return dest


class RegistryProvider(PluginProvider):
    """Install plugins from the Altruix official registry."""

    def __init__(self, client: Optional[httpx.AsyncClient] = None) -> None:
        self._client = client or httpx.AsyncClient(timeout=30.0, follow_redirects=True)
        self._registry: Optional[Dict[str, Any]] = None

    async def _load_registry(self) -> Dict[str, Any]:
        if self._registry:
            return self._registry
        try:
            resp = await self._client.get(ALTRUIX_REGISTRY_URL, timeout=10.0)
            resp.raise_for_status()
            self._registry = resp.json()
        except Exception:
            self._registry = {}
        return self._registry

    async def resolve(self, source: str) -> Optional[PluginManifest]:
        registry = await self._load_registry()
        entry = registry.get(source.lower())
        if not entry:
            return None
        data = dict(entry)
        data["name"] = source
        data["provider"] = data.get("provider", "github")
        return PluginManifest.from_dict(data)

    async def fetch(self, manifest: PluginManifest, dest_dir: Path) -> Path:
        provider_type = manifest.provider
        if provider_type == "github":
            return await GithubProvider(self._client).fetch(manifest, dest_dir)
        return await URLProvider(self._client).fetch(manifest, dest_dir)


class PluginManager:
    """
    Central plugin manager for Altruix.
    Handles install, uninstall, update, list, and hot-reload of plugins.
    """

    PLUGIN_DIR = Path("./Main/plugins/external")
    MANIFEST_FILE = Path("./Main/plugins/external/.manifests.json")

    def __init__(self, altruix: Optional[Any] = None) -> None:
        self.altruix = altruix
        self._http = httpx.AsyncClient(timeout=60.0, follow_redirects=True)
        self._providers: Dict[str, PluginProvider] = {
            "local": LocalProvider(),
            "github": GithubProvider(self._http),
            "url": URLProvider(self._http),
            "registry": RegistryProvider(self._http),
        }
        self._custom_providers: List[PluginProvider] = []
        self._installed: Dict[str, PluginManifest] = {}
        self.PLUGIN_DIR.mkdir(parents=True, exist_ok=True)
        self._load_manifest_index()

    @property
    def providers(self) -> List[PluginProvider]:
        return self._custom_providers

    def add_provider(self, provider: PluginProvider) -> None:
        self._custom_providers.append(provider)
        self._providers[getattr(provider, "name", str(len(self._custom_providers)))] = provider

    def _load_manifest_index(self) -> None:
        if self.MANIFEST_FILE.exists():
            try:
                data = json.loads(self.MANIFEST_FILE.read_text(encoding="utf-8"))
                for name, d in data.items():
                    self._installed[name] = PluginManifest.from_dict(d)
            except Exception as e:
                logger.warning(f"Failed to load plugin manifest index: {e}")

    def _save_manifest_index(self) -> None:
        try:
            data = {n: m.to_dict() for n, m in self._installed.items()}
            self.MANIFEST_FILE.write_text(
                json.dumps(data, indent=2, default=str), encoding="utf-8"
            )
        except Exception as e:
            logger.error(f"Failed to save plugin manifest index: {e}")

    def _get_provider(self, provider_name: str) -> PluginProvider:
        return self._providers.get(provider_name, self._providers["url"])

    async def resolve_manifest(self, source: str, provider: str = "github") -> Optional[PluginManifest]:
        """Auto-resolve a plugin manifest from a source string."""
        p = self._get_provider(provider)
        return await p.resolve(source)

    async def install(
        self,
        source: str,
        provider: str = "github",
        manifest: Optional[PluginManifest] = None,
        msg: Optional[Any] = None,
    ) -> Optional[PluginManifest]:
        """Install a plugin from a source."""
        # Auto-detect GitHub or generic URL provider
        if source.startswith(("http://github.com/", "https://github.com/", "git@github.com:")):
            provider = "github"
            source = GithubProvider._normalize_repo(source)
        elif source.startswith(("http://", "https://")):
            provider = "url"

        if manifest is None:
            manifest = await self.resolve_manifest(source, provider)
        if manifest is None:
            raw_name = source.rstrip("/").split("/")[-1].replace(".py", "")
            if raw_name.endswith(".git"):
                raw_name = raw_name[:-4]
            manifest = PluginManifest(
                name=raw_name,
                source=source,
                provider=provider,
            )

        if manifest.name in self._installed:
            raise ValueError(f"Plugin '{manifest.name}' is already installed. Use update() to upgrade.")

        if msg:
            with contextlib.suppress(Exception):
                await msg.edit_msg(f"📦 Installing <code>{manifest.name}</code>...")

        # Install pip dependencies
        if manifest.dependencies:
            await self._install_pip_deps(manifest.dependencies, msg)

        # Fetch plugin files
        provider_obj = self._get_provider(manifest.provider)
        plugin_path = await provider_obj.fetch(manifest, self.PLUGIN_DIR)

        # Load plugin into Altruix
        if plugin_path.is_file():
            await self.altruix.load_from_directory(str(plugin_path))
        else:
            py_files = list(plugin_path.rglob("*.py"))
            for f in py_files:
                if not f.name.startswith("_"):
                    await self.altruix.load_from_directory(str(f))

        self._installed[manifest.name] = manifest
        self._save_manifest_index()

        if msg:
            with contextlib.suppress(Exception):
                await msg.edit_msg(f"✅ Plugin <code>{manifest.name}</code> installed successfully!")

        logger.info(f"Plugin installed: {manifest.name} v{manifest.version}")
        return manifest

    async def uninstall(self, plugin_name: str, msg: Optional[Any] = None) -> bool:
        """Uninstall a plugin and remove its files."""
        if plugin_name not in self._installed:
            return False

        plugin_dir = self.PLUGIN_DIR / plugin_name
        if plugin_dir.exists():
            shutil.rmtree(plugin_dir, ignore_errors=True)

        # Also check for single-file installs
        for f in self.PLUGIN_DIR.glob(f"{plugin_name}.py"):
            f.unlink(missing_ok=True)

        del self._installed[plugin_name]
        self._save_manifest_index()

        if msg:
            with contextlib.suppress(Exception):
                await msg.edit_msg(f"🗑️ Plugin <code>{plugin_name}</code> uninstalled. Restart to fully unload.")

        logger.info(f"Plugin uninstalled: {plugin_name}")
        return True

    async def update(self, plugin_name: str, msg: Optional[Any] = None) -> Optional[PluginManifest]:
        """Update an installed plugin to the latest version."""
        if plugin_name not in self._installed:
            raise ValueError(f"Plugin '{plugin_name}' is not installed.")

        manifest = self._installed[plugin_name]
        await self.uninstall(plugin_name)
        return await self.install(manifest.source, manifest.provider, manifest, msg)

    async def list_installed(self) -> List[PluginManifest]:
        return list(self._installed.values())

    async def list_registry(self) -> Dict[str, Any]:
        """Fetch and return all available plugins from the registry."""
        registry_provider = self._providers["registry"]
        return await registry_provider._load_registry()

    async def _install_pip_deps(self, deps: List[str], msg: Optional[Any] = None) -> None:
        if not deps:
            return
        deps_str = " ".join(deps)
        logger.info(f"Installing pip dependencies: {deps_str}")
        if msg:
            with contextlib.suppress(Exception):
                await msg.edit_msg(f"📦 Installing dependencies: <code>{deps_str}</code>...")
        proc = await asyncio.create_subprocess_exec(
            sys.executable, "-m", "pip", "install", "--quiet", *deps,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()
        if proc.returncode != 0:
            logger.warning(f"Some dependencies may not have installed cleanly: {stderr.decode()}")

    async def reload(self, plugin_name: str) -> bool:
        """Hot-reload a single plugin by name."""
        manifest = self._installed.get(plugin_name)
        if not manifest:
            return False

        plugin_dir = self.PLUGIN_DIR / plugin_name
        if plugin_dir.is_dir():
            for f in plugin_dir.rglob("*.py"):
                mod_name = f"external.{plugin_name}.{f.stem}"
                if mod_name in sys.modules:
                    del sys.modules[mod_name]
            await self.altruix.load_from_directory(str(plugin_dir / "*.py"))
        return True


PluginMetadata = PluginManifest
GitHubPluginProvider = GithubProvider
