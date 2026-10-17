# Copyright (C) 2021-present by Altruix@Github, < https://github.com/Altruix >.
#
# This file is part of < https://github.com/Altruix/Altruix > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/Altriux/Altruix/blob/main/LICENSE >
#
# All rights reserved.

"""
APM Environment Pre-Boot & Dependency Resolver
==============================================
Runs before the bot process to verify, isolate, and batch-install
dependencies for all external plugins and segregated subcategories.

Features:
- Fast importlib find_spec check (never runs pip if already satisfied).
- Subcategory dependency segregation.
- Export unified requirements.txt for Docker / CI / VPS / Heroku.
- Non-blocking pre-boot execution so the bot boots in <1s with 0 runtime pip calls.

Usage:
  py -3 -m Main.core.apm_env_setup
  py -3 -m Main.core.apm_env_setup --export
  py -3 -m Main.core.apm_env_setup --check-only
"""

import sys
import os
import json
import re
import subprocess
import importlib.util
from pathlib import Path
from typing import List, Dict, Tuple, Set

# Safe UTF-8 console output on Windows
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

MANIFESTS_FILE = Path("./Main/plugins/external/.manifests.json")
EXTERNAL_DIR = Path("./Main/plugins/external")

# Standard package-name to import-module mapping
PACKAGE_TO_MODULE = {
    "pillow": "PIL",
    "beautifulsoup4": "bs4",
    "pyyaml": "yaml",
    "opencv-python": "cv2",
    "opencv-python-headless": "cv2",
    "pypdf": "pypdf",
    "pypdf2": "PyPDF2",
    "sympy": "sympy",
    "qrcode": "qrcode",
    "httpx": "httpx",
    "aiofiles": "aiofiles",
    "apscheduler": "apscheduler",
    "geopy": "geopy",
    "pytesseract": "pytesseract",
    "mutagen": "mutagen",
    "python-dateutil": "dateutil",
    "dnspython": "dns",
    "cryptography": "cryptography",
    "requests": "requests",
    "telethon": "telethon",
}


def clean_package_name(spec: str) -> str:
    """Extract bare package name from version specifier (e.g. 'pillow>=10.0' -> 'pillow')."""
    return re.split(r"[><=~!;]", spec.strip())[0].strip().lower()


def is_package_satisfied(package_spec: str) -> bool:
    """Check if a Python package is already importable without running pip."""
    bare = clean_package_name(package_spec)
    module_name = PACKAGE_TO_MODULE.get(bare, bare.replace("-", "_"))
    try:
        spec = importlib.util.find_spec(module_name)
        return spec is not None
    except Exception:
        return False


def collect_all_plugin_dependencies(filter_plugin: str = None, filter_sub: str = None) -> Tuple[Set[str], Dict[str, List[str]]]:
    """
    Collect all dependencies across all installed external plugins
    and segregated subcategories from .manifests.json and requirements.txt files.
    """
    all_deps: Set[str] = set()
    breakdown: Dict[str, List[str]] = {}

    if MANIFESTS_FILE.exists():
        try:
            manifests = json.loads(MANIFESTS_FILE.read_text(encoding="utf-8"))
            for pname, pdata in manifests.items():
                if filter_plugin and pname.lower() != filter_plugin.lower():
                    continue

                p_deps = pdata.get("dependencies", [])
                active_subs = pdata.get("active_subcategories", [])
                sub_defs = pdata.get("subcategories", {})

                # If subcategories are segregated
                if sub_defs:
                    if active_subs:
                        # Only collect dependencies for active subcategories
                        for sub_name in active_subs:
                            if filter_sub and sub_name.lower() != filter_sub.lower():
                                continue
                            sub_info = sub_defs.get(sub_name, {})
                            sub_deps = sub_info.get("dependencies", [])
                            all_deps.update(sub_deps)
                            breakdown[f"{pname}/{sub_name}"] = sub_deps
                    else:
                        # All subcategories active
                        for sub_name, sub_info in sub_defs.items():
                            if filter_sub and sub_name.lower() != filter_sub.lower():
                                continue
                            sub_deps = sub_info.get("dependencies", [])
                            all_deps.update(sub_deps)
                            breakdown[f"{pname}/{sub_name}"] = sub_deps
                else:
                    all_deps.update(p_deps)
                    breakdown[pname] = p_deps
        except Exception as e:
            print(f"[APM ENV] Warning reading manifests index: {e}")

    # Also inspect local requirements.txt files in external plugins
    if EXTERNAL_DIR.exists():
        for req_path in EXTERNAL_DIR.rglob("requirements.txt"):
            try:
                rel_parts = req_path.relative_to(EXTERNAL_DIR).parts
                label = "/".join(rel_parts[:-1]) if len(rel_parts) > 1 else rel_parts[0]
                lines = [line.strip() for line in req_path.read_text(encoding="utf-8").splitlines()]
                valid_lines = [l for l in lines if l and not l.startswith("#")]
                all_deps.update(valid_lines)
                if label not in breakdown:
                    breakdown[label] = valid_lines
            except Exception:
                pass

    # Also inspect local workspace plugin suites
    for suite_name in ("XtraPlugins", "XtraPluginsAI"):
        suite_path = Path(f"./{suite_name}")
        if suite_path.is_dir():
            pjson = suite_path / "plugin.json"
            if pjson.exists():
                try:
                    data = json.loads(pjson.read_text(encoding="utf-8"))
                    p_deps = data.get("dependencies", [])
                    all_deps.update(p_deps)
                    sub_defs = data.get("subcategories", {})
                    for sname, sinfo in sub_defs.items():
                        sdeps = sinfo.get("dependencies", [])
                        all_deps.update(sdeps)
                        breakdown[f"{suite_name}/{sname}"] = sdeps
                except Exception:
                    pass
            for req in suite_path.rglob("requirements.txt"):
                try:
                    lines = [l.strip() for l in req.read_text(encoding="utf-8").splitlines()]
                    valid = [l for l in lines if l and not l.startswith("#")]
                    all_deps.update(valid)
                except Exception:
                    pass

    return all_deps, breakdown


def verify_and_install_dependencies(check_only: bool = False) -> bool:
    """Inspect all required packages, determine which are missing, and batch-install."""
    all_deps, breakdown = collect_all_plugin_dependencies()
    if not all_deps:
        print("[APM ENV] No external plugin dependencies registered.")
        return True

    unique_missing: Dict[str, str] = {}
    satisfied_pkgs: Set[str] = set()

    for dep in sorted(all_deps):
        base_name = clean_package_name(dep)
        if is_package_satisfied(dep):
            satisfied_pkgs.add(base_name)
        else:
            if base_name not in unique_missing:
                unique_missing[base_name] = dep
            elif ">=" in dep or "==" in dep:
                unique_missing[base_name] = dep

    for sat in satisfied_pkgs:
        unique_missing.pop(sat, None)

    missing = list(unique_missing.values())
    total_packages = len(satisfied_pkgs) + len(missing)

    print(f"[APM ENV] Status: {len(satisfied_pkgs)}/{total_packages} unique package dependencies satisfied.")

    if not missing:
        print("✅ [APM ENV] All plugin dependencies are satisfied. Bot will boot with 0ms pip overhead!")
        return True

    print(f"⚠️  [APM ENV] {len(missing)} missing dependencies detected:")
    for m in missing:
        print(f"   • {m}")

    if check_only:
        return False

    print("\n📦 [APM ENV] Batch-installing missing dependencies cleanly via pip...")
    cmd = [sys.executable, "-m", "pip", "install", "--prefer-binary", *missing]
    try:
        proc = subprocess.run(cmd, check=True)
        print("✅ [APM ENV] Successfully installed all required plugin dependencies!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ [APM ENV] Pip batch-installation returned error code {e.returncode}.")
        return False


def export_unified_requirements(out_path: str = "external_requirements.txt") -> None:
    """Generate a clean unified requirements file for deployment environments."""
    all_deps, breakdown = collect_all_plugin_dependencies()
    lines = [
        "# Auto-generated unified dependencies for Altruix External Plugins",
        "# Generated by: python -m Main.core.apm_env_setup --export",
        "",
    ]
    for label, deps in breakdown.items():
        if deps:
            lines.append(f"# [{label}]")
            lines.extend(deps)
            lines.append("")

    Path(out_path).write_text("\n".join(lines), encoding="utf-8")
    print(f"📄 [APM ENV] Exported {len(all_deps)} dependencies to {out_path}")


def sync_xtra_plugins_repos() -> bool:
    """
    Syncs extra plugin repositories if LOAD_XTRA_PLUGINS is enabled.
    Supports single or multiple repositories separated by comma, semicolon, or spaces.
    Clones missing repos, pulls updates for existing ones, and installs missing dependencies.
    """
    load_xtra = os.environ.get("LOAD_XTRA_PLUGINS", "").strip().lower() in ("true", "1", "yes", "enable")
    if not load_xtra:
        return True

    repos_str = os.environ.get("XTRA_PLUGINS_REPOS", "https://github.com/Altruix/XtraPlugins").strip()
    if not repos_str:
        return True

    repos = [r.strip() for r in re.split(r"[\s,;]+", repos_str) if r.strip()]
    all_success = True

    for repo_url in repos:
        repo_name = repo_url.rstrip("/").split("/")[-1]
        if repo_name.endswith(".git"):
            repo_name = repo_name[:-4]
        if not repo_name:
            repo_name = "XtraPlugins"

        target_dir = Path(f"./{repo_name}")
        print(f"[XTRA PLUGINS] Syncing repository: {repo_url} -> ./{repo_name}")

        try:
            if not target_dir.exists():
                print(f"[XTRA PLUGINS] Cloning {repo_url} into ./{repo_name}...")
                subprocess.run(["git", "clone", "--depth", "1", repo_url, str(target_dir)], check=True)
                print(f"✅ [XTRA PLUGINS] Cloned ./{repo_name} successfully.")
            else:
                git_dir = target_dir / ".git"
                if git_dir.exists():
                    print(f"[XTRA PLUGINS] Checking updates for ./{repo_name}...")
                    pull_res = subprocess.run(["git", "-C", str(target_dir), "pull", "--ff-only"], check=False)
                    if pull_res.returncode != 0:
                        subprocess.run(["git", "-C", str(target_dir), "fetch", "origin"], check=False)
                        subprocess.run(["git", "-C", str(target_dir), "reset", "--hard", "origin/main"], check=False)

            req_file = target_dir / "requirements.txt"
            if req_file.exists():
                deps = [
                    line.strip()
                    for line in req_file.read_text(encoding="utf-8").splitlines()
                    if line.strip() and not line.strip().startswith("#")
                ]
                missing = [d for d in deps if not is_package_satisfied(d)]
                if missing:
                    print(f"📦 [XTRA PLUGINS] Installing {len(missing)} missing dependencies for {repo_name}...")
                    subprocess.run([sys.executable, "-m", "pip", "install", "--prefer-binary", *missing], check=True)
                    print(f"✅ [XTRA PLUGINS] Dependencies for {repo_name} installed.")
        except Exception as e:
            print(f"⚠️ [XTRA PLUGINS] Error syncing repository {repo_url}: {e}")
            all_success = False

    return all_success


if __name__ == "__main__":
    if "--export" in sys.argv:
        export_unified_requirements()
    elif "--check-only" in sys.argv:
        success = verify_and_install_dependencies(check_only=True)
        sys.exit(0 if success else 1)
    else:
        sync_xtra_plugins_repos()
        success = verify_and_install_dependencies(check_only=False)
        sys.exit(0 if success else 1)

