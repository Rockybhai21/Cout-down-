import asyncio
import logging
import re
import os
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
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

# Store active countdowns, user inputs, and authorized channels
active_countdowns = {}
pinned_messages = {}

# Fun facts and quotes
FUN_FACTS = [
    "Did you know? The first computer programmer was a woman named Ada Lovelace in the 1840s! 💻",
    "Fun fact: The longest recorded countdown was over 50 years for a NASA mission! 🚀",
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
        "To set a countdown, use /count <time> <message> (e.g., '/count 5 minutes to quiz start').\n\n"
        f"💡 Fun Fact: {random.choice(FUN_FACTS)}\n\n"
        f"💛 Quote of the Day: {random.choice(QUOTES)}"
    )
    await update.message.reply_text(welcome_message)

# Handle /count command in channels
async def count_command(update: Update, context: CallbackContext) -> None:
    chat_id = update.message.chat.id
    user_id = update.message.from_user.id
    args = context.args

    if not args:
        await update.message.reply_text("❌ Please provide a time (e.g., '/count 5 minutes').")
        return

    time_input = " ".join(args[:2])  # Extract time from first two words
    custom_message = " ".join(args[2:])  # Rest is custom message

    countdown_time = parse_time_input(time_input)
    if countdown_time:
        # Post the countdown in the channel
        message = await update.message.reply_text(
            f"⏳ Countdown started for {format_time(countdown_time)}!\n📢 {custom_message}",
            parse_mode="HTML"
        )

        # Pin the message in the channel
        pinned_messages[chat_id] = message.message_id
        await context.bot.pin_chat_message(chat_id, message.message_id)

        # Store active countdown
        active_countdowns[chat_id] = {
            "message": message,
            "remaining": countdown_time,
            "paused": False,
            "custom_message": custom_message,
        }

        # Start the countdown
        asyncio.create_task(countdown(chat_id))
    else:
        await update.message.reply_text("❌ Invalid time format. Try again.")

# Countdown function
async def countdown(chat_id):
    countdown_data = active_countdowns.get(chat_id)
    if not countdown_data:
        return

    message = countdown_data["message"]
    custom_message = countdown_data["custom_message"]
    while countdown_data["remaining"] > 0:
        if countdown_data["paused"]:
            await asyncio.sleep(1)
            continue

        await asyncio.sleep(1)
        countdown_data["remaining"] -= 1
        try:
            await message.edit_text(
                f"⏳ Countdown: {format_time(countdown_data['remaining'])}\n📢 {custom_message}",
                parse_mode="HTML"
            )
        except Exception:
            break

    if chat_id in active_countdowns:
        await message.reply_text(
            f"🎉 <b>Time's up!</b> 🎉\n📢 {custom_message}",
            parse_mode="HTML"
        )
        del active_countdowns[chat_id]

# Handle pause callback
async def pause_countdown(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    for chat_id, countdown_data in active_countdowns.items():
        if not countdown_data["paused"]:
            countdown_data["paused"] = True
            await query.message.reply_text("⏸ Countdown paused.")
            break

# Handle resume callback
async def resume_countdown(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    for chat_id, countdown_data in active_countdowns.items():
        if countdown_data["paused"]:
            countdown_data["paused"] = False
            await query.message.reply_text("▶ Countdown resumed.")
            break

# Handle cancel callback
async def cancel_countdown(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    for chat_id, countdown_data in active_countdowns.items():
        del active_countdowns[chat_id]
        await query.message.reply_text("❌ Countdown cancelled.")
        break

# Run bot
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("count", count_command))
    app.add_handler(CallbackQueryHandler(pause_countdown, pattern="pause"))
    app.add_handler(CallbackQueryHandler(resume_countdown, pattern="resume"))
    app.add_handler(CallbackQueryHandler(cancel_countdown, pattern="cancel"))
    app.run_polling()

if __name__ == "__main__":
    main()
