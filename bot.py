import time
import asyncio
import logging
import re
import os
import random
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

# Fun facts and quotes
FUN_FACTS = [
    "Did you know? The first computer programmer was a woman named Ada Lovelace in the 1840s! 💻",
    "Fun fact: The longest recorded countdown was over 50 years for a NASA mission! 🚀",
    "Here's a fact: The first text message ever sent was 'Merry Christmas' in 1992. 📱",
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
        "To set a countdown, send me the duration (e.g., '2 hours 30 minutes')."
    )
    await update.message.reply_text(welcome_message)

# Handle countdown input
async def countdown_input(update: Update, context: CallbackContext) -> None:
    chat_id = update.message.chat.id
    user_input = update.message.text
    countdown_time = parse_time_input(user_input)
    if countdown_time:
        keyboard = [[
            InlineKeyboardButton("✅ Confirm", callback_data=f"confirm_{chat_id}_{countdown_time}"),
            InlineKeyboardButton("✏ Modify", callback_data=f"modify_{chat_id}")
        ]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(f"You entered: {format_time(countdown_time)}", parse_mode="HTML", reply_markup=reply_markup)
    else:
        await update.message.reply_text("Invalid time format. Try again.")

# Modify countdown
async def modify_countdown(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()
    chat_id = int(query.data.split("_")[1])
    await query.message.edit_text("Send the new countdown time:")

# Confirm countdown
async def confirm_countdown(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()
    chat_id, countdown_time = map(int, query.data.split("_")[1:])
    message = await query.message.reply_text(f"⏳ Countdown started for {format_time(countdown_time)}!", parse_mode="HTML")

    # Delay pinning the message by 5 seconds
    await asyncio.sleep(5)

    if chat_id in pinned_messages:
        await context.bot.unpin_chat_message(chat_id, pinned_messages[chat_id])  # Unpin previous
    pinned_messages[chat_id] = message.message_id
    await context.bot.pin_chat_message(chat_id, message.message_id)  # Pin after 5s

    # Start countdown
    asyncio.create_task(countdown(chat_id))
    # Add control buttons
    keyboard = [
        [InlineKeyboardButton("⏸ Pause", callback_data=f"pause_{chat_id}"),
         InlineKeyboardButton("▶ Resume", callback_data=f"resume_{chat_id}"),
         InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_{chat_id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await message.reply_text("Control the countdown:", reply_markup=reply_markup)

    active_countdowns[chat_id] = {"message": message, "remaining": countdown_time, "paused": False}
    asyncio.create_task(countdown(chat_id))

# Countdown function
async def countdown(chat_id):
    """Accurate countdown timer that waits exactly 1 second per iteration."""
    countdown_data = active_countdowns.get(chat_id)
    if not countdown_data:
        return

    message = countdown_data["message"]
    start_time = time.time()  # Record the start time

    while countdown_data["remaining"] > 0:
        if countdown_data["paused"]:
            await asyncio.sleep(1)
            continue

        elapsed_time = time.time() - start_time
        sleep_time = max(1 - (elapsed_time % 1), 0)  # Adjust sleep time to sync with real seconds

        await asyncio.sleep(sleep_time)
        countdown_data["remaining"] -= 1
        start_time = time.time()  # Reset start time for the next second

        try:
            await message.edit_text(
                f"⏳ Countdown: {format_time(countdown_data['remaining'])}", parse_mode="HTML"
            )
        except Exception:
            break

    # Notify when countdown ends
    if chat_id in active_countdowns:
        await message.reply_text("🎉 <b>Time's up!</b> 🎉", parse_mode="HTML")
        del active_countdowns[chat_id]

# Pause countdown
async def pause_countdown(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    chat_id = int(query.data.split("_")[1])
    if chat_id in active_countdowns:
        active_countdowns[chat_id]["paused"] = True
        await query.message.reply_text("⏸ Countdown paused.")

# Resume countdown
async def resume_countdown(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    chat_id = int(query.data.split("_")[1])
    if chat_id in active_countdowns:
        active_countdowns[chat_id]["paused"] = False
        await query.message.reply_text("▶ Countdown resumed.")

# Cancel countdown
async def cancel_countdown(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    chat_id = int(query.data.split("_")[1])
    if chat_id in active_countdowns:
        del active_countdowns[chat_id]
        await query.message.reply_text("❌ Countdown cancelled.")

# Run bot
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, countdown_input))

    # Callback handlers
    app.add_handler(CallbackQueryHandler(confirm_countdown, pattern=r"confirm_\d+_\d+"))
    app.add_handler(CallbackQueryHandler(modify_countdown, pattern=r"modify_\d+"))
    app.add_handler(CallbackQueryHandler(pause_countdown, pattern=r"pause_\d+"))
    app.add_handler(CallbackQueryHandler(resume_countdown, pattern=r"resume_\d+"))
    app.add_handler(CallbackQueryHandler(cancel_countdown, pattern=r"cancel_\d+"))

    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
