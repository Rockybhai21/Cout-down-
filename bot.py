import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, MessageHandler, Filters, CallbackContext
import json

# Dictionary to store quizzes
quizzes = {}

# Command to create a quiz
def create_quiz(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    text = update.message.text.replace('/quiz ', '').strip()
    
    if '✅' not in text:
        update.message.reply_text("Please mark the correct answer with '✅'.")
        return
    
    parts = text.split('\n')
    question = parts[0]
    options = [opt.replace('✅', '').strip() for opt in parts[1:]]
    correct_option = next((i for i, opt in enumerate(parts[1:]) if '✅' in opt), None)
    
    if correct_option is None:
        update.message.reply_text("No correct answer marked. Use '✅' to mark the correct answer.")
        return
    
    quiz_id = f"quiz_{user_id}_{len(quizzes) + 1}"
    quizzes[quiz_id] = {"question": question, "options": options, "correct": correct_option}
    
    update.message.reply_text(f"Quiz saved with ID: {quiz_id}. Use /startquiz {quiz_id} to begin.")

# Start the quiz
def start_quiz(update: Update, context: CallbackContext) -> None:
    args = context.args
    if not args:
        update.message.reply_text("Usage: /startquiz <quiz_id>")
        return
    
    quiz_id = args[0]
    if quiz_id not in quizzes:
        update.message.reply_text("Quiz not found.")
        return
    
    quiz = quizzes[quiz_id]
    buttons = [[InlineKeyboardButton(opt, callback_data=f"{quiz_id}_{i}")] for i, opt in enumerate(quiz['options'])]
    reply_markup = InlineKeyboardMarkup(buttons)
    update.message.reply_text(quiz['question'], reply_markup=reply_markup)

# Handle answer selection
def handle_answer(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    quiz_id, selected = query.data.rsplit('_', 1)
    selected = int(selected)
    quiz = quizzes.get(quiz_id)
    
    if quiz:
        if selected == quiz['correct']:
            query.edit_message_text(f"✅ Correct! {quiz['question']}")
        else:
            query.edit_message_text(f"❌ Wrong! Correct answer: {quiz['options'][quiz['correct']]}")
    else:
        query.edit_message_text("Quiz not found.")

# Main function to run the bot
def main():
    bot_token = os.getenv("BOT_TOKEN")
    if not bot_token:
        raise ValueError("BOT_TOKEN environment variable is not set")
    
    updater = Updater(bot_token, use_context=True)
    dp = updater.dispatcher
    
    dp.add_handler(CommandHandler("quiz", create_quiz))
    dp.add_handler(CommandHandler("startquiz", start_quiz))
    dp.add_handler(CallbackQueryHandler(handle_answer))
    
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
