'''Spreadsheet.py - the backend code for altering spreadsheets
Adapted from https://github.com/AyumuKasuga/MoneyTrackerBot'''

from oauth2client.service_account import ServiceAccountCredentials

import gspread

#scope for oauth2 credentials
scope = ['https://spreadsheets.google.com/feeds',
         'https://www.googleapis.com/auth/drive']

#oauth2 credentials
credentials = ServiceAccountCredentials.from_json_keyfile_name('config/MakanBot-bfb4ea16e630.json', scope)

#authorisation of gspread
gc = gspread.authorize(credentials)


def access_vendor_spreadsheet(vendor):
    """tries to open a vendor's spreadsheet. Returns error if not found"""

    try:
        #open a certain spreadsheet
        return gc.open("{}".format(vendor))
    except gspread.exceptions.SpreadsheetNotFound:
        return "Error"


def create_vendor_spreadsheet(vendor, chat_id):
    """tries to create a vendor's spreadsheet. Spreadsheet will remain private to bot account until shared."""

    try:
        wb = gc.create("{}".format(vendor))
        ws = wb.sheet1
        #pending orders section
        ws.update_acell('A51', 'Chat ID')
        ws.update_acell('B51', 'Name')
        ws.update_acell('C51', 'Order ID')
        ws.update_acell('D51', 'Quantity')
        ws.update_acell('E51', 'Dabao?')
        #menu
        ws.update_acell('A1', 'Price')
        ws.update_acell('B1', 'Item')
        ws.update_acell('C1', 'Vendor Chat ID')
        #Completed orders section
        ws.update_acell('A151', 'Completed:')
        ws.update_acell('B151', 'Chat ID')
        ws.update_acell('C151', 'Name')
        ws.update_acell('D151', 'Order ID')
        ws.update_acell('E151', 'Quantity')
        ws.update_acell('F151', 'Dabao?')
        return wb
    except Exception as e:
        print(e)
        return "An unknown error has occured"


def vendor_check_queue(vendor):
    """Supposed to check the queue inside the spreadsheet"""

    wb = access_vendor_spreadsheet(vendor)
    ws = wb.sheet1
    #we need to find number of menu items first so we use the counter num_menu
    num_menu = 0

    for i in range(2, 51):
        test_cell = ws.acell('A{}'.format(i))
        if test_cell.value != '':
            num_menu += 1
        else:
            pass

    counter = 0 #count how many of an item is being ordered
    counterlist = [] #list will contain quantities of items being ordered

    for i in range(0, num_menu): #i = number of items in menu
        for x in range(52, 151): #range of cells in the list of orders
            test_cell = ws.acell('C{}'.format(x))
            if test_cell.value == '{}'.format(i+1): #finds first instance where order_ID matches order_ID of item from menu
                counter += int(ws.acell('D{}'.format(x)).value) #adds quantity of order to counter
            elif test_cell.value == '':
                break
            else:
                pass
        counterlist.append(counter) #adds counter into a counterlist
        counter = 0 #clears the counter for next item

    menu_dict = {}

    for i in range(0, num_menu):
        menu_dict[i] = counterlist[i]

    return menu_dict


def count_menu(vendor):
    """returns the number of menu items of a particular store"""

    wb = access_vendor_spreadsheet(vendor)
    ws = wb.sheet1
    numberofitem = 0

    for i in range(2, 50):
        menu_item = ws.acell('A{}'.format(i))
        if menu_item.value != "":
            numberofitem += 1
        else:
            break

    return numberofitem


def update_queue(vendor, name, chat_id, order_ID, quantity, dabao):
    """updates the queue for the vendor"""

    wb = access_vendor_spreadsheet(vendor)
    ws = wb.sheet1

    for i in range(52, 151): #loop to check first empty row. Also limit queue to 100 entries
        name_cell = ws.acell('A{}'.format(i))
        if name_cell.value != "":
            pass
        elif name_cell.value == "":
            break
        else:
            print("unexpected error")
            break

    #update these values inside the first empty row found
    ws.update_acell('A{}'.format(i), chat_id)
    ws.update_acell('B{}'.format(i), name)
    ws.update_acell('C{}'.format(i), order_ID)
    ws.update_acell('D{}'.format(i), quantity)
    ws.update_acell('E{}'.format(i), dabao)
    queue_no = queue_count(vendor, chat_id)
    return queue_no


def current_queue(vendor, chat_id):
    """return the current queue of the shop"""

    wb = access_vendor_spreadsheet(vendor)
    ws = wb.sheet1
    shopqueue = 0

    for i in range(52, 151):
        cqueue = ws.acell('A{}'.format(i))
        if cqueue.value != "":
            shopqueue += 1
        else:
            break

    return shopqueue


def queue_count(vendor, chat_id):
    """returns the number of orders in front of a particular person's first order"""

    wb = access_vendor_spreadsheet(vendor)
    ws = wb.sheet1
    queue = 0

    for i in range(52, 151):
        id_cell = ws.acell('A{}'.format(i))
        if id_cell.value == "":
            return queue
        elif int(id_cell.value) == chat_id:
            return queue
        else:
            queue += 1

    return "SMTH WRONG"


def check_serve_order(vendor, chat_id, order_ID):
    """Check to see if order_ID match"""

    wb = access_vendor_spreadsheet(vendor)
    ws = wb.sheet1

    for i in range(52, 151):
        order_cell = ws.acell('C{}'.format(i))
        if order_cell.value == "":
            return "Don't Match", order_ID
        elif int(order_cell.value) == int(order_ID):
            return ws.acell('A{}'.format(i)).value, order_ID
        else:
            pass

    return "SMTH WRONG"


def edit_price(vendor, item_id, price):
    """edits menu price of item specified"""

    wb = access_vendor_spreadsheet(vendor)
    ws = wb.sheet1
    i = int(item_id) + 1
    ws.update_acell('A{}'.format(i), price)
    return ws.acell('A()'.format(i)).value


def edit_menu_item(vendor, item_id, item, chat_id):
    """edits menu item specified"""

    wb = access_vendor_spreadsheet(vendor)
    ws = wb.sheet1
    i = int(item_id) + 1
    ws.update_acell('B{}'.format(i), item)
    ws.update_acell('C2', chat_id)
    return ws.acell('B{}'.format(i)).value


def update_price(vendor, price):
    """updates price specified in the first empty row of the column labeled 'Price'"""

    wb = access_vendor_spreadsheet(vendor)
    ws = wb.sheet1

    for i in range(2, 50): #loop to check first empty row
        name_cell = ws.acell('A{}'.format(i))
        if name_cell.value != "":
            pass
        elif name_cell.value == "":
            break
        else:
            print("unexpected error")
            break

    ws.update_acell('A{}'.format(i), price)


def update_menu_item(vendor, item, chat_id):
    """Updates menu item in the first empty row of the column labeled 'Item'"""

    wb = access_vendor_spreadsheet(vendor)
    ws = wb.sheet1

    for i in range(2, 50): #loop to check first empty row
        name_cell = ws.acell('A{}'.format(i))
        if name_cell.value != "":
            pass
        elif name_cell.value == "":
            break
        else:
            print("unexpected error")
            break

    ws.update_acell('B{}'.format(i), item)
    ws.update_acell('C2', chat_id)


def delete_row_menu(vendor, order_ID):
    """deletes row of menu"""

    wb = access_vendor_spreadsheet(vendor)
    ws = wb.sheet1
    i = order_ID + 1
    ws.delete_row(i)
    ws.insert_row('', index=50)
    return None


def order_completed(vendor, chat_id, order_ID):
    """deletes row of order readied"""

    wb = access_vendor_spreadsheet(vendor)
    ws = wb.sheet1

    for i in range(52, 151):
        order_cell = ws.acell('C{}'.format(i))
        if int(order_cell.value) == int(order_ID):
            #storing data to be copied into completed
            chat_id_cell = ws.acell('A{}'.format(i))
            name_cell = ws.acell('B{}'.format(i))
            order_id_cell = ws.acell('C{}'.format(i))
            quantity_cell = ws.acell('D{}'.format(i))
            dabao_cell = ws.acell('E{}'.format(i))
            ws.delete_row(i) #deletes row of completed order
            ws.insert_row('', index=150) #adds row at bottom of pending orders to keep 'completed orders' section at index 152 and above
            break

    for x in range(152, 255):
        test_cell = ws.acell('B{}'.format(x))
        if test_cell.value != "":
            pass
        elif test_cell.value == "":
            #copies data into completed
            ws.update_acell('B{}'.format(x), chat_id_cell.value)
            ws.update_acell('C{}'.format(x), name_cell.value)
            ws.update_acell('D{}'.format(x), order_id_cell.value)
            ws.update_acell('E{}'.format(x), quantity_cell.value)
            ws.update_acell('F{}'.format(x), dabao_cell.value)
            break
        else:
            print("unexpected error")
            break


    return None


def recover_order(vendor, chat_id):
    """recovers row wrongly deleted"""

    wb = access_vendor_spreadsheet(vendor)
    ws = wb.sheet1

    for i in range(152, 255):
        test_cell = ws.acell('B{}'.format(i))
        if test_cell.value != "":
            pass
        elif test_cell.value == "":
            chat_id_cell = ws.acell('B{}'.format(i-1))
            name_cell = ws.acell('C{}'.format(i-1))
            order_id_cell = ws.acell('D{}'.format(i-1))
            quantity_cell = ws.acell('E{}'.format(i-1))
            dabao_cell = ws.acell('F{}'.format(i-1))
            ws.delete_row(i-1)
            break

    for x in range(52, 152):
        test_cell = ws.acell('A{}'.format(x))
        if test_cell.value != "":
            pass
        elif test_cell.value == '':
            ws.update_acell('A{}'.format(x), chat_id_cell.value)
            ws.update_acell('B{}'.format(x), name_cell.value)
            ws.update_acell('C{}'.format(x), order_id_cell.value)
            ws.update_acell('D{}'.format(x), quantity_cell.value)
            ws.update_acell('E{}'.format(x), dabao_cell.value)
            customer_chat_id = ws.acell('A{}'.format(x))
            break
        else:
            pass

    paisehID = customer_chat_id.value
    return paisehID


def share_spreadsheet(vendor, email):
    """Shares a spreadsheet titled with the vendor's store name to the email specified"""

    _id = access_vendor_spreadsheet(vendor).id
    gc.insert_permission(_id, email, 'user', 'writer', email_message="Lai ah lai")
    return None


def del_spreadsheets():
    '''Deletes all spreadsheets associated with the account.'''

    allfiles = show_all_spreadsheets()
    for i in allfiles:
        _id = i.id
        gc.del_spreadsheet(_id)
    return None


def show_menu(vendor):
    """Function to show the menu associated with a vendor
Returns the entire menu in a list, with each item in a tuple. The tuple
contains the item number, the item name and pricing in that particular order."""

    ws = access_vendor_spreadsheet(vendor).sheet1

    for i in range(2, 50): #loop to check first empty row
        name_cell = ws.acell('A{}'.format(i))
        if name_cell.value != "":
            pass
        elif name_cell.value == "":
            break
        else:
            print("unexpected error")
            break

    data = ws.range('A2:B{}'.format(i-1))
    menu = []
    price = None
    item = None
    row_num = 0

    for i in data:
        if data.index(i) % 2 == 0:
            price = i.value
        else:
            item = i.value
            row_num += 1
            if price != None and item != None:
                menu.append((row_num, item, price))

    return menu


def show_all_spreadsheets():
    """shows all the spreadsheets currently registered with this account"""

    allfiles = gc.openall()
    return allfiles

if __name__ == "__main__":
    pass
