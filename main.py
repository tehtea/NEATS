"""!/usr/bin/env python
-*- coding: utf-8 -*-

Makan Bot that allows you to preorder your food before arriving at the eating place.
Built by NTU students, designed for NTU students (but possibly beyond!)
Authors: Chew Jing Wei, Ang Jun Liang, Kok Zi Ming, Nigel Ang Wei Jun, Ryan Lau Jit Yang (Team DLLM)
Built on Python 3.6.2, using python-telegram-bot as the wrapper for Telegram Bot API
(https://github.com/python-telegram-bot/python-telegram-bot), and gspread as the
Python API for Google Spreadsheets (https://github.com/burnash/gspread)"""

import logging
import shelve
import pprint
import sys

from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Updater, CommandHandler,\
     ConversationHandler, MessageHandler, RegexHandler, Filters, run_async

import spreadsheet







if sys.version_info[0] < 3:
    raise Exception("Must be using Python 3.")

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
LOGGER = logging.getLogger(__name__)

# Initialise global variable 'stores' when the program starts. It should contain
# a list of stores registered with the bot.
with shelve.open('userdata') as db:
    try:
        stores = db['stores']
    except:
        db['stores'] = []
        stores = db['stores']


def start(bot, update):
    """The callback which runs when /start is passed to the bot. Sends help message to user."""

    update.message.reply_text("Hi there! Thank you for trying out NEATS. "
                              "Below are the available commands you can use:\n\n"
                              "For customers:\n\n"
                              "\t/order - choose a vendor to order food from\n"
                              "\t/queue - choose a vendor to view current queue count from\n\n"
                              "For existing vendors:\n\n"
                              "\t/console - access the master console for existing vendors, "
                              "where you can view the current queue for each item, serve an order, "
                              "and edit the menu in your spreadsheet.\n"
                              "\t/add_menu - allows existing vendors to add items to their menu\n\n"
                              "For new vendors:\n\n"
                              "\t/new_vendor - register as a new vendor under NEATS\n\n"
                              "If anything cocks up during the conversations, use /cancel to end the "
                              "current conversation. \n\n"
                              "** By using the bot, you are agreeing to our terms and conditions, "
                              " which can be viewed via /terms **")


#'/order' callbacks:
def select_store(bot, update, STATE_CUSTOMER_ORDER=50):
    """First callback which runs when /order is passed to the bot. Opens up InlineKeyboard to
show a list of stores to choose from."""

    with shelve.open('userdata') as db:
        stores = db['stores']

    if len(stores) > 0:
        reply_keyboard = [stores]
        update.message.reply_text("Where are you ordering your meal from?",
                                  reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))
    else:
        update.message.reply_text("Sorry Sir/Madam, there are no stores registered with this platform at "
                                  "the moment. Try using this bot next time! The conversation will now end.")
        return ConversationHandler.END

    return STATE_CUSTOMER_ORDER


def valid_store(bot, update, STATE_DINING_PLACE=51):
    """Second callback which runs when /order is passed to the bot. It checks whether
the store chosen by the user is valid for the customer to order food."""

    chat_id = update.message.chat_id

    #get store name from the button pressed in customer_chosen
    store = update.message.text

    #save store name temporary into shelve before updating it to spreadsheet
    with shelve.open('userdata') as db:
        db['{}'.format(chat_id)] = store

    logging.info('Store Chosen: {}'.format(store))
    #get the list of menu item from spreadsheet
    menu = spreadsheet.show_menu(store)
    shop_queue = spreadsheet.current_queue(store, chat_id)

    try:
        with open('{}.png'.format(store), 'rb') as f:
            bot.send_photo(chat_id=chat_id, photo=f)
    except:
        pass

    update.message.reply_text("Current total number of pending orders: {}".format(shop_queue))
    update.message.reply_text("Below is the text menu for the store. ")
    bot.sendMessage(chat_id, "Format of menu:\n (item id, item name, item price)\n{}"
                    .format(pprint.pformat(menu)))
    bot.sendMessage(chat_id, "Send me the item id and quantity of the food that you wish to order! \n"
                             "Please enter your order in the format of (food id,quantity).\n"
                             "E.g. If you want to order 1 set of item 2, send: 2,1")
    return STATE_DINING_PLACE


def dining_place(bot, update, STATE_DINING_PLACE=51, STATE_CUSTOMER_CONFIRM_ORDER=52):
    """Third callback which runs when /order is passed to the bot. It will check whether the
order format specified by user is correct, before asking for their dining place option."""

    chat_id = update.message.chat_id

    #input validation for order item and quantity
    with shelve.open('userdata') as db:
        store = db['{}'.format(chat_id)]

    try:
        text = update.message.text.split(',')
        order_ID = text[0].strip()
        quantity = text[1].strip()
        order_ID = int(order_ID)
        quantity = int(quantity)
        logging.info('Order_ID: {} ; Quantity: {}'.format(order_ID, quantity))
    except:
        update.message.reply_text("Please send the order again in the correct format!")
        return STATE_DINING_PLACE

    if order_ID <= 0 or order_ID > spreadsheet.count_menu(store):
        update.message.reply_text("Please send the order again in the correct format!")
        return STATE_DINING_PLACE
    else:
        pass

    #save order number in shelve temporarily before updating it to spreadsheet
    with shelve.open('userdata')as db:
        db['order{}'.format(chat_id)] = order_ID

    #save quantity in shelve temporarily before updating it to spreadsheet
    with shelve.open('userdata')as db:
        db['QUANTITY{}'.format(chat_id)] = quantity

    reply_keyboard = [["Eat In", "Takeaway"]]
    update.message.reply_text("Do you want to eat in or takeaway?",
                              reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))
    return STATE_CUSTOMER_CONFIRM_ORDER


def customer_confirm_order(bot, update, STATE_SEND_ORDER=53):
    """Fourth callback whick runs when /order is passed to the bot. It opens up an InlineKeyboard
to ask the customer whether they want to confirm their order."""

    chat_id = update.message.chat_id
    dabao = update.message.text

    #save reply for dabao in shelve temporary before updating
    with shelve.open('userdata') as db:
        db['DABAO{}'.format(chat_id)] = dabao

    reply_keyboard = [["Yes", "No"]]
    update.message.reply_text("Please review your input above. Confirm order?",
                              reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))
    return STATE_SEND_ORDER


@run_async
def send_order(bot, update):
    """Fifth callback which runs when /order is passed to the bot. Sends the order
notification to the vendor and updates their spreadsheet."""

    chat_id = update.message.chat_id
    name = update.message.from_user.first_name

    #getting store, order_ID, quantity and dabao stored temporary in shelve and update it into spreadsheet
    with shelve.open('userdata') as db:
        store = db['{}'.format(chat_id)]
        order_ID = db['order{}'.format(chat_id)]
        quantity = db['QUANTITY{}'.format(chat_id)]
        dabao = db['DABAO{}'.format(chat_id)]
        #gets the chat_id tagged to the vendor chosen
        vendor_chat_id = db[store]

    spreadsheet.update_queue(store, name, chat_id, order_ID, quantity, dabao)
    bot.sendMessage(chat_id=vendor_chat_id, text="NEW ORDER: {} sets of {}, Having here or Takeaway: {}"\
                    .format(quantity, order_ID, dabao))

    queue_num = spreadsheet.queue_count(store, chat_id)
    update.message.reply_text("Number of customers in queue before you:{}".format(queue_num))
    update.message.reply_text("Alright, order sent! You will "
                              "be notified when your order is ready.")
    return ConversationHandler.END


#'/new_vendor' callbacks:
def new_vendor(bot, update, STATE_CREATE_NEW_STORE=30):
    """Callback for what happens after the user identifies themselves as a new vendor"""

    update.message.reply_text("New vendor? Very nice! \n"
                              "Please enter the name of your store, followed by a comma and then"
                              " the email you wish your spreadsheet is sent to. \n"
                              "e.g. Char Siew Png, tanahgao@outlook.com (Note: this might take a while.)")
    return STATE_CREATE_NEW_STORE


@run_async
def create_new_store(bot, update, STATE_CREATE_NEW_STORE=30):
    """Callback for registering a new store with the bot"""

    try:
        text = update.message.text.split(',')
        store = text[0].strip()
        email = text[1].strip()
    except:
        update.message.reply_text("Please use the correct format!")
        return STATE_CREATE_NEW_STORE

    logging.info('Verify Store Inputted: {}'.format(store))
    all_spreadsheets = spreadsheet.show_all_spreadsheets()

    #check all spreadsheets registered with the host account for the same store name
    for i in all_spreadsheets:
        if i.title == store:
            update.message.reply_text("Hey, this store name was already registered!!! This conversation will now end.")
            return ConversationHandler.END
        #checks whether the email specified has been used to register another store
        for e in i.list_permissions():
            if e['emailAddress'] == email:
                update.message.reply_text("Hey, this email has registered another store already!!! This conversation will now end.")
                return ConversationHandler.END
            else:
                pass
        else:
            pass

    spreadsheet.create_vendor_spreadsheet(store, update.message.chat_id)

    try:
        spreadsheet.share_spreadsheet(store, email)
    except Exception as e:
        logging.error('Update "%s" caused exception "%s"' % (update, e))
        update.message.reply_text("Something went wrong while trying to share the spreadsheet.")
        return ConversationHandler.END

    with shelve.open('userdata') as db:
        stores = db['stores']
        stores.append(store)
        db['stores'] = stores
        db[store] = update.message.chat_id
    update.message.reply_text("Alright, store registered! Send /add_menu to update your menu via Telegram. "\
                              "Alternatively, please update your menu in the spreadsheet shared with you "\
                              "using the specified format.")

    return ConversationHandler.END


#'/queue callbacks'
def customer_queue1(bot, update, STATE_CHECKQUEUE=200):
    """Command for customer to check the queue of a particular store,
       return how many orders in front of customer"""

    with shelve.open('userdata') as db:
        stores = db['stores']

    if len(stores) > 0:
        reply_keyboard = [stores]
        update.message.reply_text("Which store's queue do you want to check?",
                                  reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))
    else:
        update.message.reply_text("Sorry Sir/Madam, there are no stores registered with this platform at "
                                  "the moment. Try using this bot next time! The conversation will now end.")
        return ConversationHandler.END
    return STATE_CHECKQUEUE


def customer_queue2(bot, update):
    """runs queue_count function in spreadsheet to return queue_no for customer"""

    chat_id = update.message.chat_id
    #Gets store from user input in previous function
    store = update.message.text
    queue_no = spreadsheet.queue_count(store, chat_id)
    update.message.reply_text("There are {} orders in front of you or "
                              "in total if you haven't ordered".format(queue_no))

    return ConversationHandler.END

#'/console' callbacks
@run_async
def main_console(bot, update, STATE_VERIFY=100):
    """Verify vendor to enable access to console commands"""

    #Check stores registered > 0 & checks user chat_id matches any of the registered vendors' chat_ids
    store = ''

    if len(stores) > 0:
        with shelve.open('userdata') as db:
            for key, chat_id in db.items():
                if str(chat_id) == str(update.message.chat_id):
                    if key in db['stores']:
                        store = key

    if store in stores:
        update.message.reply_text("Hello {} vendor!".format(store))
        #store commands description: nesting etc. -> Orders ((Order Ready, Cancel Ready), Check Queue (for vendor obviously)), Edit Menu, Exit
        reply_keyboard = [["Orders/Queue", "Edit Menu", "Exit"]]
        update.message.reply_text("Which section do you want to access?",
                                  reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))
        return STATE_VERIFY
    else:
        update.message.reply_text("Sorry Sir/Madam, you do not seem to be registered as a vendor in the system. "
                                  "The conversation will now end.")
        return ConversationHandler.END


@run_async
def vendor_queue(bot, update):
    """Command for vendor to check unprepared orders on queue."""

    chat_id = update.message.chat_id
    with shelve.open('userdata') as db:
        for key, chat_id in db.items():
            if str(chat_id) == str(update.message.chat_id):
                 #store is used for foodbot, vendor used for spreadsheet
                store = key
            else:
                pass

    menu_dict = spreadsheet.vendor_check_queue(store)

    for i in menu_dict:
        update.message.reply_text("Please prepare {} more of order {}".format(menu_dict[i], i+1))

    return ConversationHandler.END


def order_or_queue(bot, update, STATE_ORDERQUEUE=101):
    """Select orders or check queue"""

    reply_keyboard = [["Orders", "Check Queue", "Back"]]
    update.message.reply_text("Please select a command.",
                              reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))
    return STATE_ORDERQUEUE


def order_console(bot, update, STATE_ORDER_DECISION=102):
    """Select order ready or cancel ready"""

    reply_keyboard = [["Order Ready", "Cancel Ready", "Back"]]
    update.message.reply_text("Please select a command.",
                              reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))
    return STATE_ORDER_DECISION


def order_prepared1(bot, update, STATE_ORDER_READY=103):
    """vendor enters the food_id of the dish which is ready"""

    update.message.reply_text("Enter the order_ID (Menu number of item) of the order you are ready to send. \n"
                              "Please enter a number! E.g: 2",
                              reply_markup=ReplyKeyboardRemove())
    return STATE_ORDER_READY


@run_async
def order_prepared2(bot, update, STATE_ORDER_READY=103):
    """To signify order is ready for collection"""

    order_ID = update.message.text
    chat_id = update.message.chat_id

    with shelve.open('userdata') as db:
        for key, chat_id in db.items():
            if str(chat_id) == str(update.message.chat_id):
                #store is used for foodbot, vendor used for spreadsheet
                store = key
            else:
                pass

    customer_chat_id, customer_order_ID = spreadsheet.check_serve_order(store, chat_id, order_ID) #changed order_chat_id to customer_chat_id for clarity

    if customer_chat_id == "Don't Match":
        update.message.reply_text("Order not found. Please check \n"
                                  "order_ID is inputted correctly! You can type in "
                                  "the order_ID to check for again.",
                                  reply_markup=ReplyKeyboardRemove())
        return STATE_ORDER_READY

    elif order_ID == customer_order_ID:
        update.message.reply_text("order_ID match! Customer notified. System is currently removing the order "
                                  "from the order queue...",
                                  reply_markup=ReplyKeyboardRemove())
        bot.sendMessage(chat_id=customer_chat_id, text="Your order is ready to be collected!")
        spreadsheet.order_completed(store, chat_id, order_ID)
        update.message.reply_text("Order removed from order queue!")
        return ConversationHandler.END

    else:
        update.message.reply_text("Order not found. Please check \n"
                                  "order_ID is inputted correctly!",
                                  reply_markup=ReplyKeyboardRemove())

        return ConversationHandler.END


def edit_menu(bot, update, STATE_EDIT1=104):
    """Callback to give vendor instructions for editing the menu"""

    reply_keyboard = [["Edit Item", "Delete Item", "Back"]]
    update.message.reply_text("Great! Send /add_menu via telegram to add to menu. \n"
                              "**For removal of items or changes to \n"
                              "existing items on menu, please select Delete Item or Edit Item \n"
                              "OR go to the link sent to the \n"
                              "email you registered the bot with to edit the \n"
                              "menu in the spreadsheet directly.",
                              reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True,
                                                               resize_keyboard=True))
    return STATE_EDIT1


def edit_item(bot, update, STATE_EDIT2=105):
    """Asks vendor whether he wants to edit item name, price or delete item"""

    reply_keyboard = [["Edit Name", "Edit Price", "Back"]]
    update.message.reply_text("Edit name or price of item? Press back to return.",
                              reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True,
                                                               resize_keyboard=True))
    return STATE_EDIT2


def edit_name1(bot, update, STATE_EDIT_NAME1=106):
    """Displays menu for vendor to edit name"""

    with shelve.open('userdata') as db:
        for key, chat_id in db.items():
            if str(chat_id) == str(update.message.chat_id):
                store = key
            else:
                pass

    chat_id = update.message.chat_id
    menu = spreadsheet.show_menu(store)
    update.message.reply_text("You will be editing the name of item. "
                              "Send me the item_id and item_name of the food that you wish to edit! \n"
                              "E.g. 2, Ramen")
    bot.sendMessage(chat_id, "Format: (item_id, item_name, item_price)\n{}"
                    .format(pprint.pformat(menu)))
    return STATE_EDIT_NAME1


def edit_name2(bot, update, STATE_EDIT_NAME1=106):
    """Updates the new food name in the vendor's spreadsheet."""

    try:
        text = update.message.text.split(',')
        item_id, food_name = text
    except ValueError:
        update.message.reply_text("Dey, wrong format lah. Try again")
        return STATE_EDIT_NAME1

    logging.info('Verify food name Inputted: {}'.format(food_name))

    with shelve.open('userdata') as db:
        for key, chat_id in db.items():
            if str(chat_id) == str(update.message.chat_id):
                store = key
            else:
                pass

    new_name = spreadsheet.edit_menu_item(store, item_id, food_name, update.message.chat_id)
    update.message.reply_text("Done! Name changed to {}. Conversation will now end.".format(new_name))

    return ConversationHandler.END


def edit_price1(bot, update, STATE_EDIT_PRICE1=108):
    """Displays menu for vendor to edit price"""

    with shelve.open('userdata') as db:
        for key, chat_id in db.items():
            if str(chat_id) == str(update.message.chat_id):
                store = key
            else:
                pass

    chat_id = update.message.chat_id
    menu = spreadsheet.show_menu(store)
    update.message.reply_text("You will be editing the price of item. "
                              "Send me the item_id and price of the food (in SGD) that you wish to edit! \n"
                              "E.g. 2, 5.50")
    bot.sendMessage(chat_id, "Format: (item_id, item_name, item_price)\n{}"
                    .format(pprint.pformat(menu)))
    return STATE_EDIT_PRICE1


def edit_price2(bot, update, STATE_EDIT_PRICE1=108):
    """Updates the new food price in the vendor's spreadsheet."""

    text = update.message.text.split(',')
    item_id, food_price = text
    logging.info('Verify food price Inputted: {}'.format(food_price))

    #input validation for the food price specified - ensures that it can be converted to a float
    try:
        food_price = float(food_price)
        food_price = '{:.2f}'.format(food_price)
    except:
        update.message.reply_text("Please enter a number! Try again")
        food_price = float(food_price)
        food_price = '{:.2f}'.format(food_price)
        return STATE_EDIT_PRICE1

    with shelve.open('userdata') as db:
        for key, chat_id in db.items():
            if str(chat_id) == str(update.message.chat_id):
                store = key
            else:
                pass

    new_price = spreadsheet.edit_price(store, item_id, food_price)
    update.message.reply_text("Done! New price changed to ${}. Conversation will now end.".format(new_price))

    return ConversationHandler.END


def delete_item1(bot, update, STATE_DELETE_ITEM1=110):
    """Displays menu for vendor to delete item"""

    with shelve.open('userdata') as db:
        for key, chat_id in db.items():
            if str(chat_id) == str(update.message.chat_id):
                store = key
            else:
                pass

    menu = spreadsheet.show_menu(store)
    update.message.reply_text("You will be deleting an item."
                              "Send me the item_id of the food that you wish to delete! \n"
                              "E.g. 2")

    update.message.reply_text("Format: (item_id, item_name, item_price){}"
                              .format(pprint.pformat(menu)))

    return STATE_DELETE_ITEM1


def delete_item2(bot, update, STATE_DELETE_ITEM2=111):
    """Deletes row in menu section of vendor's spreadsheet"""
    order_ID = update.message.text

    with shelve.open('userdata') as db:
        for key, chat_id in db.items():
            if str(chat_id) == str(update.message.chat_id):
                store = key
            else:
                pass

    outcome = spreadsheet.delete_row_menu(store, order_ID)
    update.message.reply_text("Done! Conversation will now end.")
    return ConversationHandler.END


@run_async
def cancel_last_mike(bot, update):
    """A restricted command to undo the vendor's previous 'order ready' signal."""
    chat_id = update.message.chat_id

    with shelve.open('userdata') as db:
        for key, chat_id in db.items():
            if str(chat_id) == str(update.message.chat_id):
                store = key #store is used for foodbot, vendor used for spreadsheet
            else:
                pass

    paisehID = spreadsheet.recover_order(store, chat_id)
    update.message.reply_text("Order recovered")
    bot.sendMessage(chat_id=paisehID, text='Paiseh, the vendor made a mistake and your order is not ready yet!')
    return ConversationHandler.END


#Handlers for the conversation which allows vendors to add items to their menu.
def add_menu(bot, update, STATE_2=81):
    """Requests for the new food name from the vendor"""

    update.message.reply_text("Please enter the name of food item.")
    return STATE_2


def add_menu2(bot, update, STATE_3=82):
    """Updates the new food name in the vendor's spreadsheet."""

    food_name = update.message.text
    id_found = False
    logging.info('Verify food name Inputted: {}'.format(food_name))

    with shelve.open('userdata') as db:
        for key, chat_id in db.items():
            if str(chat_id) == str(update.message.chat_id):
                store = key
                id_found = True
                break
            else:
                pass

    if not id_found:
        update.message.reply_text("You're not a store owner! Mai siao siao.")
        return ConversationHandler.END
    else:
        spreadsheet.update_menu_item(store, food_name, update.message.chat_id)
        update.message.reply_text("Good! Now, enter the price of food item in this format: "\
                                  "e.g. if you want to put $3, input '3' excluding the inverted commas.")
        return STATE_3


def add_menu3(bot, update, STATE_4=83):
    """Updates the price of the food item in the vendor's spreadsheet."""

    food_price = update.message.text
    logging.info('Verify food price Inputted: {}'.format(food_price))

    #input validation for the food price specified - ensures that it can be converted to a float
    try:
        food_price = float(food_price)
        food_price = '{:.2f}'.format(food_price)
    except:
        update.message.reply_text("Please enter a number!")
        food_price = float(food_price)
        food_price = '{:.2f}'.format(food_price)
        return STATE_3

    with shelve.open('userdata') as db:
        for key, chat_id in db.items():
            if str(chat_id) == str(update.message.chat_id):
                store = key
            else:
                pass

    spreadsheet.update_price(store, food_price)
    reply_keyboard = [["YES", "NO"]]
    update.message.reply_text("Done! Do you have anymore items to add?",
                              reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))
    return STATE_4


def add_menu4(bot, update, STATE_1=80):
    """callback to loop the conversation if the vendor wants to add another menu item"""

    return STATE_1


def customer_queue1(bot, update, STATE_CHECKQUEUE=200):
    """Command for customer to check the queue of a particular store,
       return how many orders in front of customer"""

    with shelve.open('userdata') as db:
        stores = db['stores']

    if len(stores) > 0:
        reply_keyboard = [stores]
        update.message.reply_text("Which store's queue do you want to check?",
                                  reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))
    return STATE_CHECKQUEUE


def customer_queue2(bot, update):
    """runs queue_count function in spreadsheet to return queue_no for customer"""

    chat_id = update.message.chat_id
    #Gets store from user input in previous function
    store = update.message.text
    queue_no = spreadsheet.queue_count(store, chat_id)
    update.message.reply_text("There are {} orders in front of you or "
                              "in total if you haven't ordered".format(queue_no))
    return ConversationHandler.END


def terms(bot, update):
    """shows the user the terms and conditions for the ordering system"""

    chat_id = update.message.chat_id

    #send the terms and conditions to the user
    with open("termncondition.txt", "rb") as d:
        bot.send_document(chat_id=chat_id, document=d)

    update.message.reply_text("Here are the terms and conditions! By using this bot, you hereby agree to "
                              "whatever legal nonsense we are throwing at you.")


def cancel(bot, update):
    """allows the user to cancel their current operation"""

    user = update.message.from_user
    LOGGER.info("User %s canceled the conversation." % user.first_name)
    update.message.reply_text('Thank you Sir/Madam! Please come again. -Apu',
                              reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


def error(bot, update, error):
    LOGGER.warning('Update "%s" caused error "%s"' % (update, error))


def main():
    # Create the EventHandler and pass it your bot's token.
    updater = Updater("462090913:AAG6WxcdYGxm7gfyGtT6pYMn8IUCxL-iv0o")

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # Conversation states for customer ordering food
    STATE_CUSTOMER_ORDER, STATE_DINING_PLACE, STATE_CUSTOMER_CONFIRM_ORDER,\
    STATE_SEND_ORDER = range(50, 54)

    # Conversation states for new vendor registration
    STATE_CREATE_NEW_STORE = 30

    # Conversation states for the vendor console
    STATE_VERIFY, STATE_ORDERQUEUE, STATE_ORDER_DECISION, STATE_ORDER_READY,\
    STATE_EDIT1, STATE_EDIT2, STATE_EDIT_NAME1,\
    STATE_EDIT_NAME2, STATE_EDIT_PRICE1, STATE_EDIT_PRICE2, STATE_DELETE_ITEM1, STATE_DELETE_ITEM2 = range(100, 112)

    # Conversation states for the add menu conversation
    STATE_1, STATE_2, STATE_3, STATE_4 = 80, 81, 82, 83

    # Conversation state for customer checking queue
    STATE_CHECKQUEUE = 200

    # Conversation Handler for customer ordering food (/order) (occupies states 50 - 53)
    conv_handler_ordering = ConversationHandler(

        entry_points=[CommandHandler('order', select_store)],

        states={

            STATE_CUSTOMER_ORDER: [MessageHandler(Filters.text, valid_store)],

            STATE_DINING_PLACE: [MessageHandler(Filters.text, dining_place)],

            STATE_CUSTOMER_CONFIRM_ORDER: [RegexHandler('^(Eat In|Takeaway)$', customer_confirm_order)],

            STATE_SEND_ORDER: [RegexHandler('^(Yes)$', send_order),
                               RegexHandler('^(No)$', select_store)]
            },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    # Conversation Handler for new vendor's registration (/new_vendor) (occupies state 30)
    conv_handler_new_vendor = ConversationHandler(

        entry_points=[CommandHandler('new_vendor', new_vendor)],

        states={

            STATE_CREATE_NEW_STORE: [MessageHandler(Filters.text, create_new_store)]

        },

        fallbacks=[CommandHandler('cancel', cancel)]
    )

    # Conversation Handler for adding menu (/add_menu) (occupies states 80 - 83)

    conv_handler_add_menu = ConversationHandler(

        entry_points=[CommandHandler('add_menu', add_menu)],

        states={

            STATE_1: [MessageHandler(Filters.text, add_menu)],

            STATE_2: [MessageHandler(Filters.text, add_menu2)],

            STATE_3: [MessageHandler(Filters.text, add_menu3)],

            STATE_4: [RegexHandler('^(YES)$', add_menu),\
                      RegexHandler('^(NO)$', cancel)],
        },

        fallbacks=[CommandHandler('cancel', cancel)]
    )

    # Conversation handler for an existing vendor to access the existing vendor console (/console) (occupies states 100 - 111)
    conv_handler_console = ConversationHandler(

        entry_points=[CommandHandler('console', main_console)],

        states={

            #Handler for checking if user chat_id matches that of a registered vendor's
            STATE_VERIFY: [RegexHandler('^(Orders/Queue)$', order_or_queue), #Handler to ready order/cancel ready/check queue
                           RegexHandler('^(Edit Menu)$', edit_menu), #Handler to edit menu
                           RegexHandler('^(Exit)$', cancel)], #Cancel

            STATE_ORDERQUEUE: [RegexHandler('^(Orders)$', order_console), #Handler to ready order/cancel ready/check queue
                               RegexHandler('^(Check Queue)$', vendor_queue), #Check queue
                               RegexHandler('^(Back)$', main_console)], #Returns to main console

            STATE_ORDER_DECISION: [RegexHandler('^(Order Ready)$', order_prepared1), #Ready order
                                   RegexHandler('^(Cancel Ready)$', cancel_last_mike), #Cancel Ready
                                   RegexHandler('^(Back)$', order_or_queue)], #Cancel

            STATE_ORDER_READY: [MessageHandler(Filters.text, order_prepared2)],

            STATE_EDIT1: [RegexHandler('^(Edit Item)$', edit_item),
                          RegexHandler('^(Delete Item)$', delete_item1),
                          RegexHandler('^(Back)$', main_console)],

            STATE_EDIT2: [RegexHandler('^(Edit Name)$', edit_name1),
                          RegexHandler('^(Edit Price)$', edit_price1),
                          RegexHandler('^(Back)$', edit_menu)],

            STATE_EDIT_NAME1: [MessageHandler(Filters.text, edit_name2)],

            STATE_EDIT_NAME2: [MessageHandler(Filters.text, edit_item)],

            STATE_EDIT_PRICE1: [MessageHandler(Filters.text, edit_price2)],

            STATE_EDIT_PRICE2: [MessageHandler(Filters.text, edit_item)],

            STATE_DELETE_ITEM1: [MessageHandler(Filters.text, delete_item2)],

            STATE_DELETE_ITEM2: [MessageHandler(Filters.text, edit_menu)],

        },

        fallbacks=[CommandHandler('cancel', cancel)]
    )

    # Command Handler for showing the customer queue (/queue) (occupies state 200)
    customer_queue_handler = ConversationHandler(

        entry_points=[CommandHandler('queue', customer_queue1)],

        states={

            STATE_CHECKQUEUE: [MessageHandler(Filters.text, customer_queue2)],

        },

        fallbacks=[CommandHandler('cancel', cancel)]
    )

    # Command Handler for showing start help
    start_handler = CommandHandler('start', start)

    # Command Handler for showing terms and conditions
    terms_handler = CommandHandler('terms', terms)

    # different conversation handlers for each type of action.
    dp.add_handler(conv_handler_ordering)
    dp.add_handler(conv_handler_new_vendor)
    dp.add_handler(conv_handler_add_menu)
    dp.add_handler(conv_handler_console)
    dp.add_handler(customer_queue_handler)
    dp.add_handler(start_handler)
    dp.add_handler(terms_handler)

    # log all errors. In practice, the errors will show up in your bot hosting interface.
    dp.add_error_handler(error)

    #Start the bot
    updater.start_polling()
    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()

if __name__ == '__main__':
    main()
