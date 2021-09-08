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
from kivy.uix.textinput import TextInput
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
        self.children[0].add_widget(BoxLayout(orientation='horizontal'))
        for i in transactions.columns:
            self.children[0].children[0].add_widget(Label(text=i))
        self.children[0].add_widget(GridLayout(cols=len(transactions.columns)))
        for i in transactions.values:
            self.children[0].children[0].add_widget(Label(text=i))
        self.children[0].add_widget(BoxLayout(orientation='horizontal'))
        buttons = self.children[0].children[0]
        add_t = Button(text="Add Transaction")
        add_t.bind(on_press=self.add_transactions)
        buttons.add_widget(add_t)
        return_mm = Button(text="Return To Menu")
        return_mm.bind(on_press=self.return_to_menu)
        buttons.add_widget(return_mm)
    
    def add_transactions(self, button):
        self.manager.add_widget(SubTransactionScreen(name="SubTransactionScreen"))
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
        return f"{datetime.datetime.now()}"

    def update_table(self, app_db):
        print(self)
    
    def previous_screen(self):
        self.manager.transition.direction = "right"
        self.manager.transition.duration = 1
        self.manager.current = "TransactionsScreen"

    


#Schedule
class ScheduleScreen(Screen):
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
        return sm


if __name__ == '__main__':
    MMApp().run()
