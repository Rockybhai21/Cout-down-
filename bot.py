import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackContext, CallbackQueryHandler
import threading, time

# Load environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Dictionary to store active countdowns
active_countdowns = {}

def start(update: Update, context: CallbackContext):
    keyboard = [[InlineKeyboardButton("10s", callback_data='10s'),
                 InlineKeyboardButton("1m", callback_data='1m')],
                [InlineKeyboardButton("5m", callback_data='5m'),
                 InlineKeyboardButton("1h", callback_data='1h')],
                [InlineKeyboardButton("1d", callback_data='1d'),
                 InlineKeyboardButton("7d", callback_data='7d')],
                [InlineKeyboardButton("Cancel", callback_data='cancel')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text("Welcome to Countdown Bot! Choose a duration:", reply_markup=reply_markup)

def parse_time(time_str):
    units = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400, 'w': 604800}
    try:
        unit = time_str[-1]
        value = int(time_str[:-1])
        if unit in units:
            return value * units[unit]
    except:
        return None
    return None

def countdown(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    chat_id = query.message.chat_id
    duration = parse_time(query.data)

    if query.data == "cancel":
        if chat_id in active_countdowns:
            del active_countdowns[chat_id]
            query.edit_message_text("Countdown canceled.")
        else:
            query.edit_message_text("No active countdown to cancel.")
        return

    if duration is None:
        query.edit_message_text("Invalid time format.")
        return

    if chat_id in active_countdowns:
        query.edit_message_text("You already have a countdown running! Use /cancel to stop it.")
        return

    message = query.message.reply_text(f"⏳ Countdown started: {query.data} remaining")
    context.bot.pin_chat_message(chat_id, message.message_id)
    active_countdowns[chat_id] = True

    def run_countdown():
        remaining = duration
        while remaining > 0 and active_countdowns.get(chat_id):
            time.sleep(5)
            remaining -= 5
            minutes, seconds = divmod(remaining, 60)
            hours, minutes = divmod(minutes, 60)
            days, hours = divmod(hours, 24)
            countdown_text = f"⏳ Time Remaining: {days}d {hours}h {minutes}m {seconds}s"
            try:
                context.bot.edit_message_text(chat_id=chat_id, message_id=message.message_id, text=countdown_text)
            except:
                break

        if active_countdowns.get(chat_id):
            context.bot.send_message(chat_id, "⏳ Time is up!")
            del active_countdowns[chat_id]

    threading.Thread(target=run_countdown).start()

def main():
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CallbackQueryHandler(countdown))

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()