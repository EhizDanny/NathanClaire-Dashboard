import streamlit as st 
from streamlit_extras.stylable_container import stylable_container
from streamlit_option_menu import option_menu
import datetime
from datetime import datetime, timedelta
import threading
import time
import os
import schedule, subprocess
import queue
from alerting import format_and_send_alert_email, emailAlert
from streamlit_autorefresh import st_autorefresh
import shelve
import signal
import atexit # defines  an exit function once interpreter stops
import gc # Garbage collector
from memory_profiler import profile
import tracemalloc
import objgraph

st.set_page_config(
    page_title = 'InfraObservatory', 
    page_icon = ':bar_chart:',
    layout = 'wide'
)


st.markdown("""
    <style>
        .reportview-container {
            margin-top: -2em;
        }
        #MainMenu {visibility: hidden;}
        .stDeployButton {display:none;}
        footer {visibility: hidden;}
        #stDecoration {display:none;}
    </style>
""", unsafe_allow_html=True)

# @st.cache_resource
def importLibraries():
    import plotly.express as px 
    import plotly.graph_objects as go 
    import sqlite3 
    import pathlib 
    from streamlit.components.v1 import html 
    import streamlit_antd_components as antd 
    import streamlit_shadcn_ui as shad 
    import pandas as pd        
    import numpy as np 
    import json 
    import warnings 
    warnings.filterwarnings('ignore') 
    from calculations import InfraCalculate as inf 
    # import dash_daq as daq
    # from connection import connectClientDB, fetchFromClientDB, saveToSQLite, get_last_update_time
    return go, px, sqlite3, pathlib, html, antd, pd, np,  json, warnings, inf, shad 
go,  px, sqlite3, pathlib, html, antd, pd, np, json, warnings, inf, shad = importLibraries() 

# st_autorefresh(interval=2 * 60 * 1000, key="interfaceRefresher")   # Refresh the dataframe every 3 minute 

# Sentinel value to indicate an error
ERROR_SENTINEL = "ERROR_FETCHING_DATA"

# tracemalloc.start()

# import full data on a seperate thread
# @st.cache_data(ttl=60)  # Cache for only 2 minutes (160 seconds)
# def fetch_data():
#     try:
#         if os.path.isfile('workingData.parquet') and os.path.getsize('workingData.parquet') > 0:
#             df= pd.read_parquet('workingData.parquet', engine='fastparquet')
#             reduceInt = ['CPUUsage', 'MemoryUsage', 'DiskUsage', 'TotalDiskSpaceGB', 'TotalFreeDiskGB', 'TotalMemory', 'DiskLatency', 'ReadLatency', 'WriteLatency']
#             df[reduceInt] = df[reduceInt].apply(pd.to_numeric, downcast='integer') # reduce to the barest int memory scale
#             turnToCategory = [ 'NetworkTrafficReceived', 'NetworkTrafficSent', 'NetworkTrafficAggregate']
#             df[turnToCategory] = df[turnToCategory].astype('category') # turn large numbers to categories
#             return df
#         else:
#             conn = sqlite3.connect('EdgeDB.db')
#             query = "SELECT * FROM Infra_Utilization;"
#             dataset = pd.read_sql_query(query, conn)
#             conn.close()
#             return dataset
#     except Exception as e:
#         st.error(f"Error fetching data: {e}")
#         return pd.DataFrame()  # Return an empty DataFrame on error
#     finally:
#         gc.collect()

def fetchData():
    if 'fullData' in globals():
        del fullData
    with sqlite3.connect('EdgeDB.db') as conn:
        cursor = conn.cursor()
        query = "SELECT * from Infra_Utilization;"
        return pd.read_sql_query(query, conn)
    
# get the full data
fullData = fetchData()

# Config Variables 
@st.cache_resource()
def getConfig():
    with open('config.json') as config_file:
        configVar = json.load(config_file)
    return configVar
configVar = getConfig()
clientServer = configVar['client_server']
clientDB = configVar['client_db']
clientDBUserName = configVar['client_db_username']
clientDBPass = configVar['client_db_password']
client_table_name1 = configVar['client_table_name1']
client_table_name2 = configVar['client_table_name2']

# import bootstrap 
# @st.cache_resource()
# def css_cdn():
#     return  st.markdown('<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet" integrity="sha384-QWTKZyjpPEjISv5WaRU9OFeRpok6YctnYmDr5pNlyT2bRjXh0JMhjY6hW+ALEwIH" crossorigin="anonymous">', unsafe_allow_html=True)
# css_cdn()

#Load css file
# @st.cache_resource()
def load_css(filePath:str):
    with open(filePath) as f:
        st.html(f'<style>{f.read()}</style>')
css_path = pathlib.Path('style.css')
load_css(css_path)

    # Create a sub process that runs the dataRefresh on a seperate resource (updates the data using a seperate resource)
    # Schedules this dataRefresh to take place every 3minutes 
    # then runs the entire sub process and scheduling every 3minutes on a different thread so it doesnt disturb the dashboard 
# Function to run dataRefresh.py
def run_data_refresh():
    """Calls the dataRefresh.py script as a separate process."""
    subprocess.run(["python", "dataRefresh2.py"])
    gc.collect()
    # print(f"Data refresh completed at {time.strftime('%Y-%m-%d %H:%M:%S')}")

def schedule_data_refresh():
    """Schedules the data refresh task to run every 3 minutes."""
    schedule.every(2).minutes.do(run_data_refresh)
    while True:
        schedule.run_pending()
        gc.collect()
        # time.sleep(10)  # Sleep for 2 minutes

# Keep a refresh history db to know if the refresh has been started
def saveRefreshHistory():
    with shelve.open('interfaceRefresh.db') as db:
        db['hasRefreshed'] = True 
def checkRefreshHistory():
    with shelve.open('interfaceRefresh.db') as db:
        return True if 'hasRefreshed' in db else False

if not checkRefreshHistory(): #If the refreshed hasnt been started
    # Start the scheduler in a separate thread
    data_refresh_thread = threading.Thread(target=schedule_data_refresh, daemon=True)
    data_refresh_thread.start()
    st.session_state['data_refresh_thread'] = data_refresh_thread
    saveRefreshHistory()
else:
    pass
 
# Register a function to delete the interface refresh history upon exit of program 
def deleteRefreshHistory():
    if os.path.exists('interfaceRefresh.db'):
        os.remove('interfaceRefresh.db')
    else:
        pass
atexit.register(deleteRefreshHistory)

maxdate = fullData.LogTimestamp.max()
if 'autoDataRefreshHelper' not in st.session_state:
    st.session_state['autoDataRefreshHelper'] = 0
if 'latestLog' not in st.session_state:
    st.session_state['latestlog'] = datetime.now()

# Get the maximum date from the data and use it as the stop date at default
if 'stopDate' not in st.session_state:
    st.session_state['stopDate'] = maxdate
    st.session_state['usageMonitor'] = 0  # monitor the number of times the has been ran.

if 'startDate' not in st.session_state:
    st.session_state['startDate'] = (datetime.strptime(maxdate, "%Y-%m-%d %H:%M:%S") - timedelta(minutes=30)).strftime("%Y-%m-%d %H:%M:%S")  # Start should be set to 2hours before the stop date

if 'startTime' not in st.session_state:
    st.session_state['startTime'] = "00:00:00"  # Default start time

if 'stopTime' not in st.session_state:
    st.session_state['stopTime'] = "23:59:59"  # Default stop time

if 'timeDisplay' not in st.session_state:
    st.session_state['timeDisplay'] = 'RelativeTime' 

color_continuous_scales = [
                        (0.0, "#F93827"),  # Red for 0 to 70
                        (0.7, "#F93827"),  # Red continues until 70
                        (0.7, "#FFF574"),  # Yellow starts at 70
                        (0.85, "#FFF574"), # Yellow continues until 85
                        (0.85, "#00FF9C"), # Green starts at 85
                        (1.0, "#00FF9C")   # Green continues until 100
                    ]

st.session_state.latestlog = inf(fullData).latestLog

# A callback function to update the data when the user selects a new date or time
def updateDateAndTime():
    if st.session_state.datech:
        # Check if the user selected one or both dates
        if len(st.session_state.datech) == 2:
            start_, stop_ = st.session_state.datech
        else:
            # Default stop date to the start date if only one date is selected
            start_ = st.session_state.datech[0]
            stop_ = start_ + timedelta(days=1)  
    if st.session_state.strTime:
        st.session_state['startTime'] = st.session_state.strTime
    if  st.session_state.stpTime:   
        st.session_state['stopTime'] = st.session_state.stpTime
    st.session_state['startDate'] = f"{start_} {st.session_state['startTime']}"
    st.session_state['stopDate'] = f"{stop_} {st.session_state['stopTime']}"
    st.session_state['autoDataRefreshHelper'] += 1

# Navigation Bar Top 
head1, head2, head3 = st.columns([1, 4, 1])
with head2:
    head2.markdown("""
    <div class="heading">
            <p style=" font-size: 2.7rem; font-weight: bold; color: white; text-align: center; font-family: "Source Sans Pro", sans-serif">Infrastructure Monitoring System</p>
    </div>""", unsafe_allow_html=True)

# antd.divider(label='HOME', icon='house', align='center', color='gray')

tab1, tab2 = st.tabs(["📈 Infrastructure Metrics", "🗃 Server Metrics"])
with tab1:
# date and Time Range
    containerOne = tab1.container()
    with containerOne:
        extra, col1, col2, col3, col4, col5, col6, col7, col8 = containerOne.columns([1,0.6, 0.6, 0.6, 0.6, 1, 1, 0.6, 0.6])
        with col2:
            st.warning(f"CPU: {inf(fullData).highCPUUsageCount}")
            # shad.badges([(f"CPU {calc.highCPUUsageCount}", "destructive")], class_name="flex gap-2",)
        with col3:
            st.warning(f"Mem: {inf(fullData).highMemUsageCount}")
            # shad.badges([(f"Mem {calc.highMemUsageCount}", "destructive")], class_name="flex gap-2",)
        with col4:
            st.warning(f"Disk: {inf(fullData).highDiskUsageCount}")
            # shad.badges([(f"Disk {calc.highDiskUsageCount}", "destructive")], class_name="flex gap-2",)

        twoDaysAwayFromFulldataMinDate = pd.to_datetime(fullData.LogTimestamp.min()).strftime('%Y-%m-%d')

        with col7:
            st.number_input(label='Select Time Range', min_value=1, max_value=60, step=1, key='timeRange', help='Select the range of time you want view data for. This is only applicable when you select Relative Time', value = 5)
        with col8:
            st.selectbox(label='Select Time Unit', options=['Minutes', 'Hours', 'Days'], key='timeUnit', help='Select the unit of time for the range you selected. This is only applicable when you select Relative Time', index=0)

        # Date and Time set Up -------------------------------------- 
        # with col5:
        #     st.selectbox(label='Time Selection Type', options=['Relative Time', 'Date And Time'], key='timeType', help='Select the type of time range you want to use. Relative Time allows you to select a time range from the current time, while Date and Time allows you to select a specific time range', index=0, )
        # if st.session_state.timeType == 'Relative Time':
        #     with col6:
        #         st.number_input(label='Select Time Range', min_value=1, max_value=60, step=1, key='timeRange', help='Select the range of time you want view data for. This is only applicable when you select Relative Time')
        #     with col7:
        #         st.selectbox(label='Select Time Unit', options=['Minutes', 'Hours', 'Days'], key='timeUnit', help='Select the unit of time for the range you selected. This is only applicable when you select Relative Time')
        #     st.session_state['timeDisplay'] = 'RelativeTime'
        # else:
        #     controlDates = col6.date_input(
        #             "Preferred Date Range",
        #             value=(st.session_state['startDate'], st.session_state['stopDate']), min_value= (pd.to_datetime(twoDaysAwayFromFulldataMinDate) - timedelta(days=2)).strftime('%Y-%m-%d')  ,
        #             max_value=fullData.LogTimestamp.max(),
        #             format="YYYY-MM-DD", 
        #             help='Select Start and Stop Date. If you select only start date, the app automatically selects the nextday as the stop date. Endeavour to select the start and stop dates to ensure your intended range is depicted correctly',
        #             on_change=updateDateAndTime, key = 'datech')
        #     starttime = col7.time_input('Start Time', step = 300, help = 'Specify the start time for your selected date range. This time indicates when the data extraction or analysis should begin onthe start date', key = 'strTime', on_change=updateDateAndTime)
        #     stoptime = col8.time_input('Stop Time', step = 300, help = 'Specify the stop time for your selected date range. This time marks when the data extraction or analysis should end on the stop date', key = 'stpTime', on_change=updateDateAndTime)
        #     st.session_state['timeDisplay'] = 'DateAndTime'

    if st.session_state.timeUnit == 'Minutes':
        startdate = (datetime.strptime(maxdate, "%Y-%m-%d %H:%M:%S") - timedelta(minutes=st.session_state.timeRange)).strftime("%Y-%m-%d %H:%M:%S")
        st.session_state['data'] = fullData[fullData.LogTimestamp >= startdate]
        st.session_state.data['HostAndIP'] = st.session_state['data']['Hostname'] + st.session_state['data']['IPAddress'].str.replace('"', '')
    elif st.session_state.timeUnit == 'Hours':
        startdate = (datetime.strptime(maxdate, "%Y-%m-%d %H:%M:%S") - timedelta(hours=st.session_state.timeRange)).strftime("%Y-%m-%d %H:%M:%S")
        st.session_state['data'] = fullData[fullData.LogTimestamp >= startdate]
        st.session_state.data['HostAndIP'] = st.session_state['data']['Hostname'] + st.session_state['data']['IPAddress'].str.replace('"', '')
    elif st.session_state.timeUnit == 'Days':
        startdate = (datetime.strptime(maxdate, "%Y-%m-%d %H:%M:%S") - timedelta(days=st.session_state.timeRange)).strftime("%Y-%m-%d %H:%M:%S")
        st.session_state['data'] = fullData[fullData.LogTimestamp >= startdate]
        st.session_state.data['HostAndIP'] = st.session_state['data']['Hostname'] + st.session_state['data']['IPAddress'].str.replace('"', '')
    else:
        pass

    # st.write(st.session_state['data'].sort_values(ascending = False, by = 'LogTimestamp'))
    if st.session_state['data'].empty:
        st.error('data is empty')
        st.session_state["data_empty"] = True
    else:
        st.session_state["data_empty"] = False

    # save the data in session_state and keep track of the selected server whose information is to be displayed
    if 'filteredData' not in st.session_state:
        st.session_state['filteredData'] = st.session_state['data'].copy(deep = False)
    gc.collect()

    @st.fragment
    def filters():
        #  -------------------------------------------------- Filters Container --------------------------------------------------
        with stylable_container(
                key="container_with_borders",
                css_styles="""{
                        # background: #7474A3;
                        box-shadow: rgba(0, 0, 0, 0.15) 0px 5px 15px 0px;
                        border-radius: 0.3rem;
                        padding-bottom: 5px;
                        margin-top: -10px
                    }"""):
            
            def updateFilter(key, columnName): # Define a callback function to update the data when a filter is selected
                    # if st.session_state[key]:
                    #     if st.session_state[key] != 'Select All':
                    #         st.session_state['filteredData'] = st.session_state['filteredData'][st.session_state['filteredData'][columnName] == st.session_state[key]]
                    #     else:
                    #         st.session_state['filteredData'] = st.session_state['data']
                    # else:  
                    #     pass
                    # Apply each filter dynamically
                    st.session_state['filteredData'] = st.session_state['data']
                    if st.session_state.ao != "Select All":
                        st.session_state['filteredData'] = st.session_state['filteredData'][st.session_state['filteredData']["ApplicationOwner"] == st.session_state.ao]
                    if st.session_state.an != "Select All":
                        st.session_state['filteredData'] = st.session_state['filteredData'][st.session_state['filteredData']["ApplicationName"] == st.session_state.an]
                    if st.session_state.vend != "Select All":
                        st.session_state['filteredData'] = st.session_state['filteredData'][st.session_state['filteredData']["vendor"] == st.session_state.vend]
                    if st.session_state.dc != "Select All":
                        st.session_state['filteredData'] = st.session_state['filteredData'][st.session_state['filteredData']["Datacenter"] == st.session_state.dc]
                    if st.session_state.mz != "Select All":
                        st.session_state['filteredData'] = st.session_state['filteredData'][st.session_state['filteredData']["ManagementZone"] == st.session_state.mz]
                    if st.session_state.oss != "Select All":
                        st.session_state['filteredData'] = st.session_state['filteredData'][st.session_state['filteredData']["OS"] == st.session_state.oss]

            appOwnerOptions = [option for option in st.session_state['filteredData']['ApplicationOwner'].unique().tolist()+['Select All'] if option in st.session_state['filteredData']['ApplicationOwner'].unique().tolist()  or option == 'Select All']
            appNameOptions = [option for option in st.session_state['filteredData']['ApplicationName'].unique().tolist()+['Select All'] if option in st.session_state['filteredData']['ApplicationName'].unique().tolist()  or option == 'Select All']
            vendorOptions = [option for option in st.session_state['filteredData']['vendor'].unique().tolist()+['Select All'] if option in st.session_state['filteredData']['vendor'].unique().tolist()  or option == 'Select All']
            dataCenterOptions = [option for option in st.session_state['filteredData']['DataCenter'].unique().tolist()+['Select All'] if option in st.session_state['filteredData']['DataCenter'].unique().tolist()  or option == 'Select All']
            mgtZoneOptions = [option for option in st.session_state['filteredData']['ManagementZone'].unique().tolist()+['Select All'] if option in st.session_state['filteredData']['ManagementZone'].unique().tolist()  or option == 'Select All']
            osOptions = [option for option in st.session_state['filteredData']['OS'].unique().tolist()+['Select All'] if option in st.session_state['filteredData']['OS'].unique().tolist()  or option == 'Select All']  
                    
            col7, appOwner, appName, vendor, dataCenter, mgtZone, os = st.columns([3, 1.3, 1.3, 1, 1, 1.3, 1.3])
            appOwner.selectbox('Application Owner', appOwnerOptions, index=len(appOwnerOptions)-1, key='ao', on_change=updateFilter, args=('ao', 'ApplicationOwner'))
            appName.selectbox('Application Name', appNameOptions, index=len(appNameOptions)-1, key='an', on_change=updateFilter, args=('an', 'ApplicationName'))
            vendor.selectbox('vendor', vendorOptions, index=len(vendorOptions)-1, key='vend', on_change=updateFilter, args=('vend', 'vendor'))
            dataCenter.selectbox('Data Center', dataCenterOptions, index=len(dataCenterOptions)-1, key='dc', on_change=updateFilter, args=('dc', 'DataCenter'))
            mgtZone.selectbox('Management Zone', mgtZoneOptions, index=len(mgtZoneOptions)-1, key='mz', on_change=updateFilter, args=('mz', 'ManagementZone'))
            os.selectbox('Operating System', osOptions, index=len(osOptions)-1, key='oss', on_change=updateFilter, args=('oss', 'OS'))    

            st.session_state['selectedServer'] = st.session_state['filteredData'].HostAndIP.iloc[0] if not st.session_state['filteredData'].empty else "No servers available"
            # st.session_state['metricData'] = st.session_state['filteredData'].query("HostAndIP == @st.session_state['selectedServer']")

        serverMetrics()


        # ------------------------------------------------------- Server Metrics Container -------------------------------------------------------
    
    @st.fragment
    def serverMetrics(): 
        def updateServerMetrics(): # Callback function to update the server metrics when a new server is selected
            if st.session_state.serverList:
                st.session_state['metricData'] = st.session_state['filteredData'].query("HostAndIP == @st.session_state['serverList']")
        if 'metricData' not in st.session_state:
            st.session_state['metricData'] = st.session_state.filteredData

        containerTwo = st.container()
        with containerTwo:
            col1, col2, col3, col4, col5, col6, col7, col8 = containerTwo.columns([2,1.5,2,1,1,1,1,1])
            with col1:
                col1.markdown(f"""
                        <div class="container metrics text-center" style="border-radius: 0.7rem; height: 4rem; margin-top: -7px; padding-top: 5px; align-items: center; justify-content: space-between; background-color: #0C3245; border-bottom: 1px solid #B3F361;">
                                <p style="font-size: 18px; font-weight: bold; text-align: center; align-items: center;" >Op System</p>
                                <p style="margin-top: -15px; font-size: 14px; color: #B3F361; text-align: center; align-items: center; font-family: Tahoma, Verdana;">{st.session_state.metricData.OS.iloc[0] if 'serverList' in st.session_state else st.session_state['metricData'].query("HostAndIP == @st.session_state['selectedServer']")['OS'].iloc[0] }</p>
                        </div> """, unsafe_allow_html= True)
            with col2:
                col2.markdown(f"""
                        <div class="container metrics text-center" style="border-radius: 0.7rem; height: 4rem; margin-top: -7px; padding-top: 5px; align-items: center; justify-content: space-between; background-color: #0C3245; border-bottom: 1px solid #B3F361;">
                                <p style="font-size: 18px; font-weight: bold; text-align: center; align-items: center;" >Hostname</p>
                                <p style="margin-top: -15px; font-size: 14px; color: #B3F361; text-align: center; align-items: center; font-family: Tahoma, Verdana;">{st.session_state.metricData.HostAndIP.iloc[0] if 'serverList' in st.session_state else st.session_state['metricData'].query("HostAndIP == @st.session_state['selectedServer']")['HostAndIP'].iloc[0]} </p>
                        </div> """, unsafe_allow_html= True)
            with col3:
                col3.markdown(f"""
                        <div class="container metrics text-center" style="border-radius: 0.7rem; height: 4rem; margin-top: -7px; padding-top: 5px; align-items: center; justify-content: space-between; background-color: #0C3245; border-bottom: 1px solid #B3F361;">
                                <p style="font-size: 18px; font-weight: bold; text-align: center; align-items: center;" >IP Address</p>
                                <p style="margin-top: -15px; font-size: 14px; color: #B3F361; text-align: center; align-items: center; font-family: Tahoma, Verdana;">{st.session_state.metricData.IPAddress.iloc[0] if 'serverList' in st.session_state else st.session_state['metricData'].query("HostAndIP == @st.session_state['selectedServer']")['IPAddress'].iloc[0]}</p>
                        </div> """, unsafe_allow_html= True)
            with col4:
                col4.markdown(f"""
                        <div class="container metrics text-center" style="border-radius: 0.7rem; height: 4rem; margin-top: -7px; padding-top: 5px; align-items: center; justify-content: space-between; background-color: #0C3245; border-bottom: 1px solid #B3F361;">
                                <p style="font-size: 18px; font-weight: bold; text-align: center; align-items: center;" >Total Server</p>
                                <p style="margin-top: -15px; font-size: 14px; color: #B3F361; text-align: center; align-items: center; font-family: Tahoma, Verdana;">{inf(fullData).totalServer if inf(fullData).totalServer is not None else "No data available"}</p>
                        </div> """, unsafe_allow_html= True)
            with col5:
                col5.markdown(f"""
                        <div class="container metrics text-center" style="border-radius: 0.7rem; height: 4rem; margin-top: -7px; padding-top: 5px; align-items: center; justify-content: space-between; background-color: #0C3245; border-bottom: 1px solid #B3F361;">
                                <p style="font-size: 18px; font-weight: bold; text-align: center; align-items: center;" >Active Server</p>
                                <p style="margin-top: -15px; font-size: 14px; color: #B3F361; text-align: center; align-items: center; font-family: Tahoma, Verdana;">{len(st.session_state.data[st.session_state.data.LogTimestamp >=pd.to_datetime(st.session_state.data.LogTimestamp) - timedelta(minutes= 2)].Hostname.unique())}</p>
                        </div> """, unsafe_allow_html= True)
            with col6:
                col6.markdown(f"""
                        <div class="container metrics text-center" style="border-radius: 0.7rem; height: 4rem; margin-top: -7px; padding-top: 5px; align-items: center; justify-content: space-between; background-color: #0C3245; border-bottom: 1px solid #B3F361;">
                                <p style="font-size: 18px; font-weight: bold; text-align: center; align-items: center;" >App Name</p>
                                <p style="margin-top: -15px; font-size: 14px; color: #B3F361; text-align: center; align-items: center; font-family: Tahoma, Verdana;">{st.session_state.metricData.ApplicationName.iloc[0] if 'serverList' in st.session_state else st.session_state['metricData'].query("HostAndIP == @st.session_state['selectedServer']")['ApplicationName'].iloc[0]}</p>
                        </div> """, unsafe_allow_html= True)
            with col7:
                col7.markdown(f"""
                        <div class="container metrics text-center" style="border-radius: 0.7rem; height: 4rem; margin-top: -7px; padding-top: 5px; align-items: center; justify-content: space-between; background-color: #0C3245; border-bottom: 1px solid #B3F361;">
                                <p style="font-size: 18px; font-weight: bold; text-align: center; align-items: center;" >App Owner</p>
                                <p style="margin-top: -15px; font-size: 14px; color: #B3F361; text-align: center; align-items: center; font-family: Tahoma, Verdana;">{st.session_state.metricData.ApplicationOwner.iloc[0] if 'serverList' in st.session_state else st.session_state['metricData'].query("HostAndIP == @st.session_state['selectedServer']")['ApplicationOwner'].iloc[0]}</p>
                        </div> """, unsafe_allow_html= True)
            with col8:
                col8.markdown(f"""
                        <div class="container metrics text-center" style="border-radius: 0.7rem; height: 4rem; margin-top: -7px; padding-top: 5px; align-items: center; justify-content: space-between; background-color: #0C3245; border-bottom: 1px solid #B3F361;">
                                <p style="font-size: 18px; font-weight: bold; text-align: center; align-items: center;" >vendor</p>
                                <p style="margin-top: -15px; font-size: 14px; color: #B3F361; text-align: center; align-items: center; font-family: Tahoma, Verdana;">{st.session_state.metricData.vendor.iloc[0] if 'serverList' in st.session_state else st.session_state['metricData'].query("HostAndIP == @st.session_state['selectedServer']")['vendor'].iloc[0]}</p>
                        </div> """, unsafe_allow_html= True)


            containerTwo.markdown('<br>', unsafe_allow_html=True)
        antd.divider(label='Infrastructure Analysis', icon='house', align='center', color='gray')

        # VISUALS 
        with stylable_container(
                    key="visual_container20",
                    css_styles="""{
                    background: #1F2D2D;
                                # border: 1px solid rgba(49, 51, 63, 0.2);
                                # box-shadow: rgba(50, 50, 93, 0.25) 0px 2px 5px -1px, rgba(0, 0, 0, 0.3) 0px 1px 3px -1px;
                                box-shadow: rgba(0, 0, 0, 0.24) 0px 3px 8px;
                                border-radius: 1.5rem;
                                padding: 20px 20px 20px 20px;
                                margin-top: -10px;
                            }"""):
            # Preprocess the Metric data for visuals 
            vizData = st.session_state['metricData'][['LogTimestamp', 'CPUUsage', 'MemoryUsage', 'DiskUsage', 'NetworkTrafficReceived', 'NetworkTrafficSent', 'NetworkTrafficAggregate']]
            vizData['LogTimestamp'] = pd.to_datetime(vizData['LogTimestamp'])
            vizData = vizData.set_index('LogTimestamp')
            # Group using pd.Grouper
            vizData = vizData.groupby(pd.Grouper(freq='1min')).agg({
                'CPUUsage': 'last',
                'MemoryUsage': 'last',
                'DiskUsage': 'last',
                'NetworkTrafficReceived': 'last',
                'NetworkTrafficSent': 'last',
                'NetworkTrafficAggregate': 'last'
            })

            col1, col2, col3, col4 = st.columns([2,5,1,2], border = True)
            with col1:
                col1.selectbox('Server List', st.session_state['filteredData'].HostAndIP.unique().tolist(), key='serverList',  help='Select a server to view its metrics', index = 0, on_change=updateServerMetrics) 
                st.session_state['metricData']['LogTimestamp'] = pd.to_datetime(st.session_state['metricData']['LogTimestamp'])
            with col2:
                netType = col2.selectbox('Network Bound', ['Received and Sent', 'Aggregate'], index = 0, label_visibility = 'collapsed')
                if netType == 'Received and Sent':
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(
                        x=vizData.index, y=vizData['NetworkTrafficReceived'].astype(float), fill='tozeroy', mode='lines', line=dict(color='#00FF9C'), name='Traffic Received'))
                    fig.add_trace(go.Scatter(x=vizData.index, y=vizData['NetworkTrafficSent'].astype(float), fill='tonexty', mode='lines', line=dict(color='#FFF574'),name='Traffic Sent'  ))
                    fig.update_layout(
                        xaxis_title='Time', yaxis_title='InBound and OutBound Network Reception', height=300, margin=dict(l=0, r=0, t=10, b=0))
                    st.plotly_chart(fig, use_container_width=True)

                elif netType == 'Aggregate':
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(x=vizData.index, y=vizData['NetworkTrafficAggregate'].astype(float), fill='tozeroy', mode='lines', line=dict(color='green') ))
                    fig.update_layout(
                        # title=f"CPU Usage In Last {output}",
                        xaxis_title='Time', yaxis_title='Aggregate Network Reception', height=300, margin=dict(l=0,  r=0, t=10, b=0  ))     
                    st.plotly_chart(fig, use_container_width=True)
            with col3:
                calc2 = inf(st.session_state['metricData'])
                col3.metric(label = 'Total Disk Space(GB)', value = round(calc2.currentTotalDisk,1), delta = None, border=True)
                percRemaining = (calc2.currentFreeDisk / calc2.currentTotalDisk) * 100
                col3.metric(label = 'Free Disk(GB)', value = round(calc2.currentDiskAvail, 1), delta =None,  border=True)
                col3.metric(label='Memory(GB)', value = round(calc2.currentTotalMemory, 1), delta = None, border=True)
            with col4:
                fig1 = go.Figure(go.Indicator(
                    mode = "gauge+number+delta",
                    value = calc2.currentCPU,
                    domain = {'x': [0, 1], 'y': [0, 1]},
                    # title = {'text': "Current CPU Load(%)", 'font': {'size': 18}},
                    # delta = {'reference': 400, 'increasing': {'color': "RebeccaPurple"}},
                    gauge = {
                        'axis': {'range': [1, 100], 'tickwidth': 1, 'tickcolor': "darkblue"},
                        'bar': {'color': '#00FF9C' if calc2.currentCPU <= 75 else '#FFF574' if calc2.currentCPU <= 85 else '#F93827'},
                        # 'bgcolor': "white",
                        'borderwidth': 1, 'bordercolor': "white",
                        'steps': [
                            {'range': [0, 70], 'color': '#F0F2F6'},
                            {'range': [70, 85], 'color': '#E7D283'},
                            {'range': [85, 100], 'color': '#FFDBDB'}],
                        'threshold': {
                            'line': {'color': "red", 'width': 1},
                            'thickness': 0.75,
                            'value': 80}}))
                fig1.update_layout(
                    height=115,
                    # paper_bgcolor='lightgray',  
                    paper_bgcolor='rgba(0,0,0,0)',  # Transparent background
                    # plot_bgcolor='cyan',
                    margin=dict(l=0, r=0, t=40, b=10) ,
                    title={'text': "Current CPU Load(%)", 'font': {'size': 12}, 'x': 0.3},) # Remove extra space around the gauge
                col4.plotly_chart(fig1, use_container_width=True)
                
                fig2 = go.Figure(go.Indicator(
                    mode = "gauge+number+delta",
                    value = calc2.currentMemory,
                    domain = {'x': [0, 1], 'y': [0, 1]},
                    # title = {'text': "Current Memory Load(%)", 'font': {'size': 18}},
                    # delta = {'reference': 400, 'increasing': {'color': "RebeccaPurple"}},
                    gauge = {
                        'axis': {'range': [1, 100], 'tickwidth': 1, 'tickcolor': "darkblue"},
                        'bar': {'color': '#00FF9C' if calc2.currentMemory <= 70 else '#FFF574' if calc2.currentMemory <= 85 else '#F93827'},
                        'bgcolor': "gray",
                        'borderwidth': 1,
                        'bordercolor': "white",
                        'steps': [
                            {'range': [0, 70], 'color': '#F0F2F6'},
                            {'range': [70, 85], 'color': '#E7D283'},
                            {'range': [85, 100], 'color': '#FFDBDB'}],
                        'threshold': {
                            'line': {'color': "red", 'width': 1},
                            'thickness': 0.75,
                            'value': 80}}))
                fig2.update_layout(
                    height=115,
                    # paper_bgcolor='lightgray',  
                    paper_bgcolor='rgba(0,0,0,0)',  # Transparent background
                    # plot_bgcolor='cyan',
                    margin=dict(l=0, r=0, t=40, b=10) ,
                    title={'text': "Current Memory Load(%)", 'font': {'size': 12}, 'x': 0.3},) # Remove extra space around the gauge
                col4.plotly_chart(fig2)
                
                fig3 = go.Figure(go.Indicator(
                    mode = "gauge+number+delta",
                    value = calc2.currentDisk,
                    domain = {'x': [0, 1], 'y': [0, 1]},
                    # title = {'text': "Current Disk Load(%)", 'font': {'size': 18}},
                    # delta = {'reference': 400, 'increasing': {'color': "RebeccaPurple"}},
                    gauge = {
                        'axis': {'range': [1, 100], 'tickwidth': 1, 'tickcolor': "darkblue"},
                        'bar': {'color': '#00FF9C' if calc2.currentDisk <= 75 else '#FFF574' if calc2.currentDisk <= 85 else '#F93827'},
                        # 'bgcolor': "white",
                        'borderwidth': 1,
                        'bordercolor': "white",
                        'steps': [
                            {'range': [0, 70], 'color': '#F0F2F6'},
                            {'range': [70, 85], 'color': '#E7D283'},
                            {'range': [85, 100], 'color': '#FFDBDB'}],
                        'threshold': {
                            'line': {'color': "red", 'width': 1},
                            'thickness': 0.75,
                            'value': 80}}))
                fig3.update_layout(
                    height=115,
                    width = 500,
                    # paper_bgcolor='lightgray',  
                    paper_bgcolor='rgba(0,0,0,0)',  # Transparent background
                    # plot_bgcolor='cyan',
                    margin=dict(l=0, r=0, t=40, b=10) ,
                    title={'text': "Current Disk Load(%)", 'font': {'size': 12}, 'x': 0.3},) # Remove extra space around the gauge
                col4.plotly_chart(fig3, use_container_width=True)

        # -------------------------------------------- 2nd row -----------------------------------------------
        # with stylable_container(
        #     key="visual_container2",
        #     css_styles="""{
        #                 # border: 1px solid rgba(49, 51, 63, 0.2);
        #                 box-shadow: rgba(14, 30, 37, 0.12) 0px 2px 4px 0px, rgba(14, 30, 37, 0.32) 0px 2px 16px 0px;
        #                 border-radius: 0.3rem;
        #                 padding: 5px 10px;
        #                 margin-top: -10px;
        #             }"""):
        
        if len(st.session_state['startDate']) == 10 or len(st.session_state['stopDate']) == 10:
            date1 = datetime.strptime(st.session_state['startDate']+' 00:00:00', "%Y-%m-%d %H:%M:%S")
            date2 = datetime.strptime(st.session_state['stopDate']+' 00:00:00', "%Y-%m-%d %H:%M:%S")
        else:
            date1 = datetime.strptime(st.session_state['startDate'], "%Y-%m-%d %H:%M:%S")
            date2 = datetime.strptime(st.session_state['stopDate'], "%Y-%m-%d %H:%M:%S")
        difference = date2 - date1
        days = difference.days
        hours = difference.seconds//3600
        if days > 0 and hours > 0:
            output = f"{days} days and {hours} hours"
        elif days > 0 and hours == 0:
            output = f"{days} days"
        else:
            output = f"{hours} hours"

        # if isinstance(st.session_state['startDate'], pd.Timestamp) and isinstance(st.session_state['stopDate'], pd.Timestamp):  
        #     # Convert Timestamps to strings  
        #     start_date_str = st.session_state['startDate'].strftime('%Y-%m-%d')  
        #     stop_date_str = st.session_state['stopDate'].strftime('%Y-%m-%d')  
            
        #     # Now you can check the length of the formatted strings  
        #     if len(start_date_str) == 10 and len(stop_date_str) == 10:   
        #         # Create datetime objects directly from the Timestamps  
        #         date1 = st.session_state['startDate'].to_pydatetime()  # Convert to Python datetime  
        #         date2 = st.session_state['stopDate'].to_pydatetime()    # Convert to Python datetime  
        #     else:  
        #         # This else block may not be needed if you're only working with Timestamps  
        #         date1 = datetime.strptime(start_date_str, "%Y-%m-%d")  # Use the string representation  
        #         date2 = datetime.strptime(stop_date_str, "%Y-%m-%d")    # Use the string representation  

        #     # Calculate the difference  
        #     difference = date2 - date1  
        #     days = difference.days  
        #     hours = difference.seconds // 3600  

        #     # Prepare the output based on the difference  
        #     if days > 0 and hours > 0:  
        #         output = f"{days} days and {hours} hours"  
        #     elif days > 0 and hours == 0:  
        #         output = f"{days} days"  
        #     else:  
        #         output = f"{hours} hours"  
            

        col1, col2, col3 = st.columns([1,1,1], border = False)
        # Define thresholds and colors
        thresholds = [0, 70, 85, 100]
        colours = ['#00FF9C', '#FFF574', '#F93827']
        threshold_labels = ['0 - 70', '70 - 85', '85+']
        with col1:
            with stylable_container(
                    key="visual_container21",
                    css_styles="""{
                                # border: 1px solid rgba(49, 51, 63, 0.2);
                                box-shadow: rgba(50, 50, 93, 0.25) 0px 2px 5px -1px, rgba(0, 0, 0, 0.3) 0px 1px 3px -1px;
                                border-radius: 1.5rem;
                                padding: 5px 10px;
                                margin-top: 10px;
                                # background: #1F2D2D;
                            }"""):
                    # fig = go.Figure()
                    # fig.add_trace(go.Scatter(x=vizData.index, y=vizData['CPUUsage'], fill='tozeroy', mode='lines', connectgaps=False, line=dict(color='green') ))
                    # fig.update_layout(
                    #     title=f"CPU Usage In Last {output}",
                    #     xaxis_title='Time', yaxis_title='Percentage Usage', height=300, margin=dict(l=0,  r=30, t=40, b=10  ))     
                    # st.plotly_chart(fig, use_container_width=True)
                    fig = go.Figure()
                    if not st.session_state.data.empty:
                        for i in range(len(thresholds) - 1):
                            fig.add_trace(go.Scatter(
                                x=[vizData.index[0], vizData.index[-1], vizData.index[-1], vizData.index[0]],
                                y=[thresholds[i], thresholds[i], thresholds[i + 1], thresholds[i + 1]],
                                fill='toself',  # Fill the area
                                fillcolor=colours[i],
                                line=dict(color='rgba(255,255,255,0)'),  # Transparent line
                            ))
                        # Add the line plot after the filled areas
                        fig.add_trace(go.Scatter(x=vizData.index, y=vizData['CPUUsage'], mode='lines', connectgaps=True, line=dict(color='blue', width=2)))
                        fig.update_layout(
                            showlegend=False,
                            title={'text': f"CPU Usage In Last {st.session_state.timeRange} {st.session_state.timeUnit}", 'x': 0.3},
                            yaxis=dict(range=[-10, 100]),  # Adjust Y-axis limits based on your thresholds
                            xaxis_title = None, yaxis_title = None, height = 350, margin=dict(l=0,  r=0, t=40, b=10  ))
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        None
                    
        with col2:
            with stylable_container(
                    key="visual_container21",
                    css_styles="""{
                                # border: 1px solid rgba(49, 51, 63, 0.2);
                                box-shadow: rgba(50, 50, 93, 0.25) 0px 2px 5px -1px, rgba(0, 0, 0, 0.3) 0px 1px 3px -1px;
                                # border-radius: 0.3rem;
                                padding: 5px 10px;
                                margin-top: 10px;
                            }"""):
                    fig = go.Figure()
                    if not st.session_state.data.empty:
                        for i in range(len(thresholds) - 1):
                            fig.add_trace(go.Scatter(
                                x=[vizData.index[0], vizData.index[-1], vizData.index[-1], vizData.index[0]],
                                y=[thresholds[i], thresholds[i], thresholds[i + 1], thresholds[i + 1]],
                                fill='toself',  # Fill the area
                                fillcolor=colours[i],
                                line=dict(color='rgba(255,255,255,0)'),  # Transparent line
                            ))
                        # Add the line plot after the filled areas
                        fig.add_trace(go.Scatter(x=vizData.index, y=vizData['MemoryUsage'], mode='lines', connectgaps=True, line=dict(color='blue', width=2)))
                        fig.update_layout(
                            showlegend=False,
                            title={'text': f"Memory Usage In Last {st.session_state.timeRange} {st.session_state.timeUnit}", 'x': 0.3},
                            yaxis=dict(range=[-10, 100]),  # Adjust Y-axis limits based on your thresholds
                            xaxis_title = None, yaxis_title = None, height = 350, margin=dict(l=0,  r=0, t=40, b=10  ))
                        st.plotly_chart(fig, use_container_width=True)  
                    else:
                        None
        with col3:
            with stylable_container(
                    key="visual_container21",
                    css_styles="""{
                                # border: 1px solid rgba(49, 51, 63, 0.2);
                                box-shadow: rgba(50, 50, 93, 0.25) 0px 2px 5px -1px, rgba(0, 0, 0, 0.3) 0px 1px 3px -1px;
                                # border-radius: 0.3rem;
                                padding: 5px 10px;
                                margin-top: 10px;
                            }"""):
                    fig = go.Figure()
                    if not st.session_state.data.empty:
                        for i in range(len(thresholds) - 1):
                            fig.add_trace(go.Scatter(
                                x=[vizData.index[0], vizData.index[-1], vizData.index[-1], vizData.index[0]],
                                y=[thresholds[i], thresholds[i], thresholds[i + 1], thresholds[i + 1]],
                                fill='toself',  # Fill the area
                                fillcolor=colours[i],
                                line=dict(color='rgba(255,255,255,0)'),  # Transparent line
                            ))
                        # Add the line plot after the filled areas
                        fig.add_trace(go.Scatter(x=vizData.index, y=vizData['DiskUsage'], mode='lines', connectgaps=True, line=dict(color='blue', width=2)))
                        fig.update_layout(
                            showlegend=False,
                            title={'text': f"Disk Usage In Last {st.session_state.timeRange} {st.session_state.timeUnit}", 'x': 0.3},
                            yaxis=dict(range=[-10, 100]),  # Adjust Y-axis limits based on your thresholds
                            xaxis_title = None, yaxis_title = None, height = 350, margin=dict(l=0,  r=0, t=40, b=10  ))
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        None

    filters()
        # -------------------------------------------- 3rd row -----------------------------------------------

    @st.fragment
    def pivotTable24hrs(value):
            usageData = fullData[['LogTimestamp', 'Hostname', 'IPAddress',  'CPUUsage', 'DiskUsage', 'MemoryUsage', 'NetworkTrafficReceived', 'NetworkTrafficSent', 'NetworkTrafficAggregate']].copy()
            usageData['HostAndIP'] = usageData['Hostname'] + usageData['IPAddress']
            usageData['LogTimestamp'] = pd.to_datetime(usageData['LogTimestamp'])
            # startTime = str(usageData.LogTimestamp.max() - timedelta(hours=24))
            start_time = usageData['LogTimestamp'].max() - timedelta(hours=24)
            usageData = usageData[usageData['LogTimestamp'] >= start_time]
            
            usageData.set_index('LogTimestamp', inplace = True)
            usageData = usageData[['HostAndIP', 'CPUUsage', 'DiskUsage', 'MemoryUsage', 'NetworkTrafficReceived', 'NetworkTrafficSent', 'NetworkTrafficAggregate']]

            usageData = usageData.groupby('HostAndIP').resample('h').agg({'CPUUsage': 'mean', 'DiskUsage': 'mean', 'MemoryUsage': 'mean', 'NetworkTrafficReceived': 'last', 'NetworkTrafficSent': 'last', 'NetworkTrafficAggregate': 'last'})
            usageData.reset_index(inplace = True)
            usageData['hour'] = usageData['LogTimestamp'].dt.strftime('%Y-%m-%d %H:00')
            # usageData =  pd.pivot_table(usageData, index = 'HostAndIP', columns = 'hour', values = 'CPUUsage').fillna(0).applymap(lambda x: f"{x:.2f}".rstrip('0').rstrip('.'))
            if st.session_state['data_empty'] == False:
                usageData =  pd.pivot_table(usageData, index = 'HostAndIP', columns = 'hour', values = value).fillna(0).applymap(lambda x: round(x, 2))
            else:
                return None
            result= st.write(usageData.style.background_gradient(cmap='Reds', axis=0))
            del usageData
            gc.collect()
            return result
    
    @st.fragment
    def miniHeatMap():
        with stylable_container(
                    key="visual_container30",
                    css_styles="""{
                                # border: 1px solid rgba(49, 51, 63, 0.2);
                                # box-shadow: rgba(50, 50, 93, 0.25) 0px 2px 5px -1px, rgba(0, 0, 0, 0.3) 0px 1px 3px -1px;
                                box-shadow: rgba(0, 0, 0, 0.24) 0px 3px 8px;
                                border-radius: 1.5rem;
                                padding: 20px 20px 20px 20px;
                                margin-top: 10px;
                                background: #1F2D2D;
                            }"""):
            with st.container(height = 550, border=False):
                col1, col2 = st.columns([5,1.8], border = True)
                with col1:
                    col11, col22 = col1.columns([1, 5])
                    with col11:
                        options = ['CPUUsage', 'DiskUsage', 'MemoryUsage', 'NetworkTrafficReceived', 'NetworkTrafficSent', 'NetworkTrafficAggregate']
                        col11.selectbox('Metric Selector', options, key='metricTableValue',  help='View the information of your chosen metric in the last 24hrs', index = 0)
                    with col22:
                        col22.markdown(f"""
                            
                            <div class="container metrics text-center" style="border-radius: 0.7rem; height: 4rem; margin-top: 1px; padding-top: 5px; align-items: center; justify-content: space-between; height:68px; background-color: #0C3245; border-bottom: 1px solid #B3F361;">
                                <p style="font-size: 18px; font-weight: bold; text-align: center;">24Hrs Metric Display Table</p>
                                <p style="margin-top: -15px; font-size: 16px; text-align: center; font-family: Tahoma, Verdana;">
                                    Overview of {st.session_state.metricTableValue} Across All Servers in the Last 24 Hours of Your Selected Timeframe
                                </p>
                            </div>
                            </div> """, unsafe_allow_html= True)
                    pivotTable24hrs(st.session_state.metricTableValue)
    
                twoMinutes = pd.to_datetime(st.session_state['data']['LogTimestamp']) - timedelta(minutes=2)
                heatmapData1 = st.session_state['data'][st.session_state['data']['LogTimestamp'] >= twoMinutes][['HostAndIP', 'DriveLetter', 'CPUUsage', 'DiskUsage', 'MemoryUsage']]
                heatmapData1 = heatmapData1.groupby(['HostAndIP']).agg({
                                                                        'CPUUsage': 'mean',
                                                                        'DiskUsage': 'mean',
                                                                        'MemoryUsage': 'mean',
                                                                    }).reset_index()
                for i in heatmapData1.columns:
                    heatmapData1[i] = heatmapData1[i].replace(0, 1e-6)

                # rename the hostandIP column for fitting into chart 
                heatmapData1['HostAndIP_trunc'] = heatmapData1['HostAndIP'].apply(lambda x: x[:15]+'...' if len(x) > 15 else x)
                with col2:
                    col20, col21 = col2.columns([1, 1])
                    with col20:
                        option1 = col20.selectbox('Metric Selector', ['CPUUsage', 'DiskUsage', 'MemoryUsage'], key='heatmap',  help="Displays a information of active servers' resource consumption. Use the dropdown to select resource of interest", index = 0) 
                    with col21:
                        option2 = col21.selectbox('Select prefered plot type', ['Heatmap', 'Barchart'], index = 0, help='Choose either barchart or heatmap to represent your information')

                    if option1 == 'CPUUsage':
                        # heatmapData1 = heatmapData1.groupby(['HostAndIP'])[['CPUUsage']].mean().reset_index()
                        if option2 == 'Heatmap':             
                            figs = px.treemap(data_frame=heatmapData1,path=['HostAndIP_trunc'], values = heatmapData1['CPUUsage'], color=heatmapData1['CPUUsage'], color_continuous_scale=[(0.0, "#00FF9C"), (0.7, "#FFF574"),(0.85, "#F93827"), (1.0, "#F93827") ], range_color=(0, 100), hover_data={ 'CPUUsage': ':.2f',  'HostAndIP': True,   }, height = 400 )
                        else:
                            figs = px.bar(data_frame=heatmapData1, y='HostAndIP_trunc', x='CPUUsage', color='CPUUsage', text = 'CPUUsage', color_continuous_scale=[(0.0, "#00FF9C"), (0.7, "#FFF574"),(0.85, "#F93827"), (1.0, "#F93827") ], range_color=(0, 100), hover_data={ 'CPUUsage': ':.2f',  'HostAndIP': True,   }, height = 400 )
                            figs.update_traces(textposition='inside')
                            figs.update_layout(
                                yaxis = dict(showgrid = False, showline = False),
                                yaxis_title=None, xaxis_title = None,
                                xaxis = dict(showgrid = True, showline = False, )
                                )                        

                    elif option1 == 'DiskUsage':
                        # heatmapData1 = heatmapData1.groupby(['HostAndIP'])[['DiskUsage']].mean().reset_index()
                        if option2 == 'Heatmap':
                            figs = px.treemap(data_frame=heatmapData1,path=['HostAndIP_trunc'], values = heatmapData1['DiskUsage'], color=heatmapData1['DiskUsage'], color_continuous_scale=[ (0.0, "#00FF9C"), (0.7, "#FFF574"),(0.85, "#F93827"), (1.0, "#F93827") ], range_color=(0, 100) , hover_data={ 'DiskUsage': ':.2f',  'HostAndIP': True }, height = 400)
                        else:
                            figs = px.bar(data_frame=heatmapData1, y='HostAndIP_trunc', x='DiskUsage', color='DiskUsage', text = 'DiskUsage', color_continuous_scale=[(0.0, "#00FF9C"), (0.7, "#FFF574"),(0.85, "#F93827"), (1.0, "#F93827") ], range_color=(0, 100), hover_data={ 'DiskUsage': ':.2f',  'HostAndIP': True,   }, height = 400 ) 
                            figs.update_traces(textposition='inside')
                            figs.update_layout(
                                yaxis = dict(showgrid = False, showline = False),
                                yaxis_title=None, xaxis_title = None,
                                xaxis = dict(showgrid = True, showline = False, )
                                )                        

                    elif option1 == 'MemoryUsage':
                        # heatmapData1 = heatmapData1.groupby(['HostAndIP'])[['MemoryUsage']].mean().reset_index()
                        if option2 == 'Heatmap':
                            figs = px.treemap(data_frame=heatmapData1,path=['HostAndIP_trunc'], values = heatmapData1['MemoryUsage'], color=heatmapData1['MemoryUsage'], color_continuous_scale=[(0.0, "#00FF9C"), (0.7, "#FFF574"),(0.85, "#F93827"), (1.0, "#F93827") ], range_color=(0, 100) , hover_data={ 'MemoryUsage': ':.2f',  'HostAndIP': True}, height = 400)
                        else:
                            figs = px.bar(data_frame=heatmapData1, y='HostAndIP_trunc', x='MemoryUsage', color='MemoryUsage', text = 'MemoryUsage', color_continuous_scale=[(0.0, "#00FF9C"), (0.7, "#FFF574"),(0.85, "#F93827"), (1.0, "#F93827") ], range_color=(0, 100), hover_data={ 'MemoryUsage': ':.2f',  'HostAndIP': True,   }, height = 400 ) 
                            figs.update_traces(textposition='inside')
                            figs.update_layout(
                                yaxis = dict(showgrid = False, showline = False),
                                yaxis_title=None, xaxis_title = None,
                                xaxis = dict(showgrid = True, showline = False, )
                                )
                            

                    # figs.update_traces(
                    #     hovertemplate="<b>Host and IP:</b> %{customdata[1]}<br>"
                    #   "<b>Value:</b> %{color:.2f}%<extra></extra>")
                    figs.update_layout(
                        showlegend=False,
                        margin=dict(l=0, r=0, t=0, b=0),  # Remove margins
                        uniformtext=dict(minsize=10, mode='hide'),  # Manage text size and visibility
                    )
                    figs.update(layout_coloraxis_showscale=False)  # hiding color-bar 
                    col2.plotly_chart(figs, use_container_width=True)
        del heatmapData1
        gc.collect()
    miniHeatMap()


        # -------------------------------------------- 4th row -----------------------------------------------

    @st.fragment
    def heatMap():    
        dataWtihLastValues = (st.session_state['data'].sort_values(by='LogTimestamp').groupby('HostAndIP', as_index=False).last())[['HostAndIP', 'ManagementZone', 'ApplicationName', 'CPUUsage', 'DiskUsage', 'MemoryUsage']]
        # dataWtihLastValues['HostAndIP'] = dataWtihLastValues['HostAndIP'].apply(lambda x: x[:15]+'...' if len(x) > 15 else x)  
        dataWtihLastValues['ManagementZone'].fillna('Unknown', inplace=True)
        dataWtihLastValues['ApplicationName'].fillna('Unknown', inplace=True)

        for i in dataWtihLastValues:
            if dataWtihLastValues[i].dtypes != 'O':
                dataWtihLastValues[i] = dataWtihLastValues[i].replace(0, 1e-6)

        with stylable_container(
                    key="visual_container30",
                    css_styles="""{
                                # border: 1px solid rgba(49, 51, 63, 0.2);
                                # box-shadow: rgba(50, 50, 93, 0.25) 0px 2px 5px -1px, rgba(0, 0, 0, 0.3) 0px 1px 3px -1px;
                                box-shadow: rgba(0, 0, 0, 0.24) 0px 3px 8px;
                                border-radius: 1.5rem;
                                padding: 20px 20px 20px 20px;
                                margin-top: 10px;
                            }"""):    

            with st.container(border = False, height = 500):
                col21, col22 = st.columns([1, 5], border =False)
                with col21:
                    treeSel = col21.selectbox('Select the metric to display', ['Storage Utilization', 'Application CPU Consumption', 'Application Memory Consumption'], key='treeSel', index = 0)
                
                    treemap_titles = [["Storage Utilization", "Visualizing Most Recent Disk Space Distribution Across Servers Classified Under Individual Management Zones (Based On The Selected Timeframe)"],
                        ["Application CPU Consumption", "Insights into the Most Recent CPU Resource Consumption Across Different Servers Classified Under Individual Management Zone"], 
                        ["Application Memory Consumption", "Insights into the Most Recent Memory Resource Consumption Across Different Servers Classified Under Individual Management Zone"]]
            
                    topTitle = treemap_titles[0][0] if treeSel == 'Storage Utilization' else treemap_titles[1][0] if treeSel == 'Application CPU Consumption' else treemap_titles[2][0]
                    bodytitle = treemap_titles[0][1] if treeSel == 'Storage Utilization' else treemap_titles[1][1] if treeSel == 'Application CPU Consumption' else treemap_titles[2][1]

                with col22:
                    col22.markdown(f"""
                        <div class="container metrics text-center" style="border-radius: 0.7rem; height: 4rem; margin-top: 1px; padding-top: 5px; align-items: center; justify-content: space-between; height:68px; background-color: #0C3245; border-bottom: 1px solid #B3F361;">
                            <p style="font-size: 18px; font-weight: bold; text-align: center;">{topTitle}</p>
                            <p style="margin-top: -15px; font-size: 16px; text-align: center; font-family: Tahoma, Verdana;">
                                {bodytitle}
                            </p>
                        </div>
                        </div> """, unsafe_allow_html= True)
          
                if treeSel == 'Storage Utilization':
                        figs = px.treemap(
                            data_frame=dataWtihLastValues, 
                            path=['ManagementZone', 'HostAndIP'],  
                            values=dataWtihLastValues['DiskUsage'],  
                            color=dataWtihLastValues['DiskUsage'],  
                            color_continuous_scale=[(0.0, "#00FF9C"), (0.7, "#FFF574"),(0.85, "#F93827"), (1.0, "#F93827") ],  # Gradient: red -> yellow -> green
                            range_color=(0, 100),  # Dynamic color range
                            hover_data={'DiskUsage': ':.2f', 'HostAndIP': True}, 
                            height=400)
                        figs.update_traces(
                            hovertemplate=
                                        "<b>Host and IP:</b> %{customdata[1]}<br>"
                                        "<b>Percentage UsedSpace:</b> %{color:.2f}<extra></extra>")
                        figs.update_layout(
                            margin=dict(l=0, r=0, t=0, b=0),
                            uniformtext=dict(minsize=13, mode='hide'), )
                        st.plotly_chart(figs, use_container_width=True)      
                elif treeSel == 'Application CPU Consumption':
                        figs = px.treemap(
                            data_frame=dataWtihLastValues, 
                            path=['ManagementZone', 'HostAndIP'],  
                            values=dataWtihLastValues['CPUUsage'],  
                            color=dataWtihLastValues['CPUUsage'],  
                            color_continuous_scale=[(0.0, "#00FF9C"), (0.7, "#FFF574"),(0.85, "#F93827"), (1.0, "#F93827") ],  # Gradient: red -> yellow -> green
                            range_color=(0, 100),  # Dynamic color range
                            hover_data={'CPUUsage': ':.2f', 'HostAndIP': True}, 
                            height=400)
                        figs.update_traces(
                            hovertemplate= 
                                        "<b>Host and IP:</b> %{customdata[1]}<br>"
                                        "<b>Percentage CPUusage:</b> %{color:.2f}<extra></extra>")
                        figs.update_layout(
                            margin=dict(l=0, r=0, t=0, b=0),
                            uniformtext=dict(minsize=13, mode='hide'))
                        st.plotly_chart(figs, use_container_width=True)                            
                elif treeSel == 'Application Memory Consumption':
                        figs = px.treemap(
                            data_frame=dataWtihLastValues, 
                            path=['ManagementZone',  'HostAndIP'],  
                            values=dataWtihLastValues['MemoryUsage'], 
                            color=dataWtihLastValues['MemoryUsage'], 
                            color_continuous_scale=[(0.0, "#00FF9C"), (0.7, "#FFF574"),(0.85, "#F93827"), (1.0, "#F93827") ],  # Gradient: red -> yellow -> green
                            range_color=(0, 100), # Dynamic color range
                            hover_data={'MemoryUsage': ':.2f', 'HostAndIP': True}, 
                            height=400)
                        figs.update_traces(
                            hovertemplate=
                                        "<b>Host and IP:</b> %{customdata[1]}<br>"
                                        "<b>Net Traffic Agg:</b> %{color:.2f}<extra></extra>")
                        figs.update_layout(
                            margin=dict(l=0, r=0, t=0, b=0),
                            uniformtext=dict(minsize=13, mode='hide'), )
                        st.plotly_chart(figs, use_container_width=True)   
        del dataWtihLastValues
        gc.collect()
    heatMap()

    def serviceUptime(
        df: pd.DataFrame, # type: ignore
        expected_log_interval_minutes: int = 1,
        missing_data_threshold_minutes: int = 15,
        hostname_col: str = "Hostname",
        ip_col: str = "IPAddress",
        timestamp_col: str = "LogTimestamp",
    ) -> pd.DataFrame: # type: ignore
        """
        Calculates the service uptime percentage for each server within a given timeframe.

        Args:
            data: DataFrame with server log data.
            expected_log_interval_minutes: Expected time interval between logs (in minutes).
            missing_data_threshold_minutes: Threshold for consecutive missing logs (in minutes).
            hostname_col: Column name for the hostname.
            ip_col: Column name for the IP address.
            timestamp_col: Column name for the timestamp.

        Returns:
            DataFrame with uptime results for each server.
        """
        if df.empty:
            return pd.DataFrame()

        # 1. Prepare Data
        data = df  # Avoid modifying the original DataFrame
        data["HostAndIP"] = data[hostname_col] + data[ip_col]
        data[timestamp_col] = pd.to_datetime(data[timestamp_col])
        start_time = data[timestamp_col].min().floor("H")  # Round down to the nearest hour
        end_time = data[timestamp_col].max().ceil("H")  # Round up to the nearest hour
        all_servers = data["HostAndIP"].unique()

        # 2. Create Hourly Bins: a column of a distinct date and hour from start to end of the dataframe
        hourly_bins = pd.DataFrame(
            pd.date_range(start=start_time, end=end_time, freq="H"), columns=["Hour"]
        )
        hourly_bins["key"] = 0  # temporary key for cross join
        servers_df = pd.DataFrame(all_servers, columns=["HostAndIP"])
        servers_df["key"] = 0  # temporary key for cross join
        # Join the hourly bins and server. Each server in server df will fill in all hours in the hourlybin df. len = serverdf * hourlybins
        all_hours = pd.merge(hourly_bins, servers_df, on="key").drop("key", axis=1) 

        global active_hours
        # 3. Mark Active Hours
        data["Hour"] = data[timestamp_col].dt.floor("H")  # Round down to the nearest hour
        data = data.drop_duplicates(subset=["HostAndIP", "Hour"]) # Remove rows of servers that shows more than once in an hour

        # Active hour is the df showing all servers and corresponding .floor hourly time
        active_hours = data[["HostAndIP", "Hour"]].drop_duplicates() # Dropping duplicates ensure no server shows twice in an hour
        all_hours = pd.merge(all_hours, active_hours, on=["HostAndIP", "Hour"], how="left", indicator=True)
        all_hours["Active"] = all_hours["_merge"] == "both"  # True if the hour is present in active_hours
        all_hours = all_hours.drop(columns = '_merge')

        # 4. Handling Missing Data (basic example, can be improved)
        all_hours["Missing"] = False  # Default is not missing
        for server in all_servers:
            server_data = all_hours.query("HostAndIP == @server")
            server_data = server_data.sort_values(by='Hour')
            
            for index, row in server_data.iterrows():
                current_time = row['Hour']
                if row['Active'] == False:
                    
                    # Check the time of the next row to see if it is a long gap.
                    try:
                        next_time = server_data.loc[index+1]['Hour']
                    except:
                        next_time = current_time
                    time_diff = next_time - current_time
                    if time_diff > timedelta(minutes=missing_data_threshold_minutes) :
                        all_hours.loc[index, "Missing"] = True
                    else:
                        all_hours.loc[index, "Missing"] = False
        
        # 5. Calculate Uptime
        uptime_by_server = (
            all_hours.groupby("HostAndIP")
            .agg(
                total_hours=("Hour", "count"),
                active_hours=("Active", "sum"),
                missing_hours=("Missing", "sum")
            )
            .reset_index()
        )
        uptime_by_server["Uptime(%)"] = round(
            (uptime_by_server["active_hours"] / uptime_by_server["total_hours"]) * 100, 2
        )
        
        uptime_by_server = uptime_by_server.sort_values("Uptime(%)", ascending=False)
        del data, all_servers, hourly_bins, servers_df, all_hours, active_hours
        gc.collect()
        return uptime_by_server
    
    last24 = pd.to_datetime(st.session_state['data']['LogTimestamp'].max()) - timedelta(hours=24)
    serviceUptimeDadta = st.session_state['data'][pd.to_datetime(st.session_state['data'].LogTimestamp) >= last24]
    # serviceUptimeDadta['HostAndIP'] = serviceUptimeDadta['Hostname'] + serviceUptimeDadta['IPAddress']


    @st.fragment
    def displayAndHostAvailability():
        with stylable_container(
                    key="visual_container30",
                    css_styles="""{
                                # border: 1px solid rgba(49, 51, 63, 0.2);
                                # box-shadow: rgba(50, 50, 93, 0.25) 0px 2px 5px -1px, rgba(0, 0, 0, 0.3) 0px 1px 3px -1px;
                                box-shadow: rgba(0, 0, 0, 0.24) 0px 3px 8px;
                                border-radius: 1.5rem;
                                padding: 20px 20px 20px 20px;
                                margin-top: 10px;
                            }"""):    
            with st.container(border = False, height = 550):
                st.markdown("""
                    <div class="container metrics text-center" style="border-radius: 0.8rem; height: 4rem; margin-top: 1px; margin-bottom: 1rem; padding-top: 5px; align-items: center; justify-content: space-between; height:68px; background-color: #0C3245; border-bottom: 1px solid #B3F361; ">
                    <p style="font-size: 18px; font-weight: bold; text-align: center; margin-top: 10px">Overview of Resource Availability and Server Uptime In The Last 24Hours</p>
                    </div>
                    </div> """, unsafe_allow_html= True)
                  
                usageData = fullData.copy()
                usageData['LogTimestamp'] = pd.to_datetime(usageData['LogTimestamp'])
                usageData['HostAndIP'] = usageData['Hostname'] + usageData['IPAddress']
                # last2minutes = pd.to_datetime(usageData['LogTimestamp'].max()) - timedelta(minutes=2)
                # filtered_data = usageData[usageData['LogTimestamp'] >= last2minutes]
                # Create a new DataFrame where each row corresponds to a drive on a server
                quickMetricTable = usageData[['HostAndIP', 'DriveLetter', 'ManagementZone', 
                                                'ApplicationName', 'ApplicationOwner', 'TotalDiskSpaceGB', 
                                                'TotalFreeDiskGB', 'DiskUsage', 'CPUUsage', 'MemoryUsage', 
                                                'DataCenter']]
                # Remove duplicates to ensure a unique row for each server-drive combination
                quickMetricTable = quickMetricTable.drop_duplicates(subset=['HostAndIP', 'DriveLetter'])
                quickMetricTable.rename(columns={
                    'HostAndIP': 'Hostname and IP',
                    'TotalDiskSpaceGB': 'DiskSpace (GB)',
                    'TotalFreeDiskGB': 'DiskAvailable (GB)',
                    'DiskUsage': 'DiskUsed (%)',
                    'CPUUsage': 'CPU Usage (%)',
                    'MemoryUsage': 'Memory Usage (%)',
                    'Datacenter': 'Data Center'
                }, inplace=True)
                quickMetricTable['Last Seen'] = quickMetricTable['Hostname and IP'].map(
                    lambda server: usageData[usageData['HostAndIP'] == server]['LogTimestamp'].max())
                quickMetricTable['Last Seen (Days Ago)'] = quickMetricTable['Hostname and IP'].map(
                    lambda server: (datetime.now() - usageData[usageData['HostAndIP'] == server]['LogTimestamp'].max()).total_seconds() // 86400)
                quickMetricTable['Last Seen (Hours Ago)'] = quickMetricTable['Hostname and IP'].map(
                    lambda server: (datetime.now() - usageData[usageData['HostAndIP'] == server]['LogTimestamp'].max()).total_seconds() // 3600)
                         
                quickMetricTable.set_index('Hostname and IP',  inplace=True)
                #Give duplicate hostnames a suffix of 0 - 1 etc to differentiate it from the latter
                quickMetricTable.index = quickMetricTable.index.to_series().astype(str) + "_" + quickMetricTable.groupby(level=0).cumcount().astype(str)
                st.session_state['quickMetricTable'] = quickMetricTable   

                serviceData= serviceUptime(serviceUptimeDadta)
                serviceData.sort_values(by ='Uptime(%)', ascending=False, inplace=True)
                serviceData.reset_index(inplace = True, drop = True)


                col1, col2, col3 = st.columns([2,1.8,1.3], border=True)
                with col1:
                    col1.write(st.session_state['quickMetricTable'].style.background_gradient(cmap='Blues', axis=0))
                with col2:
                    serviceData2 = serviceData.set_index('HostAndIP')
                    col2.dataframe(serviceData2.style.background_gradient(cmap='Blues', axis=1), use_container_width=True)
                with col3:
                    serviceData['HostAndIP_trunc'] = serviceData['HostAndIP'].apply(lambda x: x[:14]+'...' if len(x) > 14 else x)
                    with col3.container(height=420):
                        figs = px.bar(data_frame=serviceData, y='HostAndIP_trunc', x='Uptime(%)', text = 'Uptime(%)', color='Uptime(%)', color_continuous_scale= color_continuous_scales, range_color=(0, 100), hover_data={ 'Uptime(%)': ':.2f',  'HostAndIP': True,   }, height = 350, title = 'Server Uptime' )   
                        figs.update_traces(textposition='inside' )
                        figs.update_layout(
                            xaxis=dict(
                                title="Uptime(%)",
                                showgrid=True,
                                showline=False,
                            ),
                            yaxis=dict(
                                # title="Host and IP",
                                # tickmode="array",
                                # tickvals=serviceData['HostAndIP'],  # List all servers
                                showgrid=False,
                                showline=False,
                                # automargin=True,
                                # fixedrange=True,  # Allow scrolling
                                # showticklabels=False
                            ),
                            yaxis_title=None, xaxis_title = None,
                            # barmode="group",
                            # yaxis=dict(showticklabels=False),  # Hide y-axis tick labels
                            margin=dict(l=0, r=0, t=40, b=0),  # Remove margins
                            uniformtext=dict(minsize=10)  # Adjust text visibility
                        )   
                        # figs.update_yaxes(
                        #     fixedrange=False,  # Allow scrolling
                        #     showticklabels=True,  # Show tick labels
                        # )            
                        figs.update(layout_coloraxis_showscale=False)  # hiding color-bar 
                        st.plotly_chart(figs, use_container_width=True)                    
        del usageData,  quickMetricTable, st.session_state['quickMetricTable'], serviceData, serviceData2
        gc.collect()
    displayAndHostAvailability()


@st.dialog('Empty Data Alert', width ='small')
def emptinessDataCheck():
    st.session_state["data_empty"] = True
    st.write('No data available. Your start date will be set to the earliest available date on your data')
    st.markdown("<br>", unsafe_allow_html=True)
    st.write('The earliest date')
    # st.rerun()
        
if st.session_state['data'].empty:
    emptinessDataCheck()

# Alerting for high CPU, Memory, and Disk USage. 
# The alerting takes place on only new data, so we create a logic to keep the last row of the data
def saveLastRow():
    with shelve.open('keepLastRow.db') as db:
        db['lastRow'] = len(fullData)
        db['previouslyLoaded'] = True       
def retrieveLastRow():
    with shelve.open('keepLastRow.db') as db:
        return db.get('lastRow', 0), db.get('previouslyLoaded', False)
def deleteKeepLastRow():
    if os.path.exists('keepLastRow.db'):
        os.remove('keepLastRow.db')
    else:
        pass

lastRow, prevLoaded = retrieveLastRow()
if len(fullData) > lastRow and prevLoaded: # If the len(fulldata) is higher than the last row and its been previosuly loaded
    checkData = fullData[lastRow: ] # create new df beginning from the previous last row to the end of the current one
    checkData['HostAndIP'] = checkData['Hostname'] + checkData['IPAddress']
    highCPU = checkData[checkData['CPUUsage'] > 85]
    highMem = checkData[checkData['MemoryUsage'] > 85]
    highDisk = checkData[checkData['TotalFreeDiskGB'] < 10]
    saveLastRow()

    critical = [i for i in highCPU.HostAndIP if i in highMem.HostAndIP and i in highDisk.HostAndIP]

    countCritical = len(critical)
    countHighCPU = len(highCPU)
    countHighMem = len(highMem)
    countHighDisk = len(highDisk)

    highCPUList = [f"{row['HostAndIP']}, Drive({row['DriveLetter']}), MgtZone({row['ManagementZone']}), AppName({row['ApplicationName']}), CPU({row['CPUUsage']}), Datetime({row['LogTimestamp']})" for index, row in highCPU.iterrows()]
    highMemList = [f"{row['HostAndIP']}, Drive({row['DriveLetter']}), MgtZone({row['ManagementZone']}), AppName({row['ApplicationName']}), MemoryUsage({row['MemoryUsage']}), Datetime({row['LogTimestamp']})" for index, row in highMem.iterrows()]
    highDiskList = [f"{row['HostAndIP']}, Drive({row['DriveLetter']}), MgtZone({row['ManagementZone']}), AppName({row['ApplicationName']}), FreeDisk({row['TotalFreeDiskGB']}%), Datetime({row['LogTimestamp']})" for index, row in highDisk.iterrows()]

    if len(highCPUList) > 0 or len(highMemList) > 0 or len(highDiskList) > 0:
        sub, bod = format_and_send_alert_email(highCPUList, highMemList, highDiskList, checkData.LogTimestamp.max())
        emailAlert(['contactehiz@gmail.com', 'jegbogu@ncgafrica.com', 'cochagwu@ncgafrica.com', 'byusuf@ncgafrica.com'], sub, bod)
    del checkData, highCPU, highMem, highDisk, highCPUList, highMemList, highDiskList
else:
    pass

atexit.register(deleteKeepLastRow)

# Creating a rerun and kill process 
def kill_process():
    """Kills the current Python process."""
    st.session_state.process_killed = True
    os.kill(os.getpid(), signal.SIGTERM)  # Send a termination signal
if 'process_killed' not in st.session_state:
    st.session_state['process_killed'] = False

opens, closes = st.columns([1,4])
with opens:
    rerun, stop = opens.columns([1,1])
    with rerun:
        if st.button('Manual App Rerun'):
            st.rerun(scope='app')
    with stop:
        if st.button('Stop App'):
            if os.path.exists('interfaceRefresh.db'):
                os.remove('interfaceRefresh.db')
            kill_process()

    if st.session_state.process_killed:
        st.toast("Stopping app...")
        st.stop()

# st.session_state['usageMonitor'] += 1

with tab1:
    with st.expander(expanded=False, label='View Active DataFrame'):
        st.write(fullData.sort_values(by = 'LogTimestamp', ascending = False).reset_index(drop=True).set_index('Hostname'))

# del fullData


def check_leaks():
    snapshot = tracemalloc.take_snapshot()
    top_stats = snapshot.statistics('lineno')
    st.write("Top memory usage by line:")
    for stat in top_stats[:20]:
        st.write(stat)

if st.button("Check memory snapshot"):
    gc.collect()
    check_leaks()

import ctypes

# # optional deeper cleaning
# ctypes.CDLL("libc.so.6").malloc_trim(0)
# import ctypes
ctypes.windll.kernel32.SetProcessWorkingSetSize(-1, -1)
# if st.button("Who is holding the memory?"):
#     gc.collect()
#     objgraph.show_most_common_types(limit=10)
# gc.collect()
   

# snapshot = tracemalloc.take_snapshot()
# top_stats = snapshot.statistics('lineno')

# print("[ Top 10 Memory Consumers ]")
# for stat in top_stats:
#     print(stat)