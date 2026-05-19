# telegram-homeassistant-ai

A self-hosted home automation AI companion. Send natural language commands via Telegram, get responses from a locally running LLM, and control smart home devices through Home Assistant — all on your own hardware with no cloud dependency and no ongoing API costs.

## What it does

- Chat with a local LLM via Telegram from anywhere
- Control smart plugs and lights with `/ha` commands (natural language routing planned)
- Trigger automation routines (wake up, wind down, lights out) via `/routine`
- Wake, shutdown, and reboot machines remotely
- Monitor smart plug power consumption and energy usage
- Home Assistant manages all device state centrally — bot talks to HA's REST API
- Scheduled automations run inside HA independently of the bot (survives bot crashes)
- Geofence-triggered routines via HA Companion app (leaving/arriving home)
- Runs 24/7 as a systemd service, restarts automatically on crash
- Accessible remotely via Tailscale (private network) and SSH

## Architecture

```
┌──────────────┐     Telegram API      ┌──────────────────────────────┐
│  Your Phone  │◄─────────────────────► │  bot.py (systemd service)    │
│  (Telegram)  │                        │  ├── Ollama (Mistral 7B)     │
│              │                        │  ├── tools/homeassistant.py  │
│  HA Companion│──── location updates──►│  ├── tools/wol.py            │
│  App (iOS)   │                        │  ├── tools/power.py          │
└──────────────┘                        │  └── tools/weather.py        │
                                        └──────────┬───────────────────┘
                                                   │ REST API (port 8123)
                                        ┌──────────▼───────────────────┐
                                        │  Home Assistant (Docker)      │
                                        │  ├── Local Tuya (Nous A9 x3) │
                                        │  ├── Shelly (auto-discovered) │
                                        │  ├── Automations (5 built-in) │
                                        │  └── Zones + Geofencing       │
                                        └──────────────────────────────┘
```

All services run on a single repurposed IBuyPower laptop (Ryzen 7 3700X, RTX 2070, 16GB RAM, Ubuntu 24.04 headless). An RPI5 on the same LAN handles WOL relay, Pihole, Immich, and RustDesk.

## Stack

| Component | Technology |
|-----------|------------|
| LLM runtime | [Ollama](https://ollama.com) |
| Model | Mistral 7B (quantized) |
| Bot interface | python-telegram-bot |
| Device hub | [Home Assistant](https://www.home-assistant.io/) (Docker container) |
| Smart plugs | Nous A9 × 3 (via HA Local Tuya) + Shelly Gen2 (via HA Shelly integration) |
| Wake-on-LAN | etherwake via RPI relay |
| Remote access | Tailscale + SSH |
| Geofencing | HA Companion app (iOS) |
| OS | Ubuntu 24.04 LTS (headless) |

## Project structure

```
telegram-homeassistant-ai/
├── src/
│   ├── bot.py                 # Telegram bot entry point and command routing
│   └── tools/
│       ├── homeassistant.py   # HA REST API client — device control, routines
│       ├── machines.py        # Machine registry loaded from environment
│       ├── power.py           # Shutdown and reboot via SSH
│       ├── weather.py         # Weather via wttr.in
│       ├── plug.py            # Shelly Gen2 smart plug control (legacy, pre-HA)
│       ├── system.py          # Host machine health (CPU temp, etc.)
│       └── wol.py             # Wake-on-LAN via SSH to RPI relay
├── scripts/
│   └── homeai.service         # systemd service file
├── docs/
│   └── setup.md               # Detailed setup guide
├── .env.example               # Environment variable template
├── .gitignore
├── requirements.txt
└── README.md
```

## Quick start

### Prerequisites

- Ubuntu 24.04 LTS (headless)
- [Docker](https://docs.docker.com/engine/install/ubuntu/) and Docker Compose installed
- [Ollama](https://ollama.com) installed
- Mistral pulled: `ollama pull mistral`
- A Telegram bot token from [@BotFather](https://t.me/BotFather)
- Your Telegram user ID from [@userinfobot](https://t.me/userinfobot)
- Tailscale installed and authenticated
- RPI on the same local network with etherwake configured (for WOL) - Can use another machine as a jump server
- SSH key generated on the server and added to each target machine's `authorized_keys`

### Home Assistant setup

```bash
# Create HA directory
mkdir -p ~/home-assistant

# Create docker-compose.yml
cat <<EOF > ~/home-assistant/docker-compose.yml
version: "3.8"
services:
  homeassistant:
    container_name: homeassistant
    image: ghcr.io/home-assistant/home-assistant:stable
    volumes:
      - ./config:/config
      - /etc/localtime:/etc/localtime:ro
    restart: unless-stopped
    network_mode: host
    privileged: true
    environment:
      - TZ=America/Los_Angeles
EOF

# Start Home Assistant
cd ~/home-assistant
docker compose up -d
```

HA will be available at `http://localhost:8123`. Complete onboarding, enable 2FA, and generate a long-lived access token (Profile → Security → Long-Lived Access Tokens).

### Device integration

| Device | Integration | Notes |
|--------|-------------|-------|
| Nous A9 smart plugs | Local Tuya (HACS) | Requires Tuya developer account to extract local keys |
| Shelly Gen2 plug | Shelly (built-in) | Auto-discovers on LAN via mDNS |

`network_mode: host` in the Docker config is required for mDNS device discovery (Shelly auto-discovery).

### Bot installation

```bash
git clone https://github.com/Jicxer/telegram-homeassistant-ai.git
cd telegram-homeassistant-ai

python3 -m venv venv
source venv/bin/activate

pip install -r requirements.txt

cp .env.example .env
nano .env  # fill in your values
```

### Running as a service

```bash
sudo cp scripts/homeai.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable homeai
sudo systemctl start homeai
sudo systemctl status homeai
```

### Running manually (for development)

```bash
source venv/bin/activate
python3 src/bot.py
```

## Environment variables

Copy `.env.example` to `.env` and fill in your values. Never commit `.env` to git.

| Variable | Description |
|----------|-------------|
| `TELEGRAM_BOT_TOKEN` | Token from BotFather |
| `ALLOWED_USER_ID` | Your Telegram user ID (restricts access to you only) |
| `OLLAMA_MODEL` | Model name (default: `mistral`) |
| `OLLAMA_HOST` | Ollama API host (default: `http://localhost:11434`) |
| `HA_URL` | Home Assistant API URL (default: `http://localhost:8123`) |
| `HA_TOKEN` | Long-lived access token from HA |
| `SHELLY_DEVICE_IP` | Local IP of your Shelly Gen2 smart plug |
| `WEATHER_LOCATION` | Default location for weather queries |
| `RPI_HOST` | Tailscale IP of your RPI (WOL relay) |
| `RPI_USER` | SSH username on the RPI |
| `MACHINE_<NAME>_HOST` | Tailscale IP of a targetable machine |
| `MACHINE_<NAME>_USER` | SSH username on that machine (must have sudo) |
| `PROTECTED_MACHINES` | Comma-separated machine names excluded from shutdown/reboot |

### Adding a new machine

Add two lines to `.env` for each new machine — no code changes required:

```bash
MACHINE_SERVERNAME_HOST=100.x.x.x
MACHINE_SERVERNAME_USER=yourusername
```

Then add the server's SSH public key to that machine's `authorized_keys`.

## Bot commands

### Device control (via Home Assistant)

| Command | Description |
|---------|-------------|
| `/ha on <device>` | Turn a device on |
| `/ha off <device>` | Turn a device off |
| `/ha toggle <device>` | Toggle a device |
| `/ha status` | Show state of all HA devices |

Device names are resolved from HA friendly names — use names like `bedroom lamp`, `main lamp`, `pc plug`.

### Routines (HA automations)

| Command | Description |
|---------|-------------|
| `/routine` | List all available routines and their status |
| `/routine wakeup` | Turn on main lamp (scheduled: Wed-Thu 5am, Fri-Sat 5:30am) |
| `/routine winddown` | Main lamp off, bedroom lamp on |
| `/routine lightsout` | All lamps off |
| `/routine leaving` | All lamps off (triggered by geofence or manual) |

### Machine control

| Command | Description |
|---------|-------------|
| `/wake` | Send WOL magic packet to desktop via RPI |
| `/shutdown <machine> [now\|+minutes\|HH:MM]` | Shutdown a machine |
| `/reboot <machine>` | Reboot a machine immediately |

### Legacy / direct control

| Command | Description |
|---------|-------------|
| `/plug on/off/status` | Direct Shelly plug control (bypasses HA) |
| `/plug power` | Show wattage, voltage, current, device temp |

### General

| Command | Description |
|---------|-------------|
| `/help` | Show all available commands |

Any message without a `/` prefix is sent to the local LLM for natural language conversation.

### Shutdown examples

```
/shutdown desktop now
/shutdown desktop +10       ← shuts down in 10 minutes
/shutdown desktop 23:00     ← shuts down at 11pm
/reboot desktop
```

## Home Assistant automations

These run inside HA independently of the bot — if `bot.py` crashes, these still fire:

| Automation | Trigger | Action |
|------------|---------|--------|
| Wake Up | Wed-Thu 5:00am / Fri-Sat 5:30am | Turn on main lamp |
| Wind Down | Manual only (`/routine winddown`) | Main lamp off, bedroom lamp on |
| Lights Out | Manual only (`/routine lightsout`) | All lamps off |
| Late Night Auto-Off | Daily at 2:00am | All lamps off (safety net) |
| Sunset Lights | Sunset | Turn on main lamp |

### Geofencing (in progress)

The HA Companion app on iOS reports location to HA. Automations trigger when your phone enters or leaves the Home zone:

- **Leaving home** → turn off all lamps
- **Arriving home** → turn on main lamp (only if after sunset)

## Security

- Bot only responds to a single whitelisted Telegram user ID
- All secrets stored in `.env`, never hardcoded
- Machine config loaded dynamically from environment — no IPs or usernames in source code
- Home Assistant secured with 2FA (TOTP) and long-lived token auth
- HA port (8123) firewalled to localhost and Tailscale only (`ufw`)
- HA Cloud / Nabu Casa disabled — no external cloud dependency
- Ollama API bound to localhost only — not exposed to the network
- Remote access via Tailscale encrypted tunnel only
- No public ports exposed
- SSH key-based auth only, password auth disabled
- Destructive actions (wake, shutdown, reboot) are explicit `/commands` only — never natural language
- The server running this bot is protected from remote shutdown/reboot via `PROTECTED_MACHINES`

### Restricting SSH keys on target machines

For additional hardening, add the laptop's public key to target machines with a command restriction in `authorized_keys`:

```
command="sudo shutdown now",no-port-forwarding,no-X11-forwarding,no-agent-forwarding ssh-ed25519 AAAA... homeai-bot
```

This ensures the key can only run `sudo shutdown now` even if compromised.

## Headless laptop setup notes

If running on a repurposed laptop, prevent lid-close from triggering suspend:

```ini
# /etc/systemd/logind.conf
HandleLidSwitch=ignore
HandleLidSwitchExternalPower=ignore
HandleLidSwitchDocked=ignore
```

```bash
sudo systemctl restart systemd-logind
sudo systemctl mask sleep.target suspend.target hibernate.target hybrid-sleep.target
```

> ⚠️ These settings can be reset by system updates. Re-apply after major upgrades.

## Roadmap

### Phase 1 — Foundation ✅

- [x] Telegram bot connected to local LLM
- [x] Conversation memory within session
- [x] Wake-on-LAN support via RPI relay
- [x] Shelly Gen2 smart plug control
- [x] Power consumption monitoring (`/plug power`)
- [x] Remote shutdown and reboot with time arguments
- [x] Weather tool (wttr.in)

### Phase 2 — Home Assistant integration ✅

- [x] Home Assistant installed via Docker
- [x] Nous A9 smart plugs connected via Local Tuya
- [x] Shelly plug migrated to HA
- [x] Bot controls devices through HA REST API (`/ha` commands)
- [x] Friendly name resolution for devices
- [x] HA automations (wake up, wind down, lights out, sunset, late night auto-off)
- [x] `/routine` command to trigger HA automations from Telegram
- [x] HA secured (2FA, UFW, no cloud)
- [x] Tailscale remote access to HA dashboard

### Phase 3 — Smart automations (current)

- [ ] Geofencing setup via HA Companion app (in progress)
- [ ] Telegram notifications in HA (enables "left lights on" alerts)
- [ ] Natural language tool calling (Ollama routes "turn on the lamp" → HA)
- [ ] Energy monitoring dashboard + weekly Telegram summary
- [ ] Automated HA backups
- [ ] Dynamic routine discovery (bot auto-discovers HA automations)
- [ ] Fix `/help` command (Markdown parsing issue)

### Phase 4 — Advanced

- [ ] AppDaemon for complex Python automations
- [ ] Persistent memory across restarts
- [ ] Voice input via Whisper (Telegram voice messages)
- [ ] Additional device integrations (Linkind WiFi bulb, etc.)
- [ ] Proactive alerts (CPU temp spike, plug power threshold)
- [ ] Claude API fallback for explicit lookup requests

### Phase 5 — Knowledge & RAG

- [ ] Local document ingestion (PDF, markdown, txt)
- [ ] ChromaDB vector store
- [ ] Web search fallback (SearXNG or Tavily)
- [ ] RAG as an agent tool
- [ ] Multi-step autonomous task execution

## Power consumption

Estimated running cost on Portland, OR electricity rates ($0.20/kWh):

| State | Draw | $/month | $/year |
|-------|------|---------|--------|
| Idle (model unloaded, HA running) | ~50W | ~$7.30 | ~$88 |
| Active inference | ~150W | — | — |

Model unloads from VRAM after 5 minutes of inactivity (`OLLAMA_KEEP_ALIVE=5m`). HA container adds negligible overhead (~5W).

## License

MIT