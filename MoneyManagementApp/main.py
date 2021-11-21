import os
import datetime
import random
import json
import sqlite3
from packets import end_point_address, encryption, create_keys_rsa, build_packet, recieve_packet
import base64

import kivy
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.network.urlrequest import UrlRequest 
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.button import Button
from kivy.uix.bubble import BubbleButton
from kivy.lang import Builder
from kivy.app import App


kivy.require('2.0.0')

Builder.load_file("main.kv")

class User():
    def __init__(self, user_id, phone_number, email, username, password):
        self.user_id = user_id
        self.username = username
        self.email = email
        self.phone_number = phone_number
        self.password = password
        self.add_new_transaction_dict = None
        self.delete_transaction_dict = None
        self.add_wallet_dict = None
        self.delete_wallet_dict = None
        self.conn = sqlite3.connect("user.db")
        self.cur = self.conn.cursor()
        self.cur.execute("""
            CREATE TABLE if not exists user_table(
                user_id int,
                user_email text,
                username text,
                phone_number text,
                user_password text
            )""")
        self.conn.commit()
        self.freq_map = {
            "Once": 1,
            "Daily": 1000,
            "Weekly": 7,
            "Bi-Weekly": 14,
            "Monthly": 30,
            "Quarterly": 90,
            "Annually": 360
        }
    def __repr__(self):
        return f"username: {self.username}\nid: {self.user_id}\nemail: {self.email}\nphonenumber {self.phone_number}"

    def write_self(self):
        self.cur.execute(f"""
            INSERT INTO user_table (user_id, user_email, username, phone_number, user_password)
            VALUES({self.user_id},'{self.email}','{self.username}', '{self.phone_number}', '{self.password}')
            """)
        self.conn.commit()
             
class Screen(Screen):
    def __init__(self, name):
        self.previous_screen = None
        self.next_screen = None
        self.today = None
        super().__init__()
        self.name = name
        self.mini = False
        self.translate_columns = {
            "ID":"transaction_id",
            "Date":"transaction_date",
            "Amount":"amount",
            "Loc":"location",
            "Type":"transaction_type",
            "Tag":"transaction_tag",
            "Wallet":"wallet_name"
        }
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
        self.ordered_weekdays = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
       
    def __repr__(self):
        return f"previous Screen: {self.previous_screen}\nnext Screen: {self.next_screen}\nScreen Name:{self.name}\nsend_request commands:\n\t'register user'\n\t'login'\n\t'update'"
    
    def screen_transition(self, screen, direction='left', duration=1):
        self.manager.transition.direction = direction
        self.manager.transition.duration = duration
        self.manager.current = screen
    
    def load_transaction(self, button):
        self.manager.get_screen("ViewTransactionScreen").previous_screen = self.name
        self.screen_transition("ViewTransactionScreen", direction='up')
        self.manager.get_screen("ViewTransactionScreen").populate_screen(button.text)
  
    def send_request(self, data, action):
        endpoints = {
            "register user":"register_user",
            "login": "login_user",
            "update":"user_services/update",
        }

        UrlRequest(
            f"https://{end_point_address}/{endpoints[action]}", 
            req_headers={'Content-type': 'application/json', "fromApp": "True"}, 
            req_body=data,
            on_success=self.request_response, 
            on_progress=self.animation, 
            timeout=20, 
            on_error=self.request_error, 
            on_failure=self.failed_request, 
            verify=False
        )

    def failed_request(self, req, response):
        print("failed")
        self.prompt(f"{self.name}Error",response)

    def request_response(self, req, response):
        response = json.loads(response)
        response = recieve_packet(response)
        if "Success" in response.keys():
            if response["Success"] == 'registration complete':
                #register user
                global app_user
                app_user.user_id = response["id"]
                #save keys
                with open(f"{app_user.username}_privkey", "w") as f:
                    f.write(response['privkey'])
                with open(f"{app_user.username}_pubkey", "w") as f:
                    f.write(response['pubkey'])
                for w in self.ids.values():
                    w.text = ""
                #transition to loginscreen
                self.screen_transition("LoginScreen")
                #write to database
                app_user.write_self()
            elif response["Success"] == "User logged in with ID and password":
                #retrieve tables from end point and save to app_user
                app_user.transactions = json.loads(response["Transactions"])
                app_user.schedule = json.loads(response["Schedule"])
                app_user.wallets = json.loads(response["Wallets"])
                #transition to main menu
                self.screen_transition("MenuScreen")
            elif response["Success"] == "Transaction added":
                transaction_id = len(app_user.transactions.transaction_id) 
                transaction_df = pd.DataFrame({
                    "transaction_id": [int(transaction_id)],
                    "transaction_date": [app_user.add_new_transaction_dict["calender"]],
                    "amount": [float(app_user.add_new_transaction_dict["amount"])],
                    "location": [app_user.add_new_transaction_dict["location"]],
                    "transaction_type": [app_user.add_new_transaction_dict["transaction_type"]],
                    "transaction_tag": [app_user.add_new_transaction_dict["tag"]],
                    "wallet_name": [app_user.add_new_transaction_dict["wallet"]]
                })
                #add to transaction table
                app_user.transactions = pd.concat([app_user.transactions, transaction_df])
                app_user.transactions.transaction_id = app_user.transactions.transaction_id.astype('int')
                app_user.transactions.reset_index(inplace=True, drop=True)
                #check if transaction is scheduled for today
                if app_user.add_new_transaction_dict["calender"] == str(datetime.datetime.today().date()):
                    #subtract from wallet
                    if app_user.add_new_transaction_dict["transaction_type"] == "Withdrawl":
                        app_user.wallets.loc[app_user.wallets.wallet_name == app_user.add_new_transaction_dict["wallet"], "wallet_amount"] -= float(app_user.add_new_transaction_dict["amount"])
                    #add to wallet
                    elif app_user.add_new_transaction_dict["transaction_type"] == "Deposit":
                        app_user.wallets.loc[app_user.wallets.wallet_name == app_user.add_new_transaction_dict["wallet"], "wallet_amount"] += float(app_user.add_new_transaction_dict["amount"])
                #schedule the transaction
                if app_user.add_new_transaction_dict["frequency"] != "Daily" and app_user.add_new_transaction_dict["calender"] != str(datetime.datetime.today().date()):
                    schedule_df = pd.DataFrame({
                        "transaction_id": [int(transaction_id)],
                        "frequency": [app_user.freq_map[app_user.add_new_transaction_dict['frequency']]],
                        "scheduled_date": [app_user.add_new_transaction_dict["calender"]],
                        "next_day": [datetime.datetime.strptime(app_user.add_new_transaction_dict["calender"], "%Y-%m-%d") + datetime.timedelta(days=app_user.freq_map[app_user.add_new_transaction_dict['frequency']])],
                        "amount": [app_user.add_new_transaction_dict["amount"]],
                        "transaction_type": [app_user.add_new_transaction_dict["transaction_type"]],
                        "wallet_name": [app_user.add_new_transaction_dict["wallet"]],
                        "added_today": [True]
                    })
                    app_user.schedule = pd.concat([app_user.schedule, schedule_df])
                    app_user.transactions.reset_index(inplace=True, drop=True)
                    app_user.schedule.transaction_id = app_user.schedule.transaction_id.astype('int')
                    app_user.schedule.frequency = app_user.schedule.frequency.astype('int')
                for i,v in self.ids.items():
                    if i != "transaction_type" and i != "dropdown" and i != "wallet_dropdown" and i != "frequency_dropdown" and i != "back_button":
                        v.text = ""
                        self.ids["calender"].text = "calender"
                self.prompt("Success","Transaction Added")
                
            elif response["Success"] == "Transaction deleted, Wallet updated, Schedule updated":
                #drop row from dataframe
                app_user.transactions.drop(app_user.transactions.loc[app_user.transactions.transaction_id == int(app_user.delete_transaction_dict["transaction_id"])].index, inplace=True)
                #decrement all ids greater than current by 1
                app_user.transactions.loc[app_user.transactions.transaction_id > int(app_user.delete_transaction_dict["transaction_id"]), "transaction_id"] -= 1
                #return reverse transaction from wallet
                if app_user.delete_transaction_dict["transaction_type"] == "Withdrawl":
                    #if withdrawl deleted return the amount to the wallet
                    app_user.wallets.loc[app_user.wallets.wallet_name == app_user.delete_transaction_dict["wallet_name"], "wallet_amount"] += float(app_user.delete_transaction_dict["amount"])
                elif app_user.delete_transaction_dict["transaction_type"] == "Deposit":
                    #if deposit deleted subtract amount from wallet
                    app_user.wallets.loc[app_user.wallets.wallet_name == app_user.delete_transaction_dict["wallet_name"], "wallet_amount"] += float(app_user.delete_transaction_dict["amount"])
                #delete transaction from the schedule
                if  int(app_user.delete_transaction_dict["transaction_id"]) in app_user.schedule.transaction_id.tolist():
                    app_user.schedule.drop(app_user.schedule.loc[app_user.schedule.transaction_id == int(app_user.delete_transaction_dict["transaction_id"])].index, inplace=True)
                #clear screen
                for widget in self.ids.values():
                    widget.text = ""
                self.prompt("Success", response["Success"])
            elif response["Success"] == "New Wallet added":
                df = pd.DataFrame({
                    "wallet_id": [len(app_user.wallets)],
                    "wallet_name": [app_user.add_wallet_dict["wallet_name"]],
                    "wallet_amount": [app_user.add_wallet_dict["wallet_amount"]],
                    "short_description": [app_user.add_wallet_dict["wallet_description"]],
                    "wallet_created_date": [str(datetime.datetime.now().date())],
                    "transaction_count": [0]
                })
                app_user.wallets = pd.concat([app_user.wallets, df])
                app_user.wallets.wallet_id = app_user.wallets.wallet_id.astype('int')
                app_user.wallets.reset_index(inplace=True, drop=True)
                self.prompt("Success", response["Success"])
            
            elif response["Success"] == "Wallet deleted":
                app_user.wallets.drop(app_user.wallets.loc[app_user.wallets.wallet_name == app_user.delete_wallet_dict["wallet_name"]].index, inplace=True)
                self.prompt("Success", response["Success"])


                
        else:
            self.prompt("Error", response["Error"])
    
    def request_error(self, req, error):
        print("error")
        self.prompt(f"{self.name}Error",error)
        
    def prompt(self, error_type, error_message):
        cb = BubbleButton(text=f"{error_message}\n\n\n\n   Close")
        pu = Popup(title=f"{error_type}", content=cb, size_hint=(.5, .5))
        cb.bind(on_press=pu.dismiss)
        pu.open()
    
    def check_user_inputs(self, inputs, registration=False, wallet_check=False):
        if registration == True:
            if len(inputs["password"]) < 8:
                self.prompt("InputError", "Password Must be at least 8 characters long")
                return False
            elif inputs["confirmation"] != inputs["password"]:
                self.prompt("InputError", "Passwords must match")
                return False
            else:
                pass
        
        for i,v in inputs.items():
            if ";" in v or "select" in v.lower() or "drop" in v.lower():
                self.prompt("InputError", "No input can hold the character ';', word 'SELECT' or 'DROP'")
                return False
        if wallet_check == True:
            try:
                float(inputs['wallet_amount'])
            except:
                self.prompt("InputError", "wallet amount must be and integer or decimal")
                return False
        
        return True
    
    def build_calender(self, year=datetime.datetime.now().year, month=datetime.datetime.now().month):
        days_in_month = self.collect_days_in_month(year, month)
        self.ids['year_label'].text = str(year)
        self.ids['current_month'].text = self.calender[str(month)]
        #create a dictionary for calender weekdays related to current month
        dict_calender={}
        for i in range(1,8):
            dict_calender[f'{["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"][datetime.date(year, month, i).weekday()]}'] = []
        #pair related dates to related weekdays
        for i,v in zip(list(dict_calender.keys()) * (days_in_month//len(dict_calender.keys()) + 1) , [x for x in range(1,days_in_month+1)]):
            dict_calender[i].append(v)
        #find the first of the month
        first_of_month = [i for i,v in dict_calender.items() if 1 in v][0]
        #add padding (empty cells) before the first of the month
        for i in self.ordered_weekdays:
            if i == first_of_month:
                break
            dict_calender[i] = [""] + dict_calender[i]
        #add padding (empty cells) to the last day of the month
        max_len = max([len(i) for i in dict_calender.values()])
        for v in dict_calender.values():
            while len(v) != max_len:
                v.append("")
        #create a dataframe        
        calender_df = pd.DataFrame(dict_calender)
        #order weekdays
        calender_df = calender_df[["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]]
        #iterate over dataframe and add to gridlayout widget
        for column in calender_df.columns:
            self.ids['gl_calender'].add_widget(Label(text=column))
        for row in calender_df.values:
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
                
                if f"{year}-{month}-{new_cell}" in list(app_user.schedule["scheduled_date"]) and f"{year}-{month}-{new_cell}" != str(datetime.datetime.now().date()):
                    if self.mini == True:
                        bb = BubbleButton(text=f"{cell}", on_press=self.select_day)
                    else:
                        bb = BubbleButton(text=f"{cell}", on_press=self.view_day)
                    bb.background_normal = ""
                    bb.background_color=  (.4, .5, 100, .3)
                    self.ids['gl_calender'].add_widget(bb)
                    continue

                if f"{year}-{month}-{new_cell}" == str(datetime.datetime.now().date()):
                    if self.mini == True:
                        bb = BubbleButton(text=f"Today {cell}", on_press=self.select_day)
                    else:
                        bb = BubbleButton(text=f"Today {cell}", on_press=self.view_day)
                    bb.background_normal = ""
                    bb.background_color = (0, .5, 1, .5)
                    self.ids['gl_calender'].add_widget(bb)                           

                elif cell == "":
                    self.ids['gl_calender'].add_widget(Label(text=""))
                
                else:
                    if self.mini == True:
                        bb = BubbleButton(text=f"{cell}", on_press=self.select_day)
                    else:
                        bb = BubbleButton(text=f"{cell}", on_press=self.view_day)
                    bb.halign = "center"
                    bb.valign = "middle"
                    bb.text_size = (20,20)
                    self.ids['gl_calender'].add_widget(bb)
        self.selected_month = int(month)
    
    def view_day(self, button):
        if "Today" in button.text:
            today = button.text.replace("Today ","")
        else:
            today = button.text
        self.manager.get_screen("DayScreen").load_day(self.ids["year_label"].text, self.selected_month, today)
        self.screen_transition("DayScreen")

    def select_day(self, button):
        if len(str(self.selected_month)) == 1:
            month = f"0{self.selected_month}"
        else:
            month = str(self.selected_month)
        if len(str(button.text)) == 1:
            day = f"0{button.text}"
        else:
            day = str(button.text)
        self.manager.get_screen("AddTransactionScreen").ids["calender"].text = f"{self.ids['year_label'].text}-{month}-{day}"
        for b in self.ids["gl_calender"].children:
            b.background_normal = ""
            b.background_color=  (0, 0, 0, 0)

        button.background_normal = ""
        button.background_color = (0, .5, 1, .5)

    def change_month(self, button):
        current_month = int([i for i,v in self.calender.items() if v == self.ids["current_month"].text][0])
        if button.text == "<":
            #logic to decrement month based on january
            if current_month == 1:
                current_month = 12
                self.ids["year_label"].text = str(int(self.ids["year_label"].text) - 1)
                self.ids["current_month"].text = self.calender["12"]
            else:
                current_month -= 1
                self.ids["current_month"].text = self.calender[str(current_month)]
        #logic to increment month
        elif button.text == ">":
            #logic to increment based on december
            if current_month == 12:
                current_month = 1
                self.ids["year_label"].text = str(int(self.ids["year_label"].text) + 1)
                self.ids["current_month"].text = self.calender[str(current_month)]                
            else:
                current_month += 1
                self.ids["current_month"].text = self.calender[str(current_month)]
        self.selected_month = current_month
        #clear the calender
        self.clear_calender()
        #load the new months data
        self.build_calender(int(self.ids["year_label"].text), current_month)
    
    def clear_calender(self):
        self.ids['gl_calender'].clear_widgets()
    
    def collect_days_in_month(self, year, month):
        #calculate days in month based on december month
        if month == 12:
            days_in_month = (datetime.date(year, 2, 1) - datetime.date(year, 1, 1)).days
        #calculate days in month based on january month
        elif month == 1:
            days_in_month = (datetime.date(year + 1, 1, 1) - datetime.date(year, 12, 1)).days
        #calculate days in month based on month
        else:
            days_in_month = (datetime.date(year, month + 1, 1) - datetime.date(year, month, 1)).days
        return days_in_month

    def animation(self, req, start, end):
        print(start, end)
        pass
        
class RegistrationScreen(Screen):
    def register(self):
        user_inputs = {i:v.text for i,v in self.ids.items()}
        if self.check_user_inputs(user_inputs, registration=True) == True:
            global app_user
            data = user_inputs.copy()
            app_user = User("None", user_inputs["phone_number"], user_inputs["email"], user_inputs["username"], user_inputs["password"])
            packet = build_packet(data)
            self.send_request(packet, "register user")

        else:
            return
        
class LoginScreen(Screen):
    def login(self):
        user_inputs = {i:v.text for i,v in self.ids.items()}
        packet = user_inputs.copy()
        if self.check_user_inputs(user_inputs) == True:
            global app_user
            conn = sqlite3.connect("user.db")
            cur = conn.cursor()
            row = cur.execute("SELECT * FROM user_table").fetchall()[0]
            app_user = User(row[0], row[3], row[1], row[2], row[4])
            print(app_user)
            print(packet)
            packet = build_packet(packet, app_user.username) 
            self.send_request(packet, "login")

class MenuScreen(Screen):
    def log_out(self):
        global app_user
        del app_user
        self.screen_transition("LoginScreen", direction='right')

class TransactionsScreen(Screen):
    def display_transactions(self):
        self.column_states = {i: "unsorted" for i in self.translate_columns.keys()}
        #load the GridLayout object
        gl = self.ids["gl"] 
        #clear the widgets on gl in case there are any currently existing
        gl.clear_widgets()
        gl.size_hint_y = len(app_user.transactions) / 2.5
        #iterate over the transactions dataframe and add values to the kivy Gridlayout object
        for row in app_user.transactions:
            for row in app_user.transactions[row]:
                gl.add_widget(BubbleButton(text=str(row[0]), on_press=self.load_transaction, background_normal="", background_color=(.4, .5, 100, .3)))
                for cell in row[1:]:
                    gl.add_widget(Label(text=str(cell)))
    
    def sort_transactions(self, button):
        #clear the current widgets on gl
        gl = self.ids["gl"] 
        gl.clear_widgets()
        gl.size_hint_y = len(app.transactions) / 2.5
        if self.column_states[button.text] == "unsorted":
            for row in self.transactions.sort_values(self.translate_columns[button.text], ascending=True).values:
                gl.add_widget(BubbleButton(text=str(row[0]), on_press=self.load_transaction, background_normal="", background_color=(.4, .5, 100, .3)))
                for cell in row[1:]:
                    gl.add_widget(Label(text=str(cell)))
            self.column_states[button.text] = "sorted"
            return
        elif self.column_states[button.text] == "sorted":
            for row in self.transactions.sort_values(self.translate_columns[button.text], ascending=False).values:
                gl.add_widget(BubbleButton(text=str(row[0]), on_press=self.load_transaction, background_normal="", background_color=(.4, .5, 100, .3)))
                for cell in row[1:]:
                    gl.add_widget(Label(text=str(cell)))
            self.column_states[button.text] = "unsorted"
            return

class AddTransactionScreen(Screen):
        def build_screen(self, date=datetime.datetime.now().date()):
            self.ids["calender"].text = f"{date}"
            wd = self.ids["wallet_dropdown"]
            wd.clear_widgets()
            for i in app_user.wallets["wallet_name"].values():
                wd.add_widget(Button(text=f"{i}", size_hint_y=None, on_press= lambda x: wd.select(x.text)))
        def add_transaction(self):
            user_inputs = {i:v.text for i,v in self.ids.items() if i != "dropdown" and i != "wallet_dropdown" and i != "frequency_dropdown"}
            if self.check_user_inputs(user_inputs) == True:
                #build packet
                user_inputs["user_id"] = base64.b64encode(encryption(str(app_user.user_id), pubkey=f"{app_user.username}_pubkey", privkey=f"{app_user.username}_privkey")).decode()
                user_inputs["user_password"] = app_user.password
                packet = user_inputs.copy()
                packet["update"] = "add transaction"
                packet["user_name"] = app_user.username
                #create transaction dictionary 
                app_user.add_new_transaction_dict = user_inputs
                self.send_request(json.dumps(packet), "update")
        def mini_calender(self):
            sc = ScheduleScreen("MiniCalender")
            sc.mini = True
            sc.build_calender()
            self.manager.add_widget(sc)
            pu = Popup(title="Calender", content=sc, size_hint=(.7, .7))
            bb = BubbleButton(text="Close", on_press=pu.dismiss)
            sc.ids["bl"].remove_widget(sc.ids["dynamic_button"])
            sc.ids["bl"].add_widget(bb)
            print(self.manager.screens)
            pu.open()
                          
class ViewTransactionScreen(Screen):
    def populate_screen(self, button_txt):
        self.transaction_id = int(button_txt)
        transaction_df = app_user.transactions.loc[app_user.transactions.transaction_id == self.transaction_id]
        self.ids["transaction_id"].text = str(transaction_df.transaction_id.item())
        self.ids["date"].text = str(transaction_df.transaction_date.item())
        self.ids["amount"].text = str(transaction_df.amount.item())
        self.ids["location"].text = str(transaction_df.location.item())
        self.ids["type"].text = str(transaction_df.transaction_type.item())
        self.ids["tag"].text = str(transaction_df.transaction_tag.item())
        self.ids["wallet"].text = str(transaction_df.wallet_name.item())
    def delete_transaction(self):
        data = {
            "transaction_id": self.ids["transaction_id"].text,
            "wallet_name": self.ids["wallet"].text,
            "amount": self.ids["amount"].text,
            "user_id": str(app_user.user_id),
            "user_password": str(app_user.password),
            "transaction_type": self.ids["type"].text
        }
        #create a copy of the data
        packet = data.copy()
        #send encrypted packet
        packet = build_packet(packet, user=app_user.username)
        packet["user_name"] = app_user.username
        packet["update"] = "delete transaction"
        app_user.delete_transaction_dict = data
        self.send_request(json.dumps(packet), "update")

class ScheduleScreen(Screen):
    pass

class DayScreen(Screen):
    def load_day(self, year, month, day):
        if len(str(month)) == 1:
            month = f"0{month}"
        if len(str(day)) == 1:
            day = f"0{day}"
        self.ids["date"].text = f"{year}-{month}-{day}"
        gl = self.ids["gl"]
        day_data = app_user.schedule.loc[app_user.schedule.scheduled_date == f"{year}-{month}-{day}"]
        gl.clear_widgets()
        for row in day_data[["transaction_id", "frequency", "scheduled_date","transaction_type", "amount", "wallet_name"]].values:
            gl.add_widget(BubbleButton(text=str(row[0]), background_normal="", background_color=(.4, .5, 100, .3), on_press=self.load_transaction))
            for item in row[1:]:
                gl.add_widget(Label(text=str(item)))
    def add_transaction(self):
        self.manager.get_screen("AddTransactionScreen").previous_screen = self.name
        self.manager.get_screen("AddTransactionScreen").build_screen(date=self.ids["date"].text)
        self.screen_transition("AddTransactionScreen")
    
class WalletsScreen(Screen):
    def load_wallets(self):
        gl = self.ids["gl"]
        gl.clear_widgets()
        gl.size_hint_y = len(app_user.wallets) / 2.5
        for row in app_user.wallets[["wallet_id", "wallet_name", "wallet_amount", "short_description"]].values:
            gl.add_widget(BubbleButton(text=str(row[0]), background_normal="", background_color=(.4, .5, 100, .3), on_press=self.find_wallet))
            for item in row[1:]:
                gl.add_widget(Label(text=str(item)))
    def find_wallet(self, button):
        self.manager.get_screen("ViewWalletScreen").load_wallet(button)
        self.screen_transition("ViewWalletScreen")

class AddWalletScreen(Screen):
    def add_wallet(self):
        data = {i:v.text for i,v in self.ids.items() if i != 'gl'}
        if self.check_user_inputs(data, wallet_check=True) == True:
            data["user_id"] = app_user.user_id
            data["user_password"] = app_user.password
            packet = data.copy()
            packet = encrypt_packet(packet, app_user.username)
            packet["update"] = "add wallet"
            packet["user_name"] = app_user.username
            app_user.add_wallet_dict = data 
            self.send_request(json.dumps(packet), "update")    

class ViewWalletScreen(Screen):
    def load_wallet(self, button):
        df = app_user.wallets.loc[app_user.wallets.wallet_id == int(button.text)]
        self.ids["date_created"].text = str(df.wallet_created_date.item())
        self.ids["wallet_name"].text = df.wallet_name.item()
        self.ids["wallet_amount"].text = str(df.wallet_amount.item())
        self.ids["wallet_description"].text = df.short_description.item()
        self.ids["transaction_count"].text = str(df.transaction_count.item())
    
    def delete_wallet(self):
        data = {i:v.text for i,v in self.ids.items()}
        app_user.delete_wallet_dict 
        data["user_id"] = app_user.user_id
        data["user_password"] = app_user.password
        packet = data.copy()
        packet = encrypt_packet(packet, app_user.username)
        packet["update"] = "delete wallet"
        packet["user_name"] = app_user.username
        app_user.delete_wallet_dict  = data 
        self.send_request(json.dumps(packet), "update")

class AnalysisScreen(Screen):
    def send_email(self):
        print("sending an email!")

class MonManApp(App):
    def build(self):
        conn = sqlite3.connect("user.db")
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE if not exists user_table(
                user_id int,
                user_email text,
                username text,
                phone_number text
            )""")
        conn.commit()
        self.sm = ScreenManager()
        self.sm.add_widget(RegistrationScreen(name="RegistrationScreen"))
        self.sm.add_widget(LoginScreen(name="LoginScreen"))
        self.sm.add_widget(MenuScreen(name="MenuScreen"))
        self.sm.add_widget(TransactionsScreen(name="TransactionsScreen"))
        self.sm.add_widget(AddTransactionScreen(name="AddTransactionScreen"))
        self.sm.add_widget(ViewTransactionScreen(name="ViewTransactionScreen"))
        self.sm.add_widget(ScheduleScreen(name="ScheduleScreen"))
        self.sm.add_widget(DayScreen(name="DayScreen"))
        self.sm.add_widget(WalletsScreen(name="WalletsScreen"))
        self.sm.add_widget(AddWalletScreen(name="AddWalletScreen"))
        self.sm.add_widget(ViewWalletScreen(name="ViewWalletScreen"))
        self.sm.current =  "LoginScreen"
        return self.sm

if __name__ ==  "__main__":
    MonManApp().run()