import asyncio
import logging
import re
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
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

# Store active countdowns
active_countdowns = {}  # {chat_id: {message: Message, remaining: int, paused: bool}}

# Function to parse custom time input like "5 minutes Quiz starts soon!"
def parse_time_input(text):
    time_units = {"second": 1, "minute": 60, "hour": 3600, "day": 86400}
    total_seconds = 0
    matches = re.findall(r"(\d+)\s*(seconds?|minutes?|hours?|days?)", text, re.IGNORECASE)
    for amount, unit in matches:
        total_seconds += int(amount) * time_units[unit.lower().rstrip("s")]
    return total_seconds if total_seconds > 0 else None

# Function to format time
def format_time(seconds):
    minutes, seconds = divmod(seconds, 60)
    return f"<b>{minutes}m {seconds}s</b>" if minutes else f"<b>{seconds}s</b>"

# Start countdown command
async def start_countdown(update: Update, context: CallbackContext):
    text = update.message.text[len("/count ") :]
    countdown_time = parse_time_input(text)
    custom_message = text.split(maxsplit=1)[1] if " " in text else ""
    
    if not countdown_time:
        await update.message.reply_text("❌ Invalid time format! Use `/count 5 minutes Quiz starts soon!`")
        return
    
    chat_id = update.message.chat_id
    await update.message.reply_text(f"Countdown for\n⚠️ {custom_message}")
    
    await asyncio.sleep(1)  # Wait 1 second before sending countdown
    message = await update.message.reply_text(
        f"⏲️ Remaining: {format_time(countdown_time)}",
        parse_mode="HTML"
    )
    
    await asyncio.sleep(3)  # Wait 3 seconds before pinning
    await context.bot.pin_chat_message(chat_id, message.message_id)
    
    keyboard = [
        [
            InlineKeyboardButton("⏸ Pause", callback_data=f"pause_{chat_id}"),
            InlineKeyboardButton("▶ Resume", callback_data=f"resume_{chat_id}"),
            InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_{chat_id}"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await message.edit_text(
        f"⏲️ Remaining: {format_time(countdown_time)}",
        parse_mode="HTML",
        reply_markup=reply_markup
    )
    
    active_countdowns[chat_id] = {"message": message, "remaining": countdown_time, "paused": False}
    asyncio.create_task(run_countdown(chat_id))

# Countdown function
async def run_countdown(chat_id):
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
                f"⏲️ Remaining: {format_time(countdown_data['remaining'])}",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("⏸ Pause", callback_data=f"pause_{chat_id}"),
                        InlineKeyboardButton("▶ Resume", callback_data=f"resume_{chat_id}"),
                        InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_{chat_id}"),
                    ]
                ])
            )
        except:
            break

    if chat_id in active_countdowns:
        await message.reply_text("🎉 TIME'S UP!", parse_mode="HTML")
        del active_countdowns[chat_id]

# Pause countdown
async def pause_countdown(update: Update, context: CallbackContext):
    query = update.callback_query
    chat_id = int(query.data.split("_")[1])
    if chat_id in active_countdowns:
        active_countdowns[chat_id]["paused"] = True
        await query.answer("⏸ Countdown Paused")

# Resume countdown
async def resume_countdown(update: Update, context: CallbackContext):
    query = update.callback_query
    chat_id = int(query.data.split("_")[1])
    if chat_id in active_countdowns:
        active_countdowns[chat_id]["paused"] = False
        await query.answer("▶ Countdown Resumed")

# Cancel countdown
async def cancel_countdown(update: Update, context: CallbackContext):
    query = update.callback_query
    chat_id = int(query.data.split("_")[1])
    if chat_id in active_countdowns:
        del active_countdowns[chat_id]
        await query.answer("❌ Countdown Cancelled")
        await query.message.reply_text("❌ Countdown has been cancelled!")

# Run bot
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("count", start_countdown))
    app.add_handler(CallbackQueryHandler(pause_countdown, pattern=r"pause_\d+"))
    app.add_handler(CallbackQueryHandler(resume_countdown, pattern=r"resume_\d+"))
    app.add_handler(CallbackQueryHandler(cancel_countdown, pattern=r"cancel_\d+"))
    app.run_polling()

if __name__ == "__main__":
    main()
