import asyncio
import logging
import re
import os
import random
from datetime import datetime, timedelta
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

# Store active countdowns and authorized channels
authorized_channels = set()
active_countdowns = {}
pinned_messages = {}
user_birthdays = {}

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
        "\U0001F44B Welcome to the Countdown Bot!\n\n"
        "Commands:\n"
        "- /countdown <time> <message> - Start a countdown\n"
        "- /birthday <DD-MM> - Set birthday countdown\n"
        "- /add_channel <channel_id> - Authorize channel\n"
        "- /pause - Pause countdown\n"
        "- /resume - Resume countdown\n"
        "- /cancel - Cancel countdown\n"
        "- /modify - Modify countdown\n"
        "- /timeleft - Show remaining time\n"
    )
    await update.message.reply_text(welcome_message, parse_mode="HTML")

# Handle countdown input
async def countdown_input(update: Update, context: CallbackContext) -> None:
    chat_id = update.message.chat.id
    user_input = update.message.text.split(" ", 1)
    if len(user_input) < 2:
        await update.message.reply_text("Usage: /countdown <time> <message>")
        return
    countdown_time = parse_time_input(user_input[0])
    custom_message = user_input[1]
    if countdown_time:
        keyboard = [[
            InlineKeyboardButton("✅ Confirm", callback_data=f"confirm_{chat_id}_{countdown_time}_{custom_message}"),
            InlineKeyboardButton("✏ Modify", callback_data=f"modify_{chat_id}")
        ]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(f"Countdown: {format_time(countdown_time)}\nMessage: {custom_message}", parse_mode="HTML", reply_markup=reply_markup)
    else:
        await update.message.reply_text("Invalid time format. Try again.")

# Confirm countdown
async def confirm_countdown(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()
    chat_id, countdown_time, custom_message = query.data.split("_", 2)
    chat_id, countdown_time = int(chat_id), int(countdown_time)
    message = await query.message.reply_text(f"⏳ {custom_message} starts in {format_time(countdown_time)}!", parse_mode="HTML")
    pinned_messages[chat_id] = message.message_id
    active_countdowns[chat_id] = {"message": message, "remaining": countdown_time, "paused": False}
    await asyncio.sleep(5)
    await context.bot.pin_chat_message(chat_id, message.message_id)
    asyncio.create_task(countdown(chat_id))

# Countdown function
async def countdown(chat_id):
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
            await message.edit_text(f"⏳ {format_time(countdown_data['remaining'])}", parse_mode="HTML")
        except Exception:
            break
    del active_countdowns[chat_id]

# Set birthday countdown
async def set_birthday(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    if len(context.args) != 1:
        await update.message.reply_text("Usage: /birthday <DD-MM>")
        return
    user_birthdays[user_id] = context.args[0]
    await update.message.reply_text("🎂 Birthday countdown set!")

# Run bot
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("countdown", countdown_input))
    app.add_handler(CommandHandler("birthday", set_birthday))
    app.add_handler(CallbackQueryHandler(confirm_countdown, pattern=r"confirm_\d+_\d+_.*"))
    app.run_polling()

if __name__ == "__main__":
    main()

