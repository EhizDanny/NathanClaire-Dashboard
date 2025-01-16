import streamlit as st 
from streamlit_extras.stylable_container import stylable_container
from streamlit_option_menu import option_menu
st.set_page_config(
    page_title = 'AppMonitor', 
    page_icon = ':bar_chart:',
    layout = 'wide'
)
import datetime
from datetime import datetime, timedelta
import time

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
    import dash_daq as daq
    # from connection import connectClientDB, fetchFromClientDB, saveToSQLite, get_last_update_time
    return go, daq, px, sqlite3, pathlib, html, antd, pd, np,  json, warnings, inf, shad

go, daq, px, sqlite3, pathlib, html, antd, pd, np, json, warnings, inf, shad = importLibraries()

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
client_table_name = configVar['client_table_name']

# import bootstrap 
@st.cache_resource()
def css_cdn():
    return  st.markdown('<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet" integrity="sha384-QWTKZyjpPEjISv5WaRU9OFeRpok6YctnYmDr5pNlyT2bRjXh0JMhjY6hW+ALEwIH" crossorigin="anonymous">', unsafe_allow_html=True)
# css_cdn()

#Load css file
@st.cache_resource()
def load_css(filePath:str):
    with open(filePath) as f:
        st.html(f'<style>{f.read()}</style>')
css_path = pathlib.Path('style.css')
load_css(css_path)

#load data
# Get a start and stop filter date and time for first time loading. Update this date later to tally with users selected date
if 'stopDate' not in st.session_state:
    st.session_state['stopDate'] = datetime.today().date().strftime("%Y-%m-%d")
    st.session_state['usageMonitor'] = 0  # monitor the number of times the has been ran.
if 'startDate' not in st.session_state:
    st.session_state['startDate'] = (datetime.today().date() -timedelta(days=51)).strftime("%Y-%m-%d")
if 'startTime' not in st.session_state:
    st.session_state['startTime'] = datetime.today().time().strftime("%H:%M:%S")
if 'stopTime' not in st.session_state:
    st.session_state['stopTime'] = datetime.today().time().strftime("%H:%M:%S")
if 'autoDataRefreshHelper' not in st.session_state:
    st.session_state['autoDataRefreshHelper'] = 0
if 'latestLog' not in st.session_state:
    st.session_state['latestlog'] = datetime.now()


start_time = time.time()

@st.cache_data
def liveDataHandler(db_path, table_name, start_date, stop_date, autoChanger):
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
    autoChanger
    conn = sqlite3.connect(db_path)
    query = f"""
    SELECT * FROM '{table_name}' 
    WHERE LogTimestamp BETWEEN '{start_date}' AND '{stop_date}';
    """
    dataset = pd.read_sql_query(query, conn)
    dataset.to_parquet('workingData.parquet', engine='fastparquet', index=False)
    conn.close()
    dataset = pd.read_parquet('workingData.parquet', engine='fastparquet')
    return dataset

data = liveDataHandler('EdgeDB 2', 'Infra_Utilization', st.session_state['startDate'], st.session_state['stopDate'],  st.session_state['autoDataRefreshHelper'])
data['HostAndIP'] = data['Hostname'] + data['IPAddress'].str.replace('"', '')

if not data.empty:
    st.session_state["data_empty"] = False
else:
    st.session_state["data_empty"] = True

# def emptinessDataCheck():
#     if not data.empty:
#         st.session_state["data_empty"] = False
#     else:
#         st.session_state["data_empty"] = True
    
#     if st.session_state["data_empty"] == True: # Alert dialog if data is empty
#         dialog_result = shad.alert_dialog(
#             title="No Data Alert",
#             description="There is currently no data within your selected timeframe. Click refresh to have the minimum date range with data loaded.",
#             confirm_label="Refresh",
#             cancel_label="Cancel",
#             key="alert_dialog_1",
#             show=st.session_state["data_empty"]
#         )
#         if dialog_result == "cancel":
#             st.session_state["data_empty"] = False  # Keep the alert visible if no data   
#         elif dialog_result == "refresh":
#             st.session_state["data_empty"] = False
#             st.session_state['startDate'] = (datetime.today().date() -timedelta(days=51)).strftime("%Y-%m-%d")
#             st.session_state['stopDate'] = datetime.today().date().strftime("%Y-%m-%d")
#     if not st.session_state["data_empty"]:
#         # Display the dashboard once the alert has been addressed
#         st.success("Dashboard is loading...")
#         # Add your dashboard rendering logic here
#         st.write("Your dashboard goes here!")
# emptinessDataCheck()


# save the data in session_state and keep track of the selected server whose information is to be displayed
st.session_state['data'] = data.copy()
st.session_state['filteredData'] = st.session_state['data'].copy()

calc = inf(data)
st.session_state.latestlog = calc.latestLog

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


st.sidebar.write(len(data))
end_time = time.time()
dataloading_time = end_time - start_time

start_time = time.time()

# Navigation Bar Top 
head1, head2, head3 = st.columns([1, 2, 1])
with head2:
    head2.markdown(f"""
    <div class="heading">
            <p style="margin-top: 10px; font-size: 17px; font-weight: bold; color: #333; text-align: center; font-family: Geneva, Verdana, helvetica, sans-serif">Infrastructure Monitoring System</p>
    </div>""", unsafe_allow_html=True)


st.sidebar.image('PNG/Red.png')
# antd.divider(label='HOME', icon='house', align='center', color='gray')

tab1, tab2 = st.tabs(["📈 Infrastructure Metrics", "🗃 Server Metrics"])
with tab1:
# date and Time Range
    containerOne = tab1.container()
    with containerOne:
        col1, col2, col3, col4, col5, col6, col7, col8 = containerOne.columns([3, 0.6, 0.6, 0.6, 1, 1, 0.6, 0.6])
        with col2:
            st.error(f"CPU: {calc.highCPUUsageCount}")
            # shad.badges([(f"CPU {calc.highCPUUsageCount}", "destructive")], class_name="flex gap-2",)
        with col3:
            st.error(f"Mem: {calc.highMemUsageCount}")
            # shad.badges([(f"Mem {calc.highMemUsageCount}", "destructive")], class_name="flex gap-2",)
        with col4:
            st.error(f"Disk: {calc.highDiskUsageCount}")
            # shad.badges([(f"Disk {calc.highDiskUsageCount}", "destructive")], class_name="flex gap-2",)

        controlDates = col6.date_input(
            "Preferred Date Range",
            # (pd.to_datetime(data.LogTimestamp).max() - timedelta(weeks=8), pd.to_datetime(data.LogTimestamp).max()),
            value=(st.session_state['startDate'], st.session_state['stopDate']),
            format="YYYY-MM-DD", 
            help='Select Start and Stop Date. If you select only start date, the app automatically selects the nextday as the stop date. Endeavour to select the start and stop dates to ensure your intended range is depicted correctly',
            on_change=updateDateAndTime, key = 'datech') 

        starttime = col7.time_input('Start Time', step = 300, help = 'Specify the start time for your selected date range. This time indicates when the data extraction or analysis should begin on the start date', key = 'strTime', on_change=updateDateAndTime)
        stoptime = col8.time_input('Stop Time', step = 300, help = 'Specify the stop time for your selected date range. This time marks when the data extraction or analysis should end on the stop date', key = 'stpTime', on_change=updateDateAndTime)



    st.sidebar.write(len(st.session_state['data']))   
    @st.fragment
    def filters():
        #  -------------------------------------------------- Filters Container --------------------------------------------------
        with stylable_container(
                key="container_with_borders",
                css_styles="""{
                       
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
                    #         st.session_state['filteredData'] = st.session_state['data'].copy()
                    # else:  
                    #     pass
                    # Apply each filter dynamically
                    st.session_state['filteredData'] = st.session_state['data'].copy()
                    if st.session_state.ao != "Select All":
                        st.session_state['filteredData'] = st.session_state['filteredData'][st.session_state['filteredData']["ApplicationOwner"] == st.session_state.ao]
                    if st.session_state.an != "Select All":
                        st.session_state['filteredData'] = st.session_state['filteredData'][st.session_state['filteredData']["ApplicationName"] == st.session_state.an]
                    if st.session_state.vend != "Select All":
                        st.session_state['filteredData'] = st.session_state['filteredData'][st.session_state['filteredData']["Vendor"] == st.session_state.vend]
                    if st.session_state.dc != "Select All":
                        st.session_state['filteredData'] = st.session_state['filteredData'][st.session_state['filteredData']["Datacenter"] == st.session_state.dc]
                    if st.session_state.mz != "Select All":
                        st.session_state['filteredData'] = st.session_state['filteredData'][st.session_state['filteredData']["ManagementZone"] == st.session_state.mz]
                    if st.session_state.oss != "Select All":
                        st.session_state['filteredData'] = st.session_state['filteredData'][st.session_state['filteredData']["OS"] == st.session_state.oss]

            appOwnerOptions = [option for option in st.session_state['filteredData']['ApplicationOwner'].unique().tolist()+['Select All'] if option in st.session_state['filteredData']['ApplicationOwner'].unique().tolist()  or option == 'Select All']
            appNameOptions = [option for option in st.session_state['filteredData']['ApplicationName'].unique().tolist()+['Select All'] if option in st.session_state['filteredData']['ApplicationName'].unique().tolist()  or option == 'Select All']
            vendorOptions = [option for option in st.session_state['filteredData']['Vendor'].unique().tolist()+['Select All'] if option in st.session_state['filteredData']['Vendor'].unique().tolist()  or option == 'Select All']
            dataCenterOptions = [option for option in st.session_state['filteredData']['Datacenter'].unique().tolist()+['Select All'] if option in st.session_state['filteredData']['Datacenter'].unique().tolist()  or option == 'Select All']
            mgtZoneOptions = [option for option in st.session_state['filteredData']['ManagementZone'].unique().tolist()+['Select All'] if option in st.session_state['filteredData']['ManagementZone'].unique().tolist()  or option == 'Select All']
            osOptions = [option for option in st.session_state['filteredData']['OS'].unique().tolist()+['Select All'] if option in st.session_state['filteredData']['OS'].unique().tolist()  or option == 'Select All']  
                    
            col7, appOwner, appName, vendor, dataCenter, mgtZone, os = st.columns([4, 1.3, 1.3, 1, 1, 1.3, 1.3])
            appOwner.selectbox('Application Owner', appOwnerOptions, index=len(appOwnerOptions)-1, key='ao', on_change=updateFilter, args=('ao', 'ApplicationOwner'))
            appName.selectbox('Application Name', appNameOptions, index=len(appNameOptions)-1, key='an', on_change=updateFilter, args=('an', 'ApplicationName'))
            vendor.selectbox('Vendor', vendorOptions, index=len(vendorOptions)-1, key='vend', on_change=updateFilter, args=('vend', 'Vendor'))
            dataCenter.selectbox('Data Center', dataCenterOptions, index=len(dataCenterOptions)-1, key='dc', on_change=updateFilter, args=('dc', 'Datacenter'))
            mgtZone.selectbox('Management Zone', mgtZoneOptions, index=len(mgtZoneOptions)-1, key='mz', on_change=updateFilter, args=('mz', 'ManagementZone'))
            os.selectbox('OS', osOptions, index=len(osOptions)-1, key='oss', on_change=updateFilter, args=('oss', 'OS'))    
        
            st.session_state['selectedServer'] = st.session_state['filteredData'].HostAndIP.iloc[0] if not st.session_state['filteredData'].empty else "No servers available"
            st.session_state['metricData'] = st.session_state['filteredData'].query("HostAndIP == @st.session_state['selectedServer']")
        serverMetrics()


        # ------------------------------------------------------- Server Metrics Container -------------------------------------------------------
    @st.fragment
    def serverMetrics(): 
        def updateServerMetrics(): # Callback function to update the server metrics when a new server is selected
            if st.session_state.serverList:
                st.session_state['selectedServer'] = st.session_state.serverList
                st.session_state['metricData'] = st.session_state['filteredData'].query("HostAndIP == @st.session_state['selectedServer']")

        containerTwo = st.container()
        with containerTwo:
            col1, col2, col3, col4, col5, col6, col7, col8 = containerTwo.columns([2,1,3,1,1,1,1,1])
            with col1:
                col1.markdown(f"""
                        <div class="container metrics text-center">
                                <p style="font-size: 18px; font-weight: bold; text-align: center; align-items: center;" >Op System</p>
                                <p style="margin-top: -15px; font-size: 14px; text-align: center; align-items: center; font-family: Tahoma, Verdana;">{st.session_state['metricData'].query("HostAndIP == @st.session_state['selectedServer']")['OS'].iloc[0] if not st.session_state['metricData'].empty else "No data available"}</p>
                        </div> """, unsafe_allow_html= True)
            with col2:
                col2.markdown(f"""
                        <div class="container metrics text-center">
                                <p style="font-size: 18px; font-weight: bold; text-align: center; align-items: center;" >Hostname</p>
                                <p style="margin-top: -15px; font-size: 14px; text-align: center; align-items: center; font-family: Tahoma, Verdana;">{st.session_state['metricData'].Hostname.iloc[0] if not st.session_state['metricData'].empty else "No data available"}</p>
                        </div> """, unsafe_allow_html= True)
            with col3:
                col3.markdown(f"""
                        <div class="container metrics text-center">
                                <p style="font-size: 18px; font-weight: bold; text-align: center; align-items: center;" >IP Address</p>
                                <p style="margin-top: -15px; font-size: 14px; text-align: center; align-items: center; font-family: Tahoma, Verdana;">{st.session_state['metricData'].IPAddress.iloc[0] if not st.session_state['metricData'].empty else "No data available"}</p>
                        </div> """, unsafe_allow_html= True)
            with col4:
                col4.markdown(f"""
                        <div class="container metrics text-center">
                                <p style="font-size: 18px; font-weight: bold; text-align: center; align-items: center;" >Total Server</p>
                                <p style="margin-top: -15px; font-size: 14px; text-align: center; align-items: center; font-family: Tahoma, Verdana;">{calc.totalServer if calc.totalServer is not None else "No data available"}</p>
                        </div> """, unsafe_allow_html= True)
            with col5:
                col5.markdown(f"""
                        <div class="container metrics text-center">
                                <p style="font-size: 18px; font-weight: bold; text-align: center; align-items: center;" >Active Server</p>
                                <p style="margin-top: -15px; font-size: 14px; text-align: center; align-items: center; font-family: Tahoma, Verdana;">{len(data.Hostname.unique())}</p>
                        </div> """, unsafe_allow_html= True)
            with col6:
                col6.markdown(f"""
                        <div class="container metrics text-center">
                                <p style="font-size: 18px; font-weight: bold; text-align: center; align-items: center;" >App Name</p>
                                <p style="margin-top: -15px; font-size: 14px; text-align: center; align-items: center; font-family: Tahoma, Verdana;">{st.session_state['metricData'].ApplicationName.iloc[0] if not st.session_state['metricData'].empty else "No data available"}</p>
                        </div> """, unsafe_allow_html= True)
            with col7:
                col7.markdown(f"""
                        <div class="container metrics text-center">
                                <p style="font-size: 18px; font-weight: bold; text-align: center; align-items: center;" >App Owner</p>
                                <p style="margin-top: -15px; font-size: 14px; text-align: center; align-items: center; font-family: Tahoma, Verdana;">{st.session_state['metricData'].ApplicationOwner.iloc[0] if not st.session_state['metricData'].empty else "No data available"}</p>
                        </div> """, unsafe_allow_html= True)
            with col8:
                col8.markdown(f"""
                        <div class="container metrics text-center">
                                <p style="font-size: 18px; font-weight: bold; text-align: center; align-items: center;" >Vendor</p>
                                <p style="margin-top: -15px; font-size: 14px; text-align: center; align-items: center; font-family: Tahoma, Verdana;">{st.session_state['metricData'].Vendor.iloc[0] if not st.session_state['metricData'].empty else "No data available" }</p>
                        </div> """, unsafe_allow_html= True)

            containerTwo.markdown('<br>', unsafe_allow_html=True)
        antd.divider(label='Infrastructure Analysis', icon='house', align='center', color='gray')

        # VISUALS 
        with stylable_container(
                    key="visual_container20",
                    css_styles="""{
                                # border: 1px solid rgba(49, 51, 63, 0.2);
                                # box-shadow: rgba(50, 50, 93, 0.25) 0px 2px 5px -1px, rgba(0, 0, 0, 0.3) 0px 1px 3px -1px;
                                box-shadow: rgba(0, 0, 0, 0.24) 0px 3px 8px;
                                # border-radius: 0.3rem;
                                padding: 20px 20px 20px 20px;
                                margin-top: -10px;
                            }"""):
            # Preprocess the Metric data for visuals 
            vizData = st.session_state['metricData'][['LogTimestamp', 'CPUUsage', 'MemoryUsage', 'DiskUsage', 'NetworkTrafficReceived', 'NetworkTrafficSent', 'NetworkTrafficAggregate']]
            vizData['LogTimestamp'] = pd.to_datetime(vizData['LogTimestamp'])
            # if not vizData.empty:
            #     vizData = vizData.resample('1min', on = 'LogTimestamp').mean()
            # else:
            #     emptiness = True
            #     shad.alert_dialog(show = emptiness, title="No Data Alert", description="There is currently no data between your selected date", confirm_label="Refresh", cancel_label="Cancel", key="alert_dialog_1")
                # st.alert('Data is empty')

            col1, col2, col3, col4 = st.columns([2,5,1,2], border = True)
            with col1:
                col1.selectbox('Server List', st.session_state['filteredData'].HostAndIP.unique().tolist(), key='serverList', on_change=updateServerMetrics, help='Select a server to view its metrics', index = 0) 
                st.session_state['metricData']['LogTimestamp'] = pd.to_datetime(st.session_state['metricData']['LogTimestamp'])
            with col2:
                netType = col2.selectbox('Network Bound', ['Received and Sent', 'Aggregate'], index = 0, label_visibility = 'collapsed')
                if netType == 'Received and Sent':
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(
                        x=vizData.LogTimestamp, y=vizData['NetworkTrafficReceived'], fill='tozeroy', mode='lines', line=dict(color='green'), name='Traffic Received'))
                    fig.add_trace(go.Scatter(x=vizData.index, y=vizData['NetworkTrafficSent'], fill='tonexty', mode='lines', line=dict(color='#FFEB00'),name='Traffic Sent'  ))
                    fig.update_layout(
                        xaxis_title='Time', yaxis_title='InBound and OutBound Network Reception', height=300, margin=dict(l=0, r=0, t=40, b=10))
                    st.plotly_chart(fig, use_container_width=True)

                elif netType == 'Aggregate':
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(x=vizData.LogTimestamp, y=vizData['NetworkTrafficAggregate'], fill='tozeroy', mode='lines', line=dict(color='green') ))
                    fig.update_layout(
                        # title=f"CPU Usage In Last {output}",
                        xaxis_title='Time', yaxis_title='Aggregate Network Reception', height=300, margin=dict(l=0,  r=0, t=40, b=10  ))     
                    st.plotly_chart(fig, use_container_width=True)
            with col3:
                calc2 = inf(st.session_state['metricData'])
                col3.metric(label = 'Disk Space(GB)', value = round(calc2.currentTotalDisk,1), delta = None, border=True)
                percRemaining = 100 - calc2.currentDisk
                col3.metric(label = 'Free Disk(GB)', value = round(calc2.currentDiskAvail, 1), delta = round(percRemaining,2), delta_color= 'inverse' if percRemaining < 20 else 'normal', border=True)
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
                        'bar': {'color': '#16C47F' if calc2.currentCPU <= 75 else '#FFF574' if calc2.currentCPU <= 85 else '#F93827'},
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
                        'bar': {'color': '#16C47F' if calc2.currentMemory <= 70 else '#FFF574' if calc2.currentMemory <= 85 else '#F93827'},
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
                        'bar': {'color': '#16C47F' if calc2.currentDisk <= 75 else '#FFF574' if calc2.currentDisk <= 85 else '#F93827'},
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

        col1, col2, col3 = st.columns([1,1,1], border = False)
        with col1:
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
                    fig.add_trace(go.Scatter(x=vizData.index, y=vizData['CPUUsage'], fill='tozeroy', mode='lines', line=dict(color='green') ))
                    fig.update_layout(
                        title=f"CPU Usage In Last {output}",
                        xaxis_title='Time', yaxis_title='Percentage Usage', height=300, margin=dict(l=0,  r=30, t=40, b=10  ))     
                    st.plotly_chart(fig, use_container_width=True)

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
                    fig.add_trace(go.Scatter(x=vizData.index, y=vizData['MemoryUsage'], fill='tozeroy', mode='lines', line=dict(color='blue') ))
                    fig.update_layout(
                        title=f"Memory Usage In Last {output}",
                        xaxis_title='Time', yaxis_title='Percentage Usage', height=300, margin=dict(l=0,  r=30, t=40, b=10  ))     
                    st.plotly_chart(fig, use_container_width=True)  

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
                    fig.add_trace(go.Scatter(x=vizData.index, y=vizData['DiskUsage'], fill='tozeroy', mode='lines', line=dict(color='#FFEB00') ))
                    fig.update_layout(
                        title=f"Disk Usage In Last {output}",
                        xaxis_title='Time', yaxis_title='Percentage Usage', height=300, margin=dict(l=0,  r=30, t=40, b=10  ))     
                    st.plotly_chart(fig, use_container_width=True)  

    filters()

        # -------------------------------------------- 3rd row -----------------------------------------------
    @st.fragment
    def displayTable():
            usageData = st.session_state['data'].copy()
            usageData['LogTimestamp'] = pd.to_datetime(usageData['LogTimestamp'])
            latestLog = usageData['LogTimestamp'].max()
            filtered_data = usageData[usageData['LogTimestamp'] >= latestLog]

            # Create a new DataFrame where each row corresponds to a drive on a server
            quickMetricTable = filtered_data[['HostAndIP', 'DriveLetter', 'ManagementZone', 
                                            'ApplicationName', 'ApplicationOwner', 'TotalDiskSpaceGB', 
                                            'TotalFreeDiskGB', 'DiskUsage', 'CPUUsage', 'MemoryUsage', 
                                            'Datacenter']].copy()

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
            
            quickMetricTable.reset_index(drop=True, inplace=True)
            st.session_state['quickMetricTable'] = quickMetricTable   
            return st.dataframe(st.session_state['quickMetricTable'], use_container_width=True) 

    @st.fragment
    def pivotTable24hrs(value):
            usageData = st.session_state['data'].copy()
            usageData['LogTimestamp'] = pd.to_datetime(usageData['LogTimestamp'])
            startTime = str(usageData.LogTimestamp.max() - timedelta(hours=24))
            
            usageData.set_index('LogTimestamp', inplace = True)
            usageData = usageData[['HostAndIP', 'CPUUsage', 'DiskUsage', 'MemoryUsage', 'NetworkTrafficReceived', 'NetworkTrafficSent', 'NetworkTrafficAggregate']]

            usageData = usageData.groupby('HostAndIP').resample('h').agg({'CPUUsage': 'mean', 'DiskUsage': 'mean', 'MemoryUsage': 'mean', 'NetworkTrafficReceived': 'sum', 'NetworkTrafficSent': 'sum', 'NetworkTrafficAggregate': 'sum'})
            usageData.reset_index(inplace = True)
            usageData['hour'] = usageData['LogTimestamp'].dt.strftime('%H:00')
            # usageData =  pd.pivot_table(usageData, index = 'HostAndIP', columns = 'hour', values = 'CPUUsage').fillna(0).applymap(lambda x: f"{x:.2f}".rstrip('0').rstrip('.'))
            if st.session_state['data_empty'] == False:
                usageData =  pd.pivot_table(usageData, index = 'HostAndIP', columns = 'hour', values = value).fillna(0).applymap(lambda x: round(x, 2))
            else:
                return None
            return st.write(usageData.style.background_gradient(cmap='Reds', axis=0))

    @st.fragment
    def miniHeatMap():
        with stylable_container(
                    key="visual_container30",
                    css_styles="""{
                                # border: 1px solid rgba(49, 51, 63, 0.2);
                                # box-shadow: rgba(50, 50, 93, 0.25) 0px 2px 5px -1px, rgba(0, 0, 0, 0.3) 0px 1px 3px -1px;
                                box-shadow: rgba(0, 0, 0, 0.24) 0px 3px 8px;
                                # border-radius: 0.3rem;
                                padding: 20px 20px 20px 20px;
                                margin-top: 10px;
                            }"""):
            col1, col2 = st.columns([5,1.8], border = True)
            with col1:
                col11, col22 = col1.columns([1, 5])
                with col11:
                    options = ['CPUUsage', 'DiskUsage', 'MemoryUsage', 'NetworkTrafficReceived', 'NetworkTrafficSent', 'NetworkTrafficAggregate']
                    col11.selectbox('Metric Selector', options, key='metricTableValue',  help='View the information of your chosen metric in the last 24hrs', index = 0)
                with col22:
                    col22.markdown(f"""
                        <div class="container metrics text-center" style="margin-top: 1px; height:68px;">
                            <p style="font-size: 18px; font-weight: bold; text-align: center;">24Hrs Metric Display Table</p>
                            <p style="margin-top: -15px; font-size: 16px; text-align: center; font-family: Tahoma, Verdana;">
                                Overview of {st.session_state.metricTableValue} Across All Servers in the Last 24 Hours of Your Selected Timeframe
                            </p>
                        </div>
                        </div> """, unsafe_allow_html= True)
                pivotTable24hrs(st.session_state.metricTableValue)
  
            heatmapData1 = data[data['LogTimestamp'] >= calc.latestLog][['HostAndIP', 'DriveLetter', 'CPUUsage', 'DiskUsage', 'MemoryUsage']]
            with col2:
                col20, col21 = col2.columns([1, 1])
                with col20:
                    option1 = col20.selectbox('Metric Selector', ['CPUUsage', 'DiskUsage', 'MemoryUsage'], key='heatmap',  help="Displays a information of servers' resource consumption. Use the dropdown to select resource of interest", index = 0) 
                with col21:
                    option2 = col21.selectbox('Select prefered plot type', ['Heatmap', 'Barchart'], index = 0, help='Choose either barchart or heatmap to represent your information')

                if option1 == 'CPUUsage':
                    heatmapData1 = heatmapData1.groupby(['HostAndIP'])[['CPUUsage']].mean().reset_index()
                    if option2 == 'Heatmap':             
                        figs = px.treemap(data_frame=heatmapData1,path=['HostAndIP'], values = heatmapData1['CPUUsage'], color=heatmapData1['CPUUsage'], color_continuous_scale=[(0.0, "#16C47F"), (0.7, "#FFF574"),(0.85, "#F93827"), (1.0, "#F93827") ], range_color=(0, 100), hover_data={ 'CPUUsage': ':.2f',  'HostAndIP': True,   }, height = 400 )
                    else:
                        figs = px.bar(data_frame=heatmapData1, x='HostAndIP', y='CPUUsage', color='CPUUsage', color_continuous_scale=[(0.0, "#16C47F"), (0.7, "#FFF574"),(0.85, "#F93827"), (1.0, "#F93827") ], range_color=(0, 100), hover_data={ 'CPUUsage': ':.2f',  'HostAndIP': True,   }, height = 400 )

                elif option1 == 'DiskUsage':
                    heatmapData1 = heatmapData1.groupby(['HostAndIP'])[['DiskUsage']].mean().reset_index()
                    if option2 == 'Heatmap':
                        figs = px.treemap(data_frame=heatmapData1,path=['HostAndIP'], values = heatmapData1['DiskUsage'], color=heatmapData1['DiskUsage'], color_continuous_scale=[ (0.0, "#16C47F"), (0.7, "#FFF574"),(0.85, "#F93827"), (1.0, "#F93827") ], range_color=(0, 100) , hover_data={ 'DiskUsage': ':.2f',  'HostAndIP': True }, height = 400)
                    else:
                        figs = px.bar(data_frame=heatmapData1, x='HostAndIP', y='DiskUsage', color='DiskUsage', color_continuous_scale=[(0.0, "#16C47F"), (0.7, "#FFF574"),(0.85, "#F93827"), (1.0, "#F93827") ], range_color=(0, 100), hover_data={ 'DiskUsage': ':.2f',  'HostAndIP': True,   }, height = 400 ) 

                elif option1 == 'MemoryUsage':
                    heatmapData1 = heatmapData1.groupby(['HostAndIP'])[['MemoryUsage']].mean().reset_index()
                    if option2 == 'Heatmap':
                        figs = px.treemap(data_frame=heatmapData1,path=['HostAndIP'], values = heatmapData1['MemoryUsage'], color=heatmapData1['MemoryUsage'], color_continuous_scale=[(0.0, "#16C47F"), (0.7, "#FFF574"),(0.85, "#F93827"), (1.0, "#F93827") ], range_color=(0, 100) , hover_data={ 'MemoryUsage': ':.2f',  'HostAndIP': True}, height = 400)
                    else:
                        figs = px.bar(data_frame=heatmapData1, x='HostAndIP', y='MemoryUsage', color='MemoryUsage', color_continuous_scale=[(0.0, "#16C47F"), (0.7, "#FFF574"),(0.85, "#F93827"), (1.0, "#F93827") ], range_color=(0, 100), hover_data={ 'MemoryUsage': ':.2f',  'HostAndIP': True,   }, height = 400 ) 

                figs.update_traces(
                    hovertemplate="<b>Host and IP:</b> %{customdata[1]}<br>"
                  "<b>Value:</b> %{color:.2f}%<extra></extra>")
                figs.update_layout(
                    showlegend=False,
                    margin=dict(l=0, r=0, t=0, b=0),  # Remove margins
                    uniformtext=dict(minsize=10, mode='hide'),  # Manage text size and visibility
                )
                col2.plotly_chart(figs, use_container_width=True)
    miniHeatMap()


        # -------------------------------------------- 4th row -----------------------------------------------

    @st.fragment
    def heatMap():    
        dataWtihLastValues = (data.sort_values(by='LogTimestamp').groupby('HostAndIP', as_index=False).last())        
        with stylable_container(
                    key="visual_container40",
                    css_styles="""{
                                # border: 1px solid rgba(49, 51, 63, 0.2);
                                # box-shadow: rgba(50, 50, 93, 0.25) 0px 2px 5px -1px, rgba(0, 0, 0, 0.3) 0px 1px 3px -1px;
                                box-shadow: rgba(0, 0, 0, 0.24) 0px 3px 8px;
                                # border-radius: 0.3rem;
                                padding: 20px 20px 20px 20px;
                                margin-top: 10px;
                            }"""):    

            with st.container(border = True):
                col21, col22 = st.columns([1, 5], border =False)
                with col21:
                    treeSel = col21.selectbox('Select the metric to display', ['Storage Utilization', 'Application Resource Consumption', 'Network Traffic'], key='treeSel', index = 0)
                
                    treemap_titles = [["Storage Utilization", "Visualizing Most Recent Disk Space Distribution Across Servers (Based On The Selected Timeframe)"],
                        ["Application Resource Consumption", "Insights into the Most Recent CPU Resource Consumption Across Different Applications"], 
                        ["Network Traffic", "Monitoring Most Recent Network Bandwidth Utilization Across Applications and Servers"]]
            
                    topTitle = treemap_titles[0][0] if treeSel == 'Storage Utilization' else treemap_titles[1][0] if treeSel == 'Application Resource Consumption' else treemap_titles[2][0]
                    bodytitle = treemap_titles[0][1] if treeSel == 'Storage Utilization' else treemap_titles[1][1] if treeSel == 'Application Resource Consumption' else treemap_titles[2][1]

                with col22:
                    col22.markdown(f"""
                        <div class="container metrics text-center" style="margin-top: 1px; height:68px;">
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
                            color_continuous_scale=[(0.0, "#16C47F"), (0.7, "#FFF574"),(0.85, "#F93827"), (1.0, "#F93827") ],  # Gradient: red -> yellow -> green
                            range_color=(0, 100),  # Dynamic color range
                            hover_data={'DiskUsage': ':.2f', 'HostAndIP': True}, 
                            height=400)
                        figs.update_traces(
                            hovertemplate=
                                        "<b>Host and IP:</b> %{customdata[1]}<br>"
                                        "<b>Percentage UsedSpace:</b> %{color:.2f}<extra></extra>")
                        figs.update_layout(
                            margin=dict(l=0, r=0, t=0, b=0),
                            uniformtext=dict(minsize=10, mode='hide'), )
                        st.plotly_chart(figs, use_container_width=True)      
                elif treeSel == 'Application Resource Consumption':
                        figs = px.treemap(
                            data_frame=dataWtihLastValues, 
                            path=['ApplicationName', 'HostAndIP'],  
                            values=dataWtihLastValues['CPUUsage'],  
                            color=dataWtihLastValues['CPUUsage'],  
                            color_continuous_scale=[(0.0, "#16C47F"), (0.7, "#FFF574"),(0.85, "#F93827"), (1.0, "#F93827") ],  # Gradient: red -> yellow -> green
                            range_color=(0, 100),  # Dynamic color range
                            hover_data={'CPUUsage': ':.2f', 'HostAndIP': True}, 
                            height=400)
                        figs.update_traces(
                            hovertemplate=
                                        "<b>Host and IP:</b> %{customdata[1]}<br>"
                                        "<b>Percentage CPUusage:</b> %{color:.2f}<extra></extra>")
                        figs.update_layout(
                            margin=dict(l=0, r=0, t=0, b=0),
                            uniformtext=dict(minsize=10, mode='hide'), )
                        st.plotly_chart(figs, use_container_width=True)                            
                elif treeSel == 'Network Traffic':
                        dataWtihLastValues['NetworkTrafficAggregate'] = dataWtihLastValues['NetworkTrafficAggregate'].replace(0, 1e-6)
                        figs = px.treemap(
                            data_frame=dataWtihLastValues, 
                            path=['ApplicationName', 'HostAndIP'],  
                            values=dataWtihLastValues['NetworkTrafficAggregate'], 
                            color=dataWtihLastValues['NetworkTrafficAggregate'], 
                            color_continuous_scale=[(0.0, "#16C47F"), (0.7, "#FFF574"),(0.85, "#F93827"), (1.0, "#F93827") ],  # Gradient: red -> yellow -> green
                            range_color=(0, max(dataWtihLastValues['NetworkTrafficAggregate'])), 
                            hover_data={'NetworkTrafficAggregate': ':.2f', 'HostAndIP': True}, 
                            height=400)
                        figs.update_traces(
                            hovertemplate=
                                        "<b>Host and IP:</b> %{customdata[1]}<br>"
                                        "<b>Net Traffic Agg:</b> %{color:.2f}<extra></extra>")
                        figs.update_layout(
                            margin=dict(l=0, r=0, t=0, b=0),
                            uniformtext=dict(minsize=10, mode='hide'), )
                        st.plotly_chart(figs, use_container_width=True)   

    def displayAndHostAvailability():
        col1, col2 = st.columns([3, 1])
        with col1:
            col1.markdown(f"""
                <div class="container metrics text-center" style="margin-top: 1px; height:68px;">
                <p style="font-size: 18px; font-weight: bold; text-align: center;">Overview of Resource Availability and Server Uptime</p>
                </div>
                </div> """, unsafe_allow_html= True)
            displayTable() 

        with col2:
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=vizData.index, y=vizData['MemoryUsage'], fill='tozeroy', mode='lines', line=dict(color='blue') ))
            fig.update_layout(
                title=f"Memory Usage In Last {output}",
                xaxis_title='Time', yaxis_title='Percentage Usage', height=300, margin=dict(l=0,  r=30, t=40, b=10  ))     
            st.plotly_chart(fig, use_container_width=True) 

# <p style="margin-top: -15px; font-size: 16px; text-align: center; font-family: Tahoma, Verdana;">
    st.session_state['usageMonitor'] += 1              
    heatMap()                              
    displayTable() 

    # pivotTable24hrs()
    st.session_state['usageMonitor'] += 1

    st.markdown("<br>", unsafe_allow_html=True)




st.session_state['usageMonitor'] += 1
end_time = time.time()
uiloading_time = end_time - start_time
st.sidebar.markdown(f"App UI and Analysis loaded in {uiloading_time:.2f} seconds.")
st.sidebar.markdown(f"Data Connection and Refresh loaded in {dataloading_time:.2f} seconds.")

# time spent on each page, and the total time spent on all pages
# journey log:  how the users moved from one p[age to the other

#         with col1:
#             with stylable_container( key = 'containerTwo',
#                 css_styles="""{
#                     border: 1px solid rgba(49, 51, 63, 0.2);
#                     boshadow: rgba(0, 0, 0, 0.1) 0px 10px 15px -3px, rgba(0, 0, 0, 0.05) 0px 4px 6px -2px;
#                     border-radius: 0.3rem;
#                     padding: calc(1em - 1px);
#                     margin-top: -10px
#                 }"""):
            
#                 st.markdown(f"""
#                     <div class="container metrics text-center">
#                             <h6 class="text-3xl text-gray-900 font-bold">Op System</h6>
#                             <p style="margin-top: 10px; font-size: 17px; font-weight: bold; color: #333; text-align: center; font-family: Geneva, Verdana, Geneva, sans-serif">{data.ApplicationName.iloc[0]}</p>
#                     </div>
#                             """, unsafe_allow_html= True)
# html_code = """
# <div style="border: 1px solid #ccc; border-radius: 5px; padding: 20px; background-color: #f9f9f9;">
#     <h2 style="color: #333;">Header Title</h2>
#     <p style="color: #666;">This is a paragraph inside the container. You can add more content here as needed.</p>
# </div>
# """

# # Render the HTML in Streamlit
# st.markdown(html_code, unsafe_allow_html=True)
# shad.tabs(options=['PyGWalker', 'Graphic Walker', 'GWalkR', 'RATH'], default_value='PyGWalker', key="kanaries")

# st.markdown(f"""
# # <div class='custom-container'>
# #     <p>This is a custom container styled via CSS.</p>
# # </div>
# # """, unsafe_allow_html=True)
# sac.divider(label='label', icon='house', align='center', color='gray')







# df = fetchFromClientDB(clientServer, get_last_update_time())
# saveToSQLite(df)


# conn = sqlite3.connect('EdgeDB')
# c = conn.cursor()

# query = "SELECT * FROM Infra_Utilization"
# g = pd.read_sql_query(query, conn)
# print(g)

# df['Dayname'] = pd.to_datetime(df['logTimeStamp']).dt_day_name()
# df['time'] = pd.to_datetime(df['LogTimestamp]).dt.strftime('%-H:%M')

# Top Navigation Bar 
# with open('style.css') as f:
#     st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
# container = st.container()
# with container:
#     st.write('Hey there')

# container2 = st.container(key = 'cont1')
# with container2:keepGBFs
#     st.write('Hey there')
# Apply the styling to the container
# with container:
#     st.markdown("""
#         <style>
#             .container {
#                 display: flex;
#                 align-items: center;
#                 justify-content: space-between;
#                 padding: 10px 20px;
#                 background-color: #f8f9fa;
#                 border-bottom: 1px solid #e0e0e0;
#                 boshadow: 0 2px 4px rgba(0, 0, 0, 0.1);
#             }
#         </style>
#     """, unsafe_allow_html=True)


# with st.container(key = 'header'):
#     col1, col2, col3 = st.columns([1,4,1])

#     col11, col12 = col1.columns([1,1])
#     col11.image('PNG/Red.png', width=70)
#     col12.image('PNG/icons8-vertical-line-50.png', width=30)

#     col21, col22, col23 = col2.columns([3,0.3,0.3])
#     col21.markdown(f'Infrastrucutre Monitoring Dashboard', unsafe_allow_html=True)
#     col22.write('Im in col2.2')
#     col23.write('Im in col2.3')

#     col3.write('Hey there')

# import streamlit as st
# st.html(f"""
# <div style="
#     display: flex;
#     align-items: center;
#     justify-content: space-between;
#     padding: 10px 20px;
#     background-color: #f8f9fa;
#     border-bottom: 1px solid #e0e0e0;
#     boshadow: 0 2px 4px rgba(0, 0, 0, 0.1);
# ">
#     <!-- Logo and Dashboard Name -->
#     <div style="display: flex; align-items: center; gap: 10px;">
#         <img src="https://via.placeholder.com/40" alt="Logo" style="width: 40px; height: 40px; border-radius: 50%;">
#         <span style="font-size: 18px; font-weight: bold; color: #333;">Dashboard Name</span>
#     </div>

#     <!-- Icons (Message, Notification, User) -->
#     <div style="display: flex; align-items: center; gap: 20px;">
#         <!-- Message Icon -->
#         <img src="https://via.placeholder.com/24" alt="Message" style="width: 24px; height: 24px; cursor: pointer;">
        
#         <!-- Notification Icon -->
#         <img src="https://via.placeholder.com/24" alt="Notification" style="width: 24px; height: 24px; cursor: pointer;">
        
#         <!-- User Icon -->
#         <img src="https://via.placeholder.com/40" alt="User  " style="width: 40px; height: 40px; border-radius: 50%; cursor: pointer;">
#     </div>
# </div>
# """)

# st.button('Click me', key = 'green')