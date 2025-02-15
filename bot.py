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

# Persistent storage for authorized channels
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
    welcome_message = """
👋 Welcome to the Countdown Bot!

Use the following commands:

✅ /add_channel <channel_id> - Authorize a channel
✅ /count <time> <message> - Start a countdown

Example: `/count 5 minutes Quiz starts soon!`
    """
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
async def count(update: Update, context: CallbackContext) -> None:
    chat_id = update.message.chat.id
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /count <time> <message>")
        return
    countdown_time = parse_time_input(context.args[0])
    if not countdown_time:
        await update.message.reply_text("Invalid time format. Try again.")
        return
    custom_message = " ".join(context.args[1:])
    keyboard = [[
        InlineKeyboardButton("✅ Confirm", callback_data=f"confirm_{chat_id}_{countdown_time}_{custom_message}"),
        InlineKeyboardButton("✏ Modify", callback_data=f"modify_{chat_id}")
    ]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(f"You entered: {format_time(countdown_time)}\nMessage: {custom_message}", parse_mode="HTML", reply_markup=reply_markup)

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
    parts = query.data.split("_")
    chat_id, countdown_time, custom_message = int(parts[1]), int(parts[2]), "_".join(parts[3:])
    message = await query.message.reply_text(f"⏳ {custom_message} - {format_time(countdown_time)}", parse_mode="HTML")
    if chat_id in pinned_messages:
        await context.bot.unpin_chat_message(chat_id, pinned_messages[chat_id])
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
            await message.edit_text(f"⏳ {custom_message} - {format_time(countdown_data['remaining'])}", parse_mode="HTML")
        except Exception:
            break
    del active_countdowns[chat_id]
    await message.reply_text(f"🎉 {custom_message} - Time's up! 🎉")

# Run bot
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add_channel", add_channel))
    app.add_handler(CommandHandler("count", count))
    app.add_handler(CallbackQueryHandler(confirm_countdown, pattern=r"confirm_.*"))
    app.add_handler(CallbackQueryHandler(modify_countdown, pattern=r"modify_.*"))
    app.run_polling()

if __name__ == "__main__":
    main()

