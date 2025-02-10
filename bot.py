import asyncio
import logging
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackContext, CallbackQueryHandler

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot Token (Replace with your actual bot token)
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"

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
async def start(update: Update, context: CallbackContext):
    keyboard = [[InlineKeyboardButton("Set Countdown", callback_data="set_countdown")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text("Welcome! Set a countdown below:", reply_markup=reply_markup)

# Handle button clicks
async def button(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()

    if query.data == "set_countdown":
        await query.message.reply_text("Send the duration (e.g., '1 hour 30 minutes'):")

# Handle user input for countdown
async def countdown_input(update: Update, context: CallbackContext):
    user_input = update.message.text
    countdown_time = parse_time_input(user_input)

    if countdown_time > 0:
        keyboard = [[InlineKeyboardButton("✅ Confirm", callback_data=f"confirm_{countdown_time}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(f"You entered: {user_input}.\nConfirm countdown?", reply_markup=reply_markup)
    else:
        await update.message.reply_text("Invalid time format. Try again.")

# Handle confirmation and start countdown
async def confirm_countdown(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()

    countdown_time = int(query.data.split("_")[1])
    message = await query.message.reply_text(f"Countdown started for {countdown_time} seconds!")

    for i in range(countdown_time, 0, -1):
        await asyncio.sleep(1)
        new_text = f"Countdown: {i} seconds remaining..."
        
        try:
            await message.edit_text(new_text)
        except Exception as e:
            logger.warning(f"Error updating countdown: {e}")

    await message.edit_text("⏳ Countdown finished!")

# Run bot
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(CallbackQueryHandler(confirm_countdown, pattern=r"confirm_\d+"))
    app.add_handler(CommandHandler("countdown", countdown_input))  # Handles custom duration

    app.run_polling()

if __name__ == "__main__":
    main()
