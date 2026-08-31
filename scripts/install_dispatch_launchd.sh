#!/bin/bash
# One-time installer: replaces the (non-firing) cron entries with a launchd
# agent — macOS's native scheduler, which is what Apple actually maintains.
# Run it yourself:  bash ~/energy-trade/scripts/install_dispatch_launchd.sh
set -e
PLIST_SRC="$HOME/energy-trade/scripts/energytrade.dispatch.plist"
PLIST_DST="$HOME/Library/LaunchAgents/online.energytrade.dispatch.plist"
chmod +x "$HOME/energy-trade/scripts/dispatch_all.sh" "$HOME/energy-trade/scripts/dispatch_refresh.sh"
mkdir -p "$HOME/Library/LaunchAgents" "$HOME/energy-trade/logs"

# install + (re)load the agent
cp "$PLIST_SRC" "$PLIST_DST"
launchctl bootout "gui/$(id -u)/online.energytrade.dispatch" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST_DST"
echo "launchd agent loaded: online.energytrade.dispatch (fires every 5 min, RunAtLoad now)"

# remove the cron energy-dispatch block so nothing double-fires
if crontab -l 2>/dev/null | grep -q "energy-dispatch"; then
  crontab -l | grep -v "dispatch_refresh.sh" | grep -v "^# energy-dispatch" | crontab -
  echo "old cron energy-dispatch block removed"
fi
sleep 3
tail -3 "$HOME/energy-trade/logs/dispatch.log"
