import os
from dotenv import load_dotenv

import logging

from typing import Optional
from fastapi import FastAPI
import telegram
from pydantic import BaseModel
from telegram import Update, Bot
from telegram.ext import CommandHandler, MessageHandler, Updater, Filters, Dispatcher, CallbackContext
from deta import Deta

load_dotenv()

# TOKEN = os.environ.get("TELE_TOKEN")
TOKEN = os.getenv("TELE_TOKEN")
DETA_KEY = os.getenv("DETA_KEY")

logging.basicConfig(format="%(asctime)s - %(name)s - %(message)s", level=logging.INFO)

FIRST_MSG = """Hello {name}

Welcome to <b>Coffee Go!</b>

Congratulation!!

Now you can get a discount using your discount number {discount_num}

You can join our to follow up for more discounts
"""


app = FastAPI()

deta = Deta(DETA_KEY)

customer_db = deta.Base("Customer_DB")

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

    user_name = getattr(user, "username", '')
    first_name = getattr(user, "first_name", '')

    discount_num = str(hash(user_name))[10:]

    # before adding new data first lets check if it already exists
    customer_query = customer_db.get(str(user.id))
    if customer_query == None:
        discount_num = str(hash(user_name))[10:]
        # save every thing about user
        user_dict = user.to_dict()
        user_dict['discount_num'] = discount_num
        # discount_use(if user used his/her discount or not) and default value is False
        user_dict['discount_use'] = 'False'
        # use id as key
        user_dict['key'] = str(user.id)

        # save to db
        # using put since insert uses more time
        customer_db.put(user_dict)
    customer_query = customer_db.get(str(user.id))
    discount_num = customer_query['discount_num']
    update.message.reply_text(text=FIRST_MSG.format(name=first_name,discount_num=discount_num), parse_mode=telegram.ParseMode.HTML)
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
