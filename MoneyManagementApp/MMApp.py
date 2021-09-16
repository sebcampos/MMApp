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
                transaction_type text
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
        pass

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
    def load_transactions(self, app):
        self.sorted = None
        transactions = app.db.fetch("Transactions")
        if len(transactions) == 0:
            return
        #transactions.transaction_date = transactions.transaction_date.apply(lambda x: datetime.datetime.strptime(x, '%Y-%m-%d')) 
        transactions.sort_values("transaction_date", inplace=True)
        transactions.transaction_id = transactions.index
        self.transactions = transactions
        gl = self.children[0].children[1].children[0]
        gl.clear_widgets()
        gl.size_hint_y = len(transactions)
        for row in transactions.values:
            gl.add_widget(BubbleButton(text=f"{row[0]}"))
            for item in row[1:]:
                gl.add_widget(Label(text=str(item)))
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
        print(self.sorted)
        print(button.text)
        if self.sorted == None or self.sorted != button.text:
            transactions = self.transactions.sort_values(translate_columns[button.text], ascending=False)
        elif self.sorted == button.text:
            transactions = self.transactions.sort_values(translate_columns[button.text])
        self.sorted = button.text
        gl = self.children[0].children[1].children[0]
        gl.clear_widgets()
        gl.size_hint_y = len(transactions)
        for row in transactions.values:
            gl.add_widget(BubbleButton(text=f"{row[0]}"))
            for item in row[1:]:
                gl.add_widget(Label(text=str(item)))



    
class AddTransactionScreen(Screen):
    def today_timestamp(self):
        return f"{datetime.datetime.now().date()}"
    def update_db(self, app):
        lst = ["Wallet Name", "Tag", "Transaction Type", "Amount", "Date", "Location"]
        uinputs = {i:v.text for i,v in zip(lst, [v for v in self.children[0].children[1].children if v.text not in lst])}
        try:
            float(uinputs["Amount"])
        except:
            cb = BubbleButton(text="Amount Must be a number or decimal\n\n\n\n   Close")
            pu = Popup(title="InputError", content=cb, size_hint=(.5, .5))
            cb.bind(on_press=pu.dismiss)
            pu.open()
            return
        #make this a calender
        print(uinputs["Date"])
        try:
            datetime.datetime.strptime(uinputs["Date"], '%Y-%m-%d')
        except:
            cb = BubbleButton(text="Incorrect Date format, YYYY-M-D\n\n\n\n   Close")
            pu = Popup(title="InputError", content=cb, size_hint=(.5, .5))
            cb.bind(on_press=pu.dismiss)
            pu.open()
            return
        app.db.append(pandas.DataFrame({
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



class MMApp(App):
    def build(self):
        self.db = DB()
        self.sm = ScreenManager()
        self.sm.add_widget(RegistrationScreen(name="RegistrationScreen"))
        self.sm.add_widget(LoginScreen(name="LoginScreen"))
        self.sm.add_widget(MenuScreen(name="MenuScreen"))
        self.sm.add_widget(TransactionsScreen(name="TransactionsScreen"))
        self.sm.add_widget(AddTransactionScreen(name="AddTransactionScreen"))
        # self.sm.add_widget(ViewTransactionScreen(name="ViewTransactionScreen"))
        #self.sm.add_widget(ScheduleScreen(name="ScheduleScreen"))
        #self.sm.add_widget(DayScreen(name="DayScreen"))
        
        #check to see if User needs to be registered
        if self.db.register_user == True:
            self.sm.current = "RegistrationScreen"
        else:
            self.sm.current = "LoginScreen"
        return self.sm


if __name__ == '__main__':
    MMApp().run()
