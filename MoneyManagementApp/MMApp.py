#!/usr/local/bin/python3
import os 
import pandas
import datetime
import random
import json
import base64
from credentials import end_point_address, encryption, create_keys_rsa, AES_decrypt, AES_encrypt, AES_set_up


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
        self.dataframe = pandas.DataFrame({
            "user_id": [self.user_id],
            "username": [self.username],
            "user_email": [self.email],
            "user_password": [self.password],
            "phone_number": [self.phone_number]
        })
         
    def __repr__(self):
        return f"Username:\t{self.username}\nEmail:\t{self.email}\nPassword:\t{self.password}\nPhone:\t{self.phone_number}"

#Registration Screen
class RegistrationScreen(Screen):
    def register(self, app):
        #check if user entered password matches confirmation input
        if self.ids["password"].text != self.ids["confirmation"].text:
            cb = BubbleButton(text="Passwords do not match\n\n\n\n   Close")
            pu = Popup(title="InputError", content=cb, size_hint=(.5, .5))
            cb.bind(on_press=pu.dismiss)
            pu.open()
            return

        #create credentials to cipher larger data
        key, cipher, nonce = AES_set_up()
		with open("AES_key","wb") as f:
			f.write(key)
		with open("AES_nonce","wb") as f:
			f.write(nonce)    
        #Make a Post request to register user endpoint and encode password with rsa
        user_data_dict = {i:v.text for i,v in self.ids.items()}
        user_data_dict["key"] = base64.b64encode(key).decode()
        user_data_dict["nonce"] = base64.b64encode(nonce).decode()
        data = encryption(json.dumps(user_data_dict))
        #send json data as encrypted bytes
        req = UrlRequest(f"http://{end_point_address}/register_user", req_headers={'Content-type': 'application/octet-stream'}, req_body=data, on_progress=self.animation, timeout=10)
        req.wait()
        print(req.result)
        response = json.loads(encryption(req.result, encrypt=False))
        #if Successfull save User() as app.user write down unique number in app directory and transition to menu screen
        if "Success" in response.keys():
            print(response)
            #app.user = User(response["id"], user_data_dict["username"],  user_data_dict["email"], user_data_dict["phone_number"])
            #app.user_id = response["id"]
            with open("UserID","w") as f:
                f.write(response["id"])
            # with open()

            for w in self.ids.values():
                w.text = ""
            self.manager.transition.direction = "left"
            self.manager.transition.duration = 1
            self.manager.current = "MenuScreen"
        #if Unsuccessfull return Registration error message popup
        else:
            cb = BubbleButton(text="User Name Already Exists\n\n\n\n   Close")
            pu = Popup(title="RegistrationError", content=cb, size_hint=(.5, .5))
            cb.bind(on_press=pu.dismiss)
            pu.open()
            return
    def animation(*argsv):
        print(argsv)

#Login Screen
class LoginScreen(Screen):
    def login(self, app):
        #encrypt password
        password = encryption(self.ids["password"].text)

        #request to API for credential confirmation
        req = UrlRequest(f"http://{end_point_address}/login_user", req_headers={'Content-type': 'application/json'}, req_body=json.dumps({
            "username":self.ids["username"].text,
            "password": password,
            "user_id": app.user_id
            }), on_progress=self.animation, timeout=10)
        req.wait()
        response = json.loads(req.result)
        
        #if Successfull collect user data
        if "Success" in response.keys():
            app.transactions = pandas.DataFrame.from_dict(response["Transactions"])
            app.schedule = pandas.DataFrame.from_dict(response["Schedule"])
            app.goals = pandas.DataFrame.from_dict(response["Goals"])
            app.wallets = pandas.DataFrame.from_dict(response["Wallets"])
            app.budgets =  pandas.DataFrame.from_dict(response["Budgets"])
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

    def animation(*argsv):
        print(argsv)

    def reset_password(self):
        pass




class MenuScreen(Screen):
    def log_out(self, app):
        app.user = False
        self.manager.transition.direction = "right"
        self.manager.transition.duration = 1
        self.manager.current = "LoginScreen"

class TransactionsScreen(Screen):
    #display transaction data on screen
    def display_transactions(self, app):
        #define a column maping dictionary
        self.translate_columns = {
            "ID":"transaction_id",
            "Date":"transaction_date",
            "Amount":"amount",
            "Loc":"location",
            "Type":"transaction_type",
            "Tag":"transaction_tag",
            "Wallet":"wallet_name"
        }

        self.transactions = app.transactions

        #define a column state dictionary for sorting function
        self.column_states = {}
        for column in self.translate_columns.keys():
            self.column_states[column] = "descending"

        #load the GridLayout object
        gl = self.ids["gl"]
        
        #clear the widgets on gl in case there are any currently existing
        gl.clear_widgets()

        #iterate over the transactions dataframe and add values to the kivy Gridlayout object
        for row in app.transactions.values:
            gl.add_widget(BubbleButton(text=str(row[0]), on_press=self.load_transaction(*args)))
            for cell in row[1:]:
                gl.add_widget(Label(text=str(cell)))

    #sort table on screen based on button/columns
    def sort_table(self, button):
        #load the GridLayout object
        gl = self.ids["gl"]
        
        #clear the current widgets on gl
        gl.clear_widgets()

        #if the button state is in decending sort column values in ascending order
        if self.column_states[button.text] == "descending": 
            for row in self.transactions.sort_values(self.translate_columns[button.text], ascending=True).values:
                gl.add_widget(BubbleButton(text=str(row[0]), on_press=self.load_transaction(*args)))
                for cell in row[1:]:
                    gl.add_widget(Label(text=str(cell)))
            #set new state to ascending
            self.column_states[button.text] = "ascending"
            return
        
        #if the button state is in ascending sort column values in decending order
        elif self.column_states[button.text] == "ascending": 
            for row in self.transactions.sort_values(self.translate_columns[button.text], ascending=False).values:
                gl.add_widget(BubbleButton(text=str(row[0]), on_press=self.load_transaction(*args)))
                for cell in row[1:]:
                    gl.add_widget(Label(text=str(cell)))
            #set new state to descending                    
            self.column_states[button.text] = "descending"
            return
    
    #load a transaction and transition screen when clicked
    def load_transaction(self, button):
        self.manager.transition.direction = "left"
        self.manager.transition.duration = 1
        self.manager.current = "ViewTransactionScreen"
        self.manager.get_screen("ViewTransactionScreen").populate_screen(self.transactions, button.text)
        

class ViewTransactionScreen(Screen):
    def populate_screen(self, transactions_df, transaction_id):
        pass
    
    def delete_transaction(self):
        ## Delete from all tables ##
        pass


class AddTransactionScreen(Screen):
    #today timestamp
    def today_timestamp(self):
        return f"{datetime.datetime.now().date()}"
    #add transaction to current table(s) and update table(s) over API
    def add_transaction(self, app):
        pass
        

















class MMApp(App):
    def build(self):
        self.sm = ScreenManager()
        self.sm.add_widget(RegistrationScreen(name="RegistrationScreen"))
        self.sm.add_widget(LoginScreen(name="LoginScreen"))
        self.sm.add_widget(MenuScreen(name="MenuScreen"))
        self.sm.add_widget(TransactionsScreen(name="TransactionsScreen"))
        self.sm.add_widget(AddTransactionScreen(name="AddTransactionScreen"))
        self.sm.add_widget(ViewTransactionScreen(name="ViewTransactionScreen"))
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