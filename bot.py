import asyncmarkup=InlineKeyboardMarkup(keyboard)
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from dotenv import load_dotenv

# Configuration
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# Global storage for active countdowns
active_countdowns = {}

# Function to parse time input with spaces (e.g., "2 minutes" or "2h 30m")
def parse_duration(text: str) -> int:
    time_units = {
        'second': 1, 'seconds': 1, 'sec': 1, 's': 1,
        'minute': 60, 'minutes': 60, 'min': 60, 'm': 60,
        'hour': 3600, 'hours': 3600, 'hr': 3600, 'h': 3600,
        'day': 86400, 'days': 86400, 'd': 86400
    }
    
    # Match patterns like "2 minutes" or "1h 30m"
    pattern = r'(\d+)\s*([a-zA-Z]+)'
    matches = re.findall(pattern, text)
    
    total = 0
    for value, unit in matches:
        unit = unit.lower().rstrip('s')  # Handle plurals
        if unit in time_units:
            total += int(value) * time_units[unit]
    return total

# Function to format time in days, hours, minutes, seconds
def format_duration(seconds: int) -> str:
    periods = [
        ('day', 86400),
        ('hour', 3600),
        ('minute', 60),
        ('second', 1)
    ]
    result = []
    for period_name, period_seconds in periods:
        if seconds >= period_seconds:
            period_value, seconds = divmod(seconds, period_seconds)
            result.append(f"{period_value} {period_name}{'s' if period_value != 1 else ''}")
    return ' '.join(result) or "0 seconds"

# Handle Modify button
async def modify_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    # Prompt the user to enter a new time and message
    await query.edit_message_text(
        "✏️ Please enter the new time and message in the format:\n"
        "<time> <message>\n"
        "Example: 10m Get ready!"
    )
    
    # Store the chat ID and message ID for later use
    context.user_data['modify_message_id'] = query.message.message_id
    context.user_data['modify_chat_id'] = query.message.chat_id

# Handle user input after Modify button is pressed
async def handle_modify_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        input_text = update.message.text
        
        # Match time formats (e.g., "2h 30m", "10s", "1 hour 30 minutes")
        time_pattern = r'(\d+\s*(?:seconds?|sec|s|minutes?|min|m|hours?|hr|h|days?|d)\s*)+'
        time_match = re.search(time_pattern, input_text, re.IGNORECASE)
        
        if not time_match:
            raise ValueError
        
        time_part = time_match.group(0).strip()
        message = input_text.replace(time_part, '').strip()
        
        if not message:
            message = "Countdown in progress..."
        
        duration = parse_duration(time_part)
        if not duration:
            raise ValueError

        # Add Confirm and Modify buttons
        keyboard = [
            [InlineKeyboardButton("✅ Confirm", callback_data=f"confirm_{duration}_{message}"),
             InlineKeyboardButton("✏ Modify", callback_data="modify")]
        ]
        
        # Edit the original message with the new countdown details
        await context.bot.edit_message_text(
            chat_id=context.user_data['modify_chat_id'],
            message_id=context.user_data['modify_message_id'],
            text=f"⏳ Set {format_duration(duration)} countdown\n"
                 f"⚠️ {message}\n\n"
                 "Confirm or modify the countdown:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        await update.message.reply_text(
            "❗ Invalid format!\n"
            "Please enter the new time and message in the format:\n"
            "<time> <message>\n"
            "Example: 10m Get ready!"
        )

# Main function
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CallbackQueryHandler(modify_callback, pattern=r"modify"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_modify_input))
    
    app.run_polling()

if __name__ == "__main__":
    main()
