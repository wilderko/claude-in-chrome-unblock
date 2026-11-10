#!/usr/bin/env bash
# Nainštaluje odblokovanú kópiu rozšírenia Claude in Chrome.
#
# Chrome musí byť zatvorený — skript prepisuje jeho Preferences.
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if pgrep -f "chrome" >/dev/null 2>&1; then
  echo "Chrome beží. Zatvor ho (aj na pozadí) a spusti znova."
  echo "  flatpak:  flatpak kill com.google.Chrome"
  echo "  inak:     pkill -f chrome"
  exit 1
fi

python3 "$DIR/patch.py"
