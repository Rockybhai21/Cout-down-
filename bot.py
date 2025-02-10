import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, CallbackContext

TOKEN = "7207793925:AAFME_OkdkEMMcFd9PI7cuoP_ahAG9OHg7U"

# Format time nicely
def format_time(seconds):
    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    time_str = f"{days}d {hours}h {minutes}m {seconds}s" if days else f"{hours}h {minutes}m {seconds}s" if hours else f"{minutes}m {seconds}s" if minutes else f"{seconds}s"
    return time_str

# Start command
async def start(update: Update, context: CallbackContext):
    keyboard = [[InlineKeyboardButton("Set Countdown", callback_data="set_countdown")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Welcome! Set a countdown below:", reply_markup=reply_markup)

# Handle countdown button press
async def button(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    if query.data == "set_countdown":
        await query.message.edit_text("Enter the countdown duration (e.g., '2 hours 30 minutes'):")

# Get countdown duration
async def countdown_input(update: Update, context: CallbackContext):
    user_input = update.message.text.lower()
    seconds = parse_time(user_input)
    
    if seconds is None or seconds <= 0:
        await update.message.reply_text("Invalid time format! Please enter a valid duration.")
        return
    
    keyboard = [
        [InlineKeyboardButton("✅ Confirm", callback_data=f"confirm_{seconds}"),
         InlineKeyboardButton("✏️ Modify", callback_data="set_countdown")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(f"Set countdown for **{format_time(seconds)}**?", reply_markup=reply_markup, parse_mode="Markdown")

# Confirm and start countdown
async def confirm(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    
    seconds = int(query.data.split("_")[1])
    message = await query.message.edit_text(f"⏳ Countdown started for **{format_time(seconds)}**!")
    
    # Start countdown
    sticker_msg = None
    for i in range(seconds, 0, -1):
        await asyncio.sleep(1)
        try:
            await message.edit_text(f"⏳ Countdown: **{format_time(i)}** remaining...", parse_mode="Markdown")
            
            # Send sticker at 60 seconds left
            if i == 60:
                sticker_msg = await message.reply_sticker("-CAACAgUAAxkBAAJG4GeqNtesMkBqm32bkFRZN97PYCVfAAJhFQACi3hQVdJzsKgobr94HgQ")

            # Delete sticker when countdown ends
            if i == 1 and sticker_msg:
                await sticker_msg.delete()

        except Exception:
            break  # Stop editing if message is deleted

    # Send alert when countdown finishes
    await message.reply_text("🚨 **Time's up!** 🚨", parse_mode="Markdown")

# Parse time input
def parse_time(time_str):
    time_units = {"hour": 3600, "minute": 60, "second": 1}
    total_seconds = 0

    parts = time_str.split()
    for i in range(0, len(parts) - 1, 2):
        try:
            num = int(parts[i])
            unit = parts[i + 1].rstrip("s")
            if unit in time_units:
                total_seconds += num * time_units[unit]
        except ValueError:
            return None
    return total_seconds if total_seconds > 0 else None

# Main function
def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, countdown_input))
    app.add_handler(CallbackQueryHandler(confirm, pattern=r"confirm_\d+"))
    
    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
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

        if i in [3600, 600, 60, 10]:
            await context.bot.send_message(chat_id=message.chat_id, text=f"⏳ Reminder: {format_time(i)} remaining!")

        try:
            await message.edit_text(f"⏳ Countdown: **{format_time(i)}** remaining...")
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
    app.add_handler(CallbackQueryHandler(modify_time, pattern="modify_time"))
    app.add_handler(CallbackQueryHandler(pause_resume, pattern="pause_resume"))

    app.run_polling()

if __name__ == "__main__":
    main()
