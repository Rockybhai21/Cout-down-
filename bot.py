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

# Store countdowns & linked channels
active_countdowns = {}  # {chat_id: {message, remaining, paused, pinned_msg}}
linked_channels = {}  # {user_id: channel_id}

# Fun facts & quotes
FUN_FACTS = [
    "Did you know? The first computer programmer was Ada Lovelace in the 1840s! 💻",
    "Fun fact: The longest recorded countdown was over 50 years for a NASA mission! 🚀",
]

QUOTES = [
    "Time flies over us, but leaves its shadow behind. – Nathaniel Hawthorne 🕰️",
    "Lost time is never found again. – Benjamin Franklin ⏰",
]

# Parse time input
def parse_time_input(text):
    time_units = {"second": 1, "minute": 60, "hour": 3600, "day": 86400, "week": 604800}
    total_seconds = sum(int(amount) * time_units[unit.rstrip('s')] for amount, unit in re.findall(r"(\d+)\s*(seconds?|minutes?|hours?|days?|weeks?)", text, re.IGNORECASE))
    return total_seconds if total_seconds > 0 else None

# Format time
def format_time(seconds):
    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{days}d {hours}h {minutes}m {seconds}s" if days else f"{hours}h {minutes}m {seconds}s" if hours else f"{minutes}m {seconds}s" if minutes else f"{seconds}s"

# Start command
async def start(update: Update, context: CallbackContext):
    await update.message.reply_text(
        "👋 Welcome to the Countdown Bot!\n"
        "Send a time duration (e.g., '2 hours 30 minutes') to start a countdown."
    )

# Set a countdown
async def countdown_input(update: Update, context: CallbackContext):
    chat_id = update.message.chat.id
    countdown_time = parse_time_input(update.message.text)
    if countdown_time:
        keyboard = [[InlineKeyboardButton("✅ Confirm", callback_data=f"confirm_{chat_id}_{countdown_time}")]]
        await update.message.reply_text(f"You entered: {format_time(countdown_time)}.\nConfirm?", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text("Invalid time format. Try again.")

# Confirm & start countdown
async def confirm_countdown(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    chat_id, countdown_time = map(int, query.data.split("_")[1:])

    # Unpin previous countdown
    if chat_id in active_countdowns and "pinned_msg" in active_countdowns[chat_id]:
        try:
            await context.bot.unpin_chat_message(chat_id, active_countdowns[chat_id]["pinned_msg"])
        except:
            pass

    message = await query.message.reply_text(f"⏳ Countdown started for <b>{format_time(countdown_time)}</b>!", parse_mode="HTML")
    pinned_msg = await context.bot.pin_chat_message(chat_id, message.message_id)
    
    active_countdowns[chat_id] = {"message": message, "remaining": countdown_time, "paused": False, "pinned_msg": pinned_msg.message_id}
    asyncio.create_task(run_countdown(chat_id))

# Run countdown
async def run_countdown(chat_id):
    while active_countdowns[chat_id]["remaining"] > 0:
        if active_countdowns[chat_id]["paused"]:
            await asyncio.sleep(1)
            continue
        await asyncio.sleep(1)
        active_countdowns[chat_id]["remaining"] -= 1
        try:
            await active_countdowns[chat_id]["message"].edit_text(f"⏳ Countdown: <b>{format_time(active_countdowns[chat_id]['remaining'])}</b> remaining...", parse_mode="HTML")
        except:
            break
    await active_countdowns[chat_id]["message"].reply_text(f"🎉 <b>Time's up!</b> 🎉\n{random.choice(FUN_FACTS)}", parse_mode="HTML")
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

# Set channel for countdowns
async def set_channel(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    linked_channels[user_id] = update.message.text
    await update.message.reply_text(f"✅ Channel set: {update.message.text}")

# Show linked channels
async def linked_channels_list(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    if user_id in linked_channels:
        await update.message.reply_text(f"📢 Linked Channel: {linked_channels[user_id]}")
    else:
        await update.message.reply_text("❌ No linked channels found.")

# Main function
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("setchannel", set_channel))
    app.add_handler(CommandHandler("linkedchannels", linked_channels_list))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, countdown_input))
    app.add_handler(CallbackQueryHandler(confirm_countdown, pattern=r"confirm_\d+_\d+"))
    app.add_handler(CallbackQueryHandler(pause_countdown, pattern=r"pause_\d+"))
    app.add_handler(CallbackQueryHandler(resume_countdown, pattern=r"resume_\d+"))
    app.add_handler(CallbackQueryHandler(cancel_countdown, pattern=r"cancel_\d+"))
    app.run_polling()

if __name__ == "__main__":
    main()
