#!/bin/bash
# dispatch_refresh.sh <workflow-file.yml> — trigger an energy-trade GitHub
# Actions workflow from this Mac. GitHub's own cron scheduler is unreliably
# throttled (runs every-5-min jobs a handful of times per day), so local cron
# calls this to fire the cloud workflows on a real schedule.
#
# The GitHub token is pulled from the macOS keychain via git's credential
# helper AT RUNTIME — it is never stored in this file, the crontab, or logs.
# Workflows self-dedupe via their concurrency groups, so overlapping
# dispatches (ours + GitHub's own cron) are safe.
#
# Cron installs (local time):  see `crontab -l`, block "energy-dispatch".
set -u
WF="${1:?usage: dispatch_refresh.sh <workflow-file.yml>}"
REPO="lilaburlabur-ux/energy-trade"
LOG="$HOME/energy-trade/logs/dispatch.log"
mkdir -p "$(dirname "$LOG")"

TOKEN=$(printf "protocol=https\nhost=github.com\n" | git credential fill 2>/dev/null | awk -F= '/^password=/{print $2}')
if [ -z "$TOKEN" ]; then
  echo "$(date -u '+%F %T') $WF ERROR no-token" >> "$LOG"; exit 1
fi

CODE=$(curl -s -o /dev/null -w "%{http_code}" -m 25 -X POST \
  -H "Authorization: token $TOKEN" -H "Accept: application/vnd.github+json" \
  "https://api.github.com/repos/$REPO/actions/workflows/$WF/dispatches" \
  -d '{"ref":"main"}')
echo "$(date -u '+%F %T') $WF HTTP $CODE" >> "$LOG"
[ "$CODE" = "204" ]
