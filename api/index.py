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

we will let you know when their is another discounts
"""


DISCOUNT_GRANTED_MSG = """
<code>Congratulation!! </code> {name}

Now you can get a discount using your discount number <a href="tg://user?id={user_id}">{discount_num}</a>

When you apply this discount number on 

    Wednsday May 3rd you get 50% off

    Thursday May 4th you get 25% off

    Friday May 5th you get 10% off
"""


FIRST_MSG = """Hello 👋 <a href="tg://user?id={user_id}">{name}</a>

Welcome to <code>Coffee Go!</code>

To get discount on our services send /CoffeeGo

To get the products menu /menu

To contact us /contacts
"""

CONTACT_MSG = """
You can contact as using

@IyasuHa

@Dagalex

"""


app = FastAPI()

deta = Deta(DETA_KEY)

customer_db = deta.Base("Customer_DB")
menu_db = deta.Base("Menu_DB")
susers_db = deta.Base("Susers_DB")

# here i avoided the 9Am thing and just make it when it will be APR 30
# Sunday Apr 30 I think the server time behinde 3hrs
relaseDateTime = datetime.datetime(2023, 5, 1, 22, 10)


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

    # 
    startUser_dict = user.to_dict()
    todayNow = datetime.datetime.now()
    startUser_dict["start_at"]=todayNow.strftime("%d/%m/%y, %H:%M")
    startUser_dict['key'] = str(user.id)
    # 

    susers_db.put(startUser_dict)
    first_name = getattr(user, "first_name", '')
    update.message.reply_html(text=FIRST_MSG.format(name=first_name, user_id=user.id))

def discount(update: Update, context: CallbackContext):
    user = update.effective_user or update.effective_chat

    user_name = getattr(user, "username", '')
    first_name = getattr(user, "first_name", '')
    
    discount_num = str(hash(user_name))[10:]

    # before adding new data first lets check if it already exists
    customer_query = customer_db.get(str(user.id))
    if customer_query == None:
        # some people doesn't have username so better to add their first name
        discount_num = str(hash(user_name+first_name))[10:]
        # save every thing about user
        user_dict = user.to_dict()
        user_dict['discount_num'] = discount_num
        # discount_use(if user used his/her discount or not) and default value is False
        user_dict['discount_use'] = 'False'
        todayNow = datetime.datetime.now()
        user_dict['joined_at'] = todayNow.strftime("%d/%m/%y, %H:%M")

        # also save chat_id for schedule msgs
        # use id as key
        user_dict['key'] = str(user.id)

        # save to db
        # using put since insert uses more time
        customer_db.put(user_dict)
        # sleep time
        time.sleep(.5)
    customer_query = customer_db.get(str(user.id))
    discount_num = customer_query['discount_num']
    if customer_query['discount_use']=="False":
        update.message.reply_html(DISCOUNT_GRANTED_MSG.format(name=first_name,discount_num=discount_num,user_id=user.id))
    else:
        update.message.reply_html(DISCOUNT_USED.format(name=first_name,discount_num=discount_num))

# cron job
@app.get('/api/cron')
def menuReleased():
    # customers only who don't use their discount
    customers = customer_db.fetch({"discount_use": "False"})
    all_customers = customers.items
    while customers.last:
        customers = customer_db.fetch(last=customers.last)
        all_customers += customers.items

    # just hope menu items will not be geater than 1000
    # menus = menu_db.fetch().items

    bot = Bot(TOKEN)
    count = 0

    menuMsg = """
    /menu to see our products menu in detail
    """
    

    # counnt=1
    # for menu in menus:
    #     menuMsg+="\n"+str(counnt)+". \n"+"\tItem: "+menu["item_name"] +"\n"+ "\tPrice: "+str(menu["small_cup_price"]) +" birr\n"
    #     counnt+=1
    # update.message.reply_text("Menus: "+menuTxtAdd)
    # to avoid sending too many msgs at once only sending all menus at once here
    for customer in all_customers:
        try:
            bot.send_photo(
                int(customer['key']),
                "https://i.imgur.com/rmm4gov.jpeg"
            )
            bot.send_message(
                chat_id=int(customer['key']),
                text = menuMsg
            )
            count += 1
            if count == 20:
                time.sleep(1)
                count = 0
        except:
            pass

    return {"msg": "ok"}

def start_stat(update: Update, context: CallbackContext):
    # start stat
    msg = update.message
    effective_user = update.effective_user
    if effective_user.id not in ADMIN_IDs:
        msg.reply_text(text='You are not alloweded to use this command')
        return
    # here customers that only send start
    s_customers = susers_db.fetch()
    all_s_customers = s_customers.items
    while s_customers.last:
        s_customers = susers_db.fetch(last=s_customers.last)
        all_s_customers += s_customers.items
    msg.reply_text(text=f"""
    Total users: {len(all_s_customers)}
    """)

def stat(update: Update, context: CallbackContext):
    # to get genral status
    msg = update.message
    effective_user = update.effective_user
    if effective_user.id not in ADMIN_IDs:
        msg.reply_text(text='You are not alloweded to use this command')
        return
    
    customers = customer_db.fetch()
    all_customers = customers.items
    while customers.last:
        customers = customer_db.fetch(last=customers.last)
        all_customers += customers.items
        
    discount_use = []
    discount_notUse = []

    for customer in all_customers:
        if customer['discount_use'] == 'False':
            discount_notUse.append(customer)
        else:
            discount_use.append(customer)

    msg.reply_text(text=f"""
    Total users: {len(all_customers)}
    Discount used: {len(discount_use)}
    Discount not used: {len(discount_notUse)}
    """)

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
    return f"  {td.days}:Day/s, {td.seconds//3600}:Hour/s And {(td.seconds//60)%60}:Minute/s"

def menu(update: Update, context: CallbackContext):
    # and automate msg send when the timer complete
    msg = update.message
    # time difference
    effective_user = update.effective_user
    timeDiff = relaseDateTime - datetime.datetime.now()
    # if timeDiff.days<0 or effective_user.id in ADMIN_IDs:
    if timeDiff.days<0:
        # timer ends
        # for the first time menu should be send automatically
        msg.reply_text(text="Here are our products menu")
        msg.reply_photo("https://i.imgur.com/rmm4gov.jpeg")
        menus = menu_db.fetch().items
        for menu in menus:
            update.message.reply_html("<strong>"+menu["item_name"]+"</strong>"+"\nPrice: "+str(menu["small_cup_price"])+" birr")

    else:
        count_down_value = count_down(timeDiff)
        msg.reply_text(text=f"""
        The menu will be avaialble <strong>on Wednsday May 03</strong>

        (In <code>{count_down_value}</code>)
        """, parse_mode=telegram.ParseMode.HTML)

def contacts(update: Update, context: CallbackContext):
    msg = update.message
    msg.reply_text(text=CONTACT_MSG, parse_mode=telegram.ParseMode.HTML)

def add_menu(update: Update, context: CallbackContext):
    # this menu is just for the customers to see it
    effective_user = update.effective_user
    if effective_user.id not in ADMIN_IDs:
        update.message.reply_text(text='You are not alloweded to use this command')
        return
    menu_dict = {
        "item_name":"Chocolate Mocha", "price":40, "desc":"Chocolate moca is one of our products"
        }
    menu_db.put(menu_dict)
    update.message.reply_text(text="Initiated...")

def show_menu(update: Update, context: CallbackContext):
    # before time for me/admins
    effective_user = update.effective_user
    if effective_user.id not in ADMIN_IDs:
        update.message.reply_text(text='You are not alloweded to use this command')
        return
    menus = menu_db.fetch().items
    update.message.reply_photo("https://i.imgur.com/rmm4gov.jpeg")
    for menu in menus:
        # this causing error 
        update.message.reply_html("<strong>"+menu["item_name"]+"</strong>"+"\nPrice: "+str(menu["small_cup_price"])+" birr")

def tot_stat(update: Update, context: CallbackContext):

    effective_user = update.effective_user
    if effective_user.id not in ADMIN_IDs:
        update.message.reply_text(text="You are not alloweded to use this command")
        return
    
    customers = customer_db.fetch().items
    count = 1
    for customer in customers:
        update.message.reply_text(str(count)+"\nusername: "+customer["first_name"]+"\njoined_at: "+customer["joined_at"])
        count += 1
        

def register_handlers(dispatcher):
    dispatcher.add_handler(CommandHandler('start', start))    
    dispatcher.add_handler(CommandHandler('CoffeeGo', discount))
    dispatcher.add_handler(CommandHandler('menu', menu))
    dispatcher.add_handler(CommandHandler('contacts', contacts))

    dispatcher.add_handler(CommandHandler('discounted', status_change))
    dispatcher.add_handler(CommandHandler('startstat', start_stat))
    dispatcher.add_handler(CommandHandler('stat', stat))
    dispatcher.add_handler(CommandHandler('showMenu', show_menu))
    dispatcher.add_handler(CommandHandler('adddmenus', add_menu))
    dispatcher.add_handler(CommandHandler('totstat', tot_stat))

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
