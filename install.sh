#!/usr/bin/env bash
# Installs the unblocked copy of the Claude in Chrome extension.
#
# Chrome must be closed — the script rewrites its Preferences.
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

running() { pgrep -f "chrome($|[^/]*$)" >/dev/null 2>&1 || pgrep -f "chrome --" >/dev/null 2>&1; }

if running; then
  echo "Chrome is running. Close it (including background) and run again."
  echo "  flatpak:  flatpak kill com.google.Chrome"
  echo "  else:     pkill -f chrome"
  exit 1
fi

python3 "$DIR/patch.py"
