# home-ai-companion

A self-hosted home automation AI companion. Send natural language commands via Telegram, get responses from a locally running LLM, and control smart home devices — all on your own hardware with no cloud dependency and no ongoing API costs.

## What it does

- Chat with a local LLM via Telegram from anywhere
- Control smart home devices with natural language
- Ask about the weather
- Remembers context within a conversation
- Runs 24/7 as a systemd service, restarts automatically on crash
- Accessible remotely via Tailscale (private network) and SSH

## Stack

| Component | Technology |
|---|---|
| LLM runtime | [Ollama](https://ollama.com) |
| Model | Mistral 7B (quantized) |
| Bot interface | python-telegram-bot |
| Smart plug | Shelly HTTP REST API |
| Remote access | Tailscale + SSH |
| OS | Ubuntu 24.04 LTS (headless) |

## Project structure

```
home-ai-companion/
├── src/
│   ├── bot.py              # Telegram bot entry point
│   ├── agent/
│   │   ├── __init__.py
│   │   └── agent.py        # LLM agent loop and tool routing
│   └── tools/
│       ├── __init__.py
│       ├── weather.py      # Weather via wttr.in
│       ├── plug.py         # Shelly smart plug control
│       └── system.py       # Host machine health (CPU temp, etc.)
├── config/
│   └── prompts.py          # System prompt and prompt templates
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

- Ubuntu 24.04 LTS
- NVIDIA GPU with 6GB+ VRAM
- [Ollama](https://ollama.com) installed
- Mistral pulled: `ollama pull mistral`
- A Telegram bot token from [@BotFather](https://t.me/BotFather)
- Your Telegram user ID from [@userinfobot](https://t.me/userinfobot)

### Installation

```bash
# Clone the repo
git clone https://github.com/jicxer/home-ai-companion.git
cd home-ai-companion

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
# Copy service file
sudo cp scripts/homeai.service /etc/systemd/system/

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable homeai
sudo systemctl start homeai

# Check status
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
|---|---|
| `TELEGRAM_BOT_TOKEN` | Token from BotFather |
| `ALLOWED_USER_ID` | Your Telegram user ID (restricts access to you only) |
| `OLLAMA_MODEL` | Model name (default: `mistral`) |
| `OLLAMA_HOST` | Ollama API host (default: `http://localhost:11434`) |
| `SHELLY_DEVICE_IP` | Local IP of your Shelly smart plug |
| `WEATHER_LOCATION` | Default location for weather queries |

## Security

- Bot only responds to a single whitelisted Telegram user ID
- All secrets stored in `.env`, never hardcoded
- Ollama API bound to localhost only — not exposed to the network
- Remote access via Tailscale encrypted tunnel only
- No public ports exposed

## Roadmap

### Phase 1 — tool calling
- [x] Telegram bot connected to local LLM
- [x] Conversation memory within session
- [ ] Shelly smart plug control
- [ ] Weather tool (wttr.in)
- [ ] Proper tool-calling agent architecture

### Phase 2 — agent behaviour
- [ ] Persistent memory across restarts
- [ ] Scheduled automations ("turn off plug at midnight")
- [ ] Machine health monitoring ("how hot is the CPU?")
- [ ] Wake-on-LAN support

### Phase 3 — knowledge & RAG
- [ ] Local document ingestion (PDF, markdown, txt)
- [ ] ChromaDB vector store
- [ ] Web search fallback (SearXNG or Tavily)
- [ ] RAG as an agent tool

### Phase 4 — advanced agent
- [ ] Multi-step autonomous task execution
- [ ] Proactive alerts (CPU temp spike, etc.)
- [ ] Voice input via Whisper (Telegram voice messages)
- [ ] Multiple device support

## Power consumption

Estimated running cost on Portland, OR electricity rates ($0.20/kWh):

| State | Draw | $/month | $/year |
|---|---|---|---|
| Idle (model unloaded) | ~45W | ~$6.50 | ~$79 |
| Active inference | ~150W | — | — |

Model unloads from VRAM after 5 minutes of inactivity (`OLLAMA_KEEP_ALIVE=5m`).

## License

MIT
