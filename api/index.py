import os
from dotenv import load_dotenv

import logging
from typing import Optional
from fastapi import FastAPI
from pydantic import BaseModel
from telegram import Update, Bot
from telegram.ext import CommandHandler, MessageHandler, Updater, Filters, Dispatcher, CallbackContext

load_dotenv()

# TOKEN = os.environ.get("TELE_TOKEN")
TOKEN = os.getenv("TELE_TOKEN")

FIRST_MSG = """Hello {name}

Welcome to Ready Coffee

Congratulation!!
Now you can get discounts using your discount Number {discount_num}

You can join our to follow up for more discounts
"""


app = FastAPI()

class TelegramWebhook(BaseModel):
    update_id: int
    message: Optional[dict]
    edited_message: Optional[dict]
    channel_post: Optional[dict]
    edited_channel_post: Optional[dict]
    inline_query: Optional[dict]
    chosen_inline_result: Optional[dict]
    callback_query: Optional[dict]
    shipping_query: Optional[dict]
    pre_checkout_querry: Optional[dict]
    poll: Optional[dict]
    poll_answer: Optional[dict]


def start(update: Update, context: CallbackContext):
    user = update.effective_user or update.effective_chat
    name = getattr(user, "username", '')
    update.message.reply_text(FIRST_MSG.format(name=name,discount_num="1234"))
    # context.bot.send_message(chat_id=update.effective_chat.id, text="Hello {} Now you will have a discounts!".format(update.message.username))

def register_handlers(dispatcher):
    # start_handler = CommandHandler('start', start)
    dispatcher.add_handler(CommandHandler('start', start))

def main():
    updater = Updater(TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    register_handlers(dispatcher)
    updater.start_polling()
    updater.idle()

@app.post("/webhook")
def webhook(webhook_data: TelegramWebhook):
    bot = Bot(token=TOKEN)
    update = Update.de_json(webhook_data.__dict__, bot)
    dispatcher = Dispatcher(bot, None, workers=4, use_context=True)
    register_handlers(dispatcher)
    dispatcher.process_update(update)
    return {"status":"okay"}

@app.get("/")
def index():
    return {"status":"okay"}
