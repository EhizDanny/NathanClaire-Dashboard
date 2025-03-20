import pandas as pd 
import pyodbc 
import warnings 
warnings.filterwarnings('ignore')
import numpy as np
import sqlite3
import json
from sqlalchemy import create_engine
from datetime import datetime, timedelta
import gc
from memory_profiler import profile

three_days_ago_str = (datetime.now() - timedelta(days=3)).strftime('%Y-%m-%d %H:%M:%S')

# Config Variables 
with open('config.json') as config_file:
    configVar = json.load(config_file)

ClientServer = configVar['client_server']
ClientDB = configVar['client_db']
ClientDBUserName = configVar['client_db_username']
ClientDBPass = configVar['client_db_password']
Client_table_name1 = configVar['client_table_name1']
Client_table_name2 = configVar['client_table_name2']
driver = configVar['driver']
ClientDBPort = configVar['client_db_port']


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
    # connection_string = f"mssql+pyodbc://{username}:{password}@{server}/{database}?driver=ODBC+Driver+17+for+SQL+Server&Encrypt=yes&TrustServerCertificate=yes" #&Connection+Timeout=30;
    # connection = create_engine(connection_string) 
    connection_string = (
        f"Driver={driver};"
        f"Server=tcp:{ClientServer},{ClientDBPort};"
        f"Database={ClientDB};"
        f"Uid={ClientDBUserName};"
        f"Pwd={ClientDBPass};"
        f"Encrypt=yes;"
        f"TrustServerCertificate=yes;"
        f"Connection Timeout=30;"
    )
    try:
        conn = pyodbc.connect(connection_string)
        print("Connection to client database successful!")
        return conn
    except Exception as e:
        print("Couldnt connect to database: ",e)
        return None

def tableExist(tableName: str, dbName: str = 'EdgeDB.db') -> bool:
    """
    Check if a table exists in the SQLite database.
    Args:
        tableName (str): The name of the table to check.
        dbName (str): The name of the SQLite database file.
    Returns:
        bool: True if the table exists, False otherwise.
    """
    conn = sqlite3.connect(dbName)
    c = conn.cursor()
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?;", (tableName,))
    table_exists = c.fetchone() is not None
    conn.close()
    if table_exists:
        return True
    else:
        return False
    
def fetchFromClientDB(tab1, tab2):
    """
    Fetch data from client database and return it as a DataFrame.
    If last_update_time is provided, only fetch rows updated after this time.
    """
    server = ClientServer 
    database = ClientDB
    username = ClientDBUserName            
    password = ClientDBPass 
    conn = connectClientDB(server, database, username, password)

    if tableExist('Infra_Utilization'):
        last_update_time = get_last_update_time()
        query = f"""
            SELECT
                {tab1}.LogTimestamp, {tab1}.Hostname, {tab1}.CPUUsage, {tab1}.MemoryUsage, {tab1}.TotalMemory, {tab1}.DiskUsage,
                {tab1}.TotalFreeDiskGB, {tab1}.TotalDiskSpaceGB, {tab1}.DiskLatency, {tab1}.ReadLatency,
                {tab1}.WriteLatency, {tab1}.NetworkTrafficAggregate, {tab1}.NetworkTrafficSent,
                {tab1}.NetworkTrafficReceived,  {tab1}.IPAddress, {tab1}.OperatingSystem,
                {tab1}.OS, {tab1}.DriveLetter,
                {tab2}.ManagementZone, {tab2}.DataCenter, {tab2}.DatacenterRegion, {tab2}.ApplicationName,
                {tab2}.ApplicationOwner, {tab2}.vendor, {tab2}.userIP, {tab2}.CreatedAt, {tab2}.CreatedBy
            FROM {tab1}
            LEFT JOIN {tab2}
            ON {tab2}.hostname = {tab1}.Hostname 
            where {tab1}.LogTimestamp > '{last_update_time}'
        """
        print(f"Fetching data from {tab1} and {tab2} updated after {last_update_time}")
    else:  # Fetch all data on the first run
        query = f"""
            SELECT 
                {tab1}.LogTimestamp, {tab1}.Hostname, {tab1}.CPUUsage, {tab1}.MemoryUsage, {tab1}.TotalMemory, {tab1}.DiskUsage,
                {tab1}.TotalFreeDiskGB, {tab1}.TotalDiskSpaceGB, {tab1}.DiskLatency, {tab1}.ReadLatency,
                {tab1}.WriteLatency, {tab1}.NetworkTrafficAggregate, {tab1}.NetworkTrafficSent,
                {tab1}.NetworkTrafficReceived,  {tab1}.IPAddress, {tab1}.OperatingSystem,
                {tab1}.OS, {tab1}.DriveLetter,
                {tab2}.ManagementZone, {tab2}.DataCenter, {tab2}.DatacenterRegion, {tab2}.ApplicationName,
                {tab2}.ApplicationOwner, {tab2}.vendor, {tab2}.userIP, {tab2}.CreatedAt, {tab2}.CreatedBy
            FROM {tab1}
            LEFT JOIN {tab2}
            ON {tab2}.hostname = {tab1}.Hostname 
            WHERE {tab1}.LogTimestamp >= '{three_days_ago_str}'
        """
        print(f"Fetching all data from {tab1} and {tab2}")
    try:
        return pd.read_sql(query, conn)
    except Exception as e:
        print(f"Error occurred while fetching data from client database: {e}")
        return pd.DataFrame()


def saveToSQLite(data: pd.DataFrame):
    """
    Save a DataFrame to an SQLite database.

    This function appends new rows from the provided DataFrame to the 
    'Infra_Utilization' table in the SQLite database. If the table does 
    not exist, it will be created. Additionally, the function retrieves 
    the maximum timestamp from the 'LogTimestamp' column of the 
    'Infra_Utilization' table and stores it in a 'latestTime' table to 
    keep track of the last update time.

    Parameters:
    data (pd.DataFrame): The DataFrame containing the data to be saved. 
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
    with sqlite3.connect('EdgeDB.db') as conn:
        c = conn.cursor()  
        try:
            if data is not None:
                # If the table doesn't exist, create it. if it exists, append new rows to it
                data.to_sql('Infra_Utilization', conn, if_exists='append', index=False) 
                saveLastUpdateTime()
                del data
            else:
                print('Couldnt save empty data to SQLite')
                pass
        except Exception as e:
            print(f"Error occurred while saving to SQLite: {e}")
        gc.collect()
            
def saveLastUpdateTime():
    """
    Saves the last update time to 'latestTime' table in the sqliteDB
    Returns:
        None: It doesnt return any value. All it does is save latest time to the database 
    """
    with sqlite3.connect('EdgeDB.db') as conn:
        c = conn.cursor()
        c.execute("SELECT MAX(LogTimestamp) FROM Infra_Utilization")  # Get the latest timestamp from the Logtimestamp column   
        lastUpdate = c.fetchone()

        # Create a table to store the lastUpdate time
        c.execute("""CREATE TABLE IF NOT EXISTS latestLogTime (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                last_update_time TEXT)
            """)
        c.execute("INSERT INTO latestLogTime (last_update_time) VALUES (?)", (lastUpdate[0],))
        conn.commit()
        del lastUpdate


def get_last_update_time() -> str:
    """Get the last update time from the SQLite database.
    Returns:
        lastUpdateTime: The latest time in a SQL table and outputs the time in 'YYYY-MM-DD HH:MM:SS' format.
    """    
    with  sqlite3.connect('EdgeDB.db') as conn:
        c = conn.cursor()
        c.execute("SELECT last_update_time FROM latestLogTime ORDER BY id DESC LIMIT 1")    
        lastUpdate = c.fetchone()
        return lastUpdate[0] if lastUpdate is not None else None


# def main():
#     print("Starting main function...")
#     data = fetchFromClientDB(Client_table_name)
#     print("Data fetched from client DB.")
#     saveToSQLite(data)
#     print("Data saved to SQLite.")

# if __name__ == '__main__':
#     main()