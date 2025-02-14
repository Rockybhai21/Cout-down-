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

# Bot Token (Replace with your actual bot token)
TOKEN = "7783239593:AAEFz1dVP_3qNnV_WaW6Uw_fiyvx1lFyYuc"

# Store user input time
user_time = {}

# Function to parse custom time input like "1 hour 30 minutes"
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
    user_id = update.message.from_user.id
    user_input = update.message.text
    countdown_time = parse_time_input(user_input)

    if countdown_time > 0:
        user_time[user_id] = countdown_time
        keyboard = [[InlineKeyboardButton("âœ… Confirm", callback_data=f"confirm_{countdown_time}")]]
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
        await query.message.reply_text(f"Countdown started for {format_time(countdown_time)}!")
        await countdown(query, countdown_time)
        del user_time[user_id]

# Countdown function
async def countdown(update: Update, seconds: int):
    message = await update.message.reply_text(f"â³ Countdown: {format_time(seconds)} remaining...")

    for i in range(seconds, 0, -1):
        await asyncio.sleep(1)
        new_text = f"â³ Countdown: {format_time(i)} remaining..."
        
        try:
            await message.edit_text(new_text)
        except Exception as e:
            logger.warning(f"Error updating countdown: {e}")

    await message.edit_text("âœ… Countdown Finished!")

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
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, countdown_input))
    app.add_handler(CallbackQueryHandler(confirm_countdown, pattern=r"confirm_\d+"))

    app.run_polling()

if __name__ == "__main__":
    main()
