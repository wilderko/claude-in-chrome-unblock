#!/usr/bin/env python3
"""Disables the site blocklist in the "Claude in Chrome" extension.

For every URL the extension fetches a category from
api.anthropic.com/api/web/url_hash_check/browser_extension and redirects the
tab to blocked.html on category1 (blocked, e.g. tinder.com).

This script patches getCategory() to return "category0" (safe) for everything
except category3/category4, which are left alone (they only add a permission
prompt / copyright notice).

Why an unpacked copy instead of editing files in place: Chrome verifies the
_metadata hashes on startup, marks the edited store copy as corrupted and
reinstalls it. The script therefore installs an unpacked copy (location 4),
where hashes are not checked. The ID stays the same (the manifest carries a
"key"), so the claude.ai login keeps working.

Usage:
    ./install.sh              # normal entry point
    python3 patch.py          # same thing directly
    python3 patch.py --revert # switch back to the store version

The script must run with Chrome closed (it edits Preferences).

Re-run after every store update of the extension.
"""
import glob
import json
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
EXT_ID = "fcoeoabgfenejglbffodgkkbkcdhcgfn"
PROFILES = [
    "~/.var/app/com.google.Chrome/config/google-chrome",  # flatpak
    "~/.config/google-chrome",
    "~/.config/chromium",
    "~/Library/Application Support/Google/Chrome",  # macOS
]
DIR_NAME = "ClaudeExtUnblocked"

# Wraps getCategory() so blocking categories become category0.
HELPER = (
    'static DISABLE_BLOCKLIST=!0;'
    'static unblockCategory(e){return null==e||"category0"===e||"category3"===e'
    '||"category4"===e?e:"category0"}'
)


def profiles():
    for p in PROFILES:
        p = os.path.expanduser(p)
        if os.path.isfile(os.path.join(p, "Default", "Preferences")):
            yield p


def prefs_path(profile):
    return os.path.join(profile, "Default", "Preferences")


def target(profile):
    return os.path.join(profile, DIR_NAME)


def source_copy(profile):
    """Source: newest store copy, otherwise the bundled snapshot."""
    store = glob.glob(os.path.join(profile, "Default", "Extensions", EXT_ID, "*"))
    cand = [d for d in store if os.path.isfile(os.path.join(d, "manifest.json"))]
    if cand:
        return max(cand, key=os.path.getmtime)
    snap = os.path.join(HERE, "extension")
    return snap if os.path.isfile(os.path.join(snap, "manifest.json")) else None


def patch_js(path):
    src = open(path, encoding="utf-8").read()
    if "DISABLE_BLOCKLIST" in src:
        return True

    m = re.search(r"([A-Za-z_$][\w$]*)=class\{static cache=new Map;", src)
    if not m:
        print(f"  ! unknown structure in {os.path.basename(path)} (new build?)")
        return False
    cls = m.group(1)

    anchor = "static cache=new Map;"
    src = src.replace(anchor, anchor + HELPER, 1)

    old = "static async getCategory(e){if(e=this.normalizeUrl(e),"
    if src.count(old) != 1:
        print(f"  ! getCategory not found in {os.path.basename(path)}")
        return False
    new = (
        f"static async getCategory(e){{if(!{cls}.DISABLE_BLOCKLIST)return {cls}.getRawCategory(e);"
        f"const t={cls}.getRawCategory(e),n={cls}.unblockCategory;return t.then(n,n)}}"
        "static async getRawCategory(e){if(e=this.normalizeUrl(e),"
    )
    src = src.replace(old, new, 1)

    tmp = path[: -len(".js")] + ".__tmp.js"
    open(tmp, "w", encoding="utf-8").write(src)
    ok = subprocess.run(["node", "--check", tmp], capture_output=True).returncode == 0
    if ok:
        os.replace(tmp, path)
    else:
        os.unlink(tmp)
        print(f"  ! syntax error in {os.path.basename(path)}")
    return ok


def set_entry(profile, location, path, from_store):
    pref = prefs_path(profile)
    shutil.copy(pref, pref + ".unblock.bak")
    d = json.load(open(pref))
    e = d["extensions"]["settings"].setdefault(EXT_ID, {})
    e.update(
        location=location,
        path=path,
        from_webstore=from_store,
        disable_reasons=[],
    )
    if from_store:
        e.setdefault("creation_flags", 9)
    else:
        for k in ("cws-info", "idle_install_info", "allowlist", "dnr_keep_excess_allocation"):
            e.pop(k, None)
        e.setdefault("creation_flags", 38)
        e.setdefault("withholding_permissions", False)
    json.dump(d, open(pref, "w"), separators=(",", ":"))


def install(profile):
    src = source_copy(profile)
    if not src:
        print(f"{profile}\n  - extension not installed and no snapshot available")
        return 1

    dst = target(profile)
    if os.path.abspath(src) != os.path.abspath(dst):
        shutil.rmtree(dst, ignore_errors=True)
        shutil.copytree(src, dst)
    shutil.rmtree(os.path.join(dst, "_metadata"), ignore_errors=True)

    targets = glob.glob(os.path.join(dst, "assets", "mcpPermissions-*.js"))
    if not targets:
        print(f"{profile}\n  ! mcpPermissions-*.js missing from the extension")
        return 1
    if not all(patch_js(t) for t in targets):
        return 1

    set_entry(profile, 4, dst, False)
    print(f"{profile}\n  - installed: {dst}")
    return 0


def revert(profile):
    """Reinstates the store copy. The path must be relative, otherwise Chrome
    will not find the copy even after reinstalling it."""
    store = glob.glob(os.path.join(profile, "Default", "Extensions", EXT_ID, "*"))
    if store:
        path = os.path.join(EXT_ID, os.path.basename(max(store, key=os.path.getmtime)))
    else:
        # The copy is gone (Chrome deletes it when switching to unpacked).
        # Derive the path from the manifest; Chrome re-downloads it on start.
        ver = None
        try:
            ver = json.load(open(os.path.join(target(profile), "manifest.json")))["version"]
        except Exception:
            ver = json.load(
                open(os.path.join(HERE, "extension", "manifest.json"))
            )["version"]
        path = os.path.join(EXT_ID, f"{ver}_0")
    set_entry(profile, 1, path, True)
    shutil.rmtree(target(profile), ignore_errors=True)
    print(f"{profile}\n  - reverted to the store version")
    return 0


def main():
    undo = "--revert" in sys.argv
    found = list(profiles())
    if not found:
        print("No Chrome profile found.")
        return 1
    rc = 0
    for profile in found:
        rc |= revert(profile) if undo else install(profile)
    print("\nDone. Start Chrome.")
    return rc


if __name__ == "__main__":
    sys.exit(main())
