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
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
# from kivy.core.window import Window
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
    def add_to_database(self, db):
        users_table = pandas.read_sql("SELECT * FROM User_Table", con=db.conn)
        if self.username not in users_table.username.tolist():
            pandas.DataFrame({
                "username": [self.username], 
                "user_email": [self.email], 
                "user_password": [self.password], #hash this 
                "phone_number": [self.phone_number]
            }).to_sql("User_Table", if_exists="append",index=False, con=db.conn)
            return True
        else:
            cb = Button(text="User Already Exists in Database\n\n\n\n   Close")
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
    
    def update(self):
        pass
    def fetch(self):
        pass


#Registration Screen
class RegistrationScreen(Screen):
    def register(self, db, app):
        registered = False
        labels = []
        inputs = []
        for i in self.children[0].children[1].children:
            if isinstance(i , TextInput):
                inputs.append(i.text)
            else:
                labels.append(i.text)
        user_data = {i:v for i,v in zip(labels, inputs)}
        if user_data["Password (confirmation)"] != user_data["Password"]:
            cb = Button(text="Passwords Do not Match\n\n\n\n   Close")
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
        
        registered = user.add_to_database(db)
        
        if registered == True:
            self.manager.add_widget(LoginScreen(name="LoginScreen"))
            self.manager.transition.direction = "left"
            self.manager.transition.duration = 1
            self.manager.current = "LoginScreen"
        

#Login Screen
class LoginScreen(Screen):
    def login(self, db, app):
        labels = []
        inputs = []
        for i in self.children[0].children[2].children:
            if isinstance(i , TextInput):
                inputs.append(i.text)
            else:
                labels.append(i.text)
        user_data = {i:v for i,v in zip(labels, inputs)}
        users_table = pandas.read_sql("SELECT * FROM User_Table", con=db.conn)
        if len(users_table.loc[(users_table.username == user_data["Username"]) & (users_table.user_password == user_data["Password"])]) > 0:
            self.manager.transition.direction = "left"
            self.manager.transition.duration = 1
            self.manager.current = "MenuScreen"
            app.user = user_data["Username"] 
        
    def reset_password(self, db):
        pass
    def register_new_user(self, db):
        self.manager.add_widget(RegistrationScreen(name="RegistrationScreen"))
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
        transactions = pandas.read_sql("SELECT * from Transactions", con = app.db.conn)
        transactions.transaction_id = transactions.index
        transactions["datetime"] = transactions.transaction_date.apply(lambda x: datetime.datetime.strptime(x, '%Y-%m-%d'))
        transactions.sort_values("datetime", ascending=False, inplace=True)
        transactions.drop("datetime", axis=1, inplace=True)
        self.transactions = transactions
        self.children[0].add_widget(BoxLayout(orientation='horizontal'))
        for i in transactions.columns:
            self.children[0].children[0].add_widget(Label(text=i))
        sv = ScrollView()
        sv.bar_inactive_color = (1, 1, 1, 1)
        sv.scroll_type = ["bars"]
        sv.bar_color = (1,1,1,1)
        sv.bar_width = 10
        gl = GridLayout(cols=len(transactions.columns), size_hint_y=len(transactions))
        for row in transactions.values:
            for i in row:
                l = Label(text=str(i), size_hint_y=.5)
                l.text_size = l.size
                l.valign = "top"                                
                gl.add_widget(l)
        sv.add_widget(gl)
        self.children[0].add_widget(sv)
        self.children[0].add_widget(BoxLayout(orientation='horizontal'))
        buttons = self.children[0].children[0]
        add_t = Button(text="Add Transaction")
        add_t.bind(on_press=self.add_transactions)
        buttons.add_widget(add_t)
        return_mm = Button(text="Return To Menu")
        return_mm.bind(on_press=self.return_to_menu)
        buttons.add_widget(return_mm)
        

    def refresh_screen(self, app):
        for widget in self.children[0].children[0:3]:
            self.children[0].remove_widget(widget)
        self.load_transactions(app)

    def add_transactions(self, button):
        #self.manager.add_widget(SubTransactionScreen(name="SubTransactionScreen"))
        self.manager.transition.direction = "left"
        self.manager.transition.duration = 1
        self.manager.current = "SubTransactionScreen"
    
    
    def return_to_menu(self, button):
        self.manager.transition.direction = "right"
        self.manager.transition.duration = 1
        self.manager.current = "MenuScreen"
    

#NewTransactionScreen
class SubTransactionScreen(Screen):
    def today_timestamp(self):
        return f"{datetime.datetime.now().date()}"

    #add api call to update table
    def update_table(self, app):
        print(self.parent)
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
            cb = Button(text="Incorrect Date format, YYYY-M-D\n\n\n\n   Close")
            pu = Popup(title="InputError", content=cb, size_hint=(.5, .5))
            cb.bind(on_press=pu.dismiss)
            pu.open()
            return
        
        if data["Transaction Type"].lower() not in ["withdrawl", "deposit"]:
            cb = Button(text="Incorrect Transaction Type (Deposit or Withdrawl)\n\n\n\n   Close")
            pu = Popup(title="InputError", content=cb, size_hint=(.5, .5))
            cb.bind(on_press=pu.dismiss)
            pu.open()
            return

        try:
            float(data["Amount"])
        except:
            cb = Button(text="Incorrect Amount, amount must be integer or float\n\n\n\n   Close")
            pu = Popup(title="InputError", content=cb, size_hint=(.5, .5))
            cb.bind(on_press=pu.dismiss)
            pu.open()
            return   

        new_id = max(self.parent.screens[2].transactions.index) + 1
        pandas.DataFrame({
            "transaction_id": [new_id],
            "transaction_date": [data["Date"]],
            "amount": [data["Amount"]],
            "location": [data["Location"]],
            "transaction_type": [data["Transaction Type"]],
            "transaction_tag": [data["Tag"]],
            "wallet_id": [data["Wallet Name"]]
        }).to_sql("Transactions", if_exists="append", con=app.db.conn, index=False)
        self.parent.screens[2].refresh_screen(app)
        ##updated endpoint here##

        cb = Button(text="Transaction Added\n\n\n\n   Close")
        pu = Popup(title="Success", content=cb, size_hint=(.5, .5))
        cb.bind(on_press=pu.dismiss)
        pu.open()

    def previous_screen(self):
        self.manager.transition.direction = "right"
        self.manager.transition.duration = 1
        self.manager.current = "TransactionsScreen"

    
#Schedule
class ScheduleScreen(Screen):
    def load_schedule(self, app):
        schedule = pandas.read_sql("SELECT * from Scheduled", con = app.db.conn)
        self.today = datetime.datetime.now().day
        now = datetime.datetime.now()
        days_in_month = (datetime.date(now.year, now.month + 1, 1) - datetime.date(now.year, now.month, 1)).days
        #self.children[0].add_widget(Label(text=str(now.month)))
        gl = GridLayout(cols=5)
        for num in range(1,days_in_month+1):
            if self.today == num:
                gl.add_widget(Button(text=f"{num} TODAY", on_press=self.edit_day))
            else:
                gl.add_widget(Button(text=f"{num}", on_press=self.edit_day))

        self.children[0].add_widget(gl)
        self.children[0].add_widget(Button(text="Return To Menu", on_press=self.previous_screen))
    
    def refresh_screen(self):
        for widget in self.children[0].children[0:2]:
            self.children[0].remove_widget(widget)


    
    def edit_day(self, button):
        self.manager.transition.direction = "left"
        self.manager.transition.duration = 1
        self.manager.current = "DayScreen"
        self.manager.children[0].load(button.text)
    
    def previous_screen(self, button):
        self.manager.transition.direction = "right"
        self.manager.transition.duration = 1
        self.manager.current = "MenuScreen"
    

class DayScreen(Screen):
    def set_app(self, app):
        self.app = app
    def load(self, text):
        self.children[0].add_widget(Label(text=text))
        gl = GridLayout(cols=2)
        gl.add_widget(Label(text="Transaction ID"))
        gl.add_widget(TextInput())
        gl.add_widget(Label(text='Frequency'))
        gl.add_widget(TextInput())
        self.children[0].add_widget(gl)
        data = {i:v for i,v in list(zip([x.text for x in gl.children if isinstance(x, Label)],[x.text for x in gl.children if isinstance(x, TextInput)]))}
        print(data)
        bl = BoxLayout(orientation="horizontal")
        previous_screen = Button(text="Back", on_press=self.previous_screen)
        submit = Button(text="Add to Schedule", on_press=self.submit)
        bl.add_widget(previous_screen)
        bl.add_widget(submit)
        self.children[0].add_widget(bl)
    def refresh_screen(self):
        self.children[0].clear_widgets()
    def previous_screen(self, button):
        app = self.app
        self.manager.transition.direction = "right"
        self.manager.transition.duration = 1
        self.manager.current = "ScheduleScreen"
        self.parent.children[0].refresh_screen()
        self.refresh_screen()
        self.parent.children[0].load_schedule(app)
    def submit(self, button):
        pass


#Budgets
class BudgetScreen(Screen):
    pass


#Wallets
class WalletsScreen(Screen):
    pass


#Goals
class GoalsScreen(Screen):
    pass

#Calender



#Calculations


#Visualizations



class MMApp(App):

    def build(self):
        self.db = DB()
        sm = ScreenManager()
        #check to see if User needs to be registered
        if self.db.register_user == True:
            sm.add_widget(RegistrationScreen(name="RegistrationScreen"))
        #Login User
        else:
            sm.add_widget(LoginScreen(name="LoginScreen"))
        
        sm.add_widget(MenuScreen(name="MenuScreen"))
        sm.add_widget(TransactionsScreen(name="TransactionsScreen"))
        sm.add_widget(SubTransactionScreen(name="SubTransactionScreen"))
        sm.add_widget(ScheduleScreen(name="ScheduleScreen"))
        sm.add_widget(DayScreen(name="DayScreen"))
        return sm


if __name__ == '__main__':
    MMApp().run()
