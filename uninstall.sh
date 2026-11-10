#!/usr/bin/env bash
# Switches the Claude in Chrome extension back to the store version.
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

running() { pgrep -f "chrome($|[^/]*$)" >/dev/null 2>&1 || pgrep -f "chrome --" >/dev/null 2>&1; }

if running; then
  echo "Chrome is running. Close it and run again."
  exit 1
fi

python3 "$DIR/patch.py" --revert
