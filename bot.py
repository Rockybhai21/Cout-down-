import asyncio
import logging
import re
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from telegram.constants import ChatType
from dotenv import load_dotenv

# Configuration
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# Global storage for active countdowns
active_countdowns = {}

# Start command
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome to the Countdown Bot!\n\n"
        "Use /countdown <time> <message> to start a countdown.\n"
        "Example: /countdown 2m Quiz starts!\n\n"
        "⏲️ Supported time formats:\n"
        "- Seconds: `10s`, `10 seconds`\n"
        "- Minutes: `2m`, `2 minutes`\n"
        "- Hours: `1h`, `1 hour`\n"
        "- Days: `1d`, `1 day`\n"
        "- Combined: `1h 30m`, `1d 2h 30m`\n\n"
        "📢 The bot works in both private messages and groups.\n"
        "✅ Use /countdown to get started!"
    )

# Parse time input (e.g., "2m", "1h 30m", "2 minutes")
def parse_duration(text: str) -> int:
    time_units = {
        'second': 1, 'seconds': 1, 'sec': 1, 's': 1,
        'minute': 60, 'minutes': 60, 'min': 60, 'm': 60,
        'hour': 3600, 'hours': 3600, 'hr': 3600, 'h': 3600,
        'day': 86400, 'days': 86400, 'd': 86400
    }
    pattern = r'(\d+)\s*([a-zA-Z]+)'
    matches = re.findall(pattern, text.lower())
    return sum(int(value) * time_units[unit.rstrip('s')] for value, unit in matches)

# Format time in minutes and seconds
def format_duration(seconds: int) -> str:
    if seconds >= 60:
        return f"{seconds // 60}m {seconds % 60}s"
    return f"{seconds}s"

# Handle /countdown command
async def countdown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        args = context.args
        if not args:
            raise ValueError
        
        # Extract time and message
        input_text = ' '.join(args)
        time_match = re.search(r'\d+\s*[a-zA-Z]+', input_text, re.IGNORECASE)
        
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
        await update.message.reply_text(
            f"⏳ Set {format_duration(duration)} countdown\n"
            f"⚠️ {message}\n\n"
            "Confirm or modify the countdown:",
            reply_markup=InlineKeyboardMarkup(keyboard))
    except Exception as e:
        await update.message.reply_text(
            "❗ Invalid format!\n"
            "Use: /countdown <time> <message>\n"
            "Example: /countdown 2m Quiz starts!"
        )

# Handle Confirm button
async def confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    _, duration, message = query.data.split('_', 2)
    duration = int(duration)
    chat_id = query.message.chat_id
    
    # Generate a unique key for this countdown
    key = f"{chat_id}_{query.message.message_id}"
    
    # Send the header message
    header_msg = await query.message.reply_text(
        f"📢 Countdown for:\n⚠️ <b>{message}</b>",
        parse_mode="HTML"
    )
    
    # Send the countdown message with buttons
    keyboard = [
        [InlineKeyboardButton("⏸ Pause", callback_data=f"pause_{key}"),
         InlineKeyboardButton("▶ Resume", callback_data=f"resume_{key}"),
         InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_{key}")]
    ]
    countdown_msg = await query.message.reply_text(
        f"⏲️ <b>Remaining: {format_duration(duration)}</b>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard))
    
    # Pin countdown after 3 seconds (only in groups)
    if query.message.chat.type in ["group", "supergroup"]:
        await asyncio.sleep(3)
        await context.bot.pin_chat_message(chat_id, countdown_msg.message_id)
    
    # Store countdown
    active_countdowns[key] = {
        'remaining': duration,
        'paused': False,
        'header_id': header_msg.message_id,
        'countdown_id': countdown_msg.message_id,
        'message': message,
        'task': None  # Store the countdown task
    }
    
    # Start countdown task
    active_countdowns[key]['task'] = asyncio.create_task(update_countdown(key, context))

# Update countdown in real-time
async def update_countdown(key, context: ContextTypes.DEFAULT_TYPE):
    while key in active_countdowns and active_countdowns[key]['remaining'] > 0:
        if active_countdowns[key]['paused']:
            await asyncio.sleep(1)
            continue
        
        active_countdowns[key]['remaining'] -= 1
        
        try:
            keyboard = [
                [InlineKeyboardButton("⏸ Pause", callback_data=f"pause_{key}"),
                 InlineKeyboardButton("▶ Resume", callback_data=f"resume_{key}"),
                 InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_{key}")]
            ]
            await context.bot.edit_message_text(
                chat_id=int(key.split('_')[0]),
                message_id=active_countdowns[key]['countdown_id'],
                text=f"⏲️ <b>Remaining: {format_duration(active_countdowns[key]['remaining'])}</b>",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(keyboard))
        except Exception as e:
            logger.error(f"Error updating countdown: {e}")
            break  # Exit if editing fails
        
        await asyncio.sleep(1)  # Ensure countdown updates every second
    
    if key in active_countdowns:
        await context.bot.send_message(
            chat_id=int(key.split('_')[0]),
            text="🎉 <b>TIME'S UP!</b>",
            parse_mode="HTML"
        )
        del active_countdowns[key]

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
        time_pattern = r'(\d+)\s*([a-zA-Z]+)'
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
            reply_markup=InlineKeyboardMarkup(keyboard))
    except Exception as e:
        await update.message.reply_text(
            "❗ Invalid format!\n"
            "Please enter the new time and message in the format:\n"
            "<time> <message>\n"
            "Example: 10m Get ready!"
        )

# Handle Pause, Resume, and Cancel buttons
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    action, key = query.data.split('_', 1)
    
    if key not in active_countdowns:
        await query.edit_message_text(text="❌ Countdown not found!")
        return
    
    if action == "pause":
        active_countdowns[key]['paused'] = True
        await query.edit_message_text(
            text=f"⏸️ <b>Countdown paused at:</b>\n{format_duration(active_countdowns[key]['remaining'])}",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("▶ Resume", callback_data=f"resume_{key}"),
                 InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_{key}")]
            ])
        )
    elif action == "resume":
        active_countdowns[key]['paused'] = False
        await query.edit_message_text(
            text=f"▶️ <b>Countdown resumed at:</b>\n{format_duration(active_countdowns[key]['remaining'])}",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⏸ Pause", callback_data=f"pause_{key}"),
                 InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_{key}")]
            ])
        )
    elif action == "cancel":
        if active_countdowns[key]['task']:
            active_countdowns[key]['task'].cancel()  # Cancel the countdown task
        del active_countdowns[key]
        await query.edit_message_text(
            text="❌ <b>Countdown canceled!</b>",
            parse_mode="HTML"
        )

# Main function
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("countdown", countdown_command))
    app.add_handler(CallbackQueryHandler(confirm_callback, pattern=r"confirm_"))
    app.add_handler(CallbackQueryHandler(modify_callback, pattern=r"modify"))
    app.add_handler(CallbackQueryHandler(button_callback, pattern=r"pause_|resume_|cancel_"))
    
    # Ignore all other messages
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, lambda update, context: None))
    
    app.run_polling()

if __name__ == "__main__":
    main()
