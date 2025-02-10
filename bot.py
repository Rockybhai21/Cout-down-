import asyncio
import logging
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, CallbackQueryHandler

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = "7207793925:AAFME_OkdkEMMcFd9PI7cuoP_ahAG9OHg7U"

# Store countdowns
user_time = {}
active_countdowns = {}

# Function to parse custom time input like "2 hours 30 minutes"
def parse_time_input(text):
    time_units = {
        "second": 1, "seconds": 1,
        "minute": 60, "minutes": 60,
        "hour": 3600, "hours": 3600,
        "day": 86400, "days": 86400,
        "week": 604800, "weeks": 604800
    }
    
    total_seconds = 0
    matches = re.findall(r"(\d+)\s*(seconds?|minutes?|hours?|days?|weeks?)", text, re.IGNORECASE)

    for amount, unit in matches:
        total_seconds += int(amount) * time_units[unit.lower()]
    
    return total_seconds

# Function to start the bot
async def start(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text("Send the duration (e.g., '2 hours 30 minutes'):")

# Handle user input for countdown
async def countdown_input(update: Update, context: CallbackContext) -> None:
    if update.message.chat.type != "private":  # Only respond when setting a countdown
        return
    
    user_id = update.message.from_user.id
    user_input = update.message.text
    countdown_time = parse_time_input(user_input)

    if countdown_time > 0:
        user_time[user_id] = countdown_time
        keyboard = [[InlineKeyboardButton("✅ Confirm", callback_data=f"confirm_{countdown_time}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(f"You entered: {user_input}.\nConfirm countdown?", reply_markup=reply_markup)
    else:
        await update.message.reply_text("Invalid time format. Try again.")

# Handle confirmation and start countdown
async def confirm_countdown(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    if user_id in user_time:
        countdown_time = user_time[user_id]
        message = await query.message.reply_text(f"Countdown started for {format_time(countdown_time)}!")
        active_countdowns[user_id] = {"remaining": countdown_time, "message": message, "paused": False}

        # Pin the countdown message
        try:
            await context.bot.pin_chat_message(chat_id=query.message.chat_id, message_id=message.message_id)
        except Exception as e:
            logger.warning(f"Failed to pin message: {e}")

        await countdown(user_id, context)
        del user_time[user_id]

# Pause & Resume Countdown
async def pause_resume(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    if user_id in active_countdowns:
        active_countdowns[user_id]["paused"] = not active_countdowns[user_id]["paused"]
        state = "Paused ⏸️" if active_countdowns[user_id]["paused"] else "Resumed ▶️"
        await query.message.edit_text(f"Countdown {state}!\n⏳ {format_time(active_countdowns[user_id]['remaining'])} remaining...")

# Countdown function
async def countdown(user_id, context: CallbackContext):
    countdown_data = active_countdowns.get(user_id)
    if not countdown_data:
        return

    message = countdown_data["message"]

    for i in range(countdown_data["remaining"], 0, -1):
        if countdown_data["paused"]:
            await asyncio.sleep(1)
            continue

        countdown_data["remaining"] = i
        await asyncio.sleep(1)

        # Reminder alerts at key moments
        if i in [3600, 600, 60, 10]:  # 1 hour, 10 min, 1 min, 10 sec left
            await context.bot.send_message(chat_id=message.chat_id, text=f"⏳ Reminder: {format_time(i)} remaining!")

        try:
            await message.edit_text(f"⏳ Countdown: {format_time(i)} remaining...")
        except Exception as e:
            logger.warning(f"Error updating countdown: {e}")

    await message.edit_text("✅ Countdown Finished!")
    del active_countdowns[user_id]

# Function to format time in days, hours, minutes, seconds
def format_time(seconds):
    days = seconds // 86400
    hours = (seconds % 86400) // 3600
    minutes = (seconds % 3600) // 60
    sec = seconds % 60

    time_str = ""
    if days > 0:
        time_str += f"{days}d "
    if hours > 0:
        time_str += f"{hours}h "
    if minutes > 0:
        time_str += f"{minutes}m "
    if sec > 0 or time_str == "":
        time_str += f"{sec}s"

    return time_str.strip()

# Run bot
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, countdown_input))
    app.add_handler(CallbackQueryHandler(confirm_countdown, pattern=r"confirm_\d+"))
    app.add_handler(CallbackQueryHandler(pause_resume, pattern="pause_resume"))

    app.run_polling()

if __name__ == "__main__":
    main()
