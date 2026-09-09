#!/bin/bash
# One-paste installer for the DISPATCH_TOKEN repo secret — the single missing
# piece that keeps the pulse cloud dispatcher dead.
#
# Run it YOURSELF in your terminal (it reads your GitHub login from the Mac
# keychain, which only works in your own interactive session):
#
#     bash ~/energy-trade/scripts/set_dispatch_secret.sh
#
# What it does, transparently:
#   1. reads your saved GitHub token from the macOS keychain (never printed)
#   2. fetches the repo's public encryption key from GitHub
#   3. encrypts the token with libsodium (GitHub requirement) and stores it
#      as the Actions secret DISPATCH_TOKEN on lilaburlabur-ux/energy-trade
# The token never touches disk and is only sent to api.github.com — the same
# place it already goes on every git push.
#
# Note: this reuses your existing push token. For tighter hygiene you can
# later replace it with a fine-grained PAT scoped to this repo (Actions:
# read/write) via the same repo Settings page — the pipeline won't care.
set -euo pipefail
REPO="lilaburlabur-ux/energy-trade"
PY="$HOME/energy-trade/.venv/bin/python"

TOKEN=$(printf "protocol=https\nhost=github.com\n" | git credential fill | awk -F= '/^password=/{print $2}')
[ -n "$TOKEN" ] || { echo "ERROR: no GitHub token in keychain"; exit 1; }

KEYJSON=$(curl -sf -H "Authorization: token $TOKEN" \
  "https://api.github.com/repos/$REPO/actions/secrets/public-key")

RESP=$(SECRET_VALUE="$TOKEN" KEYJSON="$KEYJSON" "$PY" - <<'EOF'
import base64, json, os
from nacl import encoding, public
key = json.loads(os.environ["KEYJSON"])
sealed = public.SealedBox(
    public.PublicKey(key["key"].encode(), encoding.Base64Encoder())
).encrypt(os.environ["SECRET_VALUE"].encode())
print(json.dumps({"encrypted_value": base64.b64encode(sealed).decode(),
                  "key_id": key["key_id"]}))
EOF
)

CODE=$(curl -s -o /dev/null -w "%{http_code}" -X PUT \
  -H "Authorization: token $TOKEN" -H "Accept: application/vnd.github+json" \
  "https://api.github.com/repos/$REPO/actions/secrets/DISPATCH_TOKEN" \
  -d "$RESP")

if [ "$CODE" = "201" ] || [ "$CODE" = "204" ]; then
  echo "✓ DISPATCH_TOKEN secret installed on $REPO (HTTP $CODE)"
  echo "  Tell Claude 'done' — the pulse chain gets ignited and verified from there."
else
  echo "✗ failed (HTTP $CODE) — tell Claude the code you see here"
  exit 1
fi
