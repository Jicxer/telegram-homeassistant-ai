#!/bin/bash
# Run this on your machine with gh CLI authenticated
# gh auth status   ← verify you're logged in
# bash create_issues.sh

REPO="Jicxer/telegram-homeassistant-ai"

echo "Creating GitHub issues for home-ai roadmap..."

# ── Phase 1 - Remaining ────────────────────────────────────────────────────

gh issue create \
  --title "Noursi plug integration (tinytuya)" \
  --label "" \
  --body "Implement local control of NOUS A9 smart plugs via tinytuya library.

**Tasks:**
- Set up Tuya developer account and extract local keys
- Build \`tools/nous.py\` with on/off/status/power support
- Support multiple named devices loaded from .env (same pattern as machines.py)

**Environment variables:**
\`\`\`
NOUS_LAMP1_IP=192.168.x.x
NOUS_LAMP1_KEY=abc123
NOUS_LAMP2_IP=192.168.x.x
NOUS_LAMP2_KEY=abc123
\`\`\`

**Notes:**
- Local key changes if device is removed/re-added to app — don't do that once set up
- tinytuya uses TCP socket on port 6668, not simple HTTP like Shelly

**Depends on:** Physical plugs arriving" \
  --repo $REPO

# ── Phase 2 - Routines ────────────────────────────────────────────────────

gh issue create \
  --title "Good morning routine (/goodmorning)" \
  --body "Implement /goodmorning command that runs a morning automation sequence.

**Sequence:**
1. Turn on Noursi lamp 1 (desk lamp)
2. Turn on Noursi lamp 2 (room lamp)
3. Fetch today's weather summary
4. Send combined morning summary message
5. Prompt with Telegram inline keyboard: 'Wake your PC?' [Yes] [No]
   - Yes → wake_desktop()

**Notes:**
- First use of Telegram inline keyboard buttons in the bot
- Shelly is NOT part of this routine — it remains a separate crash recovery tool
- Should work when invoked manually or triggered by scheduler

**Depends on:** Noursi plug integration" \
  --repo $REPO

gh issue create \
  --title "Good night routine (/goodnight)" \
  --body "Implement /goodnight command that runs an end-of-day shutdown sequence.

**Sequence:**
1. Turn off both Noursi lamps
2. Prompt: 'Shut down your PC too?' [Yes] [No]
3. Send confirmation summary of what was turned off

**Notes:**
- Daytime-aware counterpart to /goodmorning
- Different from /leaving which handles leaving the apartment during the day

**Depends on:** Noursi plug integration" \
  --repo $REPO

gh issue create \
  --title "Leaving home and arriving home routines (/leaving, /home)" \
  --body "Implement two routines for transitioning in and out of the apartment during the day.

**/leaving:**
- Turn off all plugs
- Send confirmation summary
- Pull commute-aware weather tip (e.g. 'bring a jacket, rain at 5pm')

**/home:**
- Turn on both lamps
- Send welcome summary: any alerts fired while away? Hardware still healthy?

**Notes:**
- /leaving is the daytime equivalent of /goodnight
- /home is the arrival equivalent of /goodmorning

**Depends on:** Noursi plug integration, Ping watchdog" \
  --repo $REPO

gh issue create \
  --title "Auto-off timer for plugs" \
  --body "Allow users to schedule a plug to turn off after a delay.

**Usage:**
\`\`\`
/off lamp1 30       ← turn off lamp1 in 30 minutes
/off all 60         ← turn off all plugs in 60 minutes
\`\`\`

**Implementation:**
- Uses APScheduler (shared with scheduled routines)
- Confirm timer with message: 'Lamp 1 will turn off in 30 minutes'
- Allow cancellation: /cancel off lamp1

**Depends on:** Noursi plug integration, Scheduled routines (APScheduler)" \
  --repo $REPO

gh issue create \
  --title "Device status summary (/status)" \
  --body "Full snapshot of all devices and hardware in one command.

**Output includes:**
- Each Noursi plug: on/off state + current wattage
- Shelly plug: on/off state + wattage
- Desktop: online/offline (via ping)
- CPU/GPU temps on laptop and desktop (via SSH)
- Inline [Details] button per plug for deep dive

**Deep dive per plug shows:**
- Wattage, voltage, current, device temp, uptime

**Depends on:** Noursi plug integration, Ping watchdog" \
  --repo $REPO

gh issue create \
  --title "Scheduled routines via APScheduler" \
  --body "Allow routines to fire automatically at configured times.

**Usage:**
\`\`\`
/schedule goodmorning 07:30
/schedule goodnight 23:00
/schedule goodmorning 07:30 weekdays
/schedule list
/schedule cancel goodmorning
\`\`\`

**Implementation:**
- APScheduler library
- Persist schedules across restarts (JSON or SQLite)
- Support weekday/weekend filtering

**Depends on:** Good morning routine, Good night routine" \
  --repo $REPO

gh issue create \
  --title "Work mode and focus timer (/work, /endwork, /focus)" \
  --body "WFH-specific productivity commands.

**/work:**
- Turn on desk lamp (lamp1)
- Wake PC if offline
- Confirm 'Work mode activated'

**/endwork:**
- Send work session summary
- Turn off desk lamp, leave room lamp on
- Prompt: shut down PC?

**/focus [minutes]:**
- Start a focus timer (default 90 min)
- Send break reminder when done
- Pure Python, no hardware required

**Depends on:** Noursi plug integration" \
  --repo $REPO

gh issue create \
  --title "Reminder command (/remind)" \
  --body "Simple personal reminder system via Telegram.

**Usage:**
\`\`\`
/remind 30 take a break
/remind 120 check the laundry
\`\`\`

**Implementation:**
- Pure Python, no hardware required
- Uses APScheduler or asyncio.sleep
- Bot sends the reminder message at the right time

**Depends on:** APScheduler (or standalone asyncio implementation)" \
  --repo $REPO

# ── Phase 3 - Monitoring ──────────────────────────────────────────────────

gh issue create \
  --title "Ping watchdog — proactive offline detection" \
  --body "Monitor desktop reachability and alert proactively if it drops off the network.

**Behaviour:**
- Poll desktop Tailscale IP every 2-3 minutes via ping
- If ping fails 3 times consecutively → send Telegram alert
- Alert: 'Desktop appears offline. Use /wake to bring it back.'
- Resume monitoring silently once it comes back online

**Notes:**
- Critical for remote work crash recovery alongside Shelly
- Runs as background asyncio task alongside the bot
- Can be built independently of other features

**Depends on:** Nothing — standalone background task" \
  --repo $REPO

gh issue create \
  --title "Proactive hardware alerts (CPU/GPU temp thresholds)" \
  --body "Monitor hardware temps and alert when thresholds are exceeded.

**Behaviour:**
- Poll CPU/GPU temps on desktop and laptop periodically via SSH
- Alert if temp exceeds configurable threshold
- Send one alert per event, not repeatedly until resolved

**Environment variables:**
\`\`\`
ALERT_CPU_THRESHOLD=85
ALERT_GPU_THRESHOLD=90
\`\`\`

**Depends on:** system.py (already partially built)" \
  --repo $REPO

gh issue create \
  --title "Inactivity nudge — safety net for solo living" \
  --body "If lamps are still on and no commands have been sent past a configurable hour, send a nudge.

**Behaviour:**
- Check if any plugs are on after e.g. midnight with no recent activity
- Send: 'Hey, lamps are still on — everything okay?'
- Include inline [Turn everything off] button

**Notes:**
- Opt-in, not on by default
- Configurable threshold hour via .env

**Depends on:** Noursi plug integration, Device status summary" \
  --repo $REPO

gh issue create \
  --title "Pihole stats integration (/pihole)" \
  --body "Pull stats from the local Pihole instance running on the RPI.

**Usage:**
\`\`\`
/pihole    ← ads blocked today, % blocked, top blocked domain
\`\`\`

**Implementation:**
- Call Pihole local API: http://pi.hole/admin/api.php
- Requires PIHOLE_API_KEY in .env
- Include in /status summary and weekly report

**Depends on:** Nothing — standalone tool" \
  --repo $REPO

gh issue create \
  --title "Immich stats integration (/immich)" \
  --body "Pull stats from local Immich photo library running on the RPI.

**Usage:**
\`\`\`
/immich    ← total photos, storage used, last backup timestamp
\`\`\`

**Implementation:**
- Immich local REST API (requires IMMICH_API_KEY in .env)
- Include in weekly report optionally

**Depends on:** Nothing — standalone tool" \
  --repo $REPO

# ── Phase 4 - Intelligence & Logging ─────────────────────────────────────

gh issue create \
  --title "Weekly summary report (automated)" \
  --body "Automated weekly digest sent every Sunday.

**Report includes:**
- Hardware uptime (laptop and desktop)
- Energy usage estimate per plug (kWh)
- How many times each routine was triggered
- Alerts that fired during the week
- Pihole: ads blocked, top blocked domains
- Immich: photos added this week

**Implementation:**
- Scheduled via APScheduler (Sunday evening)
- Log routine invocations and alert events to local SQLite throughout the week

**Depends on:** Scheduled routines, Proactive hardware alerts, Pihole stats, Immich stats" \
  --repo $REPO

gh issue create \
  --title "Energy tracking and anomaly detection" \
  --body "Log plug power consumption over time and flag unusual readings.

**Features:**
- Log wattage from Shelly and Noursi plugs at regular intervals to SQLite
- Compute rolling baseline per plug
- Alert if reading deviates > configurable % from baseline
- Feed data into weekly summary report

**Depends on:** Noursi plug integration, Weekly summary report" \
  --repo $REPO

gh issue create \
  --title "Telegram journal (/note, /notes)" \
  --body "Simple personal logging via Telegram. No hardware, no cost.

**Usage:**
\`\`\`
/note picked up groceries
/note remember to call landlord tomorrow
/notes          ← list 10 most recent notes with timestamps
\`\`\`

**Implementation:**
- Append timestamped entries to local JSON or text file
- Pure Python, zero dependencies beyond what's already installed

**Depends on:** Nothing — standalone feature" \
  --repo $REPO

echo ""
echo "Done. All issues created at https://github.com/$REPO/issues"