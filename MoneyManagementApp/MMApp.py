import os 
import pandas
import datetime
import random
import json
from credentials import end_point_address, encryption, create_keys_rsa, encrypt_packet, decrypt_packet


import kivy
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.network.urlrequest import UrlRequest 
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.button import Button
from kivy.uix.bubble import BubbleButton
from kivy.app import App

kivy.require('2.0.0')
#Config files located on iOS = <HOME_DIRECTORY>/Documents/.kivy/config.ini
# os.environ['KIVY_EVENTLOOP'] = 'asyncio'

#User class
class User():
    def __init__(self, user_id, phone_number, email, username):
        self.user_id = user_id
        self.username = username
        self.email = email
        self.phone_number = phone_number
        self.dataframe = pandas.DataFrame({
            "user_id": [self.user_id],
            "username": [self.username],
            "user_email": [self.email], 
            "phone_number": [self.phone_number]
        })
         
    def __repr__(self):
        return f"Username:\t{self.username}\nEmail:\t{self.email}\nPassword:\t{self.password}\nPhone:\t{self.phone_number}"

#Registration Screen
class RegistrationScreen(Screen):
    def register(self, app):
        #make sure no ; exists in inputs
        for i,v in self.ids.items():
            if ";" in v.text:
                cb = BubbleButton(text="Inputs cannot contain ';' character\n\n\n\n   Close")
                pu = Popup(title="InputError", content=cb, size_hint=(.5, .5))
                cb.bind(on_press=pu.dismiss)
                pu.open()
                return
        #check password length
        if len(self.ids["password"].text) <= 8:
            cb = BubbleButton(text="Passwords must be longer than 8 characters\n\n\n\n   Close")
            pu = Popup(title="InputError", content=cb, size_hint=(.5, .5))
            cb.bind(on_press=pu.dismiss)
            pu.open()
            return 

        #check if user entered password matches confirmation input
        if self.ids["password"].text != self.ids["confirmation"].text:
            cb = BubbleButton(text="Passwords do not match\n\n\n\n   Close")
            pu = Popup(title="InputError", content=cb, size_hint=(.5, .5))
            cb.bind(on_press=pu.dismiss)
            pu.open()
            return 
        #Make a Post request to register user endpoint and encode password with rsa
        user_data_dict = {i:v.text for i,v in self.ids.items()}
        data = encryption(json.dumps(user_data_dict))
        #send json data as encrypted bytes
        UrlRequest(f"https://{end_point_address}/register_user", req_headers={'Content-type': 'application/json', "fromApp": "True"}, req_body=data,on_success=lambda x,y: self.success(req=y, app=app, user_data_dict=user_data_dict), on_progress=self.animation, timeout=25, on_error=self.error, on_failure=lambda x,y: print("failure",y), verify=False)
    def success(self, req, app, user_data_dict):
        response = json.loads(req)    
        #if Successfull save User() as app.user write down unique number in app directory and transition to menu screen
        if "Success" in response.keys():
            data = decrypt_packet(response)
            app.user = User(response["id"], user_data_dict["phone_number"], user_data_dict["username"],  user_data_dict["email"], )
            app.user_id = response["id"]
            #save user id
            with open("UserID","w") as f:
                f.write(response["id"])
            #save user privkey
            with open(f"{user_data_dict['username']}_privkey", "w") as f:
                f.write(response['privkey'])
            #save user pubkey
            with open(f"{user_data_dict['username']}_pubkey", "w") as f:
                f.write(response['pubkey'])
            for w in self.ids.values():
                w.text = ""
            self.manager.transition.direction = "left"
            self.manager.transition.duration = 1
            self.manager.current = "LoginScreen"
        #if Unsuccessfull return Registration error message popup
        else:
            cb = BubbleButton(text="User Name Already Exists\n\n\n\n   Close")
            pu = Popup(title="RegistrationError", content=cb, size_hint=(.5, .5))
            cb.bind(on_press=pu.dismiss)
            pu.open()
            return
    def error(*argsv):
            cb = BubbleButton(text=f"{argsv[-1]}\n\n\n\n   Close")
            pu = Popup(title="RegistrationError", content=cb, size_hint=(.5, .5))
            cb.bind(on_press=pu.dismiss)
            pu.open()

    def animation(*argsv):
        print(argsv)

#Login Screen
class LoginScreen(Screen):
    def login(self, app):
        user = self.ids['username'].text
        #encrypt packet
        packet = encrypt_packet({i:v.text for i,v in self.ids.items()}, user = self.ids['username'].text)
        packet["USER"] = user
        with open("UserID", "r") as f:
            packet["USERID"] = f.read()

        app.user_id = packet["USERID"]
        app.user_password = self.ids['password'].text
        app.user_name = self.ids['username'].text
        
        #request to API for credential confirmation
        UrlRequest(f"https://{end_point_address}/login_user", req_headers={'Content-type': 'application/json', "fromApp": "True"}, req_body=json.dumps(packet),on_success=lambda x,y: self.success(req=y, app=app), on_progress=self.animation, timeout=10, on_error=self.error, on_failure=lambda x,y: print("failure",y), verify=False)
    
    def success(self,req,app):
        #if Successfull collect user data
        user = self.ids['username'].text
        packet = json.loads(req)
        if "Success" in packet.keys():
            del packet["Success"]
            packet = decrypt_packet(packet, user = user)
            app.transactions = pandas.DataFrame.from_dict(json.loads(packet["Transactions"]))
            app.schedule = pandas.DataFrame.from_dict(json.loads(packet["Schedule"]))
            app.goals = pandas.DataFrame.from_dict(json.loads(packet["Goals"]))
            app.wallets = pandas.DataFrame.from_dict(json.loads(packet["Wallets"]))
            app.budgets =  pandas.DataFrame.from_dict(json.loads(packet["Budgets"]))
            self.manager.transition.direction = "left"
            self.manager.transition.duration = 1
            self.manager.current = "MenuScreen"

            return
        
        #return a pop up with Error message if failed
        else:
            cb = BubbleButton(text=f"{packet['Error']}\n\n\n\n   Close")
            pu = Popup(title="LoginError", content=cb, size_hint=(.5, .5))
            cb.bind(on_press=pu.dismiss)
            pu.open()
            return

    def animation(*argsv):
        print(argsv)

    def error(*argsv):
            cb = BubbleButton(text=f"{argsv[-1]}\n\n\n\n   Close")
            pu = Popup(title="LoginError", content=cb, size_hint=(.5, .5))
            cb.bind(on_press=pu.dismiss)
            pu.open()

    def reset_password(self):
        pass

class MenuScreen(Screen):
    def log_out(self, app):
        app.user = False
        app.user_name = False
        app.user_id = False
        app.user_password = False
        self.manager.transition.direction = "right"
        self.manager.transition.duration = 1
        self.manager.current = "LoginScreen"

class TransactionsScreen(Screen):
    #display transaction data on screen
    def display_transactions(self, app):
        #define a column maping dictionary
        self.translate_columns = {
            "ID":"transaction_id",
            "Date":"transaction_date",
            "Amount":"amount",
            "Loc":"location",
            "Type":"transaction_type",
            "Tag":"transaction_tag",
            "Wallet":"wallet_name"
        }

        self.transactions = app.transactions

        #define a column state dictionary for sorting function
        self.column_states = {}
        for column in self.translate_columns.keys():
            self.column_states[column] = "descending"

        #load the GridLayout object
        gl = self.ids["gl"]
        
        #clear the widgets on gl in case there are any currently existing
        gl.clear_widgets()
        gl.size_hint_y = len(app.transactions) / 2.5
        #iterate over the transactions dataframe and add values to the kivy Gridlayout object
        for row in app.transactions.values:
            gl.add_widget(BubbleButton(text=str(row[0]), on_press=self.load_transaction, background_normal="", background_color=(.4, .5, 100, .3)))
            for cell in row[1:]:
                gl.add_widget(Label(text=str(cell)))

    #sort table on screen based on button/columns
    def sort_table(self, button, app):
        #load the GridLayout object
        gl = self.ids["gl"]
        
        #clear the current widgets on gl
        gl.clear_widgets()
        gl.size_hint_y = len(app.transactions) / 2.5
        #if the button state is in decending sort column values in ascending order
        if self.column_states[button.text] == "descending": 
            for row in self.transactions.sort_values(self.translate_columns[button.text], ascending=True).values:
                gl.add_widget(BubbleButton(text=str(row[0]), on_press=self.load_transaction, background_normal="", background_color=(.4, .5, 100, .3)))
                for cell in row[1:]:
                    gl.add_widget(Label(text=str(cell)))
            #set new state to ascending
            self.column_states[button.text] = "ascending"
            return
        
        #if the button state is in ascending sort column values in decending order
        elif self.column_states[button.text] == "ascending": 
            for row in self.transactions.sort_values(self.translate_columns[button.text], ascending=False).values:
                gl.add_widget(BubbleButton(text=str(row[0]), on_press=self.load_transaction, background_normal="", background_color=(.4, .5, 100, .3)))
                for cell in row[1:]:
                    gl.add_widget(Label(text=str(cell)))
            #set new state to descending                    
            self.column_states[button.text] = "descending"
            return
    
    #load a transaction and transition screen when clicked
    def load_transaction(self, button):
        self.manager.get_screen("ViewTransactionScreen").populate_screen(button.text, self.transactions)
        self.manager.transition.direction = "left"
        self.manager.transition.duration = 1
        self.manager.current = "ViewTransactionScreen"
        
class ViewTransactionScreen(Screen):
    def populate_screen(self, button, transactions):
        df = transactions.loc[transactions.transaction_id == int(button)]
        self.ids["transaction_id"].text = str(df.transaction_id.item())
        self.ids["date"].text = str(df.transaction_date.item())
        self.ids["amount"].text = str(df.amount.item())
        self.ids["location"].text = str(df.location.item())
        self.ids["type"].text = str(df.transaction_type.item())
        self.ids["tag"].text = str(df.transaction_tag.item())
        self.ids["wallet"].text = str(df.wallet_name.item())
        
    
    def delete_transaction(self, app):
        #collect transaction_id, wallet name, amount 
        data = {
            "transaction_id": self.ids["transaction_id"].text,
            "wallet_name": self.ids["wallet"].text,
            "amount": self.ids["amount"].text,
            "user_id": str(app.user_id),
            "user_password": str(app.user_password),
            "transaction_type": self.ids["type"].text
        }
        #create a copy of the data
        packet = data.copy()
        #send encrypted packet
        packet = encrypt_packet(packet, user=app.user_name)
        packet["user_name"] = app.user_name
        packet["update"] = "delete transaction"
        UrlRequest(f"https://{end_point_address}/user_services/update", req_headers={'Content-type': 'application/json', "fromApp": "True"}, req_body=json.dumps(packet), on_success=lambda x,y: self.success(req=y, app=app, data=data), on_progress=self.animation, timeout=10, on_error=self.error, on_failure=lambda x,y: print("failure",y), verify=False)
    #function called after successfull https request
    def success(self, req, app, data):
        packet = json.loads(req)
        if "Success" in packet.keys():
            #drop row from dataframe
            app.transactions.drop(app.transactions.loc[app.transactions.transaction_id == int(data["transaction_id"])].index, inplace=True)
            #decrement all ids greater than current by 1
            app.transactions.loc[app.transactions.transaction_id > int(data["transaction_id"]), "transaction_id"] -= 1
            #return reverse transaction from wallet
            if data["transaction_type"] == "Withdrawl":
                #if withdrawl deleted return the amount to the wallet
                app.wallets.loc[app.wallets.wallet_name == data["wallet_name"], "wallet_amount"] += float(data["amount"])
            elif data["transaction_type"] == "Deposit":
                #if deposit deleted subtract amount from wallet
                app.wallets.loc[app.wallets.wallet_name == data["wallet_name"], "wallet_amount"] += float(data["amount"])
            
            #clear screen
            for widget in self.ids.values():
                widget.text = ""
            
            #return result
            cb = BubbleButton(text="Transaction Deleted\n\n\n\n   Close")
            pu = Popup(title="Success", content=cb, size_hint=(.5, .5))
            cb.bind(on_press=pu.dismiss)
            pu.open()
            return
        else:
            cb = BubbleButton(text="Something went wrong\n\n\n\n   Close")
            pu = Popup(title="DeleteError", content=cb, size_hint=(.5, .5))
            cb.bind(on_press=pu.dismiss)
            pu.open()
    #Url request error
    def error(*argsv):
            cb = BubbleButton(text=f"{argsv[-1]}\n\n\n\n   Close")
            pu = Popup(title="APIError `delete_transaction`", content=cb, size_hint=(.5, .5))
            cb.bind(on_press=pu.dismiss)
            pu.open()
    def animation(*argsv):
        print(argsv)

class AddTransactionScreen(Screen):
    #build calender
    def build_calender(self, app):
        sc = ScheduleScreen()
        sc.load_schedule(app, mini=True)
        pu = Popup(title="Calender", content=sc, size_hint=(.7, .7))
        self.pu = pu
        bb = BubbleButton(text="Close", on_press=self.pu.dismiss)
        sc.ids["bl"].remove_widget(sc.ids["dynamic_button"])
        sc.ids["bl"].add_widget(bb)
        self.pu.open()

    #today timestamp
    def build_screen(self, app):
        self.ids["calender"].text = f"{datetime.datetime.now().date()}"
        w = self.ids["wallet"]
        wd = self.ids["wallet_dropdown"]
        wd.clear_widgets()
        for i in app.wallets["wallet_name"].tolist():
            wd.add_widget(Button(text=f"{i}", size_hint_y=None, on_press= lambda x: wd.select(x.text)))
    #add transaction to current table(s) and update table(s) over API
    def add_transaction(self, app):
        data = {i:v.text for i,v in self.ids.items() if i != "dropdown" and i != "wallet_dropdown" and i != "frequency_dropdown"}
        #check for sql injection
        for i,v in data.items():
            if ";" in v:
                cb = BubbleButton(text="Character ';' not allowed\n\n\n\n   Close")
                pu = Popup(title="InputError", content=cb, size_hint=(.5, .5))
                cb.bind(on_press=pu.dismiss)
                pu.open()
                return

        data["user_id"] = app.user_id
        data["user_password"] = app.user_password
        content = data.copy()
        content = encrypt_packet(content, app.user_name)
        content["update"] = "add transaction"
        content["user_name"] = app.user_name
        #send json data as encrypted bytes
        UrlRequest(f"https://{end_point_address}/user_services/update", req_headers={'Content-type': 'application/json', "fromApp": "True"}, req_body=json.dumps(content),on_success=lambda x,y: self.success(req=y, app=app, data=data), on_progress=self.animation, timeout=10, on_error=self.error, on_failure=lambda x,y: print("failure",y), verify=False)
    def success(self, req, app, data):
        response = json.loads(req)
        if "Success" in response.keys():
            transaction_id = len(app.transactions)
            print(transaction_id)
            if transaction_id < 1:
                transaction_id =  0
            df = pandas.DataFrame({
			"transaction_id": [int(transaction_id)],
			"transaction_date": [data["calender"]],
			"amount": [float(data["amount"])],
			"location": [data["location"]],
			"transaction_type": [data["transaction_type"]],
			"transaction_tag": [data["tag"]],
			"wallet_name": [data["wallet"]]
		    })

            #add to transaction table
            app.transactions = pandas.concat([app.transactions, df])
            app.transactions.transaction_id = app.transactions.transaction_id.astype('int')
            app.transactions.reset_index(inplace=True, drop=True)
            #if transaction is for today
            if data["calender"] == str(datetime.datetime.today().date()):
                #subtract from wallet
                if data["transaction_type"] == "Withdrawl":
                    app.wallets.loc[app.wallets.wallet_name == data["wallet"], "wallet_amount"] -= float(data["amount"])
                #add to wallet
                elif data["transaction_type"] == "Deposit":
                    app.wallets.loc[app.wallets.wallet_name == data["wallet"], "wallet_amount"] += float(data["amount"])
            if data["frequency"] != "Once" and data["frequency"] != "Daily":
                #map for frequency
                freq_map = {
                    "Once": 1,
                    "Daily": 1000,
                    "Weekly": 7,
                    "Bi-Weekly": 14,
                    "Monthly": 30,
                    "Quarterly": 90,
                    "Annually": 360
                }
                df = pandas.DataFrame({
                    "transaction_id": [int(transaction_id)],
                    "frequency": [freq_map[data['frequency']]],
                    "scheduled_date": [data["calender"]],
                    "next_day": [datetime.datetime.strptime(data["calender"], "%Y-%m-%d") + datetime.timedelta(days=freq_map[data['frequency']])],
                    "amount": [data["amount"]],
                    "transaction_type": [data["transaction_type"]],
                    "wallet_name": [data["wallet"]],
                    "added_today": [True]
			    })
                app.schedule = pandas.concat([app.schedule, df])
                app.transactions.reset_index(inplace=True, drop=True)
                app.schedule.transaction_id = app.schedule.transaction_id.astype('int')

            #clear screen
            for i,v in self.ids.items():
                if i != "transaction_type" and i != "dropdown" and i != "wallet_dropdown" and i != "frequency_dropdown":
                    v.text = ""
            self.ids["calender"].text = "calender"

            cb = BubbleButton(text="Transaction Added\n\n\n\n   Close")
            pu = Popup(title="Success", content=cb, size_hint=(.5, .5))
            cb.bind(on_press=pu.dismiss)
            pu.open()
            
            return
    #Url request error
    def error(*argsv):
            cb = BubbleButton(text=f"{argsv[-1]}\n\n\n\n   Close")
            pu = Popup(title="APIError `add_transaction`", content=cb, size_hint=(.5, .5))
            cb.bind(on_press=pu.dismiss)
            pu.open()

    
    def animation(*argsv):
        print(argsv)

class ScheduleScreen(Screen):    
    def clear_calender(self):
        self.ids['gl'].clear_widgets()
    def load_schedule(self, app, new_month=False, mini=False):
        #collect todays date
        today = datetime.datetime.now()
        #build calender Map
        self.calender= {
            "1": "Jan",
            "2": "Feb",
            "3": "Mar",
            "4": "Apr",
            "5": "May",
            "6": "Jun",
            "7": "Jul",
            "8": "Aug",
            "9": "Sep",
            "10": "Oct",
            "11": "Nov",
            "12": "Dec"
        }
        #build weekdays list
        ordered_weekdays = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
        self.schedule = app.schedule
        #if new_month is True user new month to populate calender 
        if new_month != False:
            #calculate days in month based on december month
            if new_month["month"] == 12:
                days_in_month = (datetime.date(self.year, 2, 1) - datetime.date(self.year, 1, 1)).days
            #calculate days in month based on january month
            elif new_month["month"] == 1:
                days_in_month = (datetime.date(new_month["year"] + 1, 1, 1) - datetime.date(new_month["year"], 12, 1)).days
            #calculate days in month based on month
            else:
                days_in_month = (datetime.date(new_month["year"], new_month["month"] + 1, 1) - datetime.date(new_month["year"], new_month["month"], 1)).days
            year = new_month["year"]
            month = new_month["month"]
            self.ids['year_label'].text = str(year)
            self.ids['current_month'].text = self.calender[str(month)]
        #fill values with todays date
        else:
            self.year = today.year
            self.ids['year_label'].text = str(self.year)
            self.ids['current_month'].text = self.calender[str(today.month)]
            #collect days in current month
            days_in_month = (datetime.date(today.year, today.month + 1, 1) - datetime.date(today.year, today.month, 1)).days
            year = today.year
            month = today.month
        
        #create a dictionary for calender weekdays related to current month
        dict_calender={}
        for i in range(1,8):
            dict_calender[f'{["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"][datetime.date(year, month, i).weekday()]}'] = []
        #add related dates to related weekdays
        for i,v in zip(list(dict_calender.keys()) * (days_in_month//len(dict_calender.keys()) + 1) , [x for x in range(1,days_in_month+1)]):
            dict_calender[i].append(v)
        #find the first of the month
        first_of_month = [i for i,v in dict_calender.items() if 1 in v][0]
        #add padding to weekdays before the first of the month
        for i in ordered_weekdays:
            if i == first_of_month:
                break
            dict_calender[i] = [""] + dict_calender[i]
        #add padding after last day of the month
        max_len = max([len(i) for i in dict_calender.values()])
        for v in dict_calender.values():
            while len(v) != max_len:
                v.append("")
        #create a dataframe        
        df = pandas.DataFrame(dict_calender)
        #order days sunday - saturday
        df = df[["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]]
        #if mini argument has been specified
        if mini == True:
            df.columns = ["S","M","T","W","T","F","S"]
            self.mini = True
        else:
            self.mini = False
        #iterate over dataframe and add to gridlayout widget
        for column in df.columns:
            self.ids['gl'].add_widget(Label(text=column))
        for row in df.values:
            for cell in row:
                #padding months and days
                if len(str(cell)) == 1:
                    new_cell = f"0{cell}"
                else:
                    new_cell = cell
                if len(str(month)) == 1:
                    month = f"0{month}"
                else:
                    month = month
                if f"{year}-{month}-{cell}" in list(self.schedule["scheduled_date"]) and self.mini == False and f"{year}-{month}-{new_cell}" != str(datetime.datetime.now().date()):
                    bb = BubbleButton(text=f"{cell}", on_press=lambda button: self.view_day(button, app=app))
                    bb.background_normal = ""
                    bb.background_color=  (.4, .5, 100, .3)
                    self.ids['gl'].add_widget(bb)

                if f"{year}-{month}-{new_cell}" == str(datetime.datetime.now().date()):
                    bb = BubbleButton(text=f"Today {cell}", on_press=lambda button: self.view_day(button, app=app, mini=self.mini))
                    bb.background_normal = ""
                    bb.background_color = (0, .5, 1, .5)
                    self.ids['gl'].add_widget(bb)                           

                elif cell == "":
                    self.ids['gl'].add_widget(Label(text=""))
                
                else:
                    bb = BubbleButton(text=f"{cell}", on_press=lambda button: self.view_day(button, app=app, mini=self.mini))
                    bb.halign = "center"
                    bb.valign = "middle"
                    bb.text_size = (20,20)
                    self.ids['gl'].add_widget(bb)
        self.selected_month = int(month)
   
    def view_day(self, button, app, mini=False):
        if mini == True:
            button.background_normal = ""
            button.background_color = (0, .5, 1, 1)
            day = button.text
            if "Today" in day:
                day = day.replace("Today ","")
            if len(day) == 1:
                day = f"0{day}"
            if len(str(self.selected_month)) == 1:
                self.selected_month = f"0{self.selected_month}"
            app.sm.get_screen("AddTransactionScreen").ids["calender"].text = f"{self.year}-{self.selected_month}-{day}"
            return
        if "Today" in button.text:
            today = button.text.replace("Today ","")
        else:
            today = button.text
        self.manager.get_screen("DayScreen").load_day(self.schedule, self.year, self.selected_month, today, app.transactions)
        self.manager.transition.direction = "left"
        self.manager.transition.duration = 1
        self.manager.current = "DayScreen"

    def change_month(self, button, app):
        #collect current month
        current_month = int([i for i,v in self.calender.items() if v == self.ids["current_month"].text][0])
        #logic to decrement month
        if button.text == "<":
            #logic to decrement month based on january
            if current_month == 1:
                current_month = 12
                self.year -= 1
                self.ids["year_label"].text = str(self.year)
                self.ids["current_month"].text = self.calender["12"]
            else:
                current_month -= 1
                self.ids["current_month"].text = self.calender[str(current_month)]
        #logic to increment month
        elif button.text == ">":
            #logic to increment based on december
            if current_month == 12:
                current_month = 1
                self.year += 1
                self.ids["year_label"].text = str(self.year)
                self.ids["current_month"].text = self.calender[str(current_month)]                
            else:
                current_month += 1
                self.ids["current_month"].text = self.calender[str(current_month)]
        self.selected_month = current_month
        #clear the calender
        self.clear_calender()
        #load the new months data
        if self.mini == True:
            self.load_schedule(app, new_month={"year":self.year, "month": current_month}, mini=True)
        else:
            self.load_schedule(app, new_month={"year":self.year, "month": current_month})

class DayScreen(Screen):
    def load_day(self, schedule, year, month, day, df):
        self.schedule = schedule
        self.year = year
        self.month = month 
        self.day = day
        self.transactions = df
        if len(str(self.month)) == 1:
            self.month = f"0{self.month}"
        if len(str(self.day)) == 1:
            self.day = f"0{self.day}"
        self.children[0].children[1].text = f"{year}-{month}-{day}"
        if len(schedule) == 0:
            return
        self.children[0].children[-1].text = f"{self.year}-{self.month}-{self.day}"
        gl = self.children[0].children[1]
        day_data = schedule.loc[schedule.scheduled_date == f"{self.year}-{self.month}-{self.day}"]
        gl.clear_widgets()
        for row in day_data[["transaction_id", "frequency", "scheduled_date","transaction_type", "amount", "wallet_name"]].values:
            gl.add_widget(BubbleButton(text=str(row[0]), background_normal="", background_color=(.4, .5, 100, .3), on_press=self.find_transaction))
            for item in row[1:]:
                gl.add_widget(Label(text=str(item)))

    def find_transaction(self, button):
        self.parent.get_screen("ViewTransactionScreen").load_transaction(button.text, self.transactions)
        self.manager.transition.direction = "left"
        self.manager.transition.duration = 1
        self.manager.current = "ViewTransactionScreen"

    def add_transaction(self):
        if len(str(self.month)) == 1:
            self.month = f"0{self.month}"
        if len(str(self.day)) == 1:
            self.day = f"0{self.day}"
        self.manager.get_screen("AddTransactionScreen").schedule(f"{self.year}-{self.month}-{self.day}")
        self.manager.transition.direction = "down"
        self.manager.transition.duration = 1
        self.manager.current = "AddTransactionScreen"

class WalletsScreen(Screen):
    def load_wallets(self, app):
        gl = self.ids["gl"]
        gl.clear_widgets()
        gl.size_hint_y = len(app.wallets) / 2.5
        for row in app.wallets.values:
            gl.add_widget(BubbleButton(text=str(row[0]), background_normal="", background_color=(.4, .5, 100, .3)))
            for item in row[1:]:
                gl.add_widget(Label(text=str(item)))

class AddWalletScreen(Screen):
    def add_wallet(self, app):
        data = {i:v.text for i,v in self.ids.items() if i != 'gl'}
        print(data)


class MMApp(App):
    def build(self):
        self.sm = ScreenManager()
        self.sm.add_widget(RegistrationScreen(name="RegistrationScreen"))
        self.sm.add_widget(LoginScreen(name="LoginScreen"))
        self.sm.add_widget(MenuScreen(name="MenuScreen"))
        self.sm.add_widget(TransactionsScreen(name="TransactionsScreen"))
        self.sm.add_widget(AddTransactionScreen(name="AddTransactionScreen"))
        self.sm.add_widget(ViewTransactionScreen(name="ViewTransactionScreen"))
        self.sm.add_widget(ScheduleScreen(name="ScheduleScreen"))
        self.sm.add_widget(DayScreen(name="DayScreen"))
        # self.sm.add_widget(BudgetScreen(name="BudgetScreen"))
        self.sm.add_widget(WalletsScreen(name="WalletsScreen"))
        self.sm.add_widget(AddWalletScreen(name="AddWalletScreen"))
        # self.sm.add_widget(GoalsScreen(name="GoalsScreen"))
        # self.sm.add_widget(AddGoalScreen(name="AddGoalScreen"))
        # self.sm.add_widget(AnalysisScreen(name="AnalysisScreen"))        
        # #check to see if User needs to be registered
        if "UserID" in os.listdir():
            self.sm.current =  "LoginScreen"
            string = ""
            with open("UserID", "r") as f:
                string += f.read()
            self.user_id = string
        else:
            self.sm.current = "RegistrationScreen"
        return self.sm


if __name__ == '__main__':
    MMApp().run()
