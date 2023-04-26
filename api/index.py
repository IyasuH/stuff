import os
from dotenv import load_dotenv
import time
import datetime

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
ADMIN_IDs = [403875924]

logging.basicConfig(format="%(asctime)s - %(name)s - %(message)s", level=logging.INFO)

DISCOUNT_USED = """
Dear {name}

You have alreday used you discount

with discount number {discount_num}

we will let you know when their is other discounts
"""


DISCOUNT_GRANTED_MSG = """
<code>Congratulation!! </code> {name}

Now you can get a discount using your discount number {discount_num}

When you apply this discount number on 

    Wednsday May 3rd you get 50% off

    Thursday May 4th you get 25% off

    Friday May 5th you get 10% off
"""


FIRST_MSG = """Hello 👋 <a href="tg://user?id={user_id}">{name}</a>

Welcome to <code>Coffee Go!</code>

To get discount on our services send /CoffeeGo

To get the products menu /menu
"""

CONTACT_MSG = """
You can contact as using

@IyasuHa
"""


app = FastAPI()

deta = Deta(DETA_KEY)

customer_db = deta.Base("Customer_DB")
menu_db = deta.Base("Menu_DB")

# here i avoided the 9Am thing and just make it when it will be APR 30
# Sunday Apr 30
relaseDateTime = datetime.datetime(2023, 4, 27, 1, 3)


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

    first_name = getattr(user, "first_name", '')
    update.message.reply_html(text=FIRST_MSG.format(name=first_name, user_id=user.id))

def menuReleased(context:CallbackContext):
    context.bot.send_message(context.job.chat_id, text=f"Today is Sunday, And here is your menu")

def discount(update: Update, context: CallbackContext):
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
        todayNow = datetime.datetime.now()
        user_dict['joined_at'] = todayNow.strftime("%d/%m/%y, %H:%M")

        # also save chat_id for schedule msgs
        user_dict['chat_id'] = update.effective_message.chat_id
        # use id as key
        user_dict['key'] = str(user.id)

        # save to db
        # using put since insert uses more time
        customer_db.put(user_dict)
        # sleep time
        time.sleep(2)
    customer_query = customer_db.get(str(user.id))
    discount_num = customer_query['discount_num']
    if customer_query['discount_use']=="False":
        update.message.reply_text(text=DISCOUNT_GRANTED_MSG.format(name=first_name,discount_num=discount_num), parse_mode=telegram.ParseMode.HTML)
    else:
        update.message.reply_text(text=DISCOUNT_USED.format(name=first_name,discount_num=discount_num), parse_mode=telegram.ParseMode.HTML)
    # context.bot.send_message(chat_id=update.effective_chat.id, text="Hello {} Now you will have a discounts!".format(update.message.username))

    # here to send menu due Sunday Apr 30
    timeDiff = relaseDateTime - datetime.datetime.now()
    # total due seconds
    due = timeDiff.days*24*3600+timeDiff.seconds
    if due<0:
        return

    # query all users(who doesn't use their discount) and send them the scheduled msg
    customers = customer_db.fetch({"discount_use": "False"}).items
    for customer in customers:
        try:
            context.job_queue.run_once(menuReleased, due, chat_id=customer['chat_id'], name=str(customer['chat_id']), data=due)
        except:
            pass
    

def stat(update: Update, context: CallbackContext):
    # to get genral status
    msg = update.message
    effective_user = update.effective_user
    if effective_user.id not in ADMIN_IDs:
        msg.reply_text(text='You are not alloweded to use this command')
        return
    msg.reply_text(text="Sending users...")
    # since customers number not expected to be greater than 1000 normal fetch function works fine I think
    # cuatomer thoes who uses discounts
    discount_use = customer_db.fetch({"discount_use": "True"}).items
    # customer thoes who doesn't use their discount
    discount_notUse = customer_db.fetch({"discount_use": "False"}).items
    total=len(discount_use)+len(discount_notUse)
    msg.reply_text(text=f'Total users: {total}\n Discount used: {len(discount_use)}\n Discount not used: {len(discount_notUse)}')

def status_change(update: Update, context: CallbackContext):
    # to update customer discount status
    # not finished tho
    msg = update.message
    effective_user = update.effective_user
    if effective_user.id not in ADMIN_IDs:
        msg.reply_text("You are not alloweded to use this command")
        return
    userName = str(context.args[0])
    userData = customer_db.fetch({"username":userName}).items
    if userData == []:
        msg.reply_text(text=f"User named {userName} not found")
        return
    # changing discount_use to True
    changes = {"discount_use":"True"}
    customer_db.update(changes, str(userData[0]['id']))
    msg.reply_text(text=f'User named {userName} now used his discount')

def count_down(td):
    # recives time delat and return day, hour, minute format
    return f"{td.days} : Days, {td.seconds//3600} : Hours And {(td.seconds//60)%60} : Minutes"

def menu(update: Update, context: CallbackContext):
    # and automate msg send when the timer complete
    msg = update.message
    # time difference
    timeDiff = relaseDateTime - datetime.datetime.now()
    if timeDiff.days<0:
        # timer ends
        # for the first time menu should be send automatically
        msg.reply_text(text="Timer is done here are the products menu")
    else:
        count_down_value = count_down(timeDiff)
        msg.reply_text(text=f"""
        <strong>The menu will be avaialble on Sunday Apr 30</strong>

        After <code>{count_down_value}</code>
        """, parse_mode=telegram.ParseMode.HTML)

def contacts(update: Update, context: CallbackContext):
    msg = update.message
    msg.reply_text(text=CONTACT_MSG, parse_mode=telegram.ParseMode.HTML)

def register_handlers(dispatcher):
    # start_handler = CommandHandler('start', start)
    dispatcher.add_handler(CommandHandler('start', start))
    dispatcher.add_handler(CommandHandler('stat', stat))
    dispatcher.add_handler(CommandHandler('CoffeeGo', discount))
    dispatcher.add_handler(CommandHandler('discounted', status_change))
    dispatcher.add_handler(CommandHandler('menu', menu))
    dispatcher.add_handler(CommandHandler('contacts', contacts))

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
