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

# Load environment variables (Koyeb should have BOT_TOKEN set)
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Store active countdowns
active_countdowns = {}  # Format: {chat_id: {message_id, remaining, paused, pinned_message_id}}

# Fun facts and quotes
FUN_FACTS = [
    "Did you know? The first computer programmer was a woman named Ada Lovelace in the 1840s! 💻",
    "Fun fact: The longest recorded countdown was over 50 years for a NASA mission! 🚀",
    "Here's a fact: The first text message ever sent was 'Merry Christmas' in 1992. 📱",
    "Did you know? The first website is still online: http://info.cern.ch 🌐",
    "Fun fact: The first computer mouse was made of wood! 🖱️",
    "Here's a fact: The first video ever uploaded to YouTube was 'Me at the zoo' in 2005. 🎥",
]

QUOTES = [
    "Time is what we want most, but what we use worst. – William Penn ⏳",
    "The future depends on what you do today. – Mahatma Gandhi 🌟",
    "Time flies over us, but leaves its shadow behind. – Nathaniel Hawthorne 🕰️",
    "The two most powerful warriors are patience and time. – Leo Tolstoy ⏳",
    "Lost time is never found again. – Benjamin Franklin ⏰",
]

# Function to parse custom time input like "1 hour 30 minutes"
def parse_time_input(text):
    time_units = {"second": 1, "minute": 60, "hour": 3600, "day": 86400, "week": 604800}
    total_seconds = 0
    matches = re.findall(r"(\d+)\s*(seconds?|minutes?|hours?|days?|weeks?)", text, re.IGNORECASE)
    for amount, unit in matches:
        total_seconds += int(amount) * time_units[unit.lower().rstrip("s")]
    return total_seconds if total_seconds > 0 else None

# Function to format time in days, hours, minutes, seconds
def format_time(seconds):
    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    return (
        f"{days}d {hours}h {minutes}m {seconds}s"
        if days
        else f"{hours}h {minutes}m {seconds}s"
        if hours
        else f"{minutes}m {seconds}s"
        if minutes
        else f"{seconds}s"
    )

# Function to start the bot
async def start(update: Update, context: CallbackContext) -> None:
    """Handle /start command for PMs, groups, and channels"""
    welcome_message = (
        "👋 Welcome to the Countdown Bot!\n\n"
        "I can help you set countdowns in private chats, groups, and channels.\n\n"
        "To set a countdown, send me the duration (e.g., '2 hours 30 minutes').\n\n"
        f"💡 Fun Fact: {random.choice(FUN_FACTS)}\n\n"
        f"📜 Quote of the Day: {random.choice(QUOTES)}"
    )
    await update.message.reply_text(welcome_message)

# Handle user input for countdown
async def countdown_input(update: Update, context: CallbackContext) -> None:
    """Handle countdown input in PMs, groups, and channels"""
    chat_id = update.message.chat.id
    user_input = update.message.text
    countdown_time = parse_time_input(user_input)
    if countdown_time:
        keyboard = [[
            InlineKeyboardButton("✅ Confirm", callback_data=f"confirm_{chat_id}_{countdown_time}"),
            InlineKeyboardButton("✏ Modify", callback_data=f"modify_{chat_id}")
        ]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            f"You entered: {user_input}.\nConfirm countdown or modify?", reply_markup=reply_markup
        )
    else:
        await update.message.reply_text("Invalid time format. Try again.")

# Handle confirmation and start countdown
async def confirm_countdown(update: Update, context: CallbackContext) -> None:
    """Handle countdown confirmation in PMs, groups, and channels"""
    query = update.callback_query
    await query.answer()
    parts = query.data.split("_")
    chat_id = int(parts[1])
    countdown_time = int(parts[2])
    
    # Unpin previous countdown
    if chat_id in active_countdowns and "pinned_message_id" in active_countdowns[chat_id]:
        try:
            await context.bot.unpin_chat_message(chat_id, active_countdowns[chat_id]["pinned_message_id"])
        except Exception:
            pass
    
    message = await query.message.reply_text(
        f"⏳ Countdown started for <b>{format_time(countdown_time)}</b>!", parse_mode="HTML"
    )
    pinned_message = await context.bot.pin_chat_message(query.message.chat_id, message.message_id)
    
    # Store countdown data
    active_countdowns[chat_id] = {"message": message, "remaining": countdown_time, "paused": False, "pinned_message_id": pinned_message.message_id}
    asyncio.create_task(countdown(chat_id, context))

# Countdown function running in the background
async def countdown(chat_id: int, context: CallbackContext):
    """Live countdown timer update"""
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
            await message.edit_text(
                f"⏳ Countdown: <b>{format_time(countdown_data['remaining'])}</b> remaining...",
                parse_mode="HTML"
            )
        except:
            break
    del active_countdowns[chat_id]

# Run bot
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, countdown_input))
    app.add_handler(CallbackQueryHandler(confirm_countdown, pattern=r"confirm_\d+_\d+"))
    app.run_polling()

if __name__ == "__main__":
    main()
