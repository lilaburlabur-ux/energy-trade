#!/bin/bash
# dispatch_all.sh — one entry point fired every 5 minutes by launchd
# (online.energytrade.dispatch). Decides per tick which cloud workflows to
# trigger, replicating the cadence the individual cron lines intended:
#   refresh-data     every 5 min during the extended US session, 15-min floor 24/7
#   hot-refresh      every 15 min during the session
#   news-refresh     every 20 min, 24/7
#   universe-refresh 15:45 and 22:45 local
#   post-close-research 22:25 local (weekdays)
D="$HOME/energy-trade/scripts/dispatch_refresh.sh"
M=$((10#$(date +%M)))          # minute 0-59 (strip leading zero)
H=$((10#$(date +%H)))          # local hour
DOW=$(date +%u)                # 1=Mon..7=Sun
TICK=$(( M / 5 * 5 ))          # normalized 5-min tick: 0,5,10...

session=0
if [ "$DOW" -le 5 ] && [ "$H" -ge 10 ]; then session=1; fi          # 10:00-23:59 local Mon-Fri
if [ "$DOW" -ge 2 ] && [ "$DOW" -le 6 ] && [ "$H" -le 1 ]; then session=1; fi  # 00:00-01:59 spillover

# quotes: every tick in session; 15-min floor off-session (futures tape)
if [ "$session" = 1 ] || [ $(( TICK % 15 )) -eq 0 ]; then "$D" refresh-data.yml; fi
# hot tickers: every 15 min in session
if [ "$session" = 1 ] && [ $(( TICK % 15 )) -eq 0 ]; then "$D" hot-refresh.yml; fi
# news: every 20 min, around the clock
if [ $(( TICK % 20 )) -eq 0 ]; then "$D" news-refresh.yml; fi
# slow fields twice a day; research after the close (weekdays)
if [ "$DOW" -le 5 ] && [ "$TICK" -eq 45 ] && { [ "$H" -eq 15 ] || [ "$H" -eq 22 ]; }; then "$D" universe-refresh.yml; fi
if [ "$DOW" -le 5 ] && [ "$H" -eq 22 ] && [ "$TICK" -eq 25 ]; then "$D" post-close-research.yml; fi
exit 0
