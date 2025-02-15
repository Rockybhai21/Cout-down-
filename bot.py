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

# Store active countdowns and linked channels
active_countdowns = {}
linked_channels = {}

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

# Function to format time

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

# Command to start the bot
async def start(update: Update, context: CallbackContext) -> None:
    welcome_message = (
        "👋 Welcome to the Countdown Bot!\n\n"
        "I can help you set countdowns in private chats, groups, and channels.\n\n"
        "Use /countdown to start a countdown, or /channel to link a channel.\n\n"
        f"💡 Fun Fact: {random.choice(FUN_FACTS)}\n\n"
        f"📜 Quote of the Day: {random.choice(QUOTES)}"
    )
    await update.message.reply_text(welcome_message)

# Command to link a channel
async def link_channel(update: Update, context: CallbackContext) -> None:
    if update.message.forward_from_chat:
        channel_id = update.message.forward_from_chat.id
        linked_channels[channel_id] = update.message.forward_from_chat.title
        await update.message.reply_text(f"✅ Linked channel: {update.message.forward_from_chat.title}")
    else:
        await update.message.reply_text("Please forward a message from the channel to link it.")

# Command to list linked channels
async def list_channels(update: Update, context: CallbackContext) -> None:
    if not linked_channels:
        await update.message.reply_text("No channels linked yet.")
        return
    channels_list = "\n".join([f"{title} (ID: {chat_id})" for chat_id, title in linked_channels.items()])
    await update.message.reply_text(f"📢 Linked channels:\n{channels_list}")

# Command to start a countdown
async def start_countdown(update: Update, context: CallbackContext) -> None:
    user_input = " ".join(context.args)
    countdown_time = parse_time_input(user_input)
    chat_id = update.message.chat.id
    if countdown_time:
        message = await update.message.reply_text(f"⏳ Countdown started for <b>{format_time(countdown_time)}</b>!", parse_mode="HTML")
        active_countdowns[chat_id] = {"message": message, "remaining": countdown_time, "paused": False}
        asyncio.create_task(run_countdown(chat_id))
    else:
        await update.message.reply_text("Invalid format. Example: /countdown 1 hour 30 minutes")

# Countdown function
async def run_countdown(chat_id: int):
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
            await message.edit_text(f"⏳ Countdown: <b>{format_time(countdown_data['remaining'])}</b> remaining...", parse_mode="HTML")
        except:
            break
    await message.reply_text("🎉 <b>Time's up!</b> 🎉", parse_mode="HTML")
    del active_countdowns[chat_id]

# Run bot
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("channel", link_channel))
    app.add_handler(CommandHandler("channels", list_channels))
    app.add_handler(CommandHandler("countdown", start_countdown))
    app.run_polling()

if __name__ == "__main__":
    main()
