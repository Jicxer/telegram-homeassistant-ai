# home-ai-companion

A self-hosted home automation AI companion. Send natural language commands via Telegram, get responses from a locally running LLM, and control smart home devices — all on your own hardware with no cloud dependency and no ongoing API costs.

## What it does

- Chat with a local LLM via Telegram from anywhere
- Control smart home devices with natural language
- Wake, shutdown, and reboot machines remotely
- Monitor smart plug power consumption
- Remembers context within a conversation
- Runs 24/7 as a systemd service, restarts automatically on crash
- Accessible remotely via Tailscale (private network) and SSH

## Stack

| Component | Technology |
|-----------|------------|
| LLM runtime | [Ollama](https://ollama.com) |
| Model | Mistral 7B (quantized) |
| Bot interface | python-telegram-bot |
| Smart plug | Shelly Gen2 HTTP RPC API |
| Wake-on-LAN | etherwake via RPI relay |
| Remote access | Tailscale + SSH |
| OS | Ubuntu 24.04 LTS (headless) |

## Project structure

```
home-ai-companion/
├── src/
│   ├── bot.py              # Telegram bot entry point and command routing
│   └── tools/
│       ├── machines.py     # Machine registry loaded from environment
│       ├── power.py        # Shutdown and reboot via SSH
│       ├── weather.py      # Weather via wttr.in
│       ├── plug.py         # Shelly Gen2 smart plug control
│       ├── system.py       # Host machine health (CPU temp, etc.)
│       └── wol.py          # Wake-on-LAN via SSH to RPI relay
├── scripts/
│   ├── setup.sh            # Full machine setup script
│   └── homeai.service      # systemd service file
├── docs/
│   └── setup.md            # Detailed setup guide
├── .env.example            # Environment variable template
├── .gitignore
├── requirements.txt
└── README.md
```

## Quick start

### Prerequisites

- Ubuntu 24.04 LTS (headless)
- [Ollama](https://ollama.com) installed
- Mistral pulled: `ollama pull mistral`
- A Telegram bot token from [@BotFather](https://t.me/BotFather)
- Your Telegram user ID from [@userinfobot](https://t.me/userinfobot)
- Tailscale installed and authenticated
- RPI on the same local network with etherwake configured (for WOL)
- SSH key generated on the server and added to each target machine's `authorized_keys`

### Installation

```bash
# Clone the repo
git clone https://github.com/Jicxer/telegram-homeassistant-ai.git
cd telegram-homeassistant-ai

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set up environment
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
| `SHELLY_DEVICE_IP` | Local IP of your Shelly Gen2 smart plug |
| `WEATHER_LOCATION` | Default location for weather queries |
| `RPI_HOST` | Tailscale IP of your RPI (WOL relay) |
| `RPI_USER` | SSH username on the RPI |
| `MACHINE_<NAME>_HOST` | Tailscale IP of a targetable machine (e.g. `MACHINE_DESKTOP_HOST`) |
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

| Command | Description |
|---------|-------------|
| `/wake` | Send WOL magic packet to desktop via RPI |
| `/shutdown <machine> [now\|+minutes\|HH:MM]` | Shutdown a machine immediately, after a delay, or at a specific time |
| `/reboot <machine>` | Reboot a machine immediately |
| `/plug on` | Turn smart plug on |
| `/plug off` | Turn smart plug off |
| `/plug status` | Check plug on/off state |
| `/plug power` | Show wattage, voltage, current, device temp |
| `/help` | Show all available commands |

Any message without a `/` prefix is sent to the local LLM for natural language conversation.

### Shutdown examples

```
/shutdown desktop now
/shutdown desktop +10       ← shuts down in 10 minutes
/shutdown desktop 23:00     ← shuts down at 11pm
/reboot desktop
```

## Security

- Bot only responds to a single whitelisted Telegram user ID
- All secrets stored in `.env`, never hardcoded
- Machine config loaded dynamically from environment — no IPs or usernames in source code
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

If running on a repurposed laptop, prevent lid-close from triggering suspend by setting the following in `/etc/systemd/logind.conf`:

```
HandleLidSwitch=ignore
HandleLidSwitchExternalPower=ignore
HandleLidSwitchDocked=ignore
```

Then restart logind:

```bash
sudo systemctl restart systemd-logind
```

Also mask sleep targets to prevent any suspend loop:

```bash
sudo systemctl mask sleep.target suspend.target hibernate.target hybrid-sleep.target
```

> ⚠️ These settings can be reset by system updates. Re-apply after major upgrades.

## Roadmap

### Phase 1 — foundation

- [x] Telegram bot connected to local LLM
- [x] Conversation memory within session
- [x] Wake-on-LAN support via RPI relay
- [x] Shelly Gen2 smart plug control
- [x] Power consumption monitoring (`/plug power`)
- [x] Remote shutdown and reboot with time arguments
- [ ] Weather tool (wttr.in)
- [ ] Proper tool-calling agent architecture (LLM-native)

### Phase 2 — agent behaviour

- [ ] Persistent memory across restarts
- [ ] Scheduled automations ("turn off plug at midnight")
- [ ] Machine health monitoring ("how hot is the CPU?")
- [ ] Claude API fallback for explicit lookup requests

### Phase 3 — knowledge & RAG

- [ ] Local document ingestion (PDF, markdown, txt)
- [ ] ChromaDB vector store
- [ ] Web search fallback (SearXNG or Tavily)
- [ ] RAG as an agent tool

### Phase 4 — advanced agent

- [ ] Multi-step autonomous task execution
- [ ] Proactive alerts (CPU temp spike, plug power threshold, etc.)
- [ ] Voice input via Whisper (Telegram voice messages)
- [ ] Multiple device support

## Power consumption

Estimated running cost on Portland, OR electricity rates ($0.20/kWh):

| State | Draw | $/month | $/year |
|-------|------|---------|--------|
| Idle (model unloaded) | ~45W | ~$6.50 | ~$79 |
| Active inference | ~150W | — | — |

Model unloads from VRAM after 5 minutes of inactivity (`OLLAMA_KEEP_ALIVE=5m`).

## License

MIT