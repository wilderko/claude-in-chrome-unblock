#!/usr/bin/env python3
"""Verifies that the unblocked copy of Claude in Chrome is still in place and patched.

The patch lives in an unpacked copy, so nothing re-applies it on its own. A store
update, a Chrome repair, a reinstall or a manual cleanup can silently put the
blocklisted extension back. This script fails loudly so that never goes unnoticed
in the middle of a Tinder session.

Usage:
    python3 check.py        # verify only, exit 1 when anything is off
    python3 check.py --fix  # verify, and repair when Chrome is not running

Exit codes: 0 healthy, 1 broken (or repair failed), 2 nothing to check.
"""
import glob
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import patch  # noqa: E402  (reuse profile discovery and the installer)


def problems(profile):
    """Return a list of what is wrong with this profile (empty = healthy)."""
    bad = []
    pref = patch.prefs_path(profile)
    try:
        d = json.load(open(pref))
    except Exception as e:
        return [f"Preferences unreadable ({e})"]

    e = d.get("extensions", {}).get("settings", {}).get(patch.EXT_ID)
    if not e:
        return ["extension is not installed at all"]
    if e.get("location") != 4:
        bad.append(f"not the unpacked copy (location={e.get('location')})")
    if os.path.abspath(e.get("path", "")) != os.path.abspath(patch.target(profile)):
        bad.append(f"path points elsewhere ({e.get('path')})")
    if e.get("disable_reasons"):
        bad.append(f"disabled, reasons {e['disable_reasons']}")

    dst = patch.target(profile)
    if not os.path.isfile(os.path.join(dst, "manifest.json")):
        bad.append(f"copy missing ({dst})")

    targets = glob.glob(os.path.join(dst, "assets", "mcpPermissions-*.js"))
    if not targets:
        bad.append("mcpPermissions-*.js missing")
    for p in targets:
        src = open(p, encoding="utf-8").read()
        for needle in ("DISABLE_BLOCKLIST", "getRawCategory"):
            if needle not in src:
                bad.append(f"patch gone from {os.path.basename(p)} ({needle})")
        if subprocess.run(["node", "--check", p], capture_output=True).returncode:
            bad.append(f"syntax error in {os.path.basename(p)}")

    markers = glob.glob(os.path.join(dst, "assets", "agent-visual-indicator.js-*.js"))
    if not markers:
        bad.append("agent-visual-indicator.js-*.js missing")
    for p in markers:
        src = open(p, encoding="utf-8").read()
        if 'e.setAttribute("data-unblock","1")' not in src:
            bad.append(f"agent detection not hidden in {os.path.basename(p)}")
        if subprocess.run(["node", "--check", p], capture_output=True).returncode:
            bad.append(f"syntax error in {os.path.basename(p)}")

    store = glob.glob(os.path.join(profile, "Default", "Extensions", patch.EXT_ID, "*"))
    if store and os.path.isfile(os.path.join(dst, "manifest.json")):
        store_ver = max(store, key=os.path.getmtime)
        try:
            if (json.load(open(os.path.join(store_ver, "manifest.json")))["version"]
                    != json.load(open(os.path.join(dst, "manifest.json")))["version"]):
                bad.append("the store has a newer version than the patched copy")
        except Exception:
            pass
    return bad


def chrome_running():
    for pattern in ("chrome$", "chrome --", "chrome(.exe)?$"):
        if subprocess.run(["pgrep", "-f", pattern], capture_output=True).returncode == 0:
            return True
    return False


def main():
    fix = "--fix" in sys.argv
    found = list(patch.profiles())
    if not found:
        print("Tinder-unblock: no Chrome profile found.")
        return 2

    broken = {}
    for profile in found:
        bad = problems(profile)
        if bad:
            broken[profile] = bad
        else:
            ver = "?"
            try:
                ver = json.load(open(os.path.join(patch.target(profile), "manifest.json")))["version"]
            except Exception:
                pass
            print(f"Tinder-unblock: OK — {profile} (v{ver}, patched, enabled)")

    if not broken:
        return 0

    for profile, bad in broken.items():
        print(f"Tinder-unblock: BROKEN — {profile}")
        for b in bad:
            print(f"  - {b}")

    if not fix:
        print("Tinder-unblock: fix with `~/AI/untinder/repo/install.sh` (Chrome must be closed).")
        return 1

    if chrome_running():
        print("Tinder-unblock: Chrome is running, cannot repair now. Close it and run install.sh.")
        return 1

    print("Tinder-unblock: repairing…")
    rc = 0
    for profile in broken:
        rc |= patch.install(profile)
    return rc


if __name__ == "__main__":
    sys.exit(main())
