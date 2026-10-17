# Copyright (C) 2021-present by Altruix@Github, < https://github.com/Altruix >.
#
# This file is part of < https://github.com/Altruix/Altruix > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/Altriux/Altruix/blob/main/LICENSE >
#
# All rights reserved.

"""
Altruix Plugin Manager (APM v3)
===============================
Next-generation modular plugin manager supporting:
- Multi-domain subcategory segregation (e.g. media, search_osint, utilities, lifestyle, system).
- Selective subcategory installation and hot enable/disable toggling.
- Pre-flight importlib dependency checking (0ms startup overhead, avoids pip on boot).
- Quarantined safe-mode loading for faulty plugins.
- Built-in diagnostic doctor and batch repair engine.
- Providers: GitHub repositories, direct URLs, local paths, and official registry.
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
from typing import Any, Dict, List, Optional, Union, Set
from dataclasses import dataclass, field, asdict

import aiofiles
import httpx

from .apm_env_setup import is_package_satisfied, clean_package_name

logger = logging.getLogger("altruix.apm")

ALTRUIX_REGISTRY_URL = "https://raw.githubusercontent.com/Altruix/plugin-registry/main/registry.json"
GITHUB_RAW_BASE = "https://raw.githubusercontent.com/{repo}/{branch}/{path}"
GITHUB_ARCHIVE_BASE = "https://github.com/{repo}/archive/refs/heads/{branch}.zip"

PLUGIN_SHORTCUTS: Dict[str, str] = {
    "vc": "Altruix/VCPlugin",
    "vcplugin": "Altruix/VCPlugin",
    "xtra": "Altruix/XtraPlugins",
    "xtraplugins": "Altruix/XtraPlugins",
}


@dataclass
class PluginManifest:
    name: str
    version: str = "0.0.1"
    description: str = ""
    author: str = "Unknown"
    provider: str = "local"       # local | github | url | registry
    source: str = ""              # repo "user/repo", URL, or registry name
    branch: str = "main"
    entry: str = ""               # main .py file or empty for multi-module
    dependencies: List[str] = field(default_factory=list)
    apt_dependencies: List[str] = field(default_factory=list)
    subcategories: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    active_subcategories: List[str] = field(default_factory=list)
    enabled: bool = True
    quarantined: bool = False
    quarantine_reason: Optional[str] = None
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
            raise FileNotFoundError(f"Local plugin source not found: {manifest.source}")
        dest = dest_dir / manifest.name
        if src.is_dir():
            shutil.copytree(src, dest, dirs_exist_ok=True)
        else:
            dest.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest / src.name)
        return dest

    async def resolve(self, source: str) -> Optional[PluginManifest]:
        p = Path(source)
        manifest_file = p / "plugin.json" if p.is_dir() else p.parent / "plugin.json"
        if manifest_file.exists():
            try:
                data = json.loads(manifest_file.read_text(encoding="utf-8"))
                data["source"] = str(p.resolve())
                data["provider"] = "local"
                return PluginManifest.from_dict(data)
            except Exception:
                pass
        return PluginManifest(
            name=p.stem,
            source=str(p.resolve()),
            provider="local",
        )


class GithubProvider(PluginProvider):
    """Download a plugin from a GitHub repository."""
    name = "github"

    def __init__(self, repo_url: Optional[Union[str, httpx.AsyncClient]] = None, client: Optional[httpx.AsyncClient] = None) -> None:
        if isinstance(repo_url, httpx.AsyncClient):
            client = repo_url
            repo_url = None
        self.repo_url = str(repo_url) if repo_url else None
        if self.repo_url:
            self.repo_name = self._normalize_repo(self.repo_url).split("/")[-1]
            self.name = f"github:{self.repo_name}"
        else:
            self.repo_name = ""
            self.name = "github"
        self._client = client or httpx.AsyncClient(timeout=60.0, follow_redirects=True)

    @staticmethod
    def _normalize_repo(source: str) -> str:
        s = source.strip()
        for prefix in ("https://github.com/", "http://github.com/", "git@github.com:"):
            if s.startswith(prefix):
                s = s[len(prefix):]
                break
        if s.endswith(".git"):
            s = s[:-4]
        return s.strip("/")

    async def fetch(self, manifest: PluginManifest, dest_dir: Path) -> Path:
        repo = self._normalize_repo(manifest.source)
        branch = manifest.branch or "main"
        url = GITHUB_ARCHIVE_BASE.format(repo=repo, branch=branch)

        logger.info(f"Downloading GitHub archive: {url}")
        resp = await self._client.get(url)
        if resp.status_code == 404 and branch == "main":
            # Retry with master branch
            url = GITHUB_ARCHIVE_BASE.format(repo=repo, branch="master")
            resp = await self._client.get(url)

        resp.raise_for_status()

        dest = dest_dir / manifest.name
        dest.mkdir(parents=True, exist_ok=True)

        zip_path = dest / "_archive.zip"
        async with aiofiles.open(zip_path, "wb") as f:
            await f.write(resp.content)

        # Extract safely
        with zipfile.ZipFile(zip_path, "r") as z:
            top_level_dirs = {p.split("/")[0] for p in z.namelist() if "/" in p}
            if len(top_level_dirs) == 1:
                prefix = list(top_level_dirs)[0] + "/"
                for member in z.infolist():
                    if member.filename.startswith(prefix) and member.filename != prefix:
                        target = dest / member.filename[len(prefix):]
                        if member.is_dir():
                            target.mkdir(parents=True, exist_ok=True)
                        else:
                            target.parent.mkdir(parents=True, exist_ok=True)
                            with z.open(member) as source, open(target, "wb") as outfile:
                                shutil.copyfileobj(source, outfile)
            else:
                z.extractall(dest)

        zip_path.unlink(missing_ok=True)
        return dest

    async def resolve(self, source: str) -> Optional[PluginManifest]:
        clean_repo = self._normalize_repo(source)
        # Try main branch then master
        for branch in ("main", "master"):
            url = GITHUB_RAW_BASE.format(repo=clean_repo, branch=branch, path="plugin.json")
            try:
                resp = await self._client.get(url, timeout=10.0)
                if resp.status_code == 200:
                    data = resp.json()
                    data["source"] = clean_repo
                    data["branch"] = branch
                    data["provider"] = "github"
                    return PluginManifest.from_dict(data)
            except Exception:
                pass
        return None


class URLProvider(PluginProvider):
    """Download a plugin from a direct URL (zip or .py)."""
    name = "url"

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
        elif filename.endswith(".tar.gz") or filename.endswith(".tgz"):
            with tarfile.open(file_path, "r:gz") as t:
                t.extractall(dest)
            file_path.unlink(missing_ok=True)

        return dest


class RegistryProvider(PluginProvider):
    """Install plugins from the Altruix official registry."""
    name = "registry"

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
        if manifest.provider == "github":
            return await GithubProvider(self._client).fetch(manifest, dest_dir)
        return await URLProvider(self._client).fetch(manifest, dest_dir)


class PluginManager:
    """
    Central plugin manager for Altruix (APM v3).
    Supports subcategory segregation, selective component loading,
    pre-flight import satisfaction checks, and hot reloads.
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

    @property
    def providers(self) -> List[PluginProvider]:
        return self._custom_providers

    def add_provider(self, provider: PluginProvider) -> None:
        self._custom_providers.append(provider)

    def _get_provider(self, provider_name: str) -> PluginProvider:
        return self._providers.get(provider_name, self._providers["url"])

    async def resolve_manifest(self, source: str, provider: str = "github") -> Optional[PluginManifest]:
        src_clean = source.strip().lower()
        if src_clean in PLUGIN_SHORTCUTS:
            source = PLUGIN_SHORTCUTS[src_clean]
            provider = "github"
        p = self._get_provider(provider)
        return await p.resolve(source)

    def _discover_subcategories_from_disk(self, plugin_dir: Path) -> Dict[str, Dict[str, Any]]:
        """Automatically detect segregated subcategories within an installed plugin directory."""
        discovered: Dict[str, Dict[str, Any]] = {}
        if not plugin_dir.is_dir():
            return discovered

        for child in plugin_dir.iterdir():
            if child.is_dir() and not child.name.startswith((".", "_", "temp")):
                # Check if directory contains python plugins
                py_files = list(child.glob("*.py"))
                if py_files:
                    sub_deps = []
                    req_file = child / "requirements.txt"
                    if req_file.exists():
                        try:
                            lines = [l.strip() for l in req_file.read_text(encoding="utf-8").splitlines()]
                            sub_deps = [l for l in lines if l and not l.startswith("#")]
                        except Exception:
                            pass

                    discovered[child.name] = {
                        "name": child.name.replace("_", " ").title(),
                        "path": child.name,
                        "dependencies": sub_deps,
                        "file_count": len(py_files),
                        "enabled": True,
                    }
        return discovered

    async def _ensure_dependencies(self, deps: List[str], msg: Optional[Any] = None) -> Tuple[bool, List[str]]:
        """
        Fast pre-flight check. Inspects importlib specs first.
        Only runs pip install if packages are genuinely missing.
        """
        if not deps:
            return True, []

        missing = [d for d in deps if not is_package_satisfied(d)]
        if not missing:
            logger.info(f"All {len(deps)} dependencies satisfied via existing environment.")
            return True, []

        missing_str = ", ".join(missing)
        logger.info(f"Installing missing dependencies via pip: {missing_str}")
        if msg:
            with contextlib.suppress(Exception):
                await msg.edit_msg(f"📦 Installing missing packages: <code>{missing_str}</code>...")

        proc = await asyncio.create_subprocess_exec(
            sys.executable, "-m", "pip", "install", "--prefer-binary", "--quiet", *missing,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            err_text = stderr.decode(errors="replace")
            logger.warning(f"Some dependencies could not be installed: {err_text}")
            return False, missing

        return True, []

    async def install(
        self,
        source: str,
        provider: str = "github",
        manifest: Optional[PluginManifest] = None,
        subcategories: Optional[List[str]] = None,
        msg: Optional[Any] = None,
    ) -> Optional[PluginManifest]:
        """
        Install a plugin with optional subcategory segregation.
        Example: install('vc') or install('username/XtraPlugins', subcategories=['media', 'utilities'])
        """
        # Resolve package shortcuts (e.g. 'vc' -> 'Altruix/VCPlugin')
        src_clean = source.strip().lower()
        if src_clean in PLUGIN_SHORTCUTS:
            source = PLUGIN_SHORTCUTS[src_clean]
            provider = "github"
        elif source.startswith(("http://github.com/", "https://github.com/", "git@github.com:")):
            provider = "github"
            source = GithubProvider._normalize_repo(source)
        elif source.startswith(("http://", "https://")):
            provider = "url"
        elif "/" in source and not source.startswith((".", "/")):
            provider = "github"

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
                await msg.edit_msg(f"📦 Fetching plugin <code>{manifest.name}</code>...")

        # Fetch plugin files to disk
        provider_obj = self._get_provider(manifest.provider)
        plugin_path = await provider_obj.fetch(manifest, self.PLUGIN_DIR)

        # Inspect local plugin.json if present
        local_pjson = plugin_path / "plugin.json"
        if local_pjson.exists():
            try:
                local_data = json.loads(local_pjson.read_text(encoding="utf-8"))
                for k, v in local_data.items():
                    if hasattr(manifest, k) and v:
                        setattr(manifest, k, v)
            except Exception:
                pass

        # Discover disk subcategories
        discovered_subs = self._discover_subcategories_from_disk(plugin_path)
        if discovered_subs:
            # Merge with manifest subcategories
            for sname, sdata in discovered_subs.items():
                if sname not in manifest.subcategories:
                    manifest.subcategories[sname] = sdata

        # Determine active subcategories
        if subcategories:
            clean_req_subs = [s.strip().lower() for s in subcategories if s.strip()]
            valid_subs = [s for s in clean_req_subs if s in manifest.subcategories]
            manifest.active_subcategories = valid_subs if valid_subs else list(manifest.subcategories.keys())
        else:
            manifest.active_subcategories = list(manifest.subcategories.keys())

        # Collect required dependencies for active modules
        target_deps: Set[str] = set(manifest.dependencies)
        for sname in manifest.active_subcategories:
            sub_info = manifest.subcategories.get(sname, {})
            target_deps.update(sub_info.get("dependencies", []))

        # Check and install missing dependencies with pre-flight satisfaction
        success, failed_deps = await self._ensure_dependencies(list(target_deps), msg)
        if not success:
            manifest.quarantined = True
            manifest.quarantine_reason = f"Missing dependencies: {', '.join(failed_deps)}"

        # Load plugin modules into Altruix
        await self._load_plugin_modules(manifest, plugin_path)

        self._installed[manifest.name] = manifest
        self._save_manifest_index()

        if msg:
            with contextlib.suppress(Exception):
                active_str = f" ({len(manifest.active_subcategories)} subcategories active)" if manifest.active_subcategories else ""
                await msg.edit_msg(f"✅ Plugin <code>{manifest.name}</code> installed successfully!{active_str}")

        logger.info(f"Plugin installed: {manifest.name} v{manifest.version} [active: {manifest.active_subcategories}]")
        return manifest

    async def _load_plugin_modules(self, manifest: PluginManifest, plugin_path: Path) -> None:
        """Selectively load Python modules matching active subcategories."""
        if not self.altruix:
            return

        if plugin_path.is_file():
            await self.altruix.load_from_directory(str(plugin_path))
            return

        # If plugin has segregated subcategories
        if manifest.subcategories:
            for sname, sdata in manifest.subcategories.items():
                if sname in manifest.active_subcategories and sdata.get("enabled", True):
                    sub_dir = plugin_path / sdata.get("path", sname)
                    if sub_dir.exists():
                        for f in sub_dir.glob("*.py"):
                            if not f.name.startswith("_"):
                                await self.altruix.load_from_directory(str(f))
            # Also load root level py files
            for root_py in plugin_path.glob("*.py"):
                if not root_py.name.startswith("_"):
                    await self.altruix.load_from_directory(str(root_py))
        else:
            # Default recursive load
            for f in plugin_path.rglob("*.py"):
                if not f.name.startswith(("_", ".")):
                    await self.altruix.load_from_directory(str(f))

    async def uninstall(self, plugin_name: str, msg: Optional[Any] = None) -> bool:
        """Uninstall a plugin and remove all files."""
        if plugin_name not in self._installed:
            return False

        plugin_dir = self.PLUGIN_DIR / plugin_name
        if plugin_dir.exists():
            shutil.rmtree(plugin_dir, ignore_errors=True)

        for f in self.PLUGIN_DIR.glob(f"{plugin_name}.py"):
            f.unlink(missing_ok=True)

        del self._installed[plugin_name]
        self._save_manifest_index()

        if msg:
            with contextlib.suppress(Exception):
                await msg.edit_msg(f"🗑️ Plugin <code>{plugin_name}</code> uninstalled cleanly.")

        logger.info(f"Plugin uninstalled: {plugin_name}")
        return True

    async def update(self, plugin_name: str, msg: Optional[Any] = None) -> Optional[PluginManifest]:
        """Update an installed plugin while preserving active subcategories."""
        if plugin_name not in self._installed:
            raise ValueError(f"Plugin '{plugin_name}' is not installed.")

        manifest = self._installed[plugin_name]
        active_subs = manifest.active_subcategories
        await self.uninstall(plugin_name)
        return await self.install(manifest.source, manifest.provider, manifest, subcategories=active_subs, msg=msg)

    async def enable_subcategory(self, plugin_name: str, subcategory: str) -> bool:
        """Activate and hot-load a segregated subcategory."""
        manifest = self._installed.get(plugin_name)
        if not manifest or subcategory not in manifest.subcategories:
            return False

        if subcategory not in manifest.active_subcategories:
            manifest.active_subcategories.append(subcategory)

        manifest.subcategories[subcategory]["enabled"] = True
        self._save_manifest_index()

        plugin_dir = self.PLUGIN_DIR / plugin_name
        sub_dir = plugin_dir / manifest.subcategories[subcategory].get("path", subcategory)
        if sub_dir.exists() and self.altruix:
            for f in sub_dir.glob("*.py"):
                if not f.name.startswith("_"):
                    await self.altruix.load_from_directory(str(f))
        return True

    async def disable_subcategory(self, plugin_name: str, subcategory: str) -> bool:
        """Deactivate a subcategory without deleting its files."""
        manifest = self._installed.get(plugin_name)
        if not manifest or subcategory not in manifest.subcategories:
            return False

        if subcategory in manifest.active_subcategories:
            manifest.active_subcategories.remove(subcategory)

        manifest.subcategories[subcategory]["enabled"] = False
        self._save_manifest_index()
        return True

    async def doctor(self) -> Dict[str, Any]:
        """Diagnose health of all installed plugins and Python environment."""
        report = {
            "total_plugins": len(self._installed),
            "healthy": [],
            "issues": [],
            "missing_dependencies": {},
        }

        for pname, manifest in self._installed.items():
            plugin_dir = self.PLUGIN_DIR / pname
            if not plugin_dir.exists() and not (self.PLUGIN_DIR / f"{pname}.py").exists():
                report["issues"].append(f"{pname}: File system path missing")
                continue

            # Check dependencies
            all_target_deps = set(manifest.dependencies)
            for sname in manifest.active_subcategories:
                sinfo = manifest.subcategories.get(sname, {})
                all_target_deps.update(sinfo.get("dependencies", []))

            missing = [d for d in all_target_deps if not is_package_satisfied(d)]
            if missing:
                report["missing_dependencies"][pname] = missing
                report["issues"].append(f"{pname}: Missing {len(missing)} packages ({', '.join(missing)})")
            else:
                report["healthy"].append(pname)

        return report

    async def repair(self, msg: Optional[Any] = None) -> Tuple[int, int]:
        """Batch-resolve all missing dependencies across all installed plugins."""
        doc = await self.doctor()
        all_missing = []
        for missing_list in doc["missing_dependencies"].values():
            all_missing.extend(missing_list)

        unique_missing = sorted(list(set(all_missing)))
        if not unique_missing:
            if msg:
                with contextlib.suppress(Exception):
                    await msg.edit_msg("✅ <b>Doctor Report:</b> All plugin dependencies are already 100% satisfied!")
            return 0, 0

        success, failed = await self._ensure_dependencies(unique_missing, msg)
        repaired = len(unique_missing) - len(failed)
        return repaired, len(failed)

    async def list_installed(self) -> List[PluginManifest]:
        return list(self._installed.values())

    async def list_registry(self) -> Dict[str, Any]:
        registry_provider = self._providers["registry"]
        return await registry_provider._load_registry()


PluginMetadata = PluginManifest
GitHubPluginProvider = GithubProvider
