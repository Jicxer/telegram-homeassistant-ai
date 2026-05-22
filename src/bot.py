import os
import logging
import asyncio
import random
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes
from tools.power import shutdown, reboot, monitor_shutdown
from tools.weather import get_weather, get_forecast
from tools.plug import turn_on as plug_on, turn_off as plug_off, get_status, get_power
from tools.homeassistant import (
    list_devices as ha_list_devices,
    turn_on as ha_turn_on,
    turn_off as ha_turn_off,
    toggle as ha_toggle,
    get_state as ha_get_state,
    get_all_states as ha_get_all_states,
    all_off as ha_all_off,
    run_routine as ha_run_routine,
    list_routines as ha_list_routines,
    conversation_process as ha_conversation_process,
)
import ollama
from tools.wol import wake_desktop

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ALLOWED_USER_ID = int(os.getenv("ALLOWED_USER_ID"))
MODEL = os.getenv("OLLAMA_MODEL", "mistral")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are JAI, a professional home automation assistant running locally on a private server. You serve as a personal butler — composed, efficient, and attentive.

Personality:
- Professional and composed, like a well-trained butler. Never overly casual but never stiff.
- Address the user respectfully. You may use "sir" sparingly for emphasis, not every message.
- Keep responses concise — 1-3 sentences unless the user asks for detail.
- When reporting device states or information, include a brief actionable suggestion. For example: "The bedroom lamp is currently off. Shall I turn it on?"
- On first interaction in a session, greet the user briefly. For example: "Good evening. How may I assist you?"
- Be helpful and proactive in suggesting actions or providing information and also sarcastic humorous, witty and sarcastic at times.

Capabilities:
- Control smart home devices (lamps, plugs, switches) via Home Assistant
- Wake, shutdown, and reboot machines on the network
- Provide weather reports and forecasts
- Run routines (wakeup, winddown, lightsout, leaving, latenight)
- Answer general knowledge questions

Limitations:
- If asked something outside your capabilities, respond honestly: "That's outside my capabilities at the moment. Here's what I can help with:" followed by a brief summary of what you can do.
- Never fabricate device states or claim to have done something you did not.
- Never execute destructive actions (shutdown, reboot) without explicit /commands from the user.

Available /commands: /wake, /shutdown, /reboot, /plug, /ha, /routine, /weather, /forecast, /machines, /flip, /help"""

conversation_history = {}
MAX_HISTORY = 20

# ---------------------------------------------------------------------------
# Natural language routing
# ---------------------------------------------------------------------------
# Messages are checked top-down through three tiers:
#   1. Direct tool routes — keyword match → call Python function directly,
#      no LLM involved. Instant response.
#   2. Device-intent routes — keyword match → HA Ollama conversation agent
#      for NLP device control via Assist API tool calling.
#   3. Fallback — everything else → Ollama directly for general chat.
# ---------------------------------------------------------------------------

# --- Tier 1: Direct tool keywords (bypass LLM entirely) ---

WEATHER_KEYWORDS = [
    "what's the weather",
    "whats the weather",
    "how's the weather",
    "hows the weather",
    "is it raining",
    "is it going to rain",
    "is it sunny",
    "is it cold",
    "is it hot",
    "weather outside",
    "what's it like outside",
    "whats it like outside",
    "temperature outside",
    "do i need a jacket",
    "do i need an umbrella",
    "should i bring",
]

STATUS_KEYWORDS = [
    "what's on",
    "whats on",
    "what is on",
    "what lights are on",
    "what devices are on",
    "which lights are on",
    "which devices are on",
    "device status",
    "show me the status",
    "what's turned on",
    "whats turned on",
    "anything on",
    "everything off",
    "is everything off",
    "are all lights off",
    "home status",
]

FLIP_KEYWORDS = [
    "flip a coin",
    "coin flip",
    "heads or tails",
    "flip coin",
    "toss a coin",
]

ROUTINE_LIST_KEYWORDS = [
    "what routines",
    "list routines",
    "available routines",
    "show routines",
    "what automations",
    "list automations",
    "what can you run",
    "show me routines",
    "my routines",
]

TIME_KEYWORDS = [
    "what time is it",
    "what's the time",
    "whats the time",
    "current time",
    "what day is it",
    "what's the date",
    "whats the date",
    "today's date",
    "what is today",
]

HELP_KEYWORDS = [
    "what can you do",
    "help me",
    "what are your commands",
    "what commands",
    "show me commands",
    "what are you capable of",
    "what do you do",
    "how do i use you",
    "how does this work",
    "what can i ask",
]

# --- Tier 1b: Routine trigger phrases (natural language → run routine) ---

ROUTINE_TRIGGERS = {
    "wakeup": [
        "good morning",
        "morning routine",
        "wake up routine",
        "start my day",
        "gm",
    ],
    "winddown": [
        "wind down",
        "winding down",
        "relax mode",
        "chill mode",
    ],
    "lightsout": [
        "goodnight",
        "good night",
        "lights out",
        "bedtime",
        "going to bed",
        "going to sleep",
        "night night",
        "time for bed",
        "nighty night",
    ],
    "leaving": [
        "i'm leaving",
        "im leaving",
        "leaving home",
        "heading out",
        "i'm going out",
        "im going out",
        "leaving the house",
        "bye house",
    ],
    "latenight": [
        "late night mode",
        "late night",
    ],
}


def _check_routine_trigger(message: str) -> str | None:
    """Check if message matches a routine trigger phrase. Returns alias or None."""
    msg_lower = message.lower()
    for alias, phrases in ROUTINE_TRIGGERS.items():
        if any(phrase in msg_lower for phrase in phrases):
            return alias
    return None


def _check_direct_route(message: str) -> str | None:
    """Check if message matches a direct tool route. Returns route name or None."""
    msg_lower = message.lower()

    if any(kw in msg_lower for kw in WEATHER_KEYWORDS):
        return "weather"
    if any(kw in msg_lower for kw in STATUS_KEYWORDS):
        return "status"
    if any(kw in msg_lower for kw in FLIP_KEYWORDS):
        return "flip"
    if any(kw in msg_lower for kw in ROUTINE_LIST_KEYWORDS):
        return "routine_list"
    if any(kw in msg_lower for kw in TIME_KEYWORDS):
        return "time"
    if any(kw in msg_lower for kw in HELP_KEYWORDS):
        return "help"

    # Check routine trigger phrases
    routine = _check_routine_trigger(message)
    if routine:
        return f"routine:{routine}"

    return None


# --- Tier 2: Device-intent keywords (route to HA conversation agent) ---

DEVICE_INTENT_KEYWORDS = [
    # Direct control verbs
    "turn on",
    "turn off",
    "switch on",
    "switch off",
    "toggle",
    "dim",
    "brighten",
    "set brightness",
    "set temperature",
    "set the",
    # Scene / automation triggers via NLP
    "run routine",
    "activate scene",
    "start routine",
]

# Device nouns — only trigger HA routing when paired with a control verb
DEVICE_NOUNS = ["lamp", "light", "plug", "fan", "thermostat", "lock", "cover"]

CONTROL_VERBS = [
    "turn", "switch", "toggle", "dim", "brighten", "set",
    "check", "is the", "are the", "what is", "what's the",
]


def _has_device_intent(message: str) -> bool:
    """Return True if the message looks like a device-control request."""
    msg_lower = message.lower()

    # Explicit control phrases always match
    if any(kw in msg_lower for kw in DEVICE_INTENT_KEYWORDS):
        return True

    # Device noun + control verb combo (avoids false positives on bare nouns)
    has_noun = any(noun in msg_lower for noun in DEVICE_NOUNS)
    has_verb = any(verb in msg_lower for verb in CONTROL_VERBS)
    if has_noun and has_verb:
        return True

    return False


def is_authorized(user_id: int) -> bool:
    return user_id == ALLOWED_USER_ID


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user.id):
        await update.message.reply_text("Unauthorized.")
        return
    help_text = """
    <b>Home AI Commands</b>

    <b>Power</b>
    /wake — Wake up the desktop
    /shutdown machine [now|+10|23:00] — Shutdown a machine
    /reboot machine — Reboot a machine

    <b>Smart Plug</b>
    /plug on — Turn plug on
    /plug off — Turn plug off
    /plug status — Check plug state
    /plug power — Get plug power consumption

    <b>Machines</b>
    /machines — List all configured machines

    <b>Weather</b>
    /weather [location] — Current conditions
    /forecast [location] [1-3] — Multi-day forecast

    <b>Home Assistant</b>
    /ha status — Show all HA device states
    /ha devices — List controllable devices
    /ha on entity_id — Turn on a device
    /ha off entity_id — Turn off a device
    /ha toggle entity_id — Toggle a device
    /ha alloff — Turn everything off
    
    <b>Routines</b>
    /routine — List all routines
    /routine wakeup — Turn on main lamp
    /routine winddown — Main lamp off, bedroom lamp on
    /routine lightsout — All lamps off
    /routine leaving — All lamps off (except server)

    <b>Fun</b>
    /flip — Flip a coin
    /flip 5 — Flip multiple coins

    <b>Natural Language</b>
    You can also say things like "turn off the bedroom lamp"
    or "is the main lamp on?" and the AI will handle it.

    <b>Help</b>
    /help — Show this message
    """
    await update.message.reply_text(help_text, parse_mode="HTML")


async def flip_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Flip one or more coins."""
    if not is_authorized(update.effective_user.id):
        await update.message.reply_text("Unauthorized.")
        return

    count = 1
    if context.args:
        try:
            count = int(context.args[0])
        except ValueError:
            await update.message.reply_text("Usage: /flip [number]\nExample: /flip 5")
            return
        if count < 1:
            await update.message.reply_text("Need at least 1 coin to flip.")
            return
        if count > 100:
            await update.message.reply_text("Sir... that's too many coins to flip.")
            return

    flips = [random.choice(["Heads", "Tails"]) for _ in range(count)]

    if count == 1:
        coin = flips[0]
        emoji = "🪙"
        await update.message.reply_text(f"{emoji} {coin}!")
    else:
        heads = flips.count("Heads")
        tails = flips.count("Tails")
        results = ", ".join(flips)

        # Truncate individual results if too many
        if count > 20:
            summary = f"🪙 Flipped {count} coins:\n\n⚡ {heads} Heads | {tails} Tails"
        else:
            summary = (
                f"🪙 Flipped {count} coins:\n"
                f"{results}\n\n"
                f"⚡ {heads} Heads | {tails} Tails"
            )
        await update.message.reply_text(summary)


async def routine_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user.id):
        await update.message.reply_text("Unauthorized.")
        return

    if not context.args:
        result = ha_list_routines()
        await update.message.reply_text(result)
        return

    name = " ".join(context.args)
    result = ha_run_routine(name)
    await update.message.reply_text(result)


async def plug_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user.id):
        await update.message.reply_text("Unauthorized.")
        return
    if not context.args:
        await update.message.reply_text("Usage: /plug on | off | status | power")
        return
    action = context.args[0].lower()
    if action == "on":
        result = plug_on()
    elif action == "off":
        result = plug_off()
    elif action == "status":
        result = get_status()
    elif action == "power":
        result = get_power()
    else:
        result = "Unknown action. Use: on, off, status, power"
    await update.message.reply_text(result)


async def wake_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user.id):
        await update.message.reply_text("Unauthorized.")
        return
    await update.message.reply_text("Sending wake signal to desktop...")
    result = wake_desktop()
    await update.message.reply_text(result)


async def shutdown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user.id):
        await update.message.reply_text("Unauthorized.")
        return
    if len(context.args) < 1:
        await update.message.reply_text("Usage: /shutdown <machine> [now|+minutes|HH:MM]")
        return
    machine_name = context.args[0].lower()
    when = context.args[1] if len(context.args) > 1 else "now"
    success, message = shutdown(machine_name, when)
    await update.message.reply_text(message)

    if success:
        from tools.machines import get_machine
        machine = get_machine(machine_name)
        if machine:
            # Calculate delay before pinging
            delay = 10  # default for "now"
            if when.startswith("+"):
                delay = int(when[1:]) * 60  # +30 = wait 30 minutes
            elif ":" in when:
                from datetime import datetime
                now = datetime.now()
                target = datetime.strptime(when, "%H:%M").replace(
                    year=now.year, month=now.month, day=now.day
                )
                if target < now:
                    target = target.replace(day=now.day + 1)
                delay = int((target - now).total_seconds())

            async def notify(msg):
                await update.message.reply_text(msg)
            asyncio.create_task(
                monitor_shutdown(machine["host"], machine_name, notify, delay)
            )


async def reboot_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user.id):
        await update.message.reply_text("Unauthorized.")
        return
    if len(context.args) < 1:
        await update.message.reply_text("Usage: /reboot <machine>")
        return
    machine = context.args[0].lower()
    result = reboot(machine)
    await update.message.reply_text(result)


async def machines_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user.id):
        await update.message.reply_text("Unauthorized.")
        return
    from tools.machines import list_machines, is_protected
    machines = list_machines()
    if not machines:
        await update.message.reply_text("No machines configured.")
        return
    lines = []
    for name in sorted(machines):
        tag = "  protected" if is_protected(name) else ""
        lines.append(f"• {name}{tag}")
    await update.message.reply_text("*Configured machines:*\n" + "\n".join(lines), parse_mode="Markdown")


async def weather_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user.id):
        await update.message.reply_text("Unauthorized.")
        return
    location = " ".join(context.args) if context.args else None
    result = get_weather(location)
    await update.message.reply_text(result)


async def forecast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user.id):
        await update.message.reply_text("Unauthorized.")
        return
    days = 3
    location = None
    if context.args:
        # Check if last arg is a number
        if context.args[-1].isdigit():
            days = int(context.args[-1])
            location = " ".join(context.args[:-1]) or None
        else:
            location = " ".join(context.args)
    result = get_forecast(location, days)
    await update.message.reply_text(result, parse_mode="HTML")

# /ha status — show all device states
# /ha devices — list all controllable devices
# /ha on <entity_id> — turn on
# /ha off <entity_id> — turn off  
# /ha toggle <entity_id> — toggle
# /ha alloff — turn everything off


async def ha_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user.id):
        await update.message.reply_text("Unauthorized.")
        return

    if not context.args:
        await update.message.reply_text(
            "Usage:\n"
            "/ha status — all device states\n"
            "/ha devices — list controllable devices\n"
            "/ha on <entity_id> — turn on\n"
            "/ha off <entity_id> — turn off\n"
            "/ha toggle <entity_id> — toggle\n"
            "/ha alloff — turn everything off"
        )
        return

    action = context.args[0].lower()

    if action == "status":
        result = ha_get_all_states()
    elif action == "devices":
        result = ha_list_devices()
    elif action == "on":
        if len(context.args) < 2:
            result = "Specify entity: /ha on Bedroom Lamp"
        else:
            name = " ".join(context.args[1:])
            result = ha_turn_on(name)
    elif action == "off":
        if len(context.args) < 2:
            result = "Specify entity: /ha off Bedroom Lamp"
        else:
            name = " ".join(context.args[1:])
            result = ha_turn_off(name)
    elif action == "toggle":
        if len(context.args) < 2:   
            result = "Specify entity: /ha toggle Bedroom Lamp"
        else:
            name = " ".join(context.args[1:])
            result = ha_toggle(name)
    elif action == "alloff":
        result = ha_all_off()
    else:
        result = "Unknown action. Use: status, devices, on, off, toggle, alloff"

    await update.message.reply_text(result)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user.id):
        await update.message.reply_text("Unauthorized.")
        return

    user_id = update.effective_user.id
    user_message = update.message.text

    # ----- Tier 1: Direct tool routes (no LLM, instant) -----
    direct_route = _check_direct_route(user_message)
    if direct_route:
        logger.info(f"Direct route matched: {direct_route} for: {user_message}")

        if direct_route == "weather":
            result = get_weather()
            await update.message.reply_text(result)
            return

        elif direct_route == "status":
            result = ha_get_all_states()
            await update.message.reply_text(result)
            return

        elif direct_route == "flip":
            coin = random.choice(["Heads", "Tails"])
            await update.message.reply_text(f"🪙 {coin}!")
            return

        elif direct_route == "routine_list":
            result = ha_list_routines()
            await update.message.reply_text(result)
            return

        elif direct_route == "time":
            from datetime import datetime
            now = datetime.now()
            time_str = now.strftime("%I:%M %p")
            date_str = now.strftime("%A, %B %d, %Y")
            await update.message.reply_text(f"🕐 {time_str}\n📅 {date_str}")
            return

        elif direct_route == "help":
            # Reuse the help command handler
            await help_command(update, context)
            return

        elif direct_route.startswith("routine:"):
            alias = direct_route.split(":", 1)[1]
            result = ha_run_routine(alias)
            await update.message.reply_text(result)
            return

    # ----- Tier 2: Device-intent → HA Ollama conversation agent -----
    if _has_device_intent(user_message):
        logger.info(f"Device intent detected, routing to HA conversation agent: {user_message}")
        await update.message.reply_text("Talking to Home Assistant...")

        # Run the blocking HTTP call in a thread so we don't block the event loop
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, ha_conversation_process, user_message)

        if result["success"]:
            # Agent executed a device action — use its response
            reply = result["speech"] or "Done."
            logger.info(f"HA agent succeeded: {reply}")
            await update.message.reply_text(reply)
            return
        elif result["speech"]:
            # Agent responded but didn't act (e.g. "I couldn't find that device")
            logger.info(f"HA agent responded without action: {result['speech']}")
            await update.message.reply_text(result["speech"])
            return
        else:
            # HA call failed entirely — fall through to Ollama
            logger.warning("HA conversation.process failed, falling back to Ollama")

    # ----- Tier 3: General chat → Ollama directly -----
    if user_id not in conversation_history:
        conversation_history[user_id] = []

    conversation_history[user_id].append({
        "role": "user",
        "content": user_message
    })

    if len(conversation_history[user_id]) > MAX_HISTORY:
        conversation_history[user_id] = conversation_history[user_id][-MAX_HISTORY:]

    await update.message.reply_text("Thinking...")

    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + conversation_history[user_id]
    response = ollama.chat(model=MODEL, messages=messages)
    reply = response["message"]["content"]

    conversation_history[user_id].append({
        "role": "assistant",
        "content": reply
    })

    await update.message.reply_text(reply, parse_mode="HTML")

app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("wake", wake_command))
app.add_handler(CommandHandler("help", help_command))
app.add_handler(CommandHandler("plug", plug_command))
app.add_handler(CommandHandler("shutdown", shutdown_command))
app.add_handler(CommandHandler("reboot", reboot_command))
app.add_handler(CommandHandler("machines", machines_command))
app.add_handler(CommandHandler("weather", weather_command))
app.add_handler(CommandHandler("forecast", forecast_command))
app.add_handler(CommandHandler("ha", ha_command))
app.add_handler(CommandHandler("routine", routine_command))
app.add_handler(CommandHandler("flip", flip_command))

app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

print("Bot is running...")
app.run_polling()