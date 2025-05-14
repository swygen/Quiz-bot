import random
import asyncio
from datetime import datetime
from pytz import timezone

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    ContextTypes, filters
)

import easy
import hard
from keep_alive import keep_alive

BOT_TOKEN = "7467449022:AAEqnQDusVcovaO6afLaA94P61M70ukG8fo"
GROUP_USERNAME = "swygenbd"
ADMIN_IDS = [6243881362]  # আপনার টেলিগ্রাম ইউজার আইডি
user_data = {}
BD_TZ = timezone('Asia/Dhaka')
user_data = {}

def load_questions(difficulty):
    if difficulty == "easy":
        return easy.questions_easy
    elif difficulty == "hard":
        return hard.questions_hard
    return []

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    try:
        member = await context.bot.get_chat_member(f"@{GROUP_USERNAME}", user.id)
        if member.status in ['member', 'administrator', 'creator']:
            await send_main_menu(update)
        else:
            raise Exception("Not a member")
    except:
        join_btn = InlineKeyboardMarkup([[
            InlineKeyboardButton("গ্রুপে যোগ দিন", url=f"https://t.me/{GROUP_USERNAME}"),
            InlineKeyboardButton("Joined ✅", callback_data="check_join")
        ]])
        await update.message.reply_text("Quiz খেলতে হলে আমাদের গ্রুপে যোগ দিতে হবে:", reply_markup=join_btn)

async def send_main_menu(update):
    keyboard = [
        [InlineKeyboardButton("🟢 Easy Quiz", callback_data="start_easy")],
        [InlineKeyboardButton("🔴 Hard Quiz", callback_data="start_hard")],
        [InlineKeyboardButton("📊 রিপোর্ট", callback_data="daily_report")],
        [InlineKeyboardButton("✉️ ফিডব্যাক পাঠান", url="https://t.me/Swygen_bd")]
    ]
    await update.message.reply_text("Quiz শুরু করতে নিচের অপশনগুলো থেকে একটি বেছে নিন:",
                                    reply_markup=InlineKeyboardMarkup(keyboard))

async def check_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    try:
        member = await context.bot.get_chat_member(f"@{GROUP_USERNAME}", user.id)
        if member.status in ['member', 'administrator', 'creator']:
            await send_main_menu(update.callback_query)
        else:
            raise Exception("Not Joined")
    except:
        await update.callback_query.answer("আপনি এখনও গ্রুপে জয়েন করেননি!", show_alert=True)

async def start_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    difficulty = query.data.split("_")[1]
    user_id = query.from_user.id
    all_questions = load_questions(difficulty)
    asked_ids = user_data.get(user_id, {}).get("asked_ids", set())
    questions = [q for q in all_questions if q["question"] not in asked_ids]
    random.shuffle(questions)
    user_data[user_id] = {
        "questions": questions,
        "score": 0,
        "index": 0,
        "difficulty": difficulty,
        "report": {},
        "answered": False,
        "asked_ids": asked_ids
    }
    await send_question(context, query.message.chat_id, user_id)

async def send_question(context, chat_id, user_id):
    user = user_data[user_id]
    if user["index"] >= len(user["questions"]):
        await context.bot.send_message(chat_id, f"✅ Quiz শেষ!\nআপনার স্কোর: {user['score']} / {len(user['questions'])}")
        return

    q = user["questions"][user["index"]]
    options = q["options"]
    random.shuffle(options)
    buttons = [[InlineKeyboardButton(opt, callback_data=f"answer|{opt}")] for opt in options]
    user["correct"] = q["answer"]
    user["answered"] = False
    user["asked_ids"].add(q["question"])
    msg = await context.bot.send_message(chat_id,
        f"{q['category']} প্রশ্ন:\n{q['question']}\n\n⏳ সময়: 60 সেকেন্ড",
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode="Markdown")
    user["message_id"] = msg.message_id

    for t in range(59, 0, -1):
        if user["answered"]:
            return
        try:
            await asyncio.sleep(1)
            await context.bot.edit_message_text(
                chat_id=chat_id, message_id=msg.message_id,
                text=f"{q['category']} প্রশ্ন:\n{q['question']}\n\n⏳ সময়: {t} সেকেন্ড",
                parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))
        except:
            pass

    if not user["answered"]:
        await context.bot.edit_message_reply_markup(chat_id=chat_id, message_id=msg.message_id, reply_markup=None)
        await context.bot.send_message(chat_id, f"⏰ সময় শেষ!\nসঠিক উত্তর ছিল: {user['correct']}")
        update_daily_report(user_id, False)
        user["index"] += 1
        await send_question(context, chat_id, user_id)

def update_daily_report(user_id, correct):
    date = datetime.now(BD_TZ).strftime('%Y-%m-%d')
    if "report" not in user_data[user_id]:
        user_data[user_id]["report"] = {}
    if date not in user_data[user_id]["report"]:
        user_data[user_id]["report"][date] = {"answered": 0, "correct": 0}
    user_data[user_id]["report"][date]["answered"] += 1
    if correct:
        user_data[user_id]["report"][date]["correct"] += 1

async def answer_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    selected = query.data.split("|")[1]
    user = user_data.get(user_id)
    if not user or user.get("answered"):
        await query.answer("এই প্রশ্নে আপনি উত্তর দিয়েছেন বা টাইম শেষ!", show_alert=True)
        return
    correct = user["correct"]
    user["answered"] = True
    is_correct = selected == correct
    if is_correct:
        user["score"] += 1
        feedback = f"✅ সঠিক উত্তর!\nআপনার স্কোর: {user['score']}"
    else:
        feedback = f"❌ ভুল উত্তর!\nসঠিক উত্তর: {correct}\nআপনার স্কোর: {user['score']}"
    await query.edit_message_reply_markup(reply_markup=None)
    await query.message.reply_text(feedback)
    update_daily_report(user_id, is_correct)
    user["index"] += 1
    await send_question(context, query.message.chat_id, user_id)

async def daily_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    date = datetime.now(BD_TZ).strftime('%Y-%m-%d')
    time_now = datetime.now(BD_TZ).strftime('%I:%M %p')
    report = user_data.get(user_id, {}).get("report", {}).get(date)
    if not report:
        await query.answer("আজকের জন্য কোনো রিপোর্ট নেই!", show_alert=True)
    else:
        answered = report["answered"]
        correct = report["correct"]
        percentage = round((correct / answered) * 100, 2) if answered > 0 else 0
        await query.message.reply_text(
            f"📅 তারিখ: {date}\n🕒 সময়: {time_now}\nউত্তর দিয়েছেন: {answered} টি\nসঠিক উত্তর: {correct} টি\nসফলতা: {percentage}%"
        )

# Keep Alive এবং Bot চালু করা
if __name__ == "__main__":
    keep_alive()
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(check_join, pattern="^check_join$"))
    app.add_handler(CallbackQueryHandler(start_quiz, pattern="^start_"))
    app.add_handler(CallbackQueryHandler(answer_handler, pattern="^answer\|"))
    app.add_handler(CallbackQueryHandler(daily_report, pattern="^daily_report$"))
    print("Bot is running...")
    app.run_polling()
