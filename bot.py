import asyncio
import logging
import re
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # Set your webhook URL here

# Logging configuration
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# Global storage for active countdowns
active_countdowns = {}

# Start command
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome to Countdown Bot!\n\n"
        "Use /countdown <time> <message> to start a countdown.\n"
        "Example: /countdown 2m Quiz starts!\n\n"
        "⏲️ Supported time formats: 10s, 5m, 1h 30m, etc."
    )

# Parse time input (e.g., "2m", "1h 30m", "2 minutes")
def parse_duration(text: str) -> int:
    time_units = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}
    pattern = r'(\d+)\s*([smhd])'
    matches = re.findall(pattern, text.lower())
    return sum(int(value) * time_units[unit] for value, unit in matches)

# Format time for display
def format_duration(seconds: int) -> str:
    minutes, seconds = divmod(seconds, 60)
    if minutes:
        return f"{minutes}m {seconds}s"
    return f"{seconds}s"

# Handle /countdown command
async def countdown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat.type in ["group", "supergroup"]:
        await update.message.delete()  # Delete command message in groups

    try:
        args = context.args
        if not args:
            raise ValueError
        
        input_text = ' '.join(args)
        time_match = re.search(r'\d+\s*[smhd]', input_text, re.IGNORECASE)
        if not time_match:
            raise ValueError
        
        time_part = time_match.group(0).strip()
        message = input_text.replace(time_part, '').strip()
        if not message:
            message = "Countdown in progress..."

        duration = parse_duration(time_part)
        if not duration:
            raise ValueError

        keyboard = [[
            InlineKeyboardButton("✅ Confirm", callback_data=f"confirm_{duration}_{message}"),
            InlineKeyboardButton("✏ Modify", callback_data="modify")
        ]]
        await update.message.reply_text(
            f"⏳ Set {format_duration(duration)} countdown\n⚠️ {message}\n\nConfirm or modify:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception:
        await update.message.reply_text("❗ Invalid format!\nUse: /countdown <time> <message>")

# Handle Confirm button
async def confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    _, duration, message = query.data.split('_', 2)
    duration = int(duration)
    chat_id = query.message.chat_id

    header_msg = await query.message.reply_text(f"📢 Countdown for:\n⚠️ <b>{message}</b>", parse_mode="HTML")

    keyboard = [[
        InlineKeyboardButton("⏸ Pause", callback_data=f"pause_{chat_id}"),
        InlineKeyboardButton("▶ Resume", callback_data=f"resume_{chat_id}"),
        InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_{chat_id}")
    ]]
    countdown_msg = await query.message.reply_text(
        f"⏲️ <b>Remaining: {format_duration(duration)}</b>", parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    if query.message.chat.type in ["group", "supergroup"]:
        await asyncio.sleep(3)
        await context.bot.pin_chat_message(chat_id, countdown_msg.message_id)

    key = f"{chat_id}_{countdown_msg.message_id}"
    active_countdowns[key] = {
        'remaining': duration,
        'paused': False,
        'header_id': header_msg.message_id,
        'countdown_id': countdown_msg.message_id,
        'message': message,
        'task': asyncio.create_task(update_countdown(key, context))
    }

# Update countdown
async def update_countdown(key, context: ContextTypes.DEFAULT_TYPE):
    while key in active_countdowns:
        countdown = active_countdowns[key]
        if countdown['paused']:
            await asyncio.sleep(1)
            continue

        if countdown['remaining'] <= 0:
            del active_countdowns[key]
            await context.bot.send_message(key.split('_')[0], "🎉 <b>TIME'S UP!</b>", parse_mode="HTML")
            return

        countdown['remaining'] -= 1
        try:
            keyboard = [[
                InlineKeyboardButton("⏸ Pause", callback_data=f"pause_{key}"),
                InlineKeyboardButton("▶ Resume", callback_data=f"resume_{key}"),
                InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_{key}")
            ]]
            await context.bot.edit_message_text(
                chat_id=int(key.split('_')[0]),
                message_id=int(key.split('_')[1]),
                text=f"⏲️ <b>Remaining: {format_duration(countdown['remaining'])}</b>",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except Exception:
            pass

        await asyncio.sleep(1)

# Handle Pause, Resume, and Cancel buttons
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    action, key = query.data.split('_', 1)
    
    if key not in active_countdowns:
        await query.edit_message_text("❌ Countdown not found!")
        return

    if action == "pause":
        active_countdowns[key]['paused'] = True
    elif action == "resume":
        active_countdowns[key]['paused'] = False
    elif action == "cancel":
        if active_countdowns[key]['task']:
            active_countdowns[key]['task'].cancel()
        del active_countdowns[key]
        await query.edit_message_text("❌ <b>Countdown canceled!</b>", parse_mode="HTML")
        return

    await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup([[
        InlineKeyboardButton("⏸ Pause", callback_data=f"pause_{key}"),
        InlineKeyboardButton("▶ Resume", callback_data=f"resume_{key}"),
        InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_{key}")
    ]]))

# Webhook Setup
async def set_webhook(app: Application):
    await app.bot.set_webhook(WEBHOOK_URL)

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("countdown", countdown_command))
    app.add_handler(CallbackQueryHandler(confirm_callback, pattern=r"confirm_"))
    app.add_handler(CallbackQueryHandler(button_callback, pattern=r"pause_|resume_|cancel_"))

    # Start webhook
    app.run_webhook(
        listen="0.0.0.0",
        port=int(os.getenv("PORT", 8443)),
        url_path=BOT_TOKEN,
        webhook_url=f"{WEBHOOK_URL}/{BOT_TOKEN}"
    )

if __name__ == "__main__":
    main()
