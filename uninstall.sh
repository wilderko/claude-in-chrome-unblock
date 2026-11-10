#!/usr/bin/env bash
# Vráti rozšírenie Claude in Chrome späť na verziu z obchodu.
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if pgrep -f "chrome" >/dev/null 2>&1; then
  echo "Chrome beží. Zatvor ho a spusti znova."
  exit 1
fi

python3 "$DIR/patch.py" --revert
