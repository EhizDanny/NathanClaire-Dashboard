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

# set configuration 


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
# @st.cache_resource()
def load_css(filePath:str):
    with open(filePath) as f:
        st.html(f'<style>{f.read()}</style>')
css_path = pathlib.Path('style.css')
load_css(css_path)

#load data
# Get a start and stop filter date and time for first time loading. Update this date later to tally with users selected date
if 'stopDate' not in st.session_state:
    st.session_state['stopDate'] = datetime.today().date().strftime("%Y-%m-%d")
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
st.markdown(f"""
<div class="heading">
        <p style="margin-top: 10px; font-size: 17px; font-weight: bold; color: #333; text-align: center; font-family: Geneva, Verdana, helvetica, sans-serif">Infrastructure Monitoring System</p>
</div>""", unsafe_allow_html=True)


st.sidebar.image('PNG/Red.png')
# antd.divider(label='HOME', icon='house', align='center', color='gray')
st.sidebar.success(st.session_state['startDate'])
st.sidebar.success(st.session_state['stopDate'])

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



     
    # Filters Container 
    with stylable_container(
            key="container_with_border",
            css_styles="""{
                    border: 1px solid rgba(49, 51, 63, 0.2);
                    box-shadow: rgba(0, 0, 0, 0.1) 0px 10px 15px -3px, rgba(0, 0, 0, 0.05) 0px 4px 6px -2px;
                    border-radius: 0.3rem;
                    padding-bottom: 5px;
                    margin-top: -10px
                }"""):
        col7, appOwner, appName, vendor, dataCenter, mgtZone, os = st.columns([4, 1.3, 1.3, 1, 1, 1.3, 1])
        ao = appOwner.selectbox('Application Owner', data['ApplicationOwner'].unique())
        an = appName.selectbox('Application Name', data['ApplicationName'].unique())
        vend = vendor.selectbox('Vendor', data['Vendor'].unique())
        dc = dataCenter.selectbox('Data Center', data['Datacenter'].unique())
        mz = mgtZone.selectbox('Management Zone', data['ManagementZone'].unique())
        oss = os.selectbox('OS', data['OS'].unique())

    containerTwo = tab1.container()
    with containerTwo:
        col1, col2, col3, col4, col5, col6, col7, col8 = containerTwo.columns([2,1,3,1,1,1,1,1])
        with col1:
            col1.markdown(f"""
                    <div class="container metrics text-center">
                            <p style="font-size: 18px; font-weight: bold; text-align: center; align-items: center;" >Op System</p>
                            <p style="margin-top: -15px; font-size: 14px; text-align: center; align-items: center; font-family: Tahoma, Verdana;">{data.OS.iloc[0]}</p>
                    </div> """, unsafe_allow_html= True)
        with col2:
            col2.markdown(f"""
                    <div class="container metrics text-center">
                            <p style="font-size: 18px; font-weight: bold; text-align: center; align-items: center;" >Hostname</p>
                            <p style="margin-top: -15px; font-size: 14px; text-align: center; align-items: center; font-family: Tahoma, Verdana;">{data.Hostname.iloc[0]}</p>
                    </div> """, unsafe_allow_html= True)
        with col3:
            col3.markdown(f"""
                    <div class="container metrics text-center">
                            <p style="font-size: 18px; font-weight: bold; text-align: center; align-items: center;" >IP Address</p>
                            <p style="margin-top: -15px; font-size: 14px; text-align: center; align-items: center; font-family: Tahoma, Verdana;">{data.IPAddress.iloc[0]}</p>
                    </div> """, unsafe_allow_html= True)
        with col4:
            col4.markdown(f"""
                    <div class="container metrics text-center">
                            <p style="font-size: 18px; font-weight: bold; text-align: center; align-items: center;" >Total Server</p>
                            <p style="margin-top: -15px; font-size: 14px; text-align: center; align-items: center; font-family: Tahoma, Verdana;">{calc.totalServer}</p>
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
                            <p style="margin-top: -15px; font-size: 14px; text-align: center; align-items: center; font-family: Tahoma, Verdana;">{data.ApplicationName.iloc[0]}</p>
                    </div> """, unsafe_allow_html= True)
        with col7:
            col7.markdown(f"""
                    <div class="container metrics text-center">
                            <p style="font-size: 18px; font-weight: bold; text-align: center; align-items: center;" >App Owner</p>
                            <p style="margin-top: -15px; font-size: 14px; text-align: center; align-items: center; font-family: Tahoma, Verdana;">{data.ApplicationOwner.iloc[0]}</p>
                    </div> """, unsafe_allow_html= True)
        with col8:
            col8.markdown(f"""
                    <div class="container metrics text-center">
                            <p style="font-size: 18px; font-weight: bold; text-align: center; align-items: center;" >Vendor</p>
                            <p style="margin-top: -15px; font-size: 14px; text-align: center; align-items: center; font-family: Tahoma, Verdana;">{data.Vendor.iloc[0]}</p>
                    </div> """, unsafe_allow_html= True)

    tab1.markdown('<br>', unsafe_allow_html=True)
    antd.divider(label='Infrastructure Analysis', icon='house', align='center', color='gray')

# VISUALS 
    with stylable_container(
        key="visual_container",
        css_styles="""{
                    # border: 1px solid rgba(49, 51, 63, 0.2);
                    box-shadow: rgba(0, 0, 0, 0.15) 0px 5px 15px 0px;
                    border-radius: 0.3rem;
                    padding: 5px 10px;
                    margin-top: -10px;

                }"""):
        col1, col2, col3, col4 = st.columns([2,5,1,2], border = True)
        with col1:
            selServer = col1.selectbox('Server List', calc.servers)
            forNow = data[data['HostAndIP'] == selServer]
            forNow['LogTimestamp'] = pd.to_datetime(forNow['LogTimestamp'])
            forNow.set_index('LogTimestamp', inplace = True)
        with col2:
            netType = col2.selectbox('Network Bound', ['Received', 'Sent', 'Aggregate'], index = 2)
            if netType == 'Recieved':
                fig = px.line(x = forNow.index, y = forNow.NetworkTrafficReceived, height = 280)
                col2.plotly_chart(fig)
            elif netType == 'Sent':
                fig = px.line(x = forNow.index, y = forNow.NetworkTrafficSent, height = 280)
                col2.plotly_chart(fig)
            elif netType == 'Aggregate':
                fig = px.line(x = forNow.index, y = forNow.NetworkTrafficAggregate, height = 280)
                col2.plotly_chart(fig)
        with col3:
            col3.metric(label = 'Disk Space(GB)', value = round(calc.currentTotalDisk,1), delta = None, border=True)
            percRemaining = (calc.currentDiskAvail/calc.currentTotalDisk) * 100
            col3.metric(label = 'Free Disk(GB)', value = round(calc.currentFreeDisk, 1), delta = round(percRemaining,2), delta_color= 'inverse' if percRemaining < 20 else 'normal', border=True)
            col3.metric(label='Memory(GB)', value = round(calc.currentTotalMemory, 1), delta = None, border=True)
        with col4:
            fig1 = go.Figure(go.Indicator(
                mode = "gauge+number+delta",
                value = calc.currentCPU,
                domain = {'x': [0, 1], 'y': [0, 1]},
                title = {'text': "Current CPU Load(%)", 'font': {'size': 18}},
                # delta = {'reference': 400, 'increasing': {'color': "RebeccaPurple"}},
                gauge = {
                    'axis': {'range': [1, 100], 'tickwidth': 1, 'tickcolor': "darkblue"},
                    'bar': {'color': '#16C47F' if calc.currentCPU <= 75 else 'FFF574' if calc.currentCPU <= 85 else 'F93827'},
                    # 'bgcolor': "white",
                    'borderwidth': 1,
                    'bordercolor': "white",
                    'steps': [
                        {'range': [0, 80], 'color': '#F0F2F6'},
                        {'range': [80, 100], 'color': '#FFEDED'}],
                    'threshold': {
                        'line': {'color': "red", 'width': 4},
                        'thickness': 0.75,
                        'value': 80}}))
            fig1.update_layout(
                height=200,
                paper_bgcolor='rgba(0,0,0,0)',  # Transparent background
                margin=dict(l=0, r=0, t=0, b=0) ) # Remove extra space around the gauge
            col4.plotly_chart(fig1, use_container_width=True)
            
            fig2 = go.Figure(go.Indicator(
                mode = "gauge+number+delta",
                value = calc.currentMemory,
                domain = {'x': [0, 1], 'y': [0, 1]},
                title = {'text': "Current Memory Load(%)", 'font': {'size': 18}},
                # delta = {'reference': 400, 'increasing': {'color': "RebeccaPurple"}},
                gauge = {
                    'axis': {'range': [1, 100], 'tickwidth': 1, 'tickcolor': "darkblue"},
                    'bar': {'color': '#16C47F' if calc.currentCPU <= 75 else 'FFF574' if calc.currentCPU <= 85 else 'F93827'},
                    'bgcolor': "gray",
                    'borderwidth': 1,
                    'bordercolor': "white",
                    'steps': [
                        {'range': [0, 80], 'color': '#F0F2F6'},
                        {'range': [80, 100], 'color': '#FFEDED'}],
                    'threshold': {
                        'line': {'color': "red", 'width': 4},
                        'thickness': 0.75,
                        'value': 80}}))
            fig2.update_layout(
                height=200,
                paper_bgcolor='rgba(0,0,0,0)',  # Transparent background
                margin=dict(l=0, r=0, t=0, b=0) ) # Remove extra space around the gauge
            col4.plotly_chart(fig2)
            
            fig3 = go.Figure(go.Indicator(
                mode = "gauge+number+delta",
                value = calc.currentDisk,
                domain = {'x': [0, 1], 'y': [0, 1]},
                title = {'text': "Current Disk Load(%)", 'font': {'size': 18}},
                # delta = {'reference': 400, 'increasing': {'color': "RebeccaPurple"}},
                gauge = {
                    'axis': {'range': [1, 100], 'tickwidth': 1, 'tickcolor': "darkblue"},
                    'bar': {'color': '#16C47F' if calc.currentCPU <= 75 else 'FFF574' if calc.currentCPU <= 85 else 'F93827'},
                    # 'bgcolor': "white",
                    'borderwidth': 1,
                    'bordercolor': "white",
                    'steps': [
                        {'range': [0, 80], 'color': '#F0F2F6'},
                        {'range': [80, 100], 'color': '#FFEDED'}],
                    'threshold': {
                        'line': {'color': "red", 'width': 4},
                        'thickness': 0.75,
                        'value': 80}}), layout = go.Layout(height = 250))
            fig3.update_layout(
                height=200,
                paper_bgcolor='rgba(0,0,0,0)',  # Transparent background
                margin=dict(l=0, r=0, t=0, b=0) ) # Remove extra space around the gauge
            col4.plotly_chart(fig2)
            col4.plotly_chart(fig3, use_container_width=True)











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
#                     box-shadow: rgba(0, 0, 0, 0.1) 0px 10px 15px -3px, rgba(0, 0, 0, 0.05) 0px 4px 6px -2px;
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
#                 box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
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
#     box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
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