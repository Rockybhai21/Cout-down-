import asyncio
import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, CallbackContext, CallbackQueryHandler
import os

TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO
)

async def start(update: Update, context: CallbackContext):
    keyboard = [
        [InlineKeyboardButton("Set Countdown", callback_data="set_time")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Welcome! Set a countdown below:", reply_markup=reply_markup)

async def button_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()

    if query.data == "set_time":
        keyboard = [
            [InlineKeyboardButton("10 Sec", callback_data="10"),
             InlineKeyboardButton("30 Sec", callback_data="30")],
            [InlineKeyboardButton("1 Min", callback_data="60"),
             InlineKeyboardButton("5 Min", callback_data="300")],
            [InlineKeyboardButton("1 Hour", callback_data="3600"),
             InlineKeyboardButton("1 Day", callback_data="86400")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text("Select Countdown Time:", reply_markup=reply_markup)

    else:
        countdown_time = int(query.data)
        await query.message.reply_text(f"Countdown started for {countdown_time} seconds!")
        await countdown(update, countdown_time)

async def countdown(update: Update, seconds: int):
    message = await update.effective_message.reply_text(f"Countdown: {seconds}s remaining...")
    for i in range(seconds, 0, -1):
        await asyncio.sleep(1)
        await message.edit_text(f"Countdown: {i}s remaining...")

    await message.edit_text("⏳ Time's up!")

def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))

    logging.info("Bot started...")
    app.run_polling()

if __name__ == "__main__":
    main()
