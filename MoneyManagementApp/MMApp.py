#!/usr/local/bin/python3
import os 
import pandas
import datetime
import random
import json
from credentials import end_point_address


import kivy
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.network.urlrequest import UrlRequest 
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.bubble import BubbleButton
from kivy.app import App

kivy.require('2.0.0')
#Config files located on iOS = <HOME_DIRECTORY>/Documents/.kivy/config.ini
# os.environ['KIVY_EVENTLOOP'] = 'asyncio'

#User class
class User():
    def __init__(self, user_id, phone_number, password, email, username):
        self.user_id = user_id
        self.username = username
        self.email = email
        self.password = password
        self.phone_number = phone_number
         
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
        response = json.loads(req.result)
        if "Success" in response.keys():
            app.user = User(response["id"], self.ids["username"].text,  self.ids["email"].text, self.ids["password"].text, self.ids["phone_number"].text)
            app.user_id = response["id"]
            with open("UserID","w") as f:
                f.write(response["id"])
            for w in self.ids.values():
                w.text = ""
            self.manager.transition.direction = "left"
            self.manager.transition.duration = 1
            self.manager.current = "MenuScreen"
        else:
            cb = BubbleButton(text="User Name Already Exists\n\n\n\n   Close")
            pu = Popup(title="RegistrationError", content=cb, size_hint=(.5, .5))
            cb.bind(on_press=pu.dismiss)
            pu.open()
            return

#Login Screen
class LoginScreen(Screen):
    def login(self, app):
        #add password check logic
        
        #request to API for credential confirmation
        req = UrlRequest(f"http://{end_point_address}/login_user", req_headers={'Content-type': 'application/json'}, req_body=json.dumps({
            "username":self.ids["username"].text,
            "password":self.ids["password"].text,
            "user_id": app.user_id
            }))
        req.wait()
        response = json.loads(req.result)
        
        #hand to menu screen if succesful
        if "Success" in response.keys():
            self.manager.transition.direction = "left"
            self.manager.transition.duration = 1
            self.manager.current = "MenuScreen"
            return
        
        #return a pop up with Error message if failed
        else:
            print(response)
            cb = BubbleButton(text=f"{response['Error']}\n\n\n\n   Close")
            pu = Popup(title="LoginError", content=cb, size_hint=(.5, .5))
            cb.bind(on_press=pu.dismiss)
            pu.open()
            return



    def reset_password(self):
        pass




class MenuScreen(Screen):
    def log_out(self, app):
        app.user = False
        self.manager.transition.direction = "right"
        self.manager.transition.duration = 1
        self.manager.current = "LoginScreen"

class TransactionsScreen(Screen):
    def load_transactions(self, app):
        print(self.parent, app)

















class MMApp(App):
    def build(self):
        self.sm = ScreenManager()
        self.sm.add_widget(RegistrationScreen(name="RegistrationScreen"))
        self.sm.add_widget(LoginScreen(name="LoginScreen"))
        self.sm.add_widget(MenuScreen(name="MenuScreen"))
        self.sm.add_widget(TransactionsScreen(name="TransactionsScreen"))
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