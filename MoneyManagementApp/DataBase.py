import sqlite3
import datetime

#SQLite3
class DB():
    def __init__(self):
        self.conn = sqlite3.connect("MM_sqlite.db")
        self.cur = self.conn.cursor()
        self.cur.execute("""
            CREATE TABLE if not exists user_table(
                userid int,
                useremail text,
                username text,
                phonenumber text               
            )""")
        self.cur.execute("""
            CREATE TABLE if not exists transactions(
                transaction_id int,
                transaction_date date,
                amount float,
                location text,
                transaction_type text,
                transaction_tag text,
                wallet_name text
            )""")
        self.cur.execute("""
            CREATE TABLE if not exists scheduled(
                transaction_id int,
                frequency int,
                scheduled_date date,
                next_day date,
                amount int,
                transaction_type text,
                wallet_name text,
                added_today text
            )""")
        self.cur.execute("""
            CREATE TABLE if not exists wallets(
                wallet_id int,
                wallet_name text,
                wallet_amount float,
                short_description text,
                wallet_created_date date,
                transaction_count int
            )""")

        self.conn.commit()
    def create_first_wallet(self):
        today = str(datetime.datetime.now().date())
        self.cur.execute(f"""
            INSERT INTO Wallets (wallet_id, wallet_name, wallet_amount, short_description, wallet_created_date, transaction_count)
            VALUES(0, 'Standard Wallet', 0, 'Wallet created on start up', '{today}', 0)
            """)
        self.conn.commit()



    def append(self, data, table):
        pass 
    
    def delete(self, row, table):
        pass
    
    def update_row(self, row, column, table):
        pass
        
    async def refresh_tables(self):
        pass