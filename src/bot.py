import os
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes
import ollama
from tools.wol import wake_desktop

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ALLOWED_USER_ID = int(os.getenv("ALLOWED_USER_ID"))
MODEL = os.getenv("OLLAMA_MODEL", "mistral")

logging.basicConfig(level=logging.INFO)

SYSTEM_PROMPT = """You are a home automation assistant running locally on a private server.
You can answer questions and hold conversations.
Available commands:
- /wake - Wake up the desktop computer
Be concise and helpful. If you are unsure about something, say so honestly."""

conversation_history = {}
MAX_HISTORY = 20

def is_authorized(user_id: int) -> bool:
    return user_id == ALLOWED_USER_ID

async def wake_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user.id):
        await update.message.reply_text("Unauthorized.")
        return
    await update.message.reply_text("Sending wake signal to desktop...")
    result = wake_desktop()
    await update.message.reply_text(result)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user.id):
        await update.message.reply_text("Unauthorized.")
        return

    user_id = update.effective_user.id
    user_message = update.message.text

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

    await update.message.reply_text(reply)

app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("wake", wake_command))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

print("Bot is running...")
app.run_polling()