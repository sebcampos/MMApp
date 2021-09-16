#!/usr/local/bin/python3
import kivy
import os
import sqlite3 
import pandas
import datetime
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.gridlayout import GridLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.bubble import BubbleButton
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.app import App

kivy.require('2.0.0')
#Config files located on iOS = <HOME_DIRECTORY>/Documents/.kivy/config.ini
os.environ['KIVY_EVENTLOOP'] = 'asyncio'

#User class
class User():
    def __init__(self, username, email, password, phone_number):
        self.username = username
        self.email = email
        self.password = password
        self.phone_number = phone_number
        self.registered = None
    def add_to_database(self, app):
        users_table = app.db.fetch("User_Table")
        if self.username not in users_table.username.tolist():
            pandas.DataFrame({
                "username": [self.username], 
                "user_email": [self.email], 
                "user_password": [self.password], #hash this 
                "phone_number": [self.phone_number]
            }).to_sql("User_Table", if_exists="append",index=False, con=app.db.conn)
            return True
        else:
            cb = BubbleButton(text="User Already Exists in Database\n\n\n\n   Close")
            pu = Popup(title="InputError", content=cb, size_hint=(.5, .5))
            cb.bind(on_press=pu.dismiss)
            pu.open()
            return "username already exists"


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
                wallet_id int
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
    
    def update(self, table):
        pass
    def fetch(self, table):
        return pandas.read_sql(f"SELECT * from {table}", self.conn)


#Registration Screen
class RegistrationScreen(Screen):
    def register(self, app):
        labels = []
        inputs = []
        for i in self.children[0].children[1].children:
            if isinstance(i , TextInput):
                inputs.append(i.text)
            else:
                labels.append(i.text)
        user_data = {i:v for i,v in zip(labels, inputs)}
        if user_data["Password (confirmation)"] != user_data["Password"]:
            cb = BubbleButton(text="Passwords Do not Match\n\n\n\n   Close")
            pu = Popup(title="InputError", content=cb, size_hint=(.5, .5))
            cb.bind(on_press=pu.dismiss)
            pu.open()

            return "passwords do not match"
        user = User(
            user_data["Username"].rstrip(),
            user_data["Email"].rstrip(),
            user_data["Password"].rstrip(),
            user_data["Phone number"].rstrip()
        )
        
        user.add_to_database(app)
        app.user = user
        if app.user != True:
            self.manager.transition.direction = "left"
            self.manager.transition.duration = 1
            self.manager.current = "LoginScreen"


#Login Screen
class LoginScreen(Screen):
    def login(self, app):
        labels = []
        inputs = []
        for i in self.children[0].children[2].children:
            if isinstance(i , TextInput):
                inputs.append(i.text)
            else:
                labels.append(i.text)
        user_data = {i:v for i,v in zip(labels, inputs)}
        users_table = app.db.fetch("User_table")
        if len(users_table.loc[(users_table.username == user_data["Username"]) & (users_table.user_password == user_data["Password"])]) > 0:
            self.manager.transition.direction = "left"
            self.manager.transition.duration = 1
            self.manager.current = "MenuScreen"
            app.user = user_data["Username"] 
        
    def reset_password(self, db):
        pass
    def register_new_user(self, db):
        self.manager.transition.direction = "right"
        self.manager.transition.duration = 1
        self.manager.current = "RegistrationScreen"

#Menu
class MenuScreen(Screen):
    def log_out(self, app):
        app.user = False
        self.manager.transition.direction = "right"
        self.manager.transition.duration = 1
        self.manager.current = "LoginScreen"


#Transactions
class TransactionsScreen(Screen):
    def load_transactions(self, app):
        transactions = app.db.fetch("Transactions")
        transactions["datetime"] = transactions.transaction_date.apply(lambda x: datetime.datetime.strptime(x, '%Y-%m-%d'))
        transactions.sort_values("datetime", ascending=False, inplace=True)
        transactions.drop("datetime", axis=1, inplace=True)
        transactions.transaction_id = transactions.index
        self.transactions = transactions
        self.last_sort = None
        self.current_transaction = ""
        return self.build_screen(transactions, app)

    def sort_table(self, button, app):
        dictionary = {v:i for i,v in zip(self.transactions,["ID", "Date", "Amount", "Loc","Type","Tag", "Wallet"])}
        if self.last_sort == button.text:
            self.transactions.sort_values(dictionary[button.text], ascending=False, inplace=True)
            self.last_sort = ""
        else:
            self.transactions.sort_values(dictionary[button.text], inplace=True)
            self.last_sort = button.text

        for widget in self.children[0].children[:-1]:
            self.children[0].remove_widget(widget)


        self.build_screen(self.transactions, app)
    
    def build_screen(self, table, app):
        self.children[0].add_widget(BoxLayout(orientation='horizontal'))
        for i in ["ID", "Date", "Amount", "Loc","Type","Tag", "Wallet"]:
            b = Button(text=i, on_press=lambda x: self.sort_table(x, app))
            b.text_size = b.size
            b.valign = "center"
            b.halign = "center"   
            self.children[0].children[0].add_widget(b)
        sv = ScrollView()
        sv.bar_inactive_color = (1, 1, 1, 1)
        sv.scroll_type = ["bars"]
        sv.bar_color = (1,1,1,1)
        sv.bar_width = 10
        gl = GridLayout(cols=len(table.columns), size_hint_y=len(table))
        for row in self.transactions.values:
            counter = 1
            for i in row:
                if counter == 1:
                    l = Button(text=str(i), on_press=lambda x: self.view_transactions(x,app))
                    counter+=1
                else:
                    l = Label(text=str(i))
                l.text_size = l.size
                l.valign = "center"
                l.halign = "center"                                
                gl.add_widget(l)
                if counter == 6:
                    counter = 1 
        sv.add_widget(gl)
        self.children[0].add_widget(sv)
        self.children[0].add_widget(BoxLayout(orientation='horizontal'))
        buttons = self.children[0].children[0]
        add_t = BubbleButton(text="Add Transaction",  background_color=(4, 0, 100, 5))
        add_t.bind(on_press=self.add_transactions)
        buttons.add_widget(add_t)
        return_mm = BubbleButton(text="Return To Menu", background_color=(4, 0, 100, 5))
        return_mm.bind(on_press=self.return_to_menu)
        buttons.add_widget(return_mm)

    def view_transactions(self, button, app):
        self.manager.get_screen("ViewTransactionScreen").load_transaction(app, button.text, self.transactions)
        self.current_transaction = button.text
        self.manager.transition.direction = "left"
        self.manager.current = "ViewTransactionScreen"
        

    def refresh_screen(self, app):
        for widget in self.children[0].children[0:3]:
            self.children[0].remove_widget(widget)
        self.load_transactions(app)

    def add_transactions(self, button):
        self.manager.transition.direction = "left"
        self.manager.transition.duration = 1
        self.manager.current = "SubTransactionScreen"
    
    
    def return_to_menu(self, button):
        self.manager.transition.direction = "right"
        self.manager.transition.duration = 1
        self.manager.current = "MenuScreen"

#SubTransactionScreen
class SubTransactionScreen(Screen):
    def today_timestamp(self):
        return f"{datetime.datetime.now().date()}"

    #add api call to update table
    def update_table(self, app):
        labels = []
        textinputs = []
        for widget in self.children[0].children[1].children:
            if isinstance(widget, TextInput):
                textinputs.append(widget.text)
            else:
                labels.append(widget.text)
        data = {i:v for i,v in list(zip(labels, textinputs))}
        try:
            datetime.datetime.strptime(data["Date"], '%Y-%m-%d')
        except:
            cb = BubbleButton(text="Incorrect Date format, YYYY-M-D\n\n\n\n   Close")
            pu = Popup(title="InputError", content=cb, size_hint=(.5, .5))
            cb.bind(on_press=pu.dismiss)
            pu.open()
            return
        
        if data["Transaction Type"].lower() not in ["withdrawl", "deposit"]:
            cb = BubbleButton(text="Incorrect Transaction Type (Deposit or Withdrawl)\n\n\n\n   Close")
            pu = Popup(title="InputError", content=cb, size_hint=(.5, .5))
            cb.bind(on_press=pu.dismiss)
            pu.open()
            return

        try:
            float(data["Amount"])
        except:
            cb = BubbleButton(text="Incorrect Amount, amount must be integer or float\n\n\n\n   Close")
            pu = Popup(title="InputError", content=cb, size_hint=(.5, .5))
            cb.bind(on_press=pu.dismiss)
            pu.open()
            return   

        try:
            new_id = max(app.transactions.transaction_id) + 1
        except:
            new_id = 1
        pandas.DataFrame({
            "transaction_id": [new_id],
            "transaction_date": [data["Date"]],
            "amount": [data["Amount"]],
            "location": [data["Location"]],
            "transaction_type": [data["Transaction Type"]],
            "transaction_tag": [data["Tag"]],
            "wallet_id": [data["Wallet Name"]]
        }).to_sql("Transactions", if_exists="append", con=app.db.conn, index=False)
        app.sm.get_screen("TransactionsScreen").refresh_screen(app)
        ##updated endpoint here##

        cb = BubbleButton(text="Transaction Added\n\n\n\n   Close")
        pu = Popup(title="Success", content=cb, size_hint=(.5, .5))
        cb.bind(on_press=pu.dismiss)
        pu.open()

    def previous_screen(self):
        self.manager.transition.direction = "right"
        self.manager.transition.duration = 1
        self.manager.current = "TransactionsScreen"


class ViewTransactionScreen(Screen):
    def load_transaction(self, app, data="", transactions=""):
        self.children[0].children[1]
        self.current_transaction = transactions.loc[transactions.transaction_id == int(data)]
        self.children[0].add_widget(Label(text=str(self.current_transaction)))
        
        


class MonManApp(App):
    def build(self):
        self.db = DB()
        self.sm = ScreenManager()
        self.user = False
        self.current_transaction = ""
        self.sm.add_widget(RegistrationScreen(name="RegistrationScreen"))
        self.sm.add_widget(LoginScreen(name="LoginScreen"))
        self.sm.add_widget(MenuScreen(name="MenuScreen"))
        self.sm.add_widget(TransactionsScreen(name="TransactionsScreen"))
        self.sm.add_widget(SubTransactionScreen(name="SubTransactionScreen"))
        self.sm.add_widget(ViewTransactionScreen(name="ViewTransactionScreen"))
        #self.sm.add_widget(ScheduleScreen(name="ScheduleScreen"))
        #self.sm.add_widget(DayScreen(name="DayScreen"))
        
        #check to see if User needs to be registered
        if self.db.register_user == True:
            self.sm.current = "RegistrationScreen"
        else:
            self.sm.current = "LoginScreen"
        return self.sm


if __name__ == '__main__':
    MonManApp().run()