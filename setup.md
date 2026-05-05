# Setup guide

## 1. Ubuntu initial setup

### Prevent sleep when lid is closed
```bash
sudo nano /etc/systemd/logind.conf
# Set: HandleLidSwitch=ignore
sudo systemctl restart systemd-logind
sudo systemctl mask sleep.target suspend.target hibernate.target hybrid-sleep.target
gsettings set org.gnome.settings-daemon.plugins.power sleep-inactive-ac-type 'nothing'
gsettings set org.gnome.settings-daemon.plugins.power sleep-inactive-battery-type 'nothing'
```

### Disable GNOME (headless mode)
```bash
sudo systemctl set-default multi-user.target
sudo reboot
```

### CPU power saving
```bash
sudo apt install -y cpufrequtils
echo 'GOVERNOR="powersave"' | sudo tee /etc/default/cpufrequtils
sudo systemctl restart cpufrequtils
```

### Disable Bluetooth
```bash
sudo systemctl disable bluetooth
sudo systemctl stop bluetooth
```

### Temperature monitoring
```bash
sudo apt install -y lm-sensors
sudo sensors-detect --auto
sensors
```

## 2. SSH

```bash
sudo apt install -y openssh-server
sudo systemctl enable ssh
sudo systemctl start ssh
```

Connect from another machine on Tailscale:
```bash
ssh username@tailscale-ip
```

## 3. Ollama

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull mistral
```

### Set model to unload after 5 minutes idle
```bash
sudo nano /etc/systemd/system/ollama.service
# Add under [Service]:
# Environment="OLLAMA_KEEP_ALIVE=5m"
sudo systemctl daemon-reload
sudo systemctl restart ollama
```

## 4. Python environment

```bash
sudo apt install -y python3-pip python3-venv
git clone https://github.com/jicxer/home-ai-companion.git
cd home-ai-companion
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
nano .env
```

## 5. Systemd service

```bash
sudo cp scripts/homeai.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable homeai
sudo systemctl start homeai
sudo systemctl status homeai
```

## 6. Tailscale

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
tailscale ip -4
```

## Useful commands

```bash
# Check bot logs
sudo journalctl -u homeai -f

# Restart bot
sudo systemctl restart homeai

# Check GPU
nvidia-smi

# Check CPU temps
sensors

# Check all cores in powersave
cat /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor
```
