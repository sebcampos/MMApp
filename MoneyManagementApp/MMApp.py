#!/usr/local/bin/python3
import os 
import pandas
import datetime
import random
import json


import kivy
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.network.urlrequest import UrlRequest 
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.bubble import BubbleButton
from kivy.app import App

kivy.require('2.0.0')
#Config files located on iOS = <HOME_DIRECTORY>/Documents/.kivy/config.ini
os.environ['KIVY_EVENTLOOP'] = 'asyncio'

#User class
class User():
    def __init__(self, phone_number, password, email, username, user_id=False):
        if user_id == False:
            user_id = "".join([randint(100,500) for i in range(10)])
        self.username = username
        self.email = email
        self.password = password
        self.phone_number = phone_number
        self.dataframe = pandas.DataFrame({
                "user_id" : [self.user_id],
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
        if self.ids["password"].text != self.ids["confirmation"].text:
            cb = BubbleButton(text="Passwords do not match\n\n\n\n   Close")
            pu = Popup(title="InputError", content=cb, size_hint=(.5, .5))
            cb.bind(on_press=pu.dismiss)
            pu.open()
            return
        
        req = UrlRequest("http://34.94.45.224/register_user", req_headers={'Content-type': 'application/json'}, req_body=json.dumps({i:v.text for i,v in self.ids.items()}))
        req.wait()
        print(req.resp_headers)
        print(req.resp_status)
        print(req.result)
        # elif data["Username"] in users_table.values or  data["Email"] in users_table.values or data["Phone number"] in users_table.values:
        #     cb = BubbleButton(text="User data already exists\n\n\n\n   Close")
        #     pu = Popup(title="NewUserError", content=cb, size_hint=(.5, .5))
        #     cb.bind(on_press=pu.dismiss)
        #     pu.open()
        #     return
        # else:
        #     self.manager.transition.direction = "left"
        #     self.manager.transition.duration = 1
        #     self.manager.current = "MenuScreen"
        #     return

















class MMApp(App):
    def build(self):
        #self.db = DB()
        self.sm = ScreenManager()
        self.sm.add_widget(RegistrationScreen(name="RegistrationScreen"))
        # self.sm.add_widget(LoginScreen(name="LoginScreen"))
        # self.sm.add_widget(MenuScreen(name="MenuScreen"))
        # self.sm.add_widget(TransactionsScreen(name="TransactionsScreen"))
        # self.sm.add_widget(AddTransactionScreen(name="AddTransactionScreen"))
        # self.sm.add_widget(ViewTransactionScreen(name="ViewTransactionScreen"))
        # self.sm.add_widget(ScheduleScreen(name="ScheduleScreen"))
        # self.sm.add_widget(DayScreen(name="DayScreen"))
        # self.sm.add_widget(BudgetScreen(name="BudgetScreen"))
        # self.sm.add_widget(WalletsScreen(name="WalletsScreen"))
        # self.sm.add_widget(AddWalletScreen(name="AddWalletScreen"))
        # self.sm.add_widget(GoalsScreen(name="GoalsScreen"))
        # self.sm.add_widget(AddGoalScreen(name="AddGoalScreen"))
        # self.sm.add_widget(AnalysisScreen(name="AnalysisScreen"))        
        # #check to see if User needs to be registered
        # if self.db.register_user == True:
        #     self.sm.current = "RegistrationScreen"
        # else:
        #     self.sm.current = "LoginScreen"
        return self.sm


if __name__ == '__main__':
    MMApp().run()