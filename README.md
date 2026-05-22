# telegram-homeassistant-ai

A self-hosted home automation AI companion. Send natural language commands via Telegram, get responses from a locally running LLM, and control smart home devices — all on your own hardware with no cloud dependency and no ongoing API costs.

## What it does

- Chat with a local LLM via Telegram from anywhere
- Control smart home devices with natural language (via HA Ollama conversation agent)
- Run routines and automations through Telegram or geofencing triggers
- Wake, shutdown, and reboot machines remotely via WOL and SSH
- Monitor smart plug power consumption
- Get AI-generated contextual messages from HA sensors (weather, device states, alerts)
- Conversation memory within session
- Runs 24/7 as a systemd service, restarts automatically on crash
- Accessible remotely via Tailscale (private network) and SSH

## Architecture

```
┌─────────────┐
│   iPhone     │
│  Telegram    │
│  HA Companion│
└──────┬───────┘
       │ Tailscale / LAN
       ▼
┌──────────────────────────────────────────────────────────────┐
│  IBuyPower Laptop (Ubuntu 24.04 headless)                    │
│                                                              │
│  ┌──────────┐    ┌──────────┐    ┌──────────────────────┐   │
│  │  bot.py   │───▶│  Ollama  │───▶│  Tool Functions      │   │
│  │ (systemd) │    │(llama3.2)│    │  homeassistant.py    │   │
│  │           │    │          │    │  weather.py          │   │
│  │ Telegram  │    │          │    │  power.py / wol.py   │   │
│  │ polling   │    │          │    │  system.py           │   │
│  └──────────┘    └────┬─────┘    └──────────┬───────────┘   │
│                       │                      │               │
│              ┌────────▼──────────────────────▼────────┐      │
│              │  Home Assistant (Docker)                │      │
│              │                                        │      │
│              │  ┌────────────────────────────────┐    │      │
│              │  │  Ollama Conversation Agent      │    │      │
│              │  │  (Assist API + Tool Calling)    │    │      │
│              │  └────────────────────────────────┘    │      │
│              │                                        │      │
│              │  Telegram Bot (broadcast mode)         │      │
│              │  Local Tuya  ──▶ Nous A9 plugs × 3    │      │
│              │  Shelly      ──▶ Shelly Gen2 plug     │      │
│              │  Geofencing  ──▶ HA Companion app     │      │
│              │  Automations ──▶ routines, alerts      │      │
│              └────────────────────────────────────────┘      │
│                                                              │
└──────────────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────┐
│  RPI5 (LAN)  │
│  WOL relay   │
│  Pihole      │
│  Immich       │
│  RustDesk    │
└──────────────┘
```

## Stack

| Component | Technology |
|-----------|------------|
| LLM runtime | [Ollama](https://ollama.com) |
| Model | Llama 3.2 3B (general chat + HA device control) |
| Bot interface | python-telegram-bot |
| Device hub | [Home Assistant](https://www.home-assistant.io/) (Docker) |
| NLP device control | HA Ollama conversation agent (Assist API) |
| Smart plugs | Nous A9 × 3 (via HA Local Tuya) + Shelly Gen2 (via HA Shelly) |
| Wake-on-LAN | etherwake via RPI relay |
| Remote access | Tailscale + SSH |
| Geofencing | HA Companion app (iOS) |
| GPU | NVIDIA GeForce RTX 2070 (8GB VRAM) |
| OS | Ubuntu 24.04 LTS (headless) |

## Project structure

```
telegram-homeassistant-ai/
├── src/
│   ├── bot.py                 # Telegram bot entry point, command routing, NLP intent detection
│   └── tools/
│       ├── homeassistant.py   # HA REST API + conversation.process client
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

## Bot commands

### HA device control
| Command | Description |
|---------|-------------|
| `/ha on <device>` | Turn on a device via HA |
| `/ha off <device>` | Turn off a device via HA |
| `/ha status` | List all device states |
| `/ha status <device>` | Get specific device state |
| `/ha toggle <device>` | Toggle a device |
| `/ha alloff` | Turn everything off |
| `/ha devices` | List all controllable devices |

### Routines
| Command | Description |
|---------|-------------|
| `/routine <name>` | Run a named HA automation |
| `/routine list` | List available routines |

Available routines: `wakeup`, `winddown`, `lightsout`, `leaving`, `latenight`

### Machine control
| Command | Description |
|---------|-------------|
| `/wake <machine>` | Wake a machine via WOL |
| `/shutdown <machine>` | Shutdown a machine via SSH |
| `/reboot <machine>` | Reboot a machine via SSH |
| `/machines` | List all configured machines |

### Weather
| Command | Description |
|---------|-------------|
| `/weather [location]` | Current conditions |
| `/forecast [location] [1-3]` | Multi-day forecast |

### Fun
| Command | Description |
|---------|-------------|
| `/flip` | Flip a coin |
| `/flip <number>` | Flip multiple coins with stats |

### General
| Command | Description |
|---------|-------------|
| `/plug on\|off\|status\|power` | Legacy Shelly plug control |
| `/help` | List available commands |

Natural language messages (not prefixed with `/`) are routed based on intent:
- Device-related messages ("turn off the bedroom lamp", "is the main lamp on?") → HA Ollama conversation agent
- Everything else → Ollama directly for general chat

## Natural language routing

bot.py uses keyword-based intent detection to decide where to route non-command messages. If the message contains device-control verbs ("turn on", "turn off", "toggle", "dim"), state queries ("is the", "check the", "status of"), or device nouns ("lamp", "light", "plug"), it routes to HA's Ollama conversation agent via `conversation.process`. Everything else goes directly to Ollama for general chat.

The HA conversation agent uses the Assist API with tool calling to control exposed entities. The agent entity ID is configured via the `HA_CONVERSATION_AGENT` environment variable.

## Home Assistant automations

| Automation | Trigger | Actions |
|------------|---------|---------|
| Good Morning | `/routine wakeup` or schedule | Turn on lamps, send weather briefing |
| Wind Down | `/routine winddown` | Dim lights, set scene |
| Goodnight | `/routine lightsout` | All devices off |
| Leave Home | Geofence exit | All devices off, send confirmation via Telegram |
| Arriving Home | Geofence enter + after sunset | Main lamp on, Ollama-generated welcome message via Telegram |
| Late Night Auto Off | Time-based | Safety shutoff for forgotten devices |
| Left Lights On | Geofence exit + lights still on | Alert via Telegram |

## Ollama HA conversation agent setup

### Prerequisites

- Ollama running on the host and accessible from HA's Docker container
- A model with tool calling support pulled (llama3.2:3b recommended for HA)
- HA running with Telegram bot integration in broadcast mode

### Step 1 — Verify Ollama accessibility from HA

Since HA runs with `network_mode: host`, it can reach Ollama on localhost:

```bash
sudo docker exec homeassistant curl -s http://localhost:11434/api/tags | python3 -c "import sys,json; [print(m['name']) for m in json.load(sys.stdin)['models']]"
```

### Step 2 — Add Ollama integration in HA

1. Settings → Devices & Services → Add Integration → search "Ollama"
2. URL: `http://localhost:11434`
3. Select model: `llama3.2:3b`
4. Enable **"Control Home Assistant"**
5. Disable **"Thinking"** (not supported by most models, causes 400 errors)
6. Set keep-alive to `-1` (keep model in memory)
7. Set max history to `0` (each device command should be stateless)

### Step 3 — Create a Voice Assistant with the Ollama agent

1. Settings → Voice Assistants → Add Assistant
2. Name: `JAI`
3. Conversation agent: select your Ollama agent
4. Language: English

### Step 4 — Expose entities to the agent

1. Settings → Voice Assistants → Expose tab
2. Select entities the AI can control (keep under 25 for reliability with small models)
3. Use clean friendly names (e.g. "Bedroom Lamp" not "Bedroom Lamp Socket 1") — small models struggle with noisy names

### Step 5 — Test via Developer Tools

```yaml
action: conversation.process
data:
  agent_id: conversation.jai_minstral
  text: "turn off the bedroom lamp"
```

### Model selection notes

| Model | Tool calling | HA reliability | Chat quality | VRAM |
|-------|-------------|----------------|-------------|------|
| Llama 3.2 3B | ✅ | Best for HA | Adequate | 2.0 GB |
| Qwen 2.5 7B | ✅ | Inconsistent entity matching | Good | 5.3 GB |
| Mistral 7B v0.3 | ⚠️ Raw mode only | Outputs tool calls as text, doesn't execute | Best | 5.2 GB |

Llama 3.2 3B is recommended as the single model for both chat and device control on 8GB VRAM cards. Using one model avoids VRAM swapping latency.

## Quick start

### Prerequisites

- Ubuntu 24.04 LTS (headless)
- NVIDIA GPU with 8GB+ VRAM
- Docker and Docker Compose installed
- Ollama installed with llama3.2:3b pulled
- A Telegram bot token from @BotFather
- Your Telegram user ID from @userinfobot
- Tailscale installed and authenticated
- RPI on the same LAN with etherwake configured (for WOL)
- SSH key generated and added to each target machine's `authorized_keys`

### Home Assistant setup

```bash
mkdir -p ~/home-assistant

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

cd ~/home-assistant
docker compose up -d
```

HA will be available at `http://localhost:8123`. Complete onboarding, enable 2FA, and generate a long-lived access token (Profile → Security → Long-Lived Access Tokens).

### Bot setup

```bash
git clone https://github.com/Jicxer/telegram-homeassistant-ai.git ~/home-ai
cd ~/home-ai
cp .env.example .env
# Edit .env with your values
pip install -r requirements.txt
```

### Environment variables

```
TELEGRAM_BOT_TOKEN=        # From @BotFather
ALLOWED_USER_ID=           # Your Telegram user ID
OLLAMA_URL=                # http://localhost:11434
OLLAMA_MODEL=              # llama3.2:3b
HA_URL=                    # http://localhost:8123
HA_TOKEN=                  # Long-lived access token from HA
HA_CONVERSATION_AGENT=     # conversation.jai_minstral (your Ollama agent entity ID)
WEATHER_LOCATION=          # City for weather lookups
RPI_HOST=                  # RPI IP or Tailscale hostname
RPI_USER=                  # SSH user on RPI
SHELLY_IP=                 # Shelly plug IP (legacy, optional)
```

### Run as a service

```bash
sudo cp scripts/homeai.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable homeai
sudo systemctl start homeai
```

## HA device integrations

| Device | Integration | Protocol | Entity prefix |
|--------|-------------|----------|---------------|
| Nous A9 plug × 3 | Local Tuya | LAN (no cloud) | `switch.nous_*` |
| Shelly Gen2 plug | Shelly | mDNS / HTTP | `switch.shelly_*` |
| iPhone (geofencing) | HA Companion | HTTPS | `device_tracker.*` |

## Security

- No cloud services for device control — all LAN or Tailscale
- No Nabu Casa — HA is not exposed to the internet
- HA 2FA enabled
- Telegram bot restricted to single `ALLOWED_USER_ID`
- All secrets in `.env`, never committed (`.gitignore` enforced from day one)
- SSH key-only authentication to all machines
- UFW firewall active on host — only SSH (22), HA (8123), and Ollama (11434) open on LAN
- Tailscale for remote access instead of port forwarding
- HA long-lived access token scoped to bot operations
- Ollama conversation agent entity exposure kept under 25 entities to limit attack surface
- Destructive commands (`/shutdown`, `/reboot`, `/wake`) require explicit `/` prefix — never routed through natural language to prevent LLM misinterpretation

## Roadmap

### Phase 1 — core tools ✅
- [x] Telegram bot connected to local LLM (Ollama + Mistral)
- [x] Conversation memory within session
- [x] Wake-on-LAN support (via RPI relay)
- [x] Shelly Gen2 smart plug control
- [x] Weather tool (wttr.in)
- [x] `/shutdown` and `/reboot` command tools
- [x] Host machine health monitoring (CPU temp, load)

### Phase 2 — HA integration ✅
- [x] Home Assistant deployed (Docker)
- [x] Local Tuya — Nous A9 plugs integrated (no cloud)
- [x] Shelly plug migrated to HA
- [x] HA REST API client (`homeassistant.py`)
- [x] Routine system (`/routine` commands mapped to HA automations)
- [x] Telegram bot integration in HA (broadcast mode)
- [x] Geofencing via HA Companion app (leaving/arriving automations)

### Phase 3 — natural language + agent behavior ✅
- [x] Ollama conversation agent in HA (Assist API tool calling)
- [x] Wire `conversation.process` into bot.py (natural language → HA Ollama agent)
- [x] Keyword-based intent routing in bot.py (device commands → HA, general chat → Ollama)
- [x] Model evaluation (Mistral 7B → Qwen 2.5 7B → Llama 3.2 3B for HA tool calling)
- [x] Entity friendly name cleanup for reliable NLP matching
- [x] JAI persona (system prompt)

### Phase 4 — sensor context + monitoring (current)
- [ ] Sensor-contextual Ollama messages (query HA sensor → Ollama prompt → AI response)
- [ ] Ollama-generated welcome/alert messages in HA automations
- [ ] Energy monitoring (Nous plug power consumption → daily/weekly Telegram digest)
- [ ] Automated HA config backups
- [ ] Linkind bulb integration (pending protocol identification)
- [ ] Error handling in handle_message (try/except with user-friendly error messages)
- [ ] Telegram typing indicator instead of "Thinking..." messages
- [ ] Response time logging for performance tracking

### Phase 5 — knowledge + RAG
- [ ] Local document ingestion (PDF, markdown, txt)
- [ ] ChromaDB vector store
- [ ] Web search fallback (SearXNG or Tavily)
- [ ] RAG as an agent tool
- [ ] Claude API fallback for explicit lookup requests

### Phase 6 — advanced agent
- [ ] Multi-step autonomous task execution
- [ ] Proactive alerts (CPU temp spike, device anomalies)
- [ ] Voice input via Whisper (Telegram voice messages)
- [ ] AppDaemon for complex Python automations inside HA
- [ ] Daily digest automation (summarize all state changes, send via Telegram)

## Headless laptop notes

The host machine runs with the lid closed. To prevent suspend on lid close:

```
# /etc/systemd/logind.conf
HandleLidSwitch=ignore
HandleLidSwitchExternalPower=ignore
HandleLidSwitchDocked=ignore
```

Apply with `sudo systemctl restart systemd-logind`. Note: this setting can revert on system updates — monitor after `apt upgrade`.

## Power consumption

Idle draw with Ollama model loaded: ~35W. Under LLM inference load: ~85W (GPU active). HA container adds negligible overhead (~5W).

## License

MIT