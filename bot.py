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

# Store active countdowns and authorized channels
AUTHORIZED_CHANNELS_FILE = "authorized_channels.json"
active_countdowns = {}
pinned_messages = {}

# Fun messages
FUN_MESSAGES = [
    "🎉 Time's up! Are you ready for what's next?",
    "🚀 The countdown is over! Let’s get started!",
    "🔔 Time is up! Hope you’re prepared!",
]

# Save/load authorized channels
def load_authorized_channels():
    if os.path.exists(AUTHORIZED_CHANNELS_FILE):
        with open(AUTHORIZED_CHANNELS_FILE, "r") as file:
            return json.load(file)
    return []

def save_authorized_channels(channels):
    with open(AUTHORIZED_CHANNELS_FILE, "w") as file:
        json.dump(channels, file)

# Load channels
authorized_channels = load_authorized_channels()

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
        "👋 Welcome! Use /count {time} {message} to start a countdown.\n"
        "Example: /count 5 minutes Quiz starts soon!"
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
    authorized_channels.append(channel_id)
    save_authorized_channels(authorized_channels)
    await update.message.reply_text(f"✅ Channel {channel_id} authorized for countdowns.")

# Handle /count command
async def count_command(update: Update, context: CallbackContext) -> None:
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /count {time} {message}")
        return
    
    chat_id = update.message.chat.id
    time_input = " ".join(context.args[:-1])
    custom_message = context.args[-1]
    countdown_time = parse_time_input(time_input)
    
    if not countdown_time:
        await update.message.reply_text("❌ Invalid time format. Try again.")
        return
    
    keyboard = [[
        InlineKeyboardButton("✅ Confirm", callback_data=f"confirm_{chat_id}_{countdown_time}_{custom_message}"),
        InlineKeyboardButton("✏ Modify", callback_data=f"modify_{chat_id}")
    ]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(f"You entered: {format_time(countdown_time)}\nMessage: {custom_message}", parse_mode="HTML", reply_markup=reply_markup)

# Confirm countdown
async def confirm_countdown(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()
    chat_id, countdown_time, custom_message = query.data.split("_")[1:]
    countdown_time = int(countdown_time)
    message = await query.message.reply_text(f"⏳ Countdown started for {format_time(countdown_time)}!\n{custom_message}", parse_mode="HTML")
    
    keyboard = [[
        InlineKeyboardButton("⏸ Pause", callback_data=f"pause_{chat_id}"),
        InlineKeyboardButton("▶ Resume", callback_data=f"resume_{chat_id}"),
        InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_{chat_id}")
    ]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await message.reply_text("Control the countdown:", reply_markup=reply_markup)
    
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
            await message.edit_text(f"⏳ Countdown: {format_time(countdown_data['remaining'])}\n{custom_message}", parse_mode="HTML")
        except Exception:
            break
    await message.reply_text(random.choice(FUN_MESSAGES))
    del active_countdowns[chat_id]

# Run bot
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add_channel", add_channel))
    app.add_handler(CommandHandler("count", count_command))
    app.add_handler(CallbackQueryHandler(confirm_countdown, pattern=r"confirm_.*"))
    app.run_polling()

if __name__ == "__main__":
    main()

