import os
import datetime
import random
import json
import sqlite3
from packets import end_point_address, encryption, create_keys_rsa, build_packet, recieve_packet
import base64

import kivy
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.progressbar import ProgressBar
from kivy.network.urlrequest import UrlRequest 
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.button import Button
from kivy.uix.bubble import BubbleButton
from kivy.lang import Builder
from kivy.app import App


#TODO fix filtering, add a way to email data
#TODO fix font label text sizes: all columns,the days of the weeks,, Today label for calender


global DataPath
DataPath = ""

kivy.require('2.0.0')

Builder.load_file("main.kv")

class Label(Label):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.font_size = str(self.width / 10.5)+"sp"
        self.halign = 'center'
        self.valign = 'middle'
        


class User():
    def __init__(self, user_id, phone_number, email, username, password):
        self.userid = user_id
        self.username = username
        self.email = email
        self.phonenumber = phone_number
        self.password = password
        self.add_new_transaction_dict = None
        self.delete_transaction_dict = None
        self.add_wallet_dict = None
        self.delete_wallet_dict = None
        self.conn = sqlite3.connect(f"{DataPath}/user.db")
        self.cur = self.conn.cursor()
        self.cur.execute("""
            CREATE TABLE if not exists user_table(
                userid int,
                useremail text,
                username text,
                phonenumber text,
                password text
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
        return f"username: {self.username}\nid: {self.userid}\nemail: {self.email}\nphonenumber {self.phonenumber}"

    def write_self(self):
        self.cur.execute(f"""
            INSERT INTO user_table (userid, useremail, username, phonenumber, password)
            VALUES({self.userid},'{self.email}','{self.username}', '{self.phonenumber}', '{self.password}')
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
        self.pu = None
        self.pb = None
       
    def __repr__(self):
        return f"previous Screen: {self.previous_screen}\nnext Screen: {self.next_screen}\nScreen Name:{self.name}\nsend_request commands:\n\t'register user'\n\t'login'\n\t'update'"
    
    def screen_transition(self, screen, direction='left', duration=.2):
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

        self.pb = ProgressBar()
        self.pu = Popup(title="Loading...", content=self.pb, size_hint=(1, .5))
        self.pu.open()
        
    def failed_request(self, req, response):
        print("failed")
        self.pu.dismiss()
        self.pb = None
        self.pu = None
        self.prompt(f"{self.name}Error",response)

    def request_response(self, req, response):
        response = recieve_packet(json.loads(response))
        if "Success" in response.keys():
            if response["Success"] == 'registration complete':
                #register user
                global app_user
                app_user.userid = response["id"]
                #save keys
                with open(f"{DataPath}/{app_user.username}_privkey", "w") as f:
                    f.write(response['privkey'])
                with open(f"{DataPath}/{app_user.username}_pubkey", "w") as f:
                    f.write(response['pubkey'])
                for w in self.ids.values():
                    w.text = ""
                #transition to loginscreen
                self.screen_transition("LoginScreen")
                #write to database
                app_user.write_self()
            elif response["Success"] == "User logged in with ID and password":
                #retrieve tables from end point and save to app_user
                app_user.transactions = json.loads(response["transactions"])
                app_user.schedule = json.loads(response["scheduled"])
                app_user.wallets = json.loads(response["wallets"])
                #transition to main menu
                self.screen_transition("MenuScreen")
            elif response["Success"] == "Transaction added":
                #transaction_id and wallet index
                transaction_id = len(app_user.transactions["transaction_id"])
                wallet_index = None
                for i,v in app_user.wallets["wallet_name"].items():
                    if v == app_user.add_new_transaction_dict["wallet"]:
                        wallet_index = i
                        break
                #add to transactions table
                app_user.transactions["transaction_id"][str(transaction_id)] = transaction_id 
                app_user.transactions["amount"][str(transaction_id)] = app_user.add_new_transaction_dict["amount"]
                app_user.transactions["location"][str(transaction_id)] = app_user.add_new_transaction_dict["location"]
                app_user.transactions["transaction_date"][str(transaction_id)] = app_user.add_new_transaction_dict["calender"]
                app_user.transactions["wallet_name"][str(transaction_id)] = app_user.add_new_transaction_dict["wallet"]
                app_user.transactions["transaction_type"][str(transaction_id)] = app_user.add_new_transaction_dict["transaction_type"]
                app_user.transactions["transaction_tag"][str(transaction_id)] = app_user.add_new_transaction_dict["tag"]
                if datetime.datetime.strptime(app_user.add_new_transaction_dict["calender"], "%Y-%m-%d").date() <= datetime.datetime.today().date():
                    #check if transaction is scheduled for today
                    #add to wallet transaction counter
                    app_user.wallets["transaction_count"][wallet_index] += 1
                    if app_user.add_new_transaction_dict["transaction_type"] == "Withdrawl":
                        ##add from wallet
                        app_user.wallets["wallet_amount"][wallet_index] -= float(app_user.add_new_transaction_dict["amount"])
                    elif app_user.add_new_transaction_dict["transaction_type"] == "Deposit":
                        ##subtract from wallet
                        app_user.wallets["wallet_amount"][wallet_index] += float(app_user.add_new_transaction_dict["amount"])
                if app_user.add_new_transaction_dict["frequency"] != "Daily":
                    #schedule the transaction
                    app_user.schedule["transaction_id"][str(transaction_id)] = str(transaction_id)
                    app_user.schedule["frequency"][str(transaction_id)] = app_user.freq_map[app_user.add_new_transaction_dict['frequency']]
                    app_user.schedule["scheduled_date"][str(transaction_id)] = app_user.add_new_transaction_dict["calender"]
                    if app_user.add_new_transaction_dict["frequency"] != "Once":
                        app_user.schedule["next_day"][str(transaction_id)] = str(datetime.datetime.strptime(app_user.add_new_transaction_dict["calender"], "%Y-%m-%d") + datetime.timedelta(days=app_user.freq_map[app_user.add_new_transaction_dict['frequency']])).split(" ")[0].strip()
                    else:
                        app_user.schedule["next_day"][str(transaction_id)] = "None"
                    app_user.schedule["amount"][str(transaction_id)] = app_user.add_new_transaction_dict["amount"]
                    app_user.schedule["transaction_type"][str(transaction_id)] = app_user.add_new_transaction_dict["transaction_type"]
                    app_user.schedule["wallet_name"][str(transaction_id)] = app_user.add_new_transaction_dict["wallet"]
                #clear inputs
                for i,v in self.ids.items():
                    if i != "transaction_type" and i != "dropdown" and i != "wallet_dropdown" and i != "frequency_dropdown" and i != "back_button":
                        v.text = ""
                        self.ids["calender"].text = "calender"
                self.prompt("Success","Transaction Added")
                
            elif response["Success"] == "Transaction deleted, Wallet updated, Schedule updated":
                wallet_index = None
                for i,v in app_user.wallets["wallet_name"].items():
                    if v == app_user.delete_transaction_dict["wallet_name"]:
                        wallet_index = i
                        break
                #delete transaction
                for column in app_user.transactions:
                    del app_user.transactions[column][app_user.delete_transaction_dict["transaction_id"]]
                #decrement all ids greater than current by 1
                for column in app_user.transactions:
                    for key in list(app_user.transactions[column].keys()):
                        if int(key) > int(app_user.delete_transaction_dict["transaction_id"]):
                            app_user.transactions[column][str(int(key) - 1)] = app_user.transactions[column].pop(key)
                
                #decrement transaction count
                ## if date is before or euqal to transaction date ##
                if datetime.datetime.strptime(app_user.delete_transaction_dict["date"], "%Y-%m-%d").date() <= datetime.datetime.now().date():
                    app_user.wallets["transaction_count"][wallet_index] -= 1
                    #return reverse transaction from wallet
                    if app_user.delete_transaction_dict["transaction_type"] == "Withdrawl":
                        #if withdrawl deleted return the amount to the wallet
                        app_user.wallets["wallet_amount"][wallet_index] += float(app_user.delete_transaction_dict["amount"])
                    elif app_user.delete_transaction_dict["transaction_type"] == "Deposit":
                        #if deposit deleted subtract amount from wallet
                        app_user.wallets["wallet_amount"][wallet_index] -= float(app_user.delete_transaction_dict["amount"])
                #delete transaction from the schedule
                if app_user.delete_transaction_dict["transaction_id"] in app_user.schedule["transaction_id"].keys():
                    for column in app_user.schedule:
                        del app_user.schedule[column][app_user.delete_transaction_dict["transaction_id"]]


                #clear screen
                for widget in self.ids.values():
                    widget.text = ""
                self.prompt("Success", response["Success"])
            elif response["Success"] == "New Wallet added":
                wallet_id = len(app_user.wallets["wallet_id"])
                data = {
                    "wallet_id": len(app_user.wallets),
                    "wallet_name": app_user.add_wallet_dict["wallet_name"],
                    "wallet_amount": app_user.add_wallet_dict["wallet_amount"],
                    "short_description": app_user.add_wallet_dict["wallet_description"],
                    "wallet_created_date": str(datetime.datetime.now().date()),
                    "transaction_count": 0
                }
                #add to wallets 
                app_user.wallets["wallet_id"][str(wallet_id)] = wallet_id 
                app_user.wallets["wallet_name"][str(wallet_id)] = data["wallet_name"]
                app_user.wallets["wallet_amount"][str(wallet_id)] = float(data["wallet_amount"])
                app_user.wallets["short_description"][str(wallet_id)] = data["short_description"]
                app_user.wallets["wallet_created_date"][str(wallet_id)] = data["wallet_created_date"]
                app_user.wallets["transaction_count"][str(wallet_id)] = data["transaction_count"]
                
                
                self.prompt("Success", response["Success"])
            
            elif response["Success"] == "Wallet deleted":
                wallet_index = None
                for i,v in app_user.wallets["wallet_name"].items():
                    if v == app_user.delete_wallet_dict["wallet_name"]:
                        wallet_index = i
                        break
                #delete wallet
                for column in app_user.wallets:
                    del app_user.wallets[column][wallet_index]
                self.prompt("Success", response["Success"])


                
        else:
            self.prompt("Error", response["Error"])
    
    def request_error(self, req, error):
        print("error")
        self.pu.dismiss()
        self.pb = None
        self.pu = None
        self.prompt(f"{self.name}Error",error)
        
    def prompt(self, error_type, error_message):
        cb = BubbleButton(text=f"{error_message}\n\n\n\n   Close")
        cb.font_size = "10sp"
        pu = Popup(title=f"{error_type}", content=cb, size_hint=(1, .5))
        cb.bind(on_press=pu.dismiss)
        pu.open()
    
    def check_user_inputs(self, inputs, registration=False, wallet_check=False, add_transaction=False):
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
        if add_transaction == True:
            if inputs["calender"] == 'calender':
                self.prompt("InputError", "Please add a date for transaction")
                return
            try:
                float(inputs["amount"])
            except:
                self.prompt("InputError", "Please enter decimal or integer in Amount field")



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
        calender_data = []
        #order weekdays
        calender_columns = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
        size = len(dict_calender["Monday"])
        index = 0
        while index != size:
            for column in calender_columns:
                calender_data.append(dict_calender[column][index])
            index += 1
        
        if self.mini:
            calender_columns = ["S", "M", "T", "W", "T", "F", "S"]

        #iterate over dataframe and add to gridlayout widget
        for column in calender_columns:
            self.ids['gl_calender'].add_widget(Label(text=column))
        
        
        for cell in calender_data:
            #padding months and days
            if len(str(cell)) == 1:
                new_cell = f"0{cell}"
            else:
                new_cell = cell
            if len(str(month)) == 1:
                month = f"0{month}"
            else:
                month = month
            
            if f"{year}-{month}-{new_cell}" in list(app_user.schedule["scheduled_date"].values()) or f"{year}-{month}-{new_cell}" in list(app_user.schedule["next_day"].values()) and f"{year}-{month}-{new_cell}" != str(datetime.datetime.now().date()):
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
                    bb.font_size = "6sp"
                else:
                    bb = BubbleButton(text=f"Today {cell}", on_press=self.view_day)
                    bb.font_size= "11.5sp"
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
        if "Today " in day:
            day = day.replace("Today ", "")
            if len(day) == 1:
                day = "0"+day

        self.manager.get_screen("AddTransactionScreen").ids["calender"].text = f"{self.ids['year_label'].text}-{month}-{day}"
        for b in self.ids["gl_calender"].children:
            b.background_normal = ""
            b.background_color=  (0, 0, 0, 0)

        button.background_normal = ""
        button.background_color = (0, .5, 1, .5)

    def change_month(self, button):
        current_month = int([i for i,v in self.calender.items() if v == self.ids["current_month"].text][0])
        if button.text == "<<<":
            #logic to decrement month based on january
            if current_month == 1:
                current_month = 12
                self.ids["year_label"].text = str(int(self.ids["year_label"].text) - 1)
                self.ids["current_month"].text = self.calender["12"]
            else:
                current_month -= 1
                self.ids["current_month"].text = self.calender[str(current_month)]
        #logic to increment month
        elif button.text == ">>>":
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
        if self.pb == None:
            return
        self.pb.value = (start / end) * 100
        
        if start == end:
            print("end")
            self.pu.dismiss()
            self.pb = None
            self.pu = None
        
               
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
            conn = sqlite3.connect(f"{DataPath}/user.db")
            cur = conn.cursor()
            try:
                row = cur.execute("SELECT * FROM user_table").fetchall()[0]
            except sqlite3.OperationalError:
                self.prompt("LoginError", "No user registered for this app\nOnly one User per app")
                return

            app_user = User(row[0], row[3], row[1], row[2], row[4])
            packet["userid"] = str(app_user.userid)
            packet = build_packet(packet, f"{DataPath}/{app_user.username}") 
            self.send_request(packet, "login")
    
    def reset_password(self):
        self.prompt("Message","This feature is not available yet,\nplease email secampos95@gmail.com")

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
        gl.size_hint_y = len(app_user.transactions["transaction_id"]) / 2.5
        #iterate over json to create an object easier for building tables
        self.rows = {}
        for value in app_user.transactions["transaction_id"].values():
            self.rows[str(value)] = [] 
        
        for column_name,column in app_user.transactions.items():
            if column_name != "transaction_id":
                for i,v in column.items():
                    self.rows[i].append(v)
        
        for transaction_id in self.rows:
            gl.add_widget(BubbleButton(text=str(transaction_id), on_press=self.load_transaction, background_normal="", background_color=(.4, .5, 100, .3)))
            date=True
            for value in self.rows[transaction_id]:
                l = Label(text=str(value))
                l.text_size = l.width, None
                l.font_size = "7sp"
                if date != True:
                    # l.text_size = l.width, None
                    l.font_size = "9sp"
                    l.shorten = True
                date=False
                gl.add_widget(l)
            
                    
    
    def sort_table(self, button):
        #clear the current widgets on gl
        gl = self.ids["gl"] 
        gl.clear_widgets()
        gl.size_hint_y = len(app_user.transactions["transaction_id"]) / 2.5
        if self.column_states[button.text] == "unsorted":
            sorted_table = sorted(app_user.transactions[self.translate_columns[button.text]].items(), key=lambda x: x[1])
            for index, v in sorted_table:
                gl.add_widget(BubbleButton(text=str(index), on_press=self.load_transaction, background_normal="", background_color=(.4, .5, 100, .3)))
                date = True
                for value in self.rows[index]:
                    l = Label(text=str(value))
                    l.text_size = l.width, None
                    l.font_size = "7sp"
                    if date != True:
                        # l.text_size = l.width, None
                        l.font_size = "9sp"
                        l.shorten = True
                    date=False
                    gl.add_widget(l)
            self.column_states[button.text] = "sorted"
            return
        elif self.column_states[button.text] == "sorted":
            sorted_table = sorted(app_user.transactions[self.translate_columns[button.text]].items(), key=lambda x: x[1], reverse=True)
            for index, v in sorted_table:
                gl.add_widget(BubbleButton(text=str(index), on_press=self.load_transaction, background_normal="", background_color=(.4, .5, 100, .3)))
                date = True
                for value in self.rows[index]:
                    l = Label(text=str(value))
                    l.text_size = l.width, None
                    l.font_size = "7sp"
                    if date != True:
                        # l.text_size = l.width, None
                        l.font_size = "9sp"
                        l.shorten = True
                    date=False
                    gl.add_widget(l)
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
            if self.check_user_inputs(user_inputs, add_transaction=True) == True:
                #build packet
                packet = user_inputs.copy()
                packet["update"] = "add transaction"
                packet["username"] = app_user.username
                packet["password"] = app_user.password
                packet["userid"] = str(app_user.userid)
                #create transaction dictionary
                packet = build_packet(packet, f"{DataPath}/{app_user.username}") 
                app_user.add_new_transaction_dict = user_inputs
                self.send_request(packet, "update") 
        def mini_calender(self):
            sc = ScheduleScreen("MiniCalender")
            sc.mini = True
            sc.build_calender()
            self.manager.add_widget(sc)
            pu = Popup(title="Calender", content=sc, size_hint=(1, .7))
            bb = BubbleButton(text="Close", on_press=pu.dismiss)
            sc.ids["bl"].remove_widget(sc.ids["dynamic_button"])
            sc.ids["bl"].add_widget(bb)
            pu.open()
                          
class ViewTransactionScreen(Screen):
    def populate_screen(self, button_txt):
        self.transaction_id = button_txt
        transaction_data = {}
        for column in app_user.transactions:
            for k,v in app_user.transactions[column].items():
                if k == button_txt:
                    transaction_data[column] = v
        self.ids["transaction_id"].text = str(transaction_data["transaction_id"])
        self.ids["date"].text = str(transaction_data["transaction_date"])
        self.ids["amount"].text = str(transaction_data["amount"])
        self.ids["location"].text = str(transaction_data["location"])
        self.ids["type"].text = str(transaction_data["transaction_type"])
        self.ids["tag"].text = str(transaction_data["transaction_tag"])
        self.ids["wallet"].text = str(transaction_data["wallet_name"])
    def delete_transaction(self):
        data = {
            "transaction_id": self.ids["transaction_id"].text,
            "wallet_name": self.ids["wallet"].text,
            "amount": self.ids["amount"].text,
            "userid": str(app_user.userid),
            "password": str(app_user.password),
            "transaction_type": self.ids["type"].text,
            "update": "delete transaction",
            "date": self.ids["date"].text,
            "username": app_user.username,
        }
        #create a copy of the data
        packet = data.copy()
        #send encrypted packet
        app_user.delete_transaction_dict = data
        packet = build_packet(packet, user=f"{DataPath}/{app_user.username}")
        self.send_request(packet, "update")

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
        day_data = {}
        gl.clear_widgets()

        for value in zip(app_user.schedule["transaction_id"].keys(), app_user.schedule["transaction_id"].values(), app_user.schedule["scheduled_date"].values(), app_user.schedule["next_day"].values()):
            if str(value[2]) == f"{year}-{month}-{day}" or str(value[-1]) == f"{year}-{month}-{day}":
                day_data[value[1]] = [value[0]]

        
        for i,v in day_data.items():
            for index,row in app_user.schedule.items():
                if index != "next_day":
                    day_data[i].append(row[v[0]])

        for transaction_id in day_data:
            gl.add_widget(BubbleButton(text=str(transaction_id), background_normal="", background_color=(.4, .5, 100, .3), on_press=self.load_transaction))
            for value in day_data[transaction_id][2:]:
                gl.add_widget(Label(text=str(value)))

    def add_transaction(self):
        self.manager.get_screen("AddTransactionScreen").previous_screen = self.name
        self.manager.get_screen("AddTransactionScreen").build_screen(date=self.ids["date"].text)
        self.screen_transition("AddTransactionScreen")
    
class WalletsScreen(Screen):
    def load_wallets(self):
        gl = self.ids["gl"]
        gl.clear_widgets()
        gl.size_hint_y = len(app_user.wallets["wallet_name"]) / 2.5
        rows = {}
        for value in app_user.wallets["wallet_id"].values():
            rows[str(value)] = []
        
        for column_name,column in app_user.wallets.items():
            if column_name != "wallet_id" and column_name != "transaction_count" and column_name != "wallet_created_date":
                for i,v in column.items():
                    rows[i].append(v)

        for wallet_id in rows:
            gl.add_widget(BubbleButton(text=str(wallet_id), background_normal="", background_color=(.4, .5, 100, .3), on_press=self.find_wallet))
            counter = 0
            for value in rows[wallet_id]:
                l = Label(text=str(value))
                counter+=1
                if counter == 3:
                    l.shorten = True
                gl.add_widget(l)

    
    def find_wallet(self, button):
        self.manager.get_screen("ViewWalletScreen").load_wallet(button.text)
        self.screen_transition("ViewWalletScreen")

class AddWalletScreen(Screen):
    def add_wallet(self):
        data = {i:v.text for i,v in self.ids.items() if i != 'gl'}
        if self.check_user_inputs(data, wallet_check=True) == True:
            data["userid"] = str(app_user.userid)
            data["password"] = str(app_user.password)
            packet = data.copy()
            packet["update"] = "add wallet"
            packet["username"] = app_user.username
            app_user.add_wallet_dict = data
            packet = build_packet(packet, f"{DataPath}/{app_user.username}")
            self.send_request(packet, "update")    

class ViewWalletScreen(Screen):
    def load_wallet(self, button_txt):
        wallet_data = {}
        for column in app_user.wallets:
            for k,v in app_user.wallets[column].items():
                if k == button_txt:
                    wallet_data[column] = v
        self.ids["date_created"].text = str(wallet_data["wallet_created_date"])
        self.ids["wallet_name"].text = str(wallet_data["wallet_name"])
        self.ids["wallet_amount"].text = str(wallet_data["wallet_amount"])
        self.ids["wallet_description"].text = str(wallet_data["short_description"])
        self.ids["transaction_count"].text = str(wallet_data["transaction_count"])
    
    def delete_wallet(self):
        data = {i:v.text for i,v in self.ids.items()} 
        data["userid"] = str(app_user.userid)
        data["password"] = app_user.password
        packet = data.copy()
        packet["update"] = "delete wallet"
        packet["username"] = app_user.username
        app_user.delete_wallet_dict = data 
        packet = build_packet(packet, f"{DataPath}/{app_user.username}")
        self.send_request(packet, "update")

class AnalysisScreen(Screen):
    def send_email(self):
        self.prompt("Message","This feature is not available yet,\nplease email secampos95@gmail.com")
        print("sending an email!")

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
        self.sm.add_widget(WalletsScreen(name="WalletsScreen"))
        self.sm.add_widget(AddWalletScreen(name="AddWalletScreen"))
        self.sm.add_widget(ViewWalletScreen(name="ViewWalletScreen"))
        self.sm.add_widget(AnalysisScreen(name="AnalysisScreen"))
        global DataPath 
        DataPath = self.get_running_app().user_data_dir
        if "user.db" not in os.listdir(DataPath):
            self.sm.current = "RegistrationScreen"
        else:
            self.sm.current = "LoginScreen"

        return self.sm

if __name__ ==  "__main__":
    MMApp().run()
