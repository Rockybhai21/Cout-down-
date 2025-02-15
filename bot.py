import asyncio
import logging
import re
import os
import random
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatMember
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    CallbackContext,
)
from dotenv import load_dotenv

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNELS_FILE = "authorized_channels.json"

def load_channels():
    if os.path.exists(CHANNELS_FILE):
        with open(CHANNELS_FILE, "r") as file:
            return json.load(file)
    return []

def save_channels(channels):
    with open(CHANNELS_FILE, "w") as file:
        json.dump(channels, file)

# Store active countdowns and authorized channels
authorized_channels = set(load_channels())
active_countdowns = {}
pinned_messages = {}

# Fun facts and quotes
FUN_FACTS = [
    "Did you know? The first computer programmer was a woman named Ada Lovelace in the 1840s! 💻",
    "Fun fact: The longest recorded countdown was over 50 years for a NASA mission! 🚀",
    "Here's a fact: The first text message ever sent was 'Merry Christmas' in 1992. 📱",
]

QUOTES = [
    "Time is what we want most, but what we use worst. – William Penn ⏳",
    "The future depends on what you do today. – Mahatma Gandhi 🌟",
]

# Parse time input
def parse_time_input(text):
    time_units = {"second": 1, "minute": 60, "hour": 3600, "day": 86400}
    total_seconds = 0
    matches = re.findall(r"(\d+)\s*(seconds?|minutes?|hours?|days?)", text, re.IGNORECASE)
    for amount, unit in matches:
        total_seconds += int(amount) * time_units[unit.lower().rstrip("s")]
    return total_seconds if total_seconds > 0 else None

# Format time
def format_time(seconds):
    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"<b>{days}d {hours}h {minutes}m {seconds}s</b>" if days else f"<b>{hours}h {minutes}m {seconds}s</b>" if hours else f"<b>{minutes}m {seconds}s</b>" if minutes else f"<b>{seconds}s</b>"

# Start command
async def start(update: Update, context: CallbackContext) -> None:
    welcome_message = (
        "👋 Welcome to the Countdown Bot!\n\n"
        "I can help you set countdowns in PMs, groups, and channels.\n\n"
        "Use /count <time> <custom_message> to start a countdown.\n"
        "Example: /count 5 minutes Quiz starts soon!\n\n"
        f"💡 Fun Fact: {random.choice(FUN_FACTS)}\n\n"
        f"💛 Quote of the Day: {random.choice(QUOTES)}"
    )
    await update.message.reply_text(welcome_message)

# Add authorized channel
async def add_channel(update: Update, context: CallbackContext) -> None:
    if not context.args:
        await update.message.reply_text("Usage: /add_channel <channel_id>")
        return
    channel_id = context.args[0]
    chat_member = await context.bot.get_chat_member(channel_id, update.message.from_user.id)
    if chat_member.status not in [ChatMember.ADMINISTRATOR, ChatMember.CREATOR]:
        await update.message.reply_text("Only admins can add channels.")
        return
    authorized_channels.add(channel_id)
    save_channels(list(authorized_channels))
    await update.message.reply_text(f"✅ Channel {channel_id} authorized for countdowns.")

# Start countdown
async def start_countdown(update: Update, context: CallbackContext) -> None:
    if not context.args or len(context.args) < 2:
        await update.message.reply_text("Usage: /count <time> <message>")
        return
    chat_id = update.message.chat.id
    countdown_time = parse_time_input(context.args[0])
    custom_message = " ".join(context.args[1:])
    if not countdown_time:
        await update.message.reply_text("Invalid time format. Try again.")
        return
    keyboard = [[
        InlineKeyboardButton("⏸ Pause", callback_data=f"pause_{chat_id}"),
        InlineKeyboardButton("▶ Resume", callback_data=f"resume_{chat_id}"),
        InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_{chat_id}")
    ]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    message = await update.message.reply_text(
        f"⏳ Countdown started: {format_time(countdown_time)}\n{custom_message}", parse_mode="HTML", reply_markup=reply_markup
    )
    pinned_messages[chat_id] = message.message_id
    await asyncio.sleep(3)
    await context.bot.pin_chat_message(chat_id, message.message_id)
    active_countdowns[chat_id] = {"message": message, "remaining": countdown_time, "paused": False}
    asyncio.create_task(countdown(chat_id, custom_message))

# Countdown function
async def countdown(chat_id, custom_message):
    countdown_data = active_countdowns.get(chat_id)
    if not countdown_data:
        return
    message = countdown_data["message"]
    while countdown_data["remaining"] > 0:
        if countdown_data["paused"]:
            await asyncio.sleep(1)
            continue
        await asyncio.sleep(1)
        countdown_data["remaining"] -= 1
        try:
            await message.edit_text(f"⏳ {format_time(countdown_data['remaining'])}\n{custom_message}", parse_mode="HTML")
        except Exception:
            break
    await message.reply_text("🎉 Countdown finished! 🎉")
    del active_countdowns[chat_id]

# Pause countdown
async def pause_countdown(update: Update, context: CallbackContext):
    query = update.callback_query
    chat_id = int(query.data.split("_")[1])
    active_countdowns[chat_id]["paused"] = True
    await query.answer("⏸ Countdown paused")

# Resume countdown
async def resume_countdown(update: Update, context: CallbackContext):
    query = update.callback_query
    chat_id = int(query.data.split("_")[1])
    active_countdowns[chat_id]["paused"] = False
    await query.answer("▶ Countdown resumed")

# Cancel countdown
async def cancel_countdown(update: Update, context: CallbackContext):
    query = update.callback_query
    chat_id = int(query.data.split("_")[1])
    del active_countdowns[chat_id]
    await query.answer("❌ Countdown cancelled")

# Run bot
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add_channel", add_channel))
    app.add_handler(CommandHandler("count", start_countdown))
    app.add_handler(CallbackQueryHandler(pause_countdown, pattern=r"pause_\d+"))
    app.add_handler(CallbackQueryHandler(resume_countdown, pattern=r"resume_\d+"))
    app.add_handler(CallbackQueryHandler(cancel_countdown, pattern=r"cancel_\d+"))
    app.run_polling()

if __name__ == "__main__":
    main()

