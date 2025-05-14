import random
import asyncio
from datetime import datetime
from aiohttp import web
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes
)
from easy import questions as easy_questions
from hard import questions as hard_questions

# --- CONFIGURATION ---
BOT_TOKEN = "7219397761:AAGzeEKdvR8tc1DkH0zoYtrdxYH8J5eS3Jw"
GROUP_USERNAME = "@swygenbd"
ADMIN_ID = 6243881362  # Replace with your Telegram user ID

# --- Keep Alive (Web Server) ---
from keep_alive import keep_alive
async def handle(request):
    return web.Response(text="Bot is alive")

def keep_alive():
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    return runner

# --- Main Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat_member = await context.bot.get_chat_member(GROUP_USERNAME, user.id)

    if chat_member.status not in ['member', 'administrator', 'creator']:
        join_keyboard = InlineKeyboardMarkup(
            InlineKeyboardButton("✅ Joined", callback_data="check_joined")
        )
        await update.message.reply_text(
            "দয়া করে আমাদের গ্রুপে যোগ দিন তারপর Start করুন:",
            reply_markup=join_keyboard
        )
        return

    keyboard = [
        [InlineKeyboardButton("Easy Quiz", callback_data='easy_quiz')],
        [InlineKeyboardButton("Hard Quiz", callback_data='hard_quiz')],
        [InlineKeyboardButton("Report", callback_data='report')],
        [InlineKeyboardButton("Feedback", callback_data='feedback')]
    ]
    await update.message.reply_text(
        f"স্বাগতম {user.first_name}!\n\nএখানে আপনি কুইজ খেলে শিখতে পারবেন।",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def check_joined(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat_member = await context.bot.get_chat_member(GROUP_USERNAME, user.id)

    if chat_member.status in ['member', 'administrator', 'creator']:
        await start(update, context)
    else:
        await update.callback_query.answer("আপনি এখনো গ্রুপে যোগ দেননি!", show_alert=True)

async def send_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE, difficulty):
    questions = easy_questions if difficulty == "easy" else hard_questions
    question = random.choice(questions)
    context.user_data['current_question'] = question
    context.user_data['quiz_start_time'] = datetime.utcnow()
    context.user_data['last_difficulty'] = difficulty

    options = question['options']
    keyboard = [[InlineKeyboardButton(opt, callback_data=f"answer|{opt}")] for opt in options]

    msg = await update.callback_query.message.reply_text(
        f"{question['category']}:\n\n{question['question']}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    context.user_data['quiz_message'] = msg.message_id
    context.user_data['quiz_chat_id'] = msg.chat.id

    asyncio.create_task(countdown_delete(context, msg.chat.id, msg.message_id, 60))

async def countdown_delete(context, chat_id, message_id, seconds):
    await asyncio.sleep(seconds)
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    except:
        pass
    context.user_data['current_question'] = None
    await ask_new_question(context, chat_id)

async def ask_new_question(context, chat_id):
    user_data = context.user_data
    difficulty = user_data.get('last_difficulty', 'easy')
    questions = easy_questions if difficulty == "easy" else hard_questions
    question = random.choice(questions)
    user_data['current_question'] = question

    options = question['options']
    keyboard = [[InlineKeyboardButton(opt, callback_data=f"answer|{opt}")] for opt in options]

    msg = await context.bot.send_message(
        chat_id=chat_id,
        text=f"{question['category']}:\n\n{question['question']}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    user_data['quiz_message'] = msg.message_id
    user_data['quiz_chat_id'] = msg.chat.id
    asyncio.create_task(countdown_delete(context, msg.chat.id, msg.message_id, 60))

async def quiz_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.data == "easy_quiz":
        await send_quiz(update, context, "easy")
    elif query.data == "hard_quiz":
        await send_quiz(update, context, "hard")

async def answer_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    selected = query.data.split("|")[1]
    question = context.user_data.get('current_question')

    if not question:
        await query.answer("কোন প্রশ্ন পাওয়া যায়নি।")
        return

    correct = question['answer']
    msg = query.message

    new_buttons = []
    for row in msg.reply_markup.inline_keyboard:
        new_row = []
        for button in row:
            if button.text == correct:
                new_row.append(InlineKeyboardButton(f"✅ {button.text}", callback_data="disabled"))
            elif button.text == selected:
                new_row.append(InlineKeyboardButton(f"❌ {button.text}", callback_data="disabled"))
            else:
                new_row.append(InlineKeyboardButton(button.text, callback_data="disabled"))
        new_buttons.append(new_row)

    await msg.edit_reply_markup(reply_markup=InlineKeyboardMarkup(new_buttons))

    if selected == correct:
        context.user_data['correct'] = context.user_data.get('correct', 0) + 1
        await query.answer("সঠিক উত্তর!")
    else:
        context.user_data['wrong'] = context.user_data.get('wrong', 0) + 1
        await query.answer(f"ভুল উত্তর। সঠিক উত্তর: {correct}", show_alert=True)

    await asyncio.sleep(2)
    try:
        await msg.delete()
    except:
        pass

    context.user_data['current_question'] = None
    await ask_new_question(context, msg.chat.id)

async def report_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    correct = context.user_data.get('correct', 0)
    wrong = context.user_data.get('wrong', 0)
    total = correct + wrong
    percentage = round((correct / total) * 100) if total > 0 else 0

    await update.callback_query.message.reply_text(
        f"আপনার রিপোর্ট:\n"
        f"সঠিক উত্তর: {correct}\n"
        f"ভুল উত্তর: {wrong}\n"
        f"সফলতা: {percentage}%"
    )

async def feedback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text="ধন্যবাদ | Swygen Vai | এইরকম একটা শিক্ষামূলক বট তৈরি করে উপহার দেওয়ার জন্য !"
    )
    await update.callback_query.answer("আপনার ফিডব্যাক পাঠানো হয়েছে!")

# --- Main Entry Point ---
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(check_joined, pattern="check_joined"))
    app.add_handler(CallbackQueryHandler(quiz_handler, pattern="^(easy_quiz|hard_quiz)$"))
    app.add_handler(CallbackQueryHandler(answer_handler, pattern="^answer\\|"))
    app.add_handler(CallbackQueryHandler(report_handler, pattern="^report$"))
    app.add_handler(CallbackQueryHandler(feedback_handler, pattern="^feedback$"))

    runner = keep_alive()
    loop = asyncio.get_event_loop()
    loop.run_until_complete(runner.setup())
    site = web.TCPSite(runner, "0.0.0.0", 8080)
    loop.run_until_complete(site.start())

    app.run_polling()

if __name__ == "__main__":
    main()
