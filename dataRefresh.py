import time
import pandas as pd
from connection import fetchFromClientDB, saveToSQLite, get_last_update_time
import sqlite3
from datetime import datetime
import json 

with open('config.json') as config_file:
    configVar = json.load(config_file)
client_table_name = configVar['client_table_name']


def create_refresh_logs_table():
    conn = sqlite3.connect('EdgeDB')  # Connect to  SQLite database
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS RefreshLogs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            refresh_time TEXT,
            status TEXT,
            message TEXT
        )
    """)
    conn.commit()
    conn.close()


def log_refresh(status: str, message: str):
    conn = sqlite3.connect('EdgeDB')
    c = conn.cursor()
    c.execute("""
        INSERT INTO RefreshLogs (refresh_time, status, message)
        VALUES (?, ?, ?)
    """, (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), status, message))
    conn.commit()
    conn.close()


def refresh_data():
    create_refresh_logs_table()  
    # while True:
    try:
        # Fetch data from the client database
        df = fetchFromClientDB(client_table_name, get_last_update_time()) 
        
        # Save the fetched data to SQLite
        saveToSQLite(df)
        log_refresh("Success", "Data refreshed and saved to SQLite.")
    except Exception as e:
        log_refresh("Error", str(e))
    
    print(f'Refreshed Successfully\n')
    
    # Wait for 3 minutes (180 seconds) before the next refresh
    # time.sleep(180)

if __name__ == "__main__":
    refresh_data()