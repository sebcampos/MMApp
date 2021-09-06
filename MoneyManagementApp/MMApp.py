#!/usr/local/bin/python3
import kivy
import os
import sqlite3 
import pandas
from kivy.uix.screenmanager import ScreenManager, Screen
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
    def add_user(self, db):
        pass



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
    def register(self, db):
        status = "not registered"
        print(self.children[0].children)
        
        if status == "registered":
            self.manager.transition.direction = "left"
            self.manager.transition.duration = 1
            self.manager.current = "MenuScreen"
        


#Login Screen
class LoginScreen(Screen):
    pass

#Menu
class MenuScreen(Screen):
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
        return sm


if __name__ == '__main__':
    MMApp().run()
