from datetime import datetime
from streamlit import session_state as ss
import streamlit as st
import sqlite3
import pandas as pd 
import numpy as np 
import warnings 
warnings.filterwarnings('ignore')

# ------------------------# trying to update the nametag 
def lodgeToDB(tag: str, url: str, datetime, authNeeded) -> None:
    with sqlite3.connect('SyntheticDB') as conn:
        c = conn.cursor()
        c.execute("""CREATE TABLE IF NOT EXISTS oneLinkMonitor(
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  registeredTags TEXT,
                  registeredURL TEXT,
                  dateRegistered TEXT,
                  authKeysNeeded TEXT
                  )""")
        c.execute("INSERT INTO oneLinkMonitor (registeredTags, registeredURL, dateRegistered, authKeysNeeded) VALUES (?,?,?,?)", (tag, url, datetime, authNeeded))

def fetchFromDB() -> pd.DataFrame:
    conn = sqlite3.connect('SyntheticDB')
    df = pd.read_sql_query('SELECT * FROM oneLinkMonitor', conn)
    conn.close()
    return df

def addNameTag(): # Update name tag list 
    # if ss.newNameTag:
    if ss.newNameTag not in ss.nameTagList:
            ss.nameTagList.append(ss.newNameTag)
            ss.nameTagSet = list(set([i for i in ss.nameTagList if len(i) > 2]))
    else:
        pass
    # return ss.nameTagList

def updateDB(url, tag, date, authNeed) -> None: # Update URL list
    if ss.newURL:
        if ss.newURL not in ss.urlList:
            lodgeToDB(tag, url, date, authNeed)
        else:
            pass 

def buttonClick() -> bool:
    return True

def updateSelectedURL():
    return ss.chosenURL

def updateSelectedTag():
    return ss.chosenTag

@st.dialog('You have an error')
def dialoguebox(message):
    return st.write(message)

def updateShowURLPart():
    ss.show = True