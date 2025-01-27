import sqlite3
import streamlit as st
from streamlit import session_state as ss
from streamlit_extras.stylable_container import stylable_container
from streamlit_option_menu import option_menu
st.set_page_config(
    page_title = 'AppMonitor', 
    page_icon = ':bar_chart:',
    layout = 'wide'
)
import seaborn as sns 
import matplotlib.pyplot as plt
import pandas as pd 
import numpy as np
import json
import pathlib
import warnings 
from calculations import InfraCalculate as inf 
import datetime
from datetime import datetime, timedelta
import threading
import time
import schedule
import warnings 
warnings.filterwarnings('ignore')
from statsmodels.tsa.stattools import acf, pacf
from statsmodels.graphics.tsaplots import plot_acf, plot_pacf
import importlib
from modelScript.uniVariate import NathanClaire_UnivariateTimeSeries as lib
from sklearn.preprocessing import MinMaxScaler
from PIL import Image
import plotly.express as px
import pandas as pd
import google.generativeai as genai
# import modelScript.uniVariate
# importlib.reload(modelScript.uniVariate)


def liveDataHandler(db_path, table_name):
# Connect to the SQLite database.
    conn = sqlite3.connect(db_path)
    query = f"""
    SELECT * FROM '{table_name}' 
    """
    dataset = pd.read_sql_query(query, conn)
    dataset.to_parquet('modellingData.parquet', engine='fastparquet', index=False)
    conn.close()
    dataset = pd.read_parquet('modellingData.parquet', engine='fastparquet')
    return dataset

data = liveDataHandler('EdgeDB 2', 'Infra_Utilization')
data['HostAndIP'] = data['Hostname'] + data['IPAddress'].str.replace('"', '')
modellingData = data.copy()
modellingData['LogTimestamp'] = pd.to_datetime(modellingData['LogTimestamp'])


if not data.empty:
    emptyData = False 
else:
    empytyDdata = True


# Import Styling Sheet 
# @st.cache_resource()
def load_css(filePath:str):
    with open(filePath) as f:
        st.html(f'<style>{f.read()}</style>')
css_path = pathlib.Path('style2.css')
load_css(css_path)

st.session_state['data'] = data.copy()
calc = inf(data)
latestLog = calc.latestLog
  

# Define the weights for each feature (should sum to 1)
weights = {
    'CPUUsage': 0.4,
    'MemoryUsage': 0.25,
    'TotalMemory': 0.05,
    'DiskUsage': 0.15,
    'TotalFreeDiskGB': 0.1,
    'NetworkTrafficSent': 0.025,
    'NetworkTrafficReceived': 0.025
}
features = ['LogTimestamp', 'HostAndIP', 'CPUUsage', 'MemoryUsage', 'TotalMemory', 'DiskUsage', 'TotalFreeDiskGB', 'NetworkTrafficSent', 'NetworkTrafficReceived']


# Navigatio Top Bar 
head1, head2, head3 = st.columns([1, 3, 1])
with head2:
    head2.markdown(f"""
    <div class="two alt-two">
    <h1>Infrastructure Analytics
        
    </h1>
    </div>""", unsafe_allow_html=True)

@st.fragment
def resourceUtilization():  
  
        # with st.expander('Drop DownTo View Resource Utilization', expanded=False):
    global usageData
    usageData = data[data['LogTimestamp'] >= latestLog]
    usageData = usageData.sort_values(by='LogTimestamp').groupby(['HostAndIP', 'LogTimestamp']).agg({
                                'CPUUsage': 'mean',
                                'MemoryUsage': 'mean',
                                'DiskUsage': 'mean',
                                'TotalFreeDiskGB': 'last',
                            'TotalMemory': 'last',
                            'NetworkTrafficReceived': 'mean',
                            'NetworkTrafficSent': 'mean',
    }).reset_index()
    dataForWeight = usageData.copy()
    min_row = {
        'HostAndIP': np.nan, 
        'LogTimestamp': np.nan,    
        'CPUUsage': 0.1,
        'MemoryUsage': 0.1,
        'DiskUsage': 0.1,
        'TotalFreeDiskGB': 0.1,
        'TotalMemory': 0.1,
        'NetworkTrafficReceived': 0,
        'NetworkTrafficSent': 0
    }
    max_row = {
        'HostAndIP': np.nan,
        'LogTimestamp': pd.NaT,   
        'CPUUsage': 100,
        'MemoryUsage': 100,
        'DiskUsage': 100,
        'TotalFreeDiskGB': 150,
        'TotalMemory': 16,
        'NetworkTrafficReceived': 100_000_000,
        'NetworkTrafficSent': 100_000_000
    }
    # Convert the rows to DataFrames
    min_row_df = pd.DataFrame([min_row])
    max_row_df = pd.DataFrame([max_row])
    # --- Step 2: Append the Rows to the Existing DataFrame ---
    dataForWeight = pd.concat([usageData, min_row_df, max_row_df], ignore_index=True)
    for i in dataForWeight.drop(['LogTimestamp', 'HostAndIP'], axis = 1):
        normalizer = MinMaxScaler()
        dataForWeight[i] = normalizer.fit_transform(dataForWeight[[i]])
        # Calculate the composite metric
    dataForWeight['WeightedUsage'] = (
            dataForWeight['CPUUsage'] * weights['CPUUsage'] +
            dataForWeight['MemoryUsage'] * weights['MemoryUsage'] +
            dataForWeight['TotalMemory'] * weights['TotalMemory'] +
            dataForWeight['DiskUsage'] * weights['DiskUsage'] +
            dataForWeight['TotalFreeDiskGB'] * weights['TotalFreeDiskGB'] +
            dataForWeight['NetworkTrafficSent'] * weights['NetworkTrafficSent'] +
            dataForWeight['NetworkTrafficReceived'] * weights['NetworkTrafficReceived']
        ).round(2)        
    usageData['WeightedUsage'] = dataForWeight['WeightedUsage'].iloc[:-2]
    usageData['WeightedUsage'] = usageData['WeightedUsage'].apply(lambda x: str(x*100) + '%')
    usageData = usageData[['LogTimestamp', 'HostAndIP', 'WeightedUsage', 'CPUUsage', 'MemoryUsage', 'DiskUsage', 'TotalFreeDiskGB', 'TotalMemory', 'NetworkTrafficReceived', 'NetworkTrafficSent']]
    return usageData            


if 'timeInterval'not in ss:
# ss.serverName = data.HostAndIP.unique().tolist()[0]
    ss.timeInterval = 10

ds = data.copy()


@st.dialog('Resource Utility Alert')
def resourceChecker():
    count_above_85 = sum(float(i.replace('%', '').strip()) > 85 for i in usageData['WeightedUsage'].tolist())
    st.write(f'There are {count_above_85} servers experiencing high resource utility. Drop down the expander to view')


tab1, tab2, tab3 = st.tabs([':computer: Resource Utility Forecast', ':cd: Disk Usage Forecast', ':chart: Chat With Your Data'])

with tab1:
    weightData = ds[features] 
    for i in weightData.columns:
        if i != 'LogTimestamp' and i != 'HostAndIP':
            normalizer = MinMaxScaler()
            weightData[i] = normalizer.fit_transform(weightData[[i]])  

    weightData['Weighted Resource Utility'] = (
            weightData['CPUUsage'] * weights['CPUUsage'] +
            weightData['MemoryUsage'] * weights['MemoryUsage'] +
            weightData['TotalMemory'] * weights['TotalMemory'] +
            weightData['DiskUsage'] * weights['DiskUsage'] +
            weightData['TotalFreeDiskGB'] * weights['TotalFreeDiskGB'] +
            weightData['NetworkTrafficSent'] * weights['NetworkTrafficSent'] +
            weightData['NetworkTrafficReceived'] * weights['NetworkTrafficReceived']
        ).round(2)    
  
    @st.fragment
    def tsModel(classInstance):
        split_index = int(len(classInstance.data) * 0.7)
        split_date = classInstance.data.iloc[split_index: split_index+1].index.values[0]
        classInstance.generateModelData(split_date=split_date, show_split=False)
        classInstance.modelling(plotPerformance=True)
        return classInstance

        # forecasts, figure = classInstance.futureForecast(timeDiff=ss.timeInterval, interval=ss.timeframe, NumOfDays=ss.timeInterval, getForecast=True, plotForecast=True)
        # return forecasts, figure

    @st.fragment
    def utilityForecast():
        global ts
        col1, col2= st.columns([1.5, 3], border=True)
        with col1:
            col1.selectbox('Select server to forecast', [i for i in weightData['HostAndIP'].unique().tolist()], key = 'serverName', index = 0)
            col1.markdown('<br>', unsafe_allow_html=True)

            # col11, col12 = col1.columns([1,1])
            # col11.number_input('Input time interval',min_value=1, max_value=100, value=10 , help = 'Future forecast time interval in numbers', key = 'timeInterval')           
            # col12.selectbox('Select forecast time timeframe', help = 'Timeframe in minutes, hours, day, week, year',index = 0, options=['Minute', 'Hour', 'Day', 'Month', 'Year'], key = 'timeframe')
        
        with col2:   
            ts = lib(weightData, 'Weighted Resource Utility', 'LogTimestamp', ss.serverName, ss.timeInterval)                
            col2.plotly_chart(ts.visual(), use_container_width=True, theme='streamlit')
        
    with stylable_container(
                            key="visual_container42",
                            css_styles=[
                                """{
                                        # border: 1px solid rgba(49, 51, 63, 0.2);
                                        # box-shadow: rgba(50, 50, 93, 0.25) 0px 2px 5px -1px, rgba(0, 0, 0, 0.3) 0px 1px 3px -1px;
                                        box-shadow: rgba(0, 0, 0, 0.24) 0px 3px 8px;
                                        # border-radius: 0.3rem;
                                        padding: 20px 20px 20px 20px;
                                }""",]
                                    ): 
        utilityForecast()

    # Drop down resource checker 
    col1, col2, col3 = tab1.columns([1,5,1], border = False)
    with col2:
        with stylable_container(
                            key="visual_container4_",
                            css_styles=[
                                """{
                                        # border: 1px solid rgba(49, 51, 63, 0.2);
                                        # box-shadow: rgba(50, 50, 93, 0.25) 0px 2px 5px -1px, rgba(0, 0, 0, 0.3) 0px 1px 3px -1px;
                                        box-shadow: rgba(0, 0, 0, 0.24) 0px 3px 8px;
                                        # border-radius: 0.3rem;
                                        padding: 20px 20px 20px 20px;
                                }""",]
                                    ):  
            with st.expander('Drop DownTo View Resource Utilization', expanded=False,):
                resUtils = resourceUtilization()
                st.dataframe(resUtils.head(100).style.background_gradient(cmap = 'Reds'), use_container_width=True)
    
    if any(float(i.replace('%', '').strip()) > 85 for i in resUtils['WeightedUsage'].tolist()):
        resourceChecker()

    @st.fragment
    def futurePred():
        # with st.container(height=400, border=False):
            control, future = st.columns([1,2],border = True)
            with control:
                c1, c2 = control.columns([1,1])
                c1.number_input('Input time interval',min_value=1, max_value=100, value=ss.timeInterval , help = 'Future forecast time interval in numbers', key = 'timeInterval')   
                c2.selectbox('Select forecast time timeframe', help = 'Timeframe in minutes, hours, day, week, year',index = 0, options=['Minute', 'Hour', 'Day', 'Month', 'Year'], key = 'timeframe')

                c3, c4 = control.columns([1,1], vertical_alignment='bottom')
                c3.number_input('Input future forecast days', help = 'Input the number of future days to be forecasted by the model', value = 3, min_value=1, max_value=30, key='futureDays')
                c4.button('Future Forecast', help=f'Press the button to predict {ss.futureDays}days into the future', key='predict')
            with future:
                futureView, forecastView = future.tabs(['Future Focrecast', 'Forecast Plot'])    
                if ss.predict:
                    with futureView:
                        out = tsModel(ts)
                        outputData = out.futureForecast(timeDiff=ss.timeInterval, interval=ss.timeframe, NumOfDays=ss.futureDays, getForecast=True, plotForecast=False)
                        outputData.rename(columns =  {'ds':'DateAndTime', 'yhat':'Predicted Value', 'yhat_upper': 'UpperBound', 'yhat_lower':'LowerBound'}, inplace = True)
                        outputData['UpperBound'] = outputData['UpperBound'].round(2)
                        outputData['LowerBound'] = outputData['LowerBound'].round(2)
                        outputData.reset_index(drop = True, inplace = True)
                        futureView.dataframe(outputData, use_container_width=True)
                        saving = outputData.to_csv(index=False).encode('utf-8')
                        st.download_button(
                        "Click to download your forecasted values",
                        saving,
                        "forecastedValues.csv",
                        "text/csv",
                        key='download-csv')
                    with forecastView:
                        forecastView.pyplot(tsModel(ts).futureForecast(timeDiff=ss.timeInterval, interval=ss.timeframe, NumOfDays=ss.futureDays, getForecast=False, plotForecast=True))
    
    with stylable_container(
                            key="visual_container43",
                            css_styles=[
                                """{
                                        # border: 1px solid rgba(49, 51, 63, 0.2);
                                        # box-shadow: rgba(50, 50, 93, 0.25) 0px 2px 5px -1px, rgba(0, 0, 0, 0.3) 0px 1px 3px -1px;
                                        box-shadow: rgba(0, 0, 0, 0.24) 0px 3px 8px;
                                        # border-radius: 0.3rem;
                                        padding: 20px 20px 20px 20px;
                                }""",]
                                    ):  
        futurePred()




def googleModelInstruction():
    system_instruction = f"""
        You are an intelligent assistant designed to convert natural language queries into Pandas DataFrame operations. Your task is to interpret human queries and translate them into syntactically correct Python code using the Pandas library. Follow these detailed guidelines:

        1. Understand the User's Intent:
            Carefully analyze the user's natural language query to determine the requested operation.
            Identify the key elements:
            DataFrame name (if unspecified, ask the user).
            Columns to select or manipulate.
            Filters (e.g., date ranges, specific conditions).
            Aggregations (e.g., sum, average, count).
            Sorting, grouping, or any additional transformations.
            Validate and Refine the Query:

        2. Construct the Pandas Code:
            Translate the intent into Python code using Pandas.
            Use the appropriate Pandas functions and syntax, including:
            .loc[] or .query() for filtering rows.
            .groupby() for aggregation.
            .sort_values() for sorting.
            .pivot_table() or .unstack() for reshaping data, etc
            Ensure the query is syntactically correct and leverages Pandas best practices for readability and efficiency.

        3. Assumptions and Default Values:
            If the query does not specify a DataFrame name:
            You can infer the name of the dataframe from your understanding of the question. If the question is anything related to infrastructure monitoring, use modellingData as the default and you can also prompt the user for clarification if necessary.
            Here are the names of the columns in the table:[
            'LogTimestamp': dtype('Datetime'),
                'CPUUsage': dtype('float64'),
                'MemoryUsage': dtype('float64'),
                'TotalMemory': dtype('float64'),
                'DiskUsage': dtype('float64'),
                'TotalFreeDiskGB': dtype('float64'),
                'TotalDiskSpaceGB': dtype('float64'),
                'DiskLatency': dtype('float64'),
                'ReadLatency': dtype('float64'),
                'WriteLatency': dtype('float64'),
                'NetworkTrafficAggregate': dtype('float64'),
                'NetworkTrafficSent': dtype('float64'),
                'NetworkTrafficReceived': dtype('float64'),
                'Hostname': dtype('O'),
                'IPAddress': dtype('O'),
                'OperatingSystem': dtype('O'),
                'ManagementZone': dtype('O'),
                'Datacenter': dtype('O'),
                'DatacenterRegion': dtype('O'),
                'ApplicationName': dtype('O'),
                'ApplicationOwner': dtype('O'),
                'Vendor': dtype('O'),
                'OS': dtype('O'),
                'DriveLetter': dtype('O'),
                'HostAndIP': dtype('O'),
                'Overall Resource Utility: dtype('float')]
            If the query involves date filtering:
        Assume the default column name is LogTimestamp unless specified.
        Assume the date format is YYYY-MM-DD.
        For ambiguous column names:
        Provide the most likely interpretation based on context but note the assumption in your response.
        If the query involves aggregation: do aggregate and return the best pandas tables aggregration code 
        If the query involves sorting: do sort and return the best code query

        4. Examples:
            Basic Queries
            Human Query: "Show all transactions where the amount is greater than 100."
            Pandas Code: df[df['TransactionAmount'] > 100]

            Human Query: "Filter the data to include only transactions in June 2013."
            Pandas Code: df[(df['TransactionDate'] >= '2013-06-01') & (df['TransactionDate'] <= '2013-06-30')]

            Aggregations
            Human Query: "What is the total amount by customer gender?"
            Pandas Code: df.groupby('gender')['TransactionAmount'].sum()

            Human Query: "Find the average transaction amount per customer."
            Pandas Code: df.groupby('CustomerID')['TransactionAmount'].mean()

            Sorting and Formatting
            Human Query: "Sort transactions by the highest amount."
            Pandas Code: df.sort_values('TransactionAmount', ascending=False)

            Human Query: "Get the top 5 customers by total spending."
            Pandas Code: df.groupby('CustomerID')['TransactionAmount'].sum().nlargest(5)

        5. Handle Ambiguity and Errors:
            If the query is ambiguous, clarify the intent before proceeding:
            Example: "What do you mean by 'top transactions'? Is it by amount or frequency?"
            Check for potential errors or unsafe inputs:
            Example: Ensure filtering values exist in the DataFrame (e.g., column names).

        6. Output Format
            Always provide the full Pandas code snippet for execution.
            Use clear, readable formatting:
            Example:
            # Filter transactions greater than 100
            df[df['TransactionAmount'] > 100]

        7. Edge Cases:
            Handle missing data (NaN values) appropriately:
            Example: .dropna() or .fillna() if relevant to the query.
            Handle duplicate rows when necessary:
            Example: .drop_duplicates().

        8. Injections:
            Ensure that queries that may delete, truncate, or insert or drop any rows are clearly marked as such and ask for a revision of the query as you are not permitted to run queries that may harm the database.

        9. Clarification if your response is a pandas code:
            If your response is a pandas code, start your response sentence with '[PP]' then followed by the actual pandas code.
            If your response is not a pandas code, start your response sentence with '[NP]' then followed by your response.
            This will help seperating pandas code from other responses.

        10. Output Format:
            The output should be optimized so that it is a single pandas query string that can be executed directly in a pandas table.
            if its not a pandas query, ensure you dont reveal that you are using a pandas query, dont mention the name of the table, act as an agent that collects natural language and converts it to pandas query only. If the users input is not related to finding information about their data, answer briefly, dont mention pandas, direct them back to the information they seek to know from their database. Pandas is already imported, dont import it again. you are to be passed into another program as pandas query, so endeavour to output direct pandas query that can be run on a dataframe directly. you dont give a code that alters the table, if you asked in this regard, ask the user to speak to the database administrator for an update on thew data. you are to be used to query the database, not to update it. Active servers are servers that has sent information to the database within the last 5minutes, so you can give a query that finds all servers present in the database above last 5minutes. pls remember all needed libraries are already imported, no need to import them again. high resource usage are servers having Overall Resource Utility of above 85, low resource usage are servers having Overall Resource Utility of between 0 and 70, mid resource usage are servers having Overall Resource Utility of between 70 and 85. Use the pandas nunique always when you are asked to find the length of a particular variable relating to the dataframe. If servers or hosts are referred to, the user is referring to the HostAndIP column in the dataframe, unless specifically stated. You can as well ask what they mean by servers, is it Hosts differentiated by the IP's or just Hosts in general.Dont ever mention pandas in your response.

        11. Specifics:
            Some times the user might for directs specifics. here are some specifics and where they can be found.
            Content of ManagementZone amongst others : {[i for i in modellingData['ManagementZone']] },
            Content of Hostname amongst others : {[i for i in modellingData['Hostname']] },
            Content of HostAndIP amongst others : {[i for i in modellingData['HostAndIP']]},
            Content of ApplicationName amongst others : {[i for i in modellingData['ApplicationName']]},
            Content of ApplicationOwner amongst others : {[i for i in modellingData['ApplicationOwner']]},
            You can use this information so that when users asks things like 'show me all servers  under {[i for i in modellingData['ManagementZone']][0]}
        """

    return system_instruction 


with tab3:
    import google.generativeai as genai
    from flask import Flask, request, jsonify, render_template

    # OpenAI API key
    # openai.api_key = 'sk-proj-Rx8CJjHPPCpjnUW5uWbRT3BlbkFJ2kafQieDladzH2D1zkmk'
    gemini_api = 'AIzaSyDeP_zjRubaAZOBE4iDe7nNFoiJyE3xF-w'



    genai.configure(api_key=gemini_api)
    generation_config = {
    "temperature": 1,
    "top_p": 0.95,
    "top_k": 64,
    "max_output_tokens": 15000,
    "response_mime_type": "text/plain",
    }
    safety_settings = [
    {
        "category": "HARM_CATEGORY_HARASSMENT",
        "threshold": "BLOCK_MEDIUM_AND_ABOVE",
    },
    {
        "category": "HARM_CATEGORY_HATE_SPEECH",
        "threshold": "BLOCK_MEDIUM_AND_ABOVE",
    },
    {
        "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
        "threshold": "BLOCK_MEDIUM_AND_ABOVE",
    },
    {
        "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
        "threshold": "BLOCK_MEDIUM_AND_ABOVE",
    },
    ]


    system_instruction = """
    You are an intelligent assistant designed to convert natural language queries into Pandas DataFrame operations. Your task is to interpret human queries and translate them into syntactically correct Python code using the Pandas library. Follow these detailed guidelines:

    1. Understand the User's Intent:
        Carefully analyze the user's natural language query to determine the requested operation.
        Identify the key elements:
        DataFrame name (if unspecified, ask the user).
        Columns to select or manipulate.
        Filters (e.g., date ranges, specific conditions).
        Aggregations (e.g., sum, average, count).
        Sorting, grouping, or any additional transformations.
        Validate and Refine the Query:

    2. Construct the Pandas Code:
        Translate the intent into Python code using Pandas.
        Use the appropriate Pandas functions and syntax, including:
        .loc[] or .query() for filtering rows.
        .groupby() for aggregation.
        .sort_values() for sorting.
        .pivot_table() or .unstack() for reshaping data, etc
        Ensure the query is syntactically correct and leverages Pandas best practices for readability and efficiency.

    3. Assumptions and Default Values:
        If the query does not specify a DataFrame name:
        You can infer the name of the dataframe from your understanding of the question. If the question is anything related to infrastructure monitoring, use modellingData as the default and you can also prompt the user for clarification if necessary.
        Here are the names of the columns in the table:
        {'LogTimestamp': dtype('Datetime'),
            'CPUUsage': dtype('float64'),
            'MemoryUsage': dtype('float64'),
            'TotalMemory': dtype('float64'),
            'DiskUsage': dtype('float64'),
            'TotalFreeDiskGB': dtype('float64'),
            'TotalDiskSpaceGB': dtype('float64'),
            'DiskLatency': dtype('float64'),
            'ReadLatency': dtype('float64'),
            'WriteLatency': dtype('float64'),
            'NetworkTrafficAggregate': dtype('float64'),
            'NetworkTrafficSent': dtype('float64'),
            'NetworkTrafficReceived': dtype('float64'),
            'Hostname': dtype('O'),
            'IPAddress': dtype('O'),
            'OperatingSystem': dtype('O'),
            'ManagementZone': dtype('O'),
            'Datacenter': dtype('O'),
            'DatacenterRegion': dtype('O'),
            'ApplicationName': dtype('O'),
            'ApplicationOwner': dtype('O'),
            'Vendor': dtype('O'),
            'OS': dtype('O'),
            'DriveLetter': dtype('O'),
            'HostAndIP': dtype('O'),
            'Overall Resource Utility: dtype('float')}
        If the query involves date filtering:
    Assume the default column name is LogTimestamp unless specified.
    Assume the date format is YYYY-MM-DD.
    For ambiguous column names:
    Provide the most likely interpretation based on context but note the assumption in your response.
    If the query involves aggregation: do aggregate and return the best pandas tables aggregration code 
    If the query involves sorting: do sort and return the best code query

    4. Examples:
        Basic Queries
        Human Query: "Show all transactions where the amount is greater than 100."
        Pandas Code: df[df['TransactionAmount'] > 100]

        Human Query: "Filter the data to include only transactions in June 2013."
        Pandas Code: df[(df['TransactionDate'] >= '2013-06-01') & (df['TransactionDate'] <= '2013-06-30')]

        Aggregations
        Human Query: "What is the total amount by customer gender?"
        Pandas Code: df.groupby('gender')['TransactionAmount'].sum()

        Human Query: "Find the average transaction amount per customer."
        Pandas Code: df.groupby('CustomerID')['TransactionAmount'].mean()

        Sorting and Formatting
        Human Query: "Sort transactions by the highest amount."
        Pandas Code: df.sort_values('TransactionAmount', ascending=False)

        Human Query: "Get the top 5 customers by total spending."
        Pandas Code: df.groupby('CustomerID')['TransactionAmount'].sum().nlargest(5)

    5. Handle Ambiguity and Errors:
        If the query is ambiguous, clarify the intent before proceeding:
        Example: "What do you mean by 'top transactions'? Is it by amount or frequency?"
        Check for potential errors or unsafe inputs:
        Example: Ensure filtering values exist in the DataFrame (e.g., column names).

    6. Output Format
        Always provide the full Pandas code snippet for execution.
        Use clear, readable formatting:
        Example:
        # Filter transactions greater than 100
        df[df['TransactionAmount'] > 100]

    7. Edge Cases:
        Handle missing data (NaN values) appropriately:
        Example: .dropna() or .fillna() if relevant to the query.
        Handle duplicate rows when necessary:
        Example: .drop_duplicates().

    8. Injections:
        Ensure that queries that may delete, truncate, or insert or drop any rows are clearly marked as such and ask for a revision of the query as you are not permitted to run queries that may harm the database.

    9. Clarification if your response is a pandas code:
        If your response is a pandas code, start your response sentence with '[PP]' then followed by the actual pandas code.
        If your response is not a pandas code, start your response sentence with '[NP]' then followed by your response.
        This will help seperating pandas code from other responses.

    10. Output Format:
        The output should be optimized so that it is a single pandas query string that can be executed directly in a pandas table.
        if its not a pandas query, ensure you dont reveal that you are using a pandas query, dont mention the name of the table, act as an agent that collects natural language and converts it to pandas query only. If the users input is not related to finding information about their data, answer briefly, dont mention pandas, direct them back to the information they seek to know from their database. Pandas is already imported, dont import it again. you are to be passed into another program as pandas query, so endeavour to output direct pandas query that can be run on a dataframe directly. you dont give a code that alters the table, if you asked in this regard, ask the user to speak to the database administrator for an update on thew data. you are to be used to query the database, not to update it. Active servers are servers that has sent information to the database within the last 5minutes, so you can give a query that finds all servers present in the database above last 5minutes. pls remember all needed libraries are already imported, no need to import them again. high resource usage are servers having Overall Resource Utility of above 85, low resource usage are servers having Overall Resource Utility of between 0 and 70, mid resource usage are servers having Overall Resource Utility of between 70 and 85. Use the pandas nunique always when you are asked to find the length of a particular variable relating to the dataframe. Return a pandas series instead of a list. If servers or hosts are referred to, the user is referring to the HostAndIP column in the dataframe, unless specifically stated. You can as well ask what they mean by servers, is it Hosts differentiated by the IP's or just Hosts in general. Dont ever mention 'pandas query' in your response.

    11. Specifics:
            Some times the user might for directs specifics. here are some specifics and where they can be found.
            Content of ManagementZone amongst others : {[i for i in modellingData['ManagementZone']] },
            Content of Hostname amongst others : {[i for i in modellingData['Hostname']] },
            Content of HostAndIP amongst others : {[i for i in modellingData['HostAndIP']]},
            Content of ApplicationName amongst others : {[i for i in modellingData['ApplicationName']]},
            Content of ApplicationOwner amongst others : {[i for i in modellingData['ApplicationOwner']]},
            You can use this information so that when users asks things like 'show me all servers  under {[i for i in modellingData['ManagementZone']][0]}
        """

    # import pandas as pd
    # pd.set_option('display.max_columns', None)
    # modellingData = pd.read_parquet('infraParq.parquet', engine = 'fastparquet')
    # modellingData['HostAndIP'] = modellingData['Hostname'] + modellingData['IPAddress'].str.replace('"', '')
    # modellingData['LogTimestamp'] = pd.to_datetime(modellingData['LogTimestamp'])

    model = genai.GenerativeModel(
                            model_name="gemini-1.5-flash",
                            safety_settings=safety_settings,
                            generation_config=generation_config,
                            system_instruction=system_instruction
    )

    history_ = []

    def query_gpt(prompt):
        convo = model.start_chat(history= history_)
        convo.send_message(prompt)
        model_response = convo.last.text
        if prompt != None:
            history_.append({"role": "user", "parts": [prompt]})
            history_.append({"role": "model", "parts": [convo.last.text]})
        return model_response

    chat, frame = tab3.columns([1,3], border = True)

    if prompt := st.chat_input('Chat with your data'):
        chat.chat_message('human').write(prompt)

        response = query_gpt(prompt)
        if response.split(']')[0] == '[PP': 
            chat.chat_message('ai').write('Here is your requested data. You can download it by hovering over the dataframe and clicking on the download icon at the top right corner of the table')
            # chat.chat_message('ai').write(response)
            output = response.split(']', 1)[1]
            try:
                # Evaluate the query
                output = eval(output)

                # Handle different output types
                if isinstance(output, pd.DataFrame):
                    frame.dataframe(output, use_container_width=True)
                    if output.empty: 
                        frame.info('No condition was met. The specifics you requested were not found in the database')
                        frame.warning('You can ask the chat to show all information on the table so to enable you see what you are not referencing correctly')
                elif isinstance(output, pd.Series):
                    frame.write(output.to_frame())  # Convert to DataFrame for display
                elif isinstance(output, list):
                    frame.write(pd.Series(output))
                elif isinstance(output, (int, float, str)):
                    frame.write(f'There are {output}')
                else:
                    frame.write("Unhandled Output Type: Pls reframe your request")
                    frame.write(output)

            except Exception as e:
                frame.error(f"Error occurred: {e}")
            # result = modellingData.query(output)
            
            # frame.write(output)
            # frame.dataframe(eval(output), use_container_width=True)
            # frame.dataframe(result, use_container_width=True)
            
        elif response.split(']')[0] == '[NP':
            chat.chat_message('ai').write(response.split(']', 1)[1])
    if not prompt:
        chat.warning('No query yet.')
        frame.warning('Nothing to display')

    st.markdown(
        """
        <div style="background-color: #e7f3fe; padding: 10px; border-left: 6px solid #2196F3; color: #333;">
            <strong>Info:</strong>
            <ul>
                <li>If the returned DataFrame is empty, then it means none of the conditions in your query were met.</li>
                <li>Check again and be sure of the specifics of your query.</li>
                <li>If you are querying specifics, ensure you are right with the name or spelling of the specific.</li>
                <li>Please be clear and direct as possible to ensure your request is processed with accuracy.</li>
            </ul>
        </div>
        """,
        unsafe_allow_html=True
    )
