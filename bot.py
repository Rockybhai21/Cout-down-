import asyncio
import logging
import re
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, CallbackContext

# Enable logging
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# Bot Token from environment variable (Koyeb)
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Store user input time
user_time = {}
active_countdowns = {}

# Function to parse custom time input like "1 hour 30 minutes"
def parse_time_input(text):
    time_units = {"second": 1, "minute": 60, "hour": 3600, "day": 86400, "week": 604800}
    total_seconds = 0
    matches = re.findall(r"(\d+)\s*(seconds?|minutes?|hours?|days?|weeks?)", text, re.IGNORECASE)
    for amount, unit in matches:
        total_seconds += int(amount) * time_units[unit.lower().rstrip('s')]
    return total_seconds if total_seconds > 0 else None

# Function to start the bot
async def start(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text("Send the duration (e.g., '2 hours 30 minutes'):")

# Handle user input for countdown
async def countdown_input(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    user_input = update.message.text
    countdown_time = parse_time_input(user_input)
    if countdown_time:
        user_time[user_id] = countdown_time
        keyboard = [
            [InlineKeyboardButton("✅ Confirm", callback_data=f"confirm_{countdown_time}"),
             InlineKeyboardButton("✏ Modify", callback_data="modify")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(f"You entered: {user_input}.\nConfirm countdown or modify?", reply_markup=reply_markup)
    else:
        await update.message.reply_text("Invalid time format. Try again.")

# Handle modification request
async def modify_countdown(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()
    await query.message.edit_text("Send the new duration (e.g., '1 hour 15 minutes'):")

# Handle confirmation and start countdown
async def confirm_countdown(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    if user_id in user_time:
        countdown_time = user_time[user_id]
        message = await query.message.reply_text(f"⏳ Countdown started for <b>{format_time(countdown_time)}</b>!", parse_mode="HTML")
        active_countdowns[user_id] = {"message": message, "remaining": countdown_time, "paused": False}
        await context.bot.pin_chat_message(query.message.chat_id, message.message_id)
        await countdown(user_id)
        del user_time[user_id]

# Countdown function
async def countdown(user_id):
    countdown_data = active_countdowns.get(user_id)
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
        except Exception as e:
            logger.warning(f"Error updating countdown: {e}")
            break
    await message.reply_text("🎉 <b>Time's up!</b> 🎉\nHere’s something interesting: \nDid you know that the longest recorded countdown was over 50 years for a NASA mission? 🚀", parse_mode="HTML")
    del active_countdowns[user_id]

# Pause countdown
async def pause_countdown(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    if user_id in active_countdowns:
        active_countdowns[user_id]["paused"] = True
        await update.message.reply_text("⏸ Countdown paused.")

# Resume countdown
async def resume_countdown(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    if user_id in active_countdowns:
        active_countdowns[user_id]["paused"] = False
        await update.message.reply_text("▶ Countdown resumed.")

# Cancel countdown
async def cancel_countdown(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    if user_id in active_countdowns:
        del active_countdowns[user_id]
        await update.message.reply_text("❌ Countdown cancelled.")

# Function to format time in days, hours, minutes, seconds
def format_time(seconds):
    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{days}d {hours}h {minutes}m {seconds}s" if days else f"{hours}h {minutes}m {seconds}s" if hours else f"{minutes}m {seconds}s" if minutes else f"{seconds}s"

# Run bot
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, countdown_input))
    app.add_handler(CallbackQueryHandler(confirm_countdown, pattern=r"confirm_\d+"))
    app.add_handler(CallbackQueryHandler(modify_countdown, pattern="modify"))
    app.add_handler(CommandHandler("pause", pause_countdown))
    app.add_handler(CommandHandler("resume", resume_countdown))
    app.add_handler(CommandHandler("cancel", cancel_countdown))
    app.run_polling()

if __name__ == "__main__":
    main()
