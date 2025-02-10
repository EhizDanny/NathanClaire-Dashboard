import time
import pandas as pd
from connection import fetchFromClientDB, saveToSQLite, get_last_update_time
import sqlite3
from datetime import datetime
import json 
import threading   
lock = threading.Lock()  # Create a lock object

with open('config.json') as config_file:
    configVar = json.load(config_file)
client_table_name = configVar['client_table_name']


def create_refresh_logs_table():
    conn = sqlite3.connect('EdgeDB')  # Connect to  SQLite database
    conn.execute('PRAGMA journal_mode=WAL')
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS RefreshLogs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tableName TEXT,
            refresh_time TEXT,
            status TEXT,
            message TEXT
        )
    """)
    conn.commit()
    conn.close()


def log_refresh(status: str, message: str): 
    conn = sqlite3.connect('EdgeDB')
    conn.execute('PRAGMA journal_mode=WAL')
    c = conn.cursor()
    c.execute("""
        INSERT INTO RefreshLogs (tableName, refresh_time, status, message)
        VALUES (?, ?, ?, ?)
    """, (client_table_name ,datetime.now().strftime("%Y-%m-%d %H:%M:%S"), status, message))
    conn.commit()
    conn.close()

def liveDataHandler(db_path, table_name):
    """
    Load data from the database and save it to a Parquet file.
    Args:
        db_path (str): Path to the SQLite database.
        table_name (str): Table name to query.
        start_date (str): Start date for filtering data.
        stop_date (str): Stop date for filtering data.
    Returns:
        pd.DataFrame: The loaded dataset.
    """
    conn = sqlite3.connect(db_path)
    conn.execute('PRAGMA journal_mode=WAL')
    query = f"""
    SELECT * FROM '{table_name}' ;
    """
    dataset = pd.read_sql_query(query, conn)
    dataset.to_parquet('workingData.parquet', engine='fastparquet', index=False)
    conn.close()


def refresh_data():  
    if lock.acquire(blocking=False):  # Non-blocking mode  
        try:  
            create_refresh_logs_table()  
            try:  
                # Fetch data from the client database  
                df = fetchFromClientDB(client_table_name, get_last_update_time())   
                saveToSQLite(df)  # Save the fetched data to SQLite  
                log_refresh("Success", "Data refreshed and saved to SQLite.")  
            except Exception as e:  
                log_refresh("Error", str(e))  

            print(f'Refreshed Successfully\n')  
        finally:  
            liveDataHandler('EdgeDB', 'Infra_Utilization') # Call the liveDataHandler function to save to parquet
            lock.release()  # Release the lock after the operation is done  
    else:  
        print("Previous refresh_data execution is still running. Skipping this call.")  

    # Schedule the next refresh after 3 minutes  
    print('Waiting for next refresh in 3minutes')
    threading.Timer(180, refresh_data).start()  # 180 seconds = 3 minutes  




if __name__ == "__main__":  
    refresh_data() 
    

# def refresh_data():
#     create_refresh_logs_table()  
#     # while True:
#     try:
#         # Fetch data from the client database
#         df = fetchFromClientDB(client_table_name, get_last_update_time()) 
        
#         # Save the fetched data to SQLite
#         saveToSQLite(df)
#         log_refresh("Success", "Data refreshed and saved to SQLite.")
#     except Exception as e:
#         log_refresh("Error", str(e))

#     print(f'Refreshed Successfully\n')

#     # Wait for 3 minutes (180 seconds) before the next refresh
#     # time.sleep(180)

# if __name__ == "__main__":
#     refresh_data()