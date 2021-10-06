#!/usr/local/bin/python3
import os 
import pandas
import datetime
import random
import json
from credentials import end_point_address, encryption, create_keys_rsa, encrypt_packet, decrypt_packet


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
    def __init__(self, user_id, phone_number, email, username):
        self.user_id = user_id
        self.username = username
        self.email = email
        self.phone_number = phone_number
        self.dataframe = pandas.DataFrame({
            "user_id": [self.user_id],
            "username": [self.username],
            "user_email": [self.email], 
            "phone_number": [self.phone_number]
        })
         
    def __repr__(self):
        return f"Username:\t{self.username}\nEmail:\t{self.email}\nPassword:\t{self.password}\nPhone:\t{self.phone_number}"

#Registration Screen
class RegistrationScreen(Screen):
    def register(self, app):
        #check password length
        if len(self.ids["password"].text) <= 8:
            cb = BubbleButton(text="Passwords must be longer than 8 characters\n\n\n\n   Close")
            pu = Popup(title="InputError", content=cb, size_hint=(.5, .5))
            cb.bind(on_press=pu.dismiss)
            pu.open()
            return 

        #check if user entered password matches confirmation input
        if self.ids["password"].text != self.ids["confirmation"].text:
            cb = BubbleButton(text="Passwords do not match\n\n\n\n   Close")
            pu = Popup(title="InputError", content=cb, size_hint=(.5, .5))
            cb.bind(on_press=pu.dismiss)
            pu.open()
            return 
        #Make a Post request to register user endpoint and encode password with rsa
        user_data_dict = {i:v.text for i,v in self.ids.items()}
        data = encryption(json.dumps(user_data_dict))
        #send json data as encrypted bytes
        req = UrlRequest(f"http://{end_point_address}/register_user", req_headers={'Content-type': 'application/octet-stream'}, req_body=data, on_progress=self.animation, timeout=10, on_error=lambda x,y: print("error",y), on_failure=lambda x,y: print("failure",y))
        req.wait()
        response = json.loads(req.result)
        #if Successfull save User() as app.user write down unique number in app directory and transition to menu screen
        if "Success" in response.keys():
            data = decrypt_packet(response)
            app.user = User(response["id"], user_data_dict["phone_number"], user_data_dict["username"],  user_data_dict["email"], )
            app.user_id = response["id"]
            #save user id
            with open("UserID","w") as f:
                f.write(response["id"])
            #save user privkey
            with open(f"{user_data_dict['username']}_privkey", "w") as f:
                f.write(response['privkey'])
            #save user pubkey
            with open(f"{user_data_dict['username']}_pubkey", "w") as f:
                f.write(response['pubkey'])
            for w in self.ids.values():
                w.text = ""
            self.manager.transition.direction = "left"
            self.manager.transition.duration = 1
            self.manager.current = "LoginScreen"
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
        user = self.ids['username'].text
        #encrypt packet
        packet = encrypt_packet({i:v.text for i,v in self.ids.items()}, user = self.ids['username'].text)
        packet["USER"] = user
        with open("UserID", "r") as f:
            packet["USERID"] = f.read()

        app.user_id = packet["USERID"]
        app.user_password = self.ids['password'].text
        app.user_name = self.ids['username'].text
        
        #request to API for credential confirmation
        req = UrlRequest(f"http://{end_point_address}/login_user", req_headers={'Content-type': 'application/json'}, req_body=json.dumps(packet), on_progress=self.animation, timeout=10, on_error=lambda x,y: print("error",y), on_failure=lambda x,y: print("failure",y))
        req.wait()
        packet = json.loads(req.result)
        
        #if Successfull collect user data
        if "Success" in packet.keys():
            del packet["Success"]
            packet = decrypt_packet(packet, user = user)
            app.transactions = pandas.DataFrame.from_dict(json.loads(packet["Transactions"]))
            app.schedule = pandas.DataFrame.from_dict(json.loads(packet["Schedule"]))
            app.goals = pandas.DataFrame.from_dict(json.loads(packet["Goals"]))
            app.wallets = pandas.DataFrame.from_dict(json.loads(packet["Wallets"]))
            app.budgets =  pandas.DataFrame.from_dict(json.loads(packet["Budgets"]))
            self.manager.transition.direction = "left"
            self.manager.transition.duration = 1
            self.manager.current = "MenuScreen"

            return
        
        #return a pop up with Error message if failed
        else:
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
        app.user_name = False
        app.user_id = False
        app.user_password = False
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
        gl.size_hint_y = len(app.transactions)
        #iterate over the transactions dataframe and add values to the kivy Gridlayout object
        for row in app.transactions.values:
            gl.add_widget(BubbleButton(text=str(row[0]), on_press=self.load_transaction, background_normal="", background_color=(.4, .5, 100, .3)))
            for cell in row[1:]:
                gl.add_widget(Label(text=str(cell)))

    #sort table on screen based on button/columns
    def sort_table(self, button, app):
        #load the GridLayout object
        gl = self.ids["gl"]
        
        #clear the current widgets on gl
        gl.clear_widgets()
        gl.size_hint_y = len(app.transactions)
        #if the button state is in decending sort column values in ascending order
        if self.column_states[button.text] == "descending": 
            for row in self.transactions.sort_values(self.translate_columns[button.text], ascending=True).values:
                gl.add_widget(BubbleButton(text=str(row[0]), on_press=self.load_transaction, background_normal="", background_color=(.4, .5, 100, .3)))
                for cell in row[1:]:
                    gl.add_widget(Label(text=str(cell)))
            #set new state to ascending
            self.column_states[button.text] = "ascending"
            return
        
        #if the button state is in ascending sort column values in decending order
        elif self.column_states[button.text] == "ascending": 
            for row in self.transactions.sort_values(self.translate_columns[button.text], ascending=False).values:
                gl.add_widget(BubbleButton(text=str(row[0]), on_press=self.load_transaction, background_normal="", background_color=(.4, .5, 100, .3)))
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
        self.manager.get_screen("ViewTransactionScreen").populate_screen(self.transactions, button)
        

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
        data = {i:v.text for i,v in self.ids.items() if i != "dropdown"}
        data["user_id"] = app.user_id
        data["user_password"] = app.user_password
        content = data.copy()
        content = encrypt_packet(content, app.user_name)
        content["update"] = "add transaction"
        content["user_name"] = app.user_name
        #send json data as encrypted bytes
        req = UrlRequest(f"http://{end_point_address}/user_services/update", req_headers={'Content-type': 'application/json'}, req_body=json.dumps(content), on_progress=self.animation, timeout=10, on_error=lambda x,y: print("error",y), on_failure=lambda x,y: print("failure",y))
        req.wait()
        response = json.loads(req.result)
        if "Success" in response.keys():
            transaction_id = len(app.transactions)
            df = pandas.DataFrame({
			"transaction_id": [int(transaction_id)],
			"transaction_date": [data["date"]],
			"amount": [data["amount"]],
			"location": [data["location"]],
			"transaction_type": [data["transaction_type"]],
			"transaction_tag": [data["tag"]],
			"wallet_name": [data["wallet"]]
		    })

            app.transactions = pandas.concat([app.transactions, df])

            print(app.transactions)

            #subtract from wallet
            if content["transaction_type"] == "Withdrawl":
                app.wallets.loc[wallets.wallet_name == content["wallet"], "wallet_amount"] -= int(content["amount"])
            #add to wallet
            elif content["transaction_type"] == "Deposit":
                app.wallets.loc[wallets.wallet_name == content["wallet"], "wallet_amount"] += int(content["amount"])
            
            cb = BubbleButton(text="Transaction Added\n\n\n\n   Close")
            pu = Popup(title="Success", content=cb, size_hint=(.5, .5))
            cb.bind(on_press=pu.dismiss)
            pu.open()
            
            return


    
    def animation(*argsv):
        print(argsv)


        

















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