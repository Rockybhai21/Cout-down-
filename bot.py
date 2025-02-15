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
user_input_data = {}  # Stores user countdown time before confirmation

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
        "To set a countdown, send me the duration (e.g., '2 hours 30 minutes').\n\n"
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
    await update.message.reply_text(f"✅ Channel {channel_id} authorized for countdowns.")

# Handle countdown input
async def countdown_input(update: Update, context: CallbackContext) -> None:
    chat_id = update.message.chat.id
    user_id = update.message.from_user.id
    user_input = update.message.text
    countdown_time = parse_time_input(user_input)

    if countdown_time:
        user_input_data[user_id] = countdown_time  # Store countdown before confirmation

        keyboard = [[
            InlineKeyboardButton("✅ Confirm", callback_data=f"confirm_{chat_id}_{user_id}"),
            InlineKeyboardButton("✏ Modify", callback_data=f"modify_{user_id}")
        ]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(f"You entered: {format_time(countdown_time)}", parse_mode="HTML", reply_markup=reply_markup)
    else:
        await update.message.reply_text("Invalid time format. Try again.")

# Modify countdown
async def modify_countdown(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    user_id = int(query.data.split("_")[1])

    if user_id not in user_input_data:
        await query.answer("❌ No countdown time found. Please enter a time first.", show_alert=True)
        return

    await query.answer()
    await query.message.edit_text("Send the new countdown time:")

# Confirm countdown
async def confirm_countdown(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()

    chat_id, user_id = map(int, query.data.split("_")[1:])
    countdown_time = user_input_data.get(user_id)

    if countdown_time is None:
        await query.answer("❌ No countdown time found. Please enter a time first.", show_alert=True)
        return

    message = await query.message.reply_text(f"⏳ Countdown started for {format_time(countdown_time)}!", parse_mode="HTML")

    if chat_id in pinned_messages:
        await context.bot.unpin_chat_message(chat_id, pinned_messages[chat_id])

    pinned_messages[chat_id] = message.message_id
    await asyncio.sleep(5)  # Pin after 5 seconds
    await context.bot.pin_chat_message(chat_id, message.message_id)

    active_countdowns[chat_id] = {"message": message, "remaining": countdown_time, "paused": False}
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
            await message.edit_text(f"⏳ Countdown: {format_time(countdown_data['remaining'])}", parse_mode="HTML")
        except Exception:
            break

    if chat_id in active_countdowns:
        await message.reply_text("🎉 <b>Time's up!</b> 🎉\nHere's something interesting: \nDid you know that the longest recorded countdown was over 50 years for a NASA mission? 🚀", parse_mode="HTML")
        del active_countdowns[chat_id]

# Run bot
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add_channel", add_channel))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, countdown_input))
    app.add_handler(CallbackQueryHandler(confirm_countdown, pattern=r"confirm_\d+_\d+"))
    app.add_handler(CallbackQueryHandler(modify_countdown, pattern=r"modify_\d+"))

    app.run_polling()

if __name__ == "__main__":
    main()
