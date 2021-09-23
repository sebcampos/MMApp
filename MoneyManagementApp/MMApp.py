#!/usr/local/bin/python3
import os
import sqlite3 
import pandas
import datetime


import kivy
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.bubble import BubbleButton
from kivy.app import App


kivy.require('2.0.0')
#Config files located on iOS = <HOME_DIRECTORY>/Documents/.kivy/config.ini
os.environ['KIVY_EVENTLOOP'] = 'asyncio'

#SQLite3
class DB():
    def __init__(self):
        self.conn = sqlite3.connect("MM_sqlite.db")
        self.cur = self.conn.cursor()
        self.cur.execute("""
            CREATE TABLE if not exists User_Table(
                username text,
                user_email text,
                user_password text,
                phone_number text               
            )""")
        self.cur.execute("""
            CREATE TABLE if not exists Transactions(
                transaction_id int,
                transaction_date date,
                amount float,
                location text,
                transaction_type text,
                transaction_tag text,
                wallet_name text
            )""")
        self.cur.execute("""
            CREATE TABLE if not exists Scheduled(
                transaction_id int,
                frequency int,
                scheduled_date date,
                transaction_type text,
                wallet_name text
            )""")
        self.cur.execute("""
            CREATE TABLE if not exists Goals(
                goal_id int,
                wallet_id int,
                short_description text
            )""")
        self.cur.execute("""
            CREATE TABLE if not exists Wallets(
                wallet_id int,
                wallet_name text,
                wallet_amount float,
                short_description text
            )""")
        self.cur.execute("""
            CREATE TABLE if not exists Budgets(
                budget_id int,
                wallet_id int,
                budget_name text,
                budget_amount float
            )""")
        
        self.conn.commit()
        df = pandas.read_sql("select * from User_Table", con = self.conn)
        if len(df) == 0:
            self.register_user = True
        elif len(df) > 0:
            self.register_user = False
    
    def append(self, dataframe, table):
        return dataframe.to_sql(table, if_exists="append", index=False, con=self.conn)
    
    def delete(self, table, value):
        df = self.fetch(table)
        df.drop(value, inplace=True)
        return df.to_sql(table, if_exists='replace', index=False, con=self.conn)

    def fetch(self, table):
        return pandas.read_sql(f"SELECT * from {table}", self.conn)



#User class
class User():
    def __init__(self, phone_number, password, email, username):
        self.username = username
        self.email = email
        self.password = password
        self.phone_number = phone_number
        self.dataframe = pandas.DataFrame({
                "username": [self.username], 
                "user_email": [self.email], 
                "user_password": [self.password], #hash this 
                "phone_number": [self.phone_number]
            })
    def __repr__(self):
        return f"Username:\t{self.username}\nEmail:\t{self.email}\nPassword:\t{self.password}\nPhone:\t{self.phone_number}"

#Registration Screen
class RegistrationScreen(Screen):
    def register(self, app):
        users_table = app.db.fetch("User_table")
        lst = ['Phone number', 'Password (confirmation)', 'Password', 'Email', 'Username']
        data = {name: uinput for name, uinput in zip(lst, [i.text for i in self.children[0].children[1].children if i.text not in lst])}
        if data["Password"] != data["Password (confirmation)"]:
            cb = BubbleButton(text="Passwords do not match\n\n\n\n   Close")
            pu = Popup(title="InputError", content=cb, size_hint=(.5, .5))
            cb.bind(on_press=pu.dismiss)
            pu.open()
            return
        elif data["Username"] in users_table.values or  data["Email"] in users_table.values or data["Phone number"] in users_table.values:
            cb = BubbleButton(text="User data already exists\n\n\n\n   Close")
            pu = Popup(title="NewUserError", content=cb, size_hint=(.5, .5))
            cb.bind(on_press=pu.dismiss)
            pu.open()
            return
        else:
            del data["Password (confirmation)"]
            app.user = User(data["Phone number"], data["Password"], data["Email"], data["Username"])
            app.db.append(app.user.dataframe, "User_Table")
            self.manager.transition.direction = "left"
            self.manager.transition.duration = 1
            self.manager.current = "MenuScreen"
            return

#Login Screen
class LoginScreen(Screen):
    def login(self, app):
        user_table = app.db.fetch("User_Table")
        lst = ['Password','Username']
        data = {name: uinput for name, uinput in zip(lst, [i.text for i in self.children[0].children[2].children if i.text not in lst])}
        match = user_table.loc[(user_table.username == data["Username"]) & (user_table.user_password == data["Password"])]
        if len(match) > 0:
            self.manager.transition.direction = "left"
            self.manager.transition.duration = 1
            self.manager.current = "MenuScreen"
            user = user_table.loc[user_table.username == data["Username"]]
            app.user = User(user.phone_number.item(), user.user_password.item(), user.user_email.item(), user.username.item())
            return 
        else:
            cb = BubbleButton(text="No login found\n\n\n\n   Close")
            pu = Popup(title="LoginError", content=cb, size_hint=(.5, .5))
            cb.bind(on_press=pu.dismiss)
            pu.open()
            return

    def reset_password(self, db):
        pass
    def register_new_user(self, db):
        self.manager.transition.direction = "right"
        self.manager.transition.duration = 1
        self.manager.current = "RegistrationScreen"


class MenuScreen(Screen):
    def log_out(self, app):
        app.user = False
        self.manager.transition.direction = "right"
        self.manager.transition.duration = 1
        self.manager.current = "LoginScreen"

class TransactionsScreen(Screen):
    def find_transaction(self, button):
        self.parent.get_screen("ViewTransactionScreen").load_transaction(button.text, self.transactions)
        self.manager.transition.direction = "left"
        self.manager.transition.duration = 1
        self.manager.current = "ViewTransactionScreen"
    def load_transactions(self, app):
        transactions = app.db.fetch("Transactions")
        if len(transactions) == 0:
            return
        #transactions.transaction_date = transactions.transaction_date.apply(lambda x: datetime.datetime.strptime(x, '%Y-%m-%d'))
        self.sorted = {"ascending":True}
        transactions.sort_values("transaction_date", inplace=True)
        #transactions.transaction_id = transactions.index
        self.transactions = transactions
        gl = self.children[0].children[1].children[0]
        gl.clear_widgets()
        gl.size_hint_y = len(transactions)
        for row in transactions.values:
            gl.add_widget(BubbleButton(text=f"{row[0]}", on_press=self.find_transaction, background_normal="", background_color=(.4, .5, 100, .3)))
            for item in row[1:]:
                gl.add_widget(Label(text=str(item)))
        return
    def sort_table(self, button):
        translate_columns = {
            "ID":"transaction_id",
            "Date":"transaction_date",
            "Amount":"amount",
            "Loc":"location",
            "Type":"transaction_type",
            "Tag":"transaction_tag",
            "Wallet":"wallet_name"
        }
        if self.sorted["ascending"] == True:
            transactions = self.transactions.sort_values(translate_columns[button.text], ascending=False)
            self.sorted["ascending"] = False

        elif self.sorted["ascending"] == False:
            transactions = self.transactions.sort_values(translate_columns[button.text], ascending=True)
            self.sorted["ascending"] = True
        
        gl = self.children[0].children[1].children[0]
        gl.clear_widgets()
        gl.size_hint_y = len(transactions)
        for row in transactions.values:
            gl.add_widget(BubbleButton(text=f"{row[0]}", on_press=self.find_transaction))
            for item in row[1:]:
                gl.add_widget(Label(text=str(item)))
        return

class ViewTransactionScreen(Screen):
    def load_transaction(self, transaction_num, dataframe): 
        transaction = dataframe.loc[dataframe.transaction_id == int(transaction_num)]
        gl = self.children[0].children[1]
        lst = [str(i) for i in transaction.values[0]]
        self.data = transaction
        labels = ["Transaction ID", "Date", "Amount", "Location", "Type", "Tag", "Wallet"]
        lst.reverse()
        for gl_label,new_text in zip([child for child in gl.children if child.text not in labels],lst):
            gl_label.text = new_text
    
    def delete_transaction(self, app, transaction_num):
        app.db.delete("Transactions", int(transaction_num))
        cb = BubbleButton(text="Transaction Deleted\n\n\n\n   Close")
        pu = Popup(title="Success", content=cb, size_hint=(.5, .5))
        cb.bind(on_press=pu.dismiss)
        pu.open()
        gl = self.children[0].children[1]
        labels = ["Transaction ID", "Date", "Amount", "Location", "Type", "Tag", "Wallet"]
        for gl_label in gl.children:
            if gl_label.text not in labels:
                gl_label.text = ""
    def schedule_transaction(self):
        self.manager.get_screen("AddTransactionScreen").schedule(self.data["transaction_date"], data=self.data)
        self.manager.transition.direction = "left"
        self.manager.transition.duration = 1
        self.manager.current = "AddTransactionScreen"

            
class AddTransactionScreen(Screen):
    def today_timestamp(self):
        return f"{datetime.datetime.now().date()}"
    
    def schedule(self, date, data=[]):
        #if data is true fill info
        if len(data) != 0:
            lst = ["Frequency", "Wallet Name", "Tag", "Transaction Type", "Amount", "Date", "Location"]
            data = data[["location", "transaction_date","amount","transaction_type","transaction_tag","wallet_name"]].values.tolist()[0]
            data.reverse()
            textinputs = [widget for widget in self.children[0].children[1].children[1:] if widget.text not in lst]
            for widget,info in zip(textinputs,data):
                widget.text = str(info)
            self.transaction_exists = True
            return
        
        #add date and wait for frequency
        new_item = False
        for child in self.children[0].children[1].children:
            if new_item == True:
                child.text = date
                break
            if child.text == "Amount":
                new_item = True
        return

    def update_db(self, app):
        transaction_id = len(app.db.fetch("Transactions"))
        lst = ["Frequency", "Wallet Name", "Tag", "Transaction Type", "Amount", "Date", "Location"]
        uinputs = {i:v.text for i,v in zip(lst, [v for v in self.children[0].children[1].children if v.text not in lst])}        
        for i,v in uinputs.items():
            print(f"{i} : {v}")
        #throw error for amount that cannot be converted to a float
        try:
            float(uinputs["Amount"])
        except:
            cb = BubbleButton(text="Amount Must be a number or decimal\n\n\n\n   Close")
            pu = Popup(title="InputError", content=cb, size_hint=(.5, .5))
            cb.bind(on_press=pu.dismiss)
            pu.open()
            return
        #throw error if datetime is not in proper format
        ##make this a calender
        try:
            datetime.datetime.strptime(uinputs["Date"], '%Y-%m-%d')
        except:
            cb = BubbleButton(text="Incorrect Date format, YYYY-MM-D\n\n\n\n   Close")
            pu = Popup(title="InputError", content=cb, size_hint=(.5, .5))
            cb.bind(on_press=pu.dismiss)
            pu.open()
            return

        if uinputs["Frequency"] != "" and uinputs["Frequency"] != "Days":      
            #throw error is frequency is not an integer
            try:
                int(uinputs["Frequency"])
                app.db.append(pandas.DataFrame({
                    "transaction_id":[transaction_id],
                    "frequency": [uinputs["Frequency"]],
                    "scheduled_date": [uinputs["Date"]],
                    "transaction_type": [uinputs["Transaction Type"]],
                    "wallet_name": [uinputs["Wallet Name"]]
                }), "Scheduled")
            except Exception as e:
                print(e)
                cb = BubbleButton(text="Frequency needs to be an integer\n\n\n\n   Close")
                pu = Popup(title="InputError", content=cb, size_hint=(.5, .5))
                cb.bind(on_press=pu.dismiss)
                pu.open()
                return        
        try:
            if self.transaction_exists == True:
                cb = BubbleButton(text="Transaction Added\n\n\n\n   Close")
                pu = Popup(title="Success", content=cb, size_hint=(.5, .5))
                cb.bind(on_press=pu.dismiss)
                pu.open()
                self.transaction_exists = False
                return
        except Exception as e:
            print(e)
        app.db.append(pandas.DataFrame({
            "transaction_id" : [transaction_id],
            "transaction_date": [uinputs["Date"]],
            "amount": [uinputs["Amount"]],
            "location": [uinputs["Location"]],
            "transaction_type": [uinputs["Transaction Type"]],
            "transaction_tag": [uinputs["Tag"]],
            "wallet_name": [uinputs["Wallet Name"]]
        }), "Transactions" )
        cb = BubbleButton(text="Transaction Added\n\n\n\n   Close")
        pu = Popup(title="Success", content=cb, size_hint=(.5, .5))
        cb.bind(on_press=pu.dismiss)
        pu.open()


class ScheduleScreen(Screen):
    def clear_calender(self):
        gl = self.children[0].children[1]
        gl.clear_widgets()
    def load_schedule(self, app):
        self.transactions_df = app.db.fetch("Transactions")
        today = datetime.datetime.now()
        schedule = app.db.fetch("Scheduled")
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
        self.weekdays = day_name= ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday','Sunday']
        self.schedule = schedule
        self.year = today.year
        self.children[0].children[3].text = str(self.year)
        self.children[0].children[2].children[1].text = self.calender[str(today.month)]
        gl = self.children[0].children[1]
        days_in_month = (datetime.date(today.year, today.month + 1, 1) - datetime.date(today.year, today.month, 1)).days
        for i in range(1,8):
            gl.add_widget(Label(text=f"{self.weekdays[datetime.date(today.year, today.month, i).weekday()]}"))

        for i in range(1,days_in_month+1):
            if len(str(today.month)) == 1:
                month = f"0{today.month}"
            else:
                month = today.month
            if f"{self.year}-{month}-{i}" in list(self.schedule["scheduled_date"]) or f"{self.year}-{month}-0{i}" in list(self.schedule["scheduled_date"]):
                bb = BubbleButton(text=f"{i}", on_press=self.view_day)
                bb.background_normal = ""
                bb.background_color=  (.4, .5, 100, .3)
            else:
                bb = BubbleButton(text=f"{i}", on_press=self.view_day)
            bb.halign = "center"
            bb.valign = "middle"
            bb.text_size = (20,20)
            gl.add_widget(bb)
        self.selected_month = today.month
   
    def view_day(self, button):
        self.manager.get_screen("DayScreen").load_day(self.schedule, self.year, self.selected_month, button.text, self.transactions_df)
        self.manager.transition.direction = "left"
        self.manager.transition.duration = 1
        self.manager.current = "DayScreen"

    def change_month(self, button):
        today = datetime.datetime.now()
        current_month = int([i for i,v in self.calender.items() if v == self.children[0].children[2].children[1].text][0])
        gl = self.children[0].children[1]
        year_label = self.children[0].children[3]
        gl.clear_widgets()
        if button.text == "<":
            current_month -= 1
            if current_month == 1:
                self.year -= 1
                year_label.text = str(self.year)
                days_in_month = (datetime.date(self.year + 1, 1 , 1) - datetime.date(self.year, 12, 1)).days
                self.children[0].children[2].children[1].text = self.calender["12"]
            else:
                days_in_month = (datetime.date(self.year, current_month +1 , 1) - datetime.date(self.year, current_month, 1)).days
                self.children[0].children[2].children[1].text = self.calender[str(current_month)]
            for i in range(1,8):
                gl.add_widget(Label(text=f"{self.weekdays[datetime.date(self.year, current_month, i).weekday()]}"))

            for i in range(1,days_in_month+1):
                if len(str(current_month)) == 1:
                    padded_month = f"0{current_month}"
                else:
                    padded_month = current_month
                if f"{self.year}-{padded_month}-{i}" in list(self.schedule["scheduled_date"]) or f"{self.year}-{padded_month}-0{i}" in list(self.schedule["scheduled_date"]):
                    bb = BubbleButton(text=f"{i}", on_press=self.view_day)
                    bb.background_normal = ""
                    bb.background_color=  (.4, .5, 100, .3)
                else:
                    bb = BubbleButton(text=f"{i}", on_press=self.view_day)
                bb.halign = "center"
                bb.valign = "middle"
                bb.text_size = bb.size
                gl.add_widget(bb)
        elif button.text == ">":
            current_month += 1
            if current_month == 12:
                self.year += 1
                year_label.text = str(self.year)
                days_in_month = (datetime.date(self.year, 1, 1) - datetime.date(self.year - 1, 12, 1)).days
                self.children[0].children[2].children[1].text = self.calender["12"]
            elif current_month == 13:
                current_month = 1
                days_in_month = (datetime.date(self.year, current_month + 1, 1) - datetime.date(self.year, current_month, 1)).days
                self.children[0].children[2].children[1].text = self.calender[str(current_month)]                
            else:
                days_in_month = (datetime.date(self.year, current_month + 1, 1) - datetime.date(self.year, current_month, 1)).days
                self.children[0].children[2].children[1].text = self.calender[str(current_month)]
            for i in range(1,8):
                gl.add_widget(Label(text=f"{self.weekdays[datetime.date(self.year, current_month, i).weekday()]}"))            
            for i in range(1, days_in_month+1):
                if len(str(current_month)) == 1:
                    padded_month = f"0{current_month}"
                else:
                    padded_month = current_month              
                if f"{self.year}-{padded_month}-{i}" in list(self.schedule["scheduled_date"]) or f"{self.year}-{padded_month}-0{i}" in list(self.schedule["scheduled_date"]):
                    bb = BubbleButton(text=f"{i}", on_press=self.view_day)
                    bb.background_normal = ""
                    bb.background_color=  (.4, .5, 100, .3)
                else:
                    bb = BubbleButton(text=f"{i}", on_press=self.view_day)
                bb.halign = "center"
                bb.valign = "middle"
                bb.text_size = bb.size
                gl.add_widget(bb)
        self.selected_month = current_month


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
        for row in day_data.values:
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
        


class MMApp(App):
    def build(self):
        self.db = DB()
        self.sm = ScreenManager()
        self.sm.add_widget(RegistrationScreen(name="RegistrationScreen"))
        self.sm.add_widget(LoginScreen(name="LoginScreen"))
        self.sm.add_widget(MenuScreen(name="MenuScreen"))
        self.sm.add_widget(TransactionsScreen(name="TransactionsScreen"))
        self.sm.add_widget(AddTransactionScreen(name="AddTransactionScreen"))
        self.sm.add_widget(ViewTransactionScreen(name="ViewTransactionScreen"))
        self.sm.add_widget(ScheduleScreen(name="ScheduleScreen"))
        self.sm.add_widget(DayScreen(name="DayScreen"))        
        #check to see if User needs to be registered
        if self.db.register_user == True:
            self.sm.current = "RegistrationScreen"
        else:
            self.sm.current = "LoginScreen"
        return self.sm


if __name__ == '__main__':
    MMApp().run()
