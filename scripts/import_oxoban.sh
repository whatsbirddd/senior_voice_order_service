#!/usr/bin/env bash
set -euo pipefail

BACKEND_BASE=${BACKEND_BASE:-http://localhost:3000}
HERE=$(cd "$(dirname "$0")" && pwd)
DATA="$HERE/../data/oxoban_menu.json"

if [ ! -f "$DATA" ]; then
  echo "Data file not found: $DATA" >&2
  exit 1
fi

echo "Posting to $BACKEND_BASE/api/menu/import ..."
curl -sS -X POST "$BACKEND_BASE/api/menu/import" \
  -H 'Content-Type: application/json' \
  --data-binary @"$DATA"
echo

