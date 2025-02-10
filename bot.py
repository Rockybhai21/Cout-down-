import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, CallbackContext

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Replace with your bot token
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"

# Stores user-selected time
user_time = {}

async def start(update: Update, context: CallbackContext) -> None:
    keyboard = [[InlineKeyboardButton("Set Countdown", callback_data="set_time")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Welcome! Set a countdown below:", reply_markup=reply_markup)

async def set_time(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("1 min", callback_data="time_60"), InlineKeyboardButton("5 min", callback_data="time_300")],
        [InlineKeyboardButton("30 min", callback_data="time_1800"), InlineKeyboardButton("1 hour", callback_data="time_3600")],
        [InlineKeyboardButton("Custom", callback_data="custom_time")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("Select the countdown time:", reply_markup=reply_markup)

async def confirm_time(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()
    
    selected_time = int(query.data.split("_")[1])
    user_time[query.from_user.id] = selected_time

    keyboard = [
        [InlineKeyboardButton("✅ Yes, Start", callback_data="start_countdown")],
        [InlineKeyboardButton("❌ No, Cancel", callback_data="set_time")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(f"Confirm countdown: {format_time(selected_time)}", reply_markup=reply_markup)

async def start_countdown(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if user_id in user_time:
        seconds = user_time[user_id]
        await countdown(query, seconds)

async def countdown(update: Update, seconds: int):
    message = await update.message.reply_text(f"⏳ Countdown: {format_time(seconds)} remaining...")

    for i in range(seconds, 0, -1):
        await asyncio.sleep(1)
        try:
            await message.edit_text(f"⏳ Countdown: {format_time(i)} remaining...")
        except Exception:
            pass  # Ignore errors if message deleted

    await message.edit_text("✅ Countdown Finished!")

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

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(set_time, pattern="set_time"))
    app.add_handler(CallbackQueryHandler(confirm_time, pattern="time_\\d+"))
    app.add_handler(CallbackQueryHandler(start_countdown, pattern="start_countdown"))

    app.run_polling()

if __name__ == "__main__":
    main()
