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

# Parse time input
def parse_time_input(text):
    time_units = {"second": 1, "minute": 60, "hour": 3600, "day": 86400, "week": 604800}
    total_seconds = 0
    matches = re.findall(r"(\d+)\s*(seconds?|minutes?|hours?|days?|weeks?)", text, re.IGNORECASE)
    for amount, unit in matches:
        total_seconds += int(amount) * time_units[unit.lower().rstrip("s")]
    return total_seconds if total_seconds > 0 else None

# Format time
def format_time(seconds):
    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{days}d {hours}h {minutes}m {seconds}s" if days else f"{hours}h {minutes}m {seconds}s" if hours else f"{minutes}m {seconds}s" if minutes else f"{seconds}s"

# Start command
async def start(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text("👋 Welcome! Use /add_channel to authorize a channel and start countdowns.")

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

# Start countdown in a channel
async def start_channel_countdown(update: Update, context: CallbackContext) -> None:
    if not context.args:
        await update.message.reply_text("Usage: /start_channel_countdown <channel_id> <time>")
        return
    channel_id, *time_args = context.args
    if channel_id not in authorized_channels:
        await update.message.reply_text("❌ Channel not authorized.")
        return
    countdown_time = parse_time_input(" ".join(time_args))
    if countdown_time:
        message = await context.bot.send_message(channel_id, f"⏳ Countdown started for {format_time(countdown_time)}!")
        active_countdowns[channel_id] = {"message": message, "remaining": countdown_time, "paused": False}
        asyncio.create_task(countdown(channel_id))
    else:
        await update.message.reply_text("Invalid time format. Try again.")

# Countdown logic
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
            await message.edit_text(f"⏳ Countdown: {format_time(countdown_data['remaining'])} remaining...")
        except Exception as e:
            logger.warning(f"Error updating countdown: {e}")
            break
    if chat_id in active_countdowns:
        await message.reply_text("🎉 Time's up! 🎉")
        del active_countdowns[chat_id]

# Pause countdown
async def pause_countdown(update: Update, context: CallbackContext):
    query = update.callback_query
    chat_id = int(query.data.split("_")[1])
    if chat_id in active_countdowns:
        active_countdowns[chat_id]["paused"] = True
    await query.answer("⏸ Countdown paused")

# Resume countdown
async def resume_countdown(update: Update, context: CallbackContext):
    query = update.callback_query
    chat_id = int(query.data.split("_")[1])
    if chat_id in active_countdowns:
        active_countdowns[chat_id]["paused"] = False
    await query.answer("▶ Countdown resumed")

# Cancel countdown
async def cancel_countdown(update: Update, context: CallbackContext):
    query = update.callback_query
    chat_id = int(query.data.split("_")[1])
    if chat_id in active_countdowns:
        del active_countdowns[chat_id]
    await query.answer("❌ Countdown cancelled")

# Run bot
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add_channel", add_channel))
    app.add_handler(CommandHandler("start_channel_countdown", start_channel_countdown))
    app.add_handler(CallbackQueryHandler(pause_countdown, pattern=r"pause_\d+"))
    app.add_handler(CallbackQueryHandler(resume_countdown, pattern=r"resume_\d+"))
    app.add_handler(CallbackQueryHandler(cancel_countdown, pattern=r"cancel_\d+"))
    app.run_polling()

if __name__ == "__main__":
    main()

