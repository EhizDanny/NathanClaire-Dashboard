import pandas as pd
from connection import fetchFromClientDB, saveToSQLite  
import sqlite3
from datetime import datetime
import json
import time
import os
from deleteDBRows import delete_old_rows, delete_old_refresh_logs, delete_old_lastupdateTIme
import gc
from memory_profiler import profile, memory_usage


# Load configuration
with open('config.json') as config_file:
    configVar = json.load(config_file)
client_table_name1 = configVar['client_table_name1']
client_table_name2 = configVar['client_table_name2']


def create_refresh_logs_table():
    """Creates the RefreshLogs table if it doesn't exist."""
    with sqlite3.connect('EdgeDB.db') as conn:
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

def log_refresh(status: str, message: str):
    """Logs the data refresh event to the RefreshLogs table."""
    with sqlite3.connect('EdgeDB.db') as conn:
        conn.execute('PRAGMA journal_mode=WAL')
        c = conn.cursor()
        c.execute("""
            INSERT INTO RefreshLogs (tableName, refresh_time, status, message)
            VALUES (?, ?, ?, ?)
        """, (client_table_name1, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), status, message))
        conn.commit()


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
    with sqlite3.connect(db_path) as conn:
        conn.execute('PRAGMA journal_mode=WAL')
        query = f"""
        SELECT * FROM '{table_name}' ;
        """
        dataset = pd.read_sql_query(query, conn)
        dataset.to_parquet('workingData.parquet', engine='fastparquet', index=False)
        del dataset
        gc.collect()

# @profile
def refresh_data():
    """
    Fetches data from the client database, saves it to SQLite, and updates a Parquet file.
    This function is designed to be called once per invocation.
    """
    create_refresh_logs_table()
    print("Starting data refresh...")
    try:
        # Fetch data from the client database
        data = fetchFromClientDB(client_table_name1, client_table_name2)
        if data.empty:
            log_refresh("Error", "Could not connect to client database.")
            print("Failed to fetch data from client database.")
        else:
            # Save to SQLite only if data was fetched
            saveToSQLite(data)
            print(f"Data fetched from client database at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}.")
            log_refresh("Success", "Data refreshed and saved to SQLite.")
            delete_old_rows('EdgeDB.db', 'Infra_Utilization', 2)
            print("Deleting rows from EdgeDB.db/Infra_Utilization older than 2 days...")
            delete_old_refresh_logs('EdgeDB.db', 'RefreshLogs', 7)
            delete_old_lastupdateTIme('EdgeDB.db', 'latestLogTime', 7)
    except Exception as e:
        log_refresh("Error", str(e))
        print(f"Error during data refresh: {e}")
    finally:
        # Save the data to parquet
        print('Saving data to parquet...')
        # liveDataHandler('EdgeDB.db', 'Infra_Utilization') # Call the liveDataHandler function to save to parquet
        print(f"Data refresh completed.\n")



if __name__ == "__main__":
    # start_time = time.time()
    refresh_data()
    # end_time = time.time()
    # print(f"refresh script took {round(end_time-start_time,2)} seconds to run\n")
    print('Eventual consistency in 2 minutes  ...')
    # mem_usage = memory_usage((refresh_data, (), {}))
    # print(mem_usage)
    gc.collect()
