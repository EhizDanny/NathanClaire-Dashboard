import pandas as pd 
import pyodbc 
import warnings 
warnings.filterwarnings('ignore')
import numpy as np
import sqlite3
import json
from sqlalchemy import create_engine

# Config Variables 
with open('config.json') as config_file:
    configVar = json.load(config_file)

clientServer = configVar['client_server']
clientDB = configVar['client_db']
clientDBUserName = configVar['client_db_username']
clientDBPass = configVar['client_db_password']
client_table_name = configVar['client_table_name']




def connectClientDB(server: str, database: str, username: str, password: str) -> str:
    """
    Owner: 
        Nathan Claire Africa
    Args:
        server (str): the server from which information is to be collected
        database (str): the database name housing the table of interest
        username (str): database credential -> username
        password (str): database credential -> password
    Returns:
        str: returns the pyodbc connection string, to be used an input to the pyodbc.connect() function
    """   
    connection_string = f"mssql+pyodbc://{username}:{password}@{server}/{database}?driver=ODBC+Driver+17+for+SQL+Server"
    # connection_string = f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server};DATABASE={database};UID={username};PWD={password}'
    connection = create_engine(connection_string) 
    return connection


def fetchFromClientDB(clientTableName, last_update_time=None):
    """
    Fetch data from client database and return it as a DataFrame.
    If last_update_time is provided, only fetch rows updated after this time.
    """
    server = clientServer 
    database = clientDB
    username = clientDBUserName            
    password = clientDBPass 
    conn = connectClientDB(server, database, username, password)

    # On the first run, metaData table doesnt exist....
    # This code then checks if the Metadata table exists
    metadata_exists = False
    try:
        c = conn.cursor()
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='Metadata';")
        metadata_exists = c.fetchone() is not None
    except Exception as e:
        # print(f"Error checking Metadata table existence; {e}")
        pass

    # If the Metadata table exists, get the last update time
    if metadata_exists:
        last_update_time = get_last_update_time()

    # Fetch last update if last_update_time is provided
    if last_update_time is not None:
        query = f"""
        SELECT * FROM {clientTableName} 
        WHERE LogTimestamp > '{last_update_time}'
        """
        print(f'collecting data from last update time; {last_update_time}\n')
    else:
        print(f'\nfetching data for the first time. default time is 2months of data')
        query = f"SELECT * FROM {clientTableName}"  # Fetch all data on the first run

    df = pd.read_sql(query, conn)
    #conn.close()
    return df

def saveToSQLite(frame: pd.DataFrame):
    """
    Save a DataFrame to an SQLite database.

    This function appends new rows from the provided DataFrame to the 
    'Infra_Utilization' table in the SQLite database. If the table does 
    not exist, it will be created. Additionally, the function retrieves 
    the maximum timestamp from the 'LogTimestamp' column of the 
    'Infra_Utilization' table and stores it in a 'Metadata' table to 
    keep track of the last update time.

    Parameters:
    frame (pd.DataFrame): The DataFrame containing the data to be saved. 
                          It must include a 'LogTimestamp' column for 
                          tracking updates.

    Returns:
    None: This function does not return any value. It performs the 
          operation of saving data to the database and updating the 
          metadata.
    
    Raises:
    Exception: If an error occurs during the database operations, 
               an exception will be raised and printed to the console.
    """
    with sqlite3.connect('EdgeDB') as conn:
        c = conn.cursor()
        
        try:
            # If the table doesn't exist, create it. if it exists, append new rows to it
            frame.to_sql('Infra_Utilization', conn, if_exists='append', index=False) 
            
            # Get the lastUpdate from this newly updated data
            c.execute("SELECT MAX(LogTimestamp) FROM Infra_Utilization")     
            lastUpdate = c.fetchone()
            
            # Create a table to store the lastUpdate time
            c.execute("""CREATE TABLE IF NOT EXISTS Metadata (
                      id INTEGER PRIMARY KEY AUTOINCREMENT,
                      last_update_time TEXT)
                """)
            
            if lastUpdate is not None and lastUpdate[0] is not None:
                c.execute("INSERT INTO Metadata (last_update_time) VALUES (?)", (lastUpdate[0],))
        except Exception as e:
            print(f"Error occurred while saving to SQLite: {e}")

def get_last_update_time() -> str:
    """Get the last update time from the SQLite database.
    Returns:
        lastUpdateTime: The latest time in a SQL table and outputs the time in 'YYYY-MM-DD HH:MM:SS' format.
    """    
    # Implementing a check to see if the metadata table exists
    metadata_exists = False  

    conn = sqlite3.connect('EdgeDB')
    c = conn.cursor()
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='Metadata';")
    metadata_exists = c.fetchone() is not None

    if metadata_exists:
        c.execute("""
                SELECT last_update_time FROM Metadata
                ORDER BY id DESC
                LIMIT 1
                """)
        lastUpdate = c.fetchone()
        conn.close()

        if lastUpdate is None:
            return None
        return lastUpdate[0]
    else:
        pass


# def fetchData():
#     """
#     Returns:
#         pandas: [description]
#     """    
#     server = 'EHIZDANIEL273A' #EHIZDANIEL273A'4.149.240.230' #'EHIZDANIEL273A'
#     database = 'Dynatrace_API'
#     username = 'sa' #'data_science' #'sa'
#     password = 'danielle1990' #'2424DATA++' #'danielle1990'
#     conn = connectToClientDB(server, database, username, password)
#     cursor = conn.cursor()
#     query = "SELECT * FROM Infrastructure_Utilization" # Query to fetch the data from source
#     df = pd.read_sql(query, conn) # Use pandas to read the SQL query directly into a DataFrame
#     conn.close() # Closr the connection
#     return df