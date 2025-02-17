import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

TOKEN = "YOUR_BOT_TOKEN"
logging.basicConfig(level=logging.INFO)

active_countdowns = {}

def create_keyboard():
    return [
        [InlineKeyboardButton("Pause", callback_data="pause"),
         InlineKeyboardButton("Resume", callback_data="resume"),
         InlineKeyboardButton("Cancel", callback_data="cancel")]
    ]

async def countdown_task(context: ContextTypes.DEFAULT_TYPE, chat_id: int, duration: int):
    for remaining in range(duration, 0, -1):
        if chat_id not in active_countdowns:
            return  # Countdown cancelled

        status = active_countdowns[chat_id]
        if status["paused"]:
            await asyncio.sleep(1)
            continue
        
        text = f"⏳ Countdown: {remaining} seconds"
        try:
            await context.bot.edit_message_text(chat_id=chat_id, message_id=status["message_id"],
                                                text=text, reply_markup=InlineKeyboardMarkup(create_keyboard()))
        except:
            pass
        await asyncio.sleep(1)
    
    if chat_id in active_countdowns:
        await context.bot.edit_message_text(chat_id=chat_id, message_id=status["message_id"], text="🎉 TIME'S UP!")
        del active_countdowns[chat_id]

async def start_countdown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 1 or not context.args[0].isdigit():
        await update.message.reply_text("Usage: /countdown <seconds>")
        return
    
    duration = int(context.args[0])
    chat_id = update.message.chat_id
    
    keyboard = [[InlineKeyboardButton("Confirm", callback_data=f"confirm_{duration}"),
                 InlineKeyboardButton("Modify", callback_data="modify")]]
    
    await update.message.reply_text(f"Start countdown for {duration} seconds?", 
                                    reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = query.message.chat_id
    data = query.data
    
    if data.startswith("confirm_"):
        duration = int(data.split("_")[1])
        sent_message = await query.message.reply_text(f"⏳ Countdown: {duration} seconds",
                                                      reply_markup=InlineKeyboardMarkup(create_keyboard()))
        active_countdowns[chat_id] = {"paused": False, "message_id": sent_message.message_id}
        asyncio.create_task(countdown_task(context, chat_id, duration))
    
    elif data == "modify":
        await query.message.edit_text("Modify the countdown and send the command again.")
    
    elif data == "pause":
        if chat_id in active_countdowns:
            active_countdowns[chat_id]["paused"] = True
            await query.answer("Countdown paused.")
    
    elif data == "resume":
        if chat_id in active_countdowns:
            active_countdowns[chat_id]["paused"] = False
            await query.answer("Countdown resumed.")
    
    elif data == "cancel":
        if chat_id in active_countdowns:
            del active_countdowns[chat_id]
            await query.message.edit_text("❌ Countdown cancelled.")
            await query.answer("Countdown cancelled.")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome! Use /countdown <seconds> to start a countdown.")

app = Application.builder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("countdown", start_countdown))
app.add_handler(CallbackQueryHandler(handle_buttons))

if __name__ == "__main__":
    print("Bot is running...")
    app.run_polling()
