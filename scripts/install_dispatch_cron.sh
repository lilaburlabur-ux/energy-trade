#!/bin/bash
# One-time installer: adds the energy-dispatch block to YOUR crontab.
# Run it yourself:  bash ~/energy-trade/scripts/install_dispatch_cron.sh
# Idempotent — refuses to double-install.
set -e
if crontab -l 2>/dev/null | grep -q "energy-dispatch"; then
  echo "energy-dispatch block already installed — nothing to do."; exit 0
fi
( crontab -l 2>/dev/null; cat <<'EOF'
# energy-dispatch: Mac fires energy-trade cloud refreshes (GitHub cron is throttled to a few runs/day). Times are local.
*/5 10-23 * * 1-5 /Users/pierre/energy-trade/scripts/dispatch_refresh.sh refresh-data.yml >/dev/null 2>&1
*/5 0-1 * * 2-6 /Users/pierre/energy-trade/scripts/dispatch_refresh.sh refresh-data.yml >/dev/null 2>&1
*/15 * * * * /Users/pierre/energy-trade/scripts/dispatch_refresh.sh refresh-data.yml >/dev/null 2>&1
7-59/15 10-23 * * 1-5 /Users/pierre/energy-trade/scripts/dispatch_refresh.sh hot-refresh.yml >/dev/null 2>&1
*/20 * * * * /Users/pierre/energy-trade/scripts/dispatch_refresh.sh news-refresh.yml >/dev/null 2>&1
45 15,22 * * 1-5 /Users/pierre/energy-trade/scripts/dispatch_refresh.sh universe-refresh.yml >/dev/null 2>&1
25 22 * * 1-5 /Users/pierre/energy-trade/scripts/dispatch_refresh.sh post-close-research.yml >/dev/null 2>&1
EOF
) | crontab -
echo "Installed. Dispatch log: ~/energy-trade/logs/dispatch.log"
crontab -l | grep -c dispatch_refresh | xargs -I{} echo "{} energy-dispatch entries active."
