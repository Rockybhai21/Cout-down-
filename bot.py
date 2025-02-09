import os
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# Load environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Dictionary to store active countdowns
active_countdowns = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("10s", callback_data='10s'),
                 InlineKeyboardButton("1m", callback_data='1m')],
                [InlineKeyboardButton("5m", callback_data='5m'),
                 InlineKeyboardButton("1h", callback_data='1h')],
                [InlineKeyboardButton("1d", callback_data='1d'),
                 InlineKeyboardButton("7d", callback_data='7d')],
                [InlineKeyboardButton("Cancel", callback_data='cancel')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Welcome to Countdown Bot! Choose a duration:", reply_markup=reply_markup)

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

async def countdown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id
    duration = parse_time(query.data)

    if query.data == "cancel":
        if chat_id in active_countdowns:
            del active_countdowns[chat_id]
            await query.edit_message_text("Countdown canceled.")
        else:
            await query.edit_message_text("No active countdown to cancel.")
        return

    if duration is None:
        await query.edit_message_text("Invalid time format.")
        return

    if chat_id in active_countdowns:
        await query.edit_message_text("You already have a countdown running! Use /cancel to stop it.")
        return

    message = await query.message.reply_text(f"⏳ Countdown started: {query.data} remaining")
    await context.bot.pin_chat_message(chat_id, message.message_id)
    active_countdowns[chat_id] = True

    async def run_countdown():
        remaining = duration
        while remaining > 0 and active_countdowns.get(chat_id):
            await asyncio.sleep(5)
            remaining -= 5
            minutes, seconds = divmod(remaining, 60)
            hours, minutes = divmod(minutes, 60)
            days, hours = divmod(hours, 24)
            countdown_text = f"⏳ Time Remaining: {days}d {hours}h {minutes}m {seconds}s"
            try:
                await context.bot.edit_message_text(chat_id=chat_id, message_id=message.message_id, text=countdown_text)
            except:
                break

        if active_countdowns.get(chat_id):
            await context.bot.send_message(chat_id, "⏳ Time is up!")
            del active_countdowns[chat_id]

    asyncio.create_task(run_countdown())

async def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(countdown))

    print("Bot is running...")
    await app.run_polling()

if __name__ == "__main__":
    try:
        # Run the bot using asyncio.run() in a normal environment
        asyncio.run(main())
    except RuntimeError as e:
        # Handle environments where the event loop is already running (e.g., Render)
        if str(e) == "Cannot close a running event loop":
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If the loop is already running, create a task for main()
                loop.create_task(main())
            else:
                # Otherwise, run the loop until main() completes
                loop.run_until_complete(main())
        else:
            raise e
