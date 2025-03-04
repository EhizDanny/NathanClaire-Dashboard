import streamlit as st
import warnings 
warnings.filterwarnings('ignore')
import pathlib
# import threading
import time
from playwright.sync_api import sync_playwright, Page, Playwright
import time
from datetime import datetime
import callbackFunctions as callbacks
st.set_page_config(
    page_title = 'AppMonitor', 
    page_icon = ':bar_chart:',
    layout = 'wide'
)
@st.cache_resource
def import_libraries():
    from streamlit import session_state as ss
    from streamlit_folium import st_folium
    import folium
    import streamlit_antd_components as antd
    from streamlit_extras.stylable_container import stylable_container 
    import json
    import pandas as pd
    import sqlite3
    import numpy as np
    import matplotlib.pyplot as plt
    import plotly.express as px
    import plotly.graph_objects as go
    return ss, st_folium, folium, antd, stylable_container, json, pd, sqlite3, np, plt, px, go
ss, st_folium, folium, antd, stylable_container, json, pd, sqlite3, np, plt, px, go = import_libraries()



# Predefined geolocations for major cities in Nigeria
# geolocations = {
#     "Lagos": {"latitude": 37.7749, "longitude": -122.4194},
#     "Abuja": {"latitude": 40.7128, "longitude": -74.0060},
#     "PortHarcourt": {"latitude": 51.5074, "longitude": -0.1278},
#     "Ibadan": {"latitude": 52.5200, "longitude": 13.4050},
#     "Ogun": {"latitude": 35.6895, "longitude": 139.6917},
#     "Onitsha": {"latitude": -33.8688, "longitude": 151.2093},
#     "Enugu": {"latitude": 35.6895, "longitude": 139.6917},
#     "Kaduna": {"latitude": 35.6895, "longitude": 139.6917},
#     "Kano": {"latitude": 35.6895, "longitude": 139.6917},
#     "Sokoto": {"latitude": 35.6895, "longitude": 139.6917},
# }
mapData = pd.read_csv('nigerianStatesCoordinates.csv')
mapData.rename(columns = {'Latitude': 'lat', 'Longitude': 'lon'}, inplace = True)
selectedLocations = [i for i in mapData.State]

# @st.cache_resource()
def load_css(filePath:str):
    with open(filePath) as f:
        st.html(f'<style>{f.read()}</style>')
css_path = pathlib.Path('style.css')
load_css(css_path)

# monitoring one link 
def monitor_link(link: str, page: Page, playwright: sync_playwright) -> None:
    """Navigates a website, captures performance metrics, and logs issues."""

    # start_time = time.time()
    # Capture network requests and response times
    start_time = time.time()
    requests_log = []

    def log_request(request) -> None:
        requests_log.append({
            "url": request.url,
            "method": request.method,
            "type": request.resource_type,
            "start_time": time.time(),
        })

    def log_response(response) -> None:
        for req in requests_log:
            if req["url"] == response.url:
                req["status"] = response.status
                req["end_time"] = time.time()
                req["duration"] = req["end_time"] - req["start_time"]

    # Listen for network events
    page.on("request", log_request)
    page.on("response", log_response)

    # Capture error logs 
    errors = []
    page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else errors.append(None))

    # Navigate to link 
    page.goto(link, wait_until="load")

    end_time = time.time() # stop time reading
    total_duration = end_time - start_time

    import json
    with open('requestLog.json', 'w') as f:
        json.dump(requests_log, f, indent = 4)


def main(link: str) -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        context = browser.new_context(
                    geolocation=ss.geoLocation,
                    permissions=["geolocation"]
                )
        page = context.new_page()

        monitor_link(link, page, playwright)

        # process the request Log data 
        with open('requestLog.json', 'r') as file:
            data = json.load(file)
        df = pd.DataFrame(data)
        df['end_time'] = df['end_time'].apply(lambda x: datetime.fromtimestamp(x).time())
        df['start_time'] = df['start_time'].apply(lambda x: datetime.fromtimestamp(x).time())
        df['duration'] = round(df['duration'], 2)

        context.close()
        browser.close()
        return df



if "log_messages" not in ss:
    ss.log_messages = []

def take_screenshot(url, screenshot_path):
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            context = browser.new_context()
            page = context.new_page()
            
            page.goto(url)  # Set a timeout for the page load
            
            page.screenshot(path=screenshot_path, full_page=False)
            browser.close()
            ss.log_messages.append("✅ Screenshot successfully captured!")
            ss.page_responded = True
            ss.screenshot_ready = True
    except Exception as e:
        ss.page_responded = False
        ss.error_message = str(e)
        ss.log_messages.append(f"❌ Error: {str(e)}")
        ss.screenshot_ready = False

if 'screenshot_ready' not in ss:
    ss.screenshot_ready = False


try:
    df = callbacks.fetchFromDB()
except Exception:
    pass


                #  ------------------------ Streamlit Implementation  ---------------- 
head1, head2, head3 = st.columns([1, 4, 1])
with head2:
    head2.markdown("""
    <div class="heading">
            <p style=" font-size: 2.7rem; font-weight: bold; color: #2c456b; text-align: center; font-family: "Source Sans Pro", sans-serif">Synthetic Monitoring System</p>
    </div>""", unsafe_allow_html=True)

# Session states declarations 
if 'auth' not in ss:
    ss.auth = 'No'

if 'show' not in ss:
    ss.show = False 

if 'nameTagList' not in ss: #If name is not previously in cache, ....
    try: # depend on db to provide tag lists
        ss.nameTagList = callbacks.fetchFromDB()['registeredTags'].tolist() 
        ss.nameTagSet = list(set([i for i in ss.nameTagList if len(i) >2]))
    except Exception: # If its also not in the db ....
        ss.nameTagList = [] # Create it
        ss.nameTagSet = list(set([i for i in ss.nameTagList if len(i) > 2]))
# else:
#     if 'newNameTag' in ss:
#         ss.nameTagList.append(ss.newNameTag)
#         ss.nameTagSet = list(set([i for i in ss.nameTagList if len(i) > 2]))

if 'urlList' not in ss:
    ss.urlList = []
try:
    ss.urlList = callbacks.fetchFromDB()['registeredURL'].tolist() 
    ss.urlSet = list(set(ss.urlList))
except Exception:
    ss.urlSet = list(set(ss.urlList))
    pass


if 'synthGroups' not in ss:
    try:
        ss.synthGroups = callbacks.fetchFromDB().groupby('Tags')['URL'].apply(list).to_dict()
    except Exception:
        ss.synthGroups = {}
if 'authentications' not in ss:
    # try:
        # ss.authentications = fetchFromDB().set_index('registeredURL')[['authKeysUsername', 'authKeysPassword']].apply(lambda x: [x['authKeysUsername'], x['authKeysPassword']], axis=1).to_dict()
    # except:
    ss.authentications = {}
if 'buttonClicked' not in ss:
    ss.buttonClicked = False
if 'completeReg' not in ss:
    ss.completeReg = False
if 'newURL' not in ss:
    ss.newURL = None



st.markdown(
    """
    <style>
    .custom-button {
        display: flex;
        justify-content: center;
        align-items: center;
        height: 38px; /* Adjust height to match text inputs */
        margin-top: -10px; /* Fine-tune vertical alignment */
    }
    </style>
    """,
    unsafe_allow_html=True,
)

tab1, tab2 = st.tabs(['HTTP Request Monitor', 'Simulated User Monitor'])
with tab1:
    control1, control2, control3 = tab1.columns([1,2,1])
    control3.selectbox(label='Monitor View', options= ['URL Link Registration', 'HTTP Request Performance Monitoring', 'Monitored Entity Overview'], key = 'view', ) 

    
    def linkInput():
            with stylable_container(
                key="visual_container21",
                css_styles="""{
                    box-shadow: rgba(0, 0, 0, 0.24) 0px 3px 8px;
                    padding: 20px 20px 20px 20px;
                    # margin-top: -10px;
                }"""): 
                col1, col3, col2 = st.columns([1.5,0.3,2])
                with col1:
                    col1.image('PNG/pngwing.com (17).png')
                with col2:
                    antd.divider(label='URL Registration', icon='search', align='center', color='gray')
                    col21, col22, col23 = col2.columns([1.5, 1, 0.8])
                    # col21.markdown('<br>', unsafe_allow_html=True)
                    # col22.markdown('<br>', unsafe_allow_html=True)
                    # col23.markdown('<br>', unsafe_allow_html=True)
                    
                    # First row 
                    col21.text_input(label='Register a name tag', placeholder='NCG Monitoring Group', key='newNameTag', help='Register a name tag', on_change=callbacks.addNameTag) # Add the item to temporary namTag holder to make it avaialble for choosing in options
                    col22.selectbox(label='Select from existing name tag', options = ss.nameTagSet, key='existingNameTag', help='Select from existing name tag if the name tag is already registered', index = len(ss.nameTagSet) -1)
                    col23.markdown('<div class="custom-button">', unsafe_allow_html=True)
                    col23.button('Register Tag', use_container_width=True, type='secondary', help='Register a name tag to have access', key='registerButton', on_click=callbacks.updateShowURLPart)

                    if ss.show:
                        if ss.existingNameTag is not None:
                            col21.text_input(label='Enter URL', key='newURL', placeholder='https://ncgafrica.com', help='Enter URL to be monitored')
                            ss.urlList.append(ss.newURL)
                            col22.selectbox(label='Add Authentication', options=['Yes', 'No'], key='addAuth', index=1,)
                            if ss.addAuth == 'Yes':
                                if ss.newURL in ss.authentications.keys():
                                    st.toast('🔊  There is an already existing authentication for this URL. \nYour new input will overwrite it')
                                else:
                                    pass

                            dontAuthenticate = True if ss.addAuth == 'No' else False

                            col23.selectbox(label='Auth Type', options=['Basic Auth', 'Bearer Auth'], key='authType', index=0, help='Select the type of authentication to be used', disabled=dontAuthenticate)
                            col21.text_input(label='Enter Username or Email', placeholder='user_me@example.com', key='userName', help='Enter username or email', disabled=dontAuthenticate)
                            col22.text_input(label='Enter Password', placeholder='password123', key='passWord', type='password', disabled=dontAuthenticate)
                            col23.markdown('<div class="custom-button">', unsafe_allow_html=True)
                            if ss.newURL is not None:
                                if ss.newURL[:8] == 'https://':
                                    if col23.button('Register URL', key='completeRegistration', use_container_width=True,):
                                        st.toast(f'🔊 Successfully Registered {ss.newURL[8:19]} under {ss.existingNameTag}')
                                        ss.completeReg = True
                                        #------------ Working on screenshot 
                                        # ss.page_responded = False # Reset the status of the screenshot 
                                        # threading.Thread(target=take_screenshot, args=(ss.newURL, "snippet.png"), daemon=True).start()
                                        # for msg in ss.log_messages:
                                        #     st.write(msg)

                                        # -----------
                                
                                # col23.markdown("</div>", unsafe_allow_html=True)

                                        if len(ss.nameTagList) > 0: # If the tag has been chosen
                                            if ss.newURL: # If a URL was entered
                                                if ss.existingNameTag not in ss.synthGroups.keys(): # Check if the tag is already registered, if not
                                                    ss.synthGroups[ss.existingNameTag] = [ss.newURL] # Create it as key, and a corresponding URL to it 
                                                else: # But if the tag is already registered
                                                    if ss.newURL not in ss.synthGroups[ss.existingNameTag]:  # and the URL is not registered under it
                                                        ss.synthGroups[ss.existingNameTag].append(ss.newURL) # Register the URL then
                                                    else:
                                                        st.toast(f'🔊 {ss.newURL[8:19]}... has already been registered under {ss.existingNameTag}')
                                                ss.authNeeded = False
                                                if ss.addAuth == 'Yes':
                                                    if ss.newURL in ss.authentications.keys():
                                                        st.toast('Authentication already registered')
                                                        ss.authNeeded = False
                                                    else:
                                                        ss.authentications[ss.newURL] = [ss.userName, ss.passWord]
                                                        ss.authNeeded = True
                                else:
                                    st.error('🚨 Please start your address with an https://')
                            
                            # if col23.button('Register New URL', use_container_width=True):
                            #     st.rerun(scope = 'app')
                                                    

    if ss.view == 'URL Link Registration':        
        linkInput()

        antd.divider(label='Synthetic Monitor Specification', icon='check-circle', align='center', color='gray')
        if ss.completeReg:
            st.markdown('<br>', unsafe_allow_html=True)
            # side1, side2 = tab1.columns([1,2])

            @st.fragment
            def registerMonitor():
                side1, side2 =  st.columns([1.5,2])
                with side1:
                    side11, side12 = side1.columns([1,1])
                    side11.multiselect(label='Browser Type', options=['Chromium', 'Firefox', 'Webkit'], key='browserType', placeholder='Chromium', disabled=True)
                    side12.selectbox(label='Synthetic Event Interval', options=[str(i) + ' minutes' for i in range(10, 61, 10)], key='monitoringLocation')
                    side11.multiselect(label='Monitored GeoLocation', options=[i for i in selectedLocations], key='geoLocation', help='You can select multiple locations', default='Lagos')
                    side12.markdown('<div class="custom-button">', unsafe_allow_html=True)
                    if side12.button('Register Monitor', key='registerMonitor'):
                        # Didnt make the urlColumn in db a unique column so that the page will be resaved for each call so for it reflect an update in the page 
                        callbacks.lodgeToDB(ss.existingNameTag, ss.newURL, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 'True' if ss.authNeeded else 'False')
                        
                        side12.toast('🔊 Successfully Registered a Synthetic Monitor. Go to performance tab to view the performance of the URL')

                        mpdata = mapData.copy() 
                        mpdata = mpdata[mpdata['State'].isin(ss.geoLocation)]

                        mapView, pageView = side2.tabs(['Location View', 'Page Snapshot'])
                        mapView.map(mpdata, size=100 if len(ss.geoLocation) == 1 else 15000, color="#FFA500") 

                        # Create a saveToMemory name for the image snippet using their URL
                        image_name = ss.newURL
                        image_name = image_name[:-4] # Remove .png
                        image_name = image_name.replace('.','_') # Replace all . with _
                        image_name+='.png' # Add .png back to it

                        ss.page_responded = False
                        take_screenshot(ss.newURL, f'{image_name}')  
                        responded = False if not ss.page_responded else True
                        if responded:
                            try:
                                with sqlite3.connect('SyntheticDB') as conn:  # Ensure the database file has the correct extension
                                    c = conn.cursor()
                                    # Create the table if it doesn't exist
                                    c.execute("""CREATE TABLE IF NOT EXISTS SNIPPETS (
                                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                                        imageName TEXT UNIQUE)
                                    """)
                                    try: # The imageName is a unique column, if the imageName exist, it will throw error. Try and error block averts that
                                        c.execute("INSERT INTO SNIPPETS (imageName) VALUES (?)", (f'{image_name}',)) # Insert a new image name into the table
                                        conn.commit()  # Commit the changes to the database. This is necessary to save the changes
                                    except Exception: 
                                        pass
                                    c.execute("SELECT * FROM SNIPPETS WHERE imageName = ?", (f'{image_name}',)) # Fetch the last inserted row
                                    row = c.fetchone() # This will retrieve the row you just inserted
                                    if row:
                                        db_image_name = row[1]
                            except Exception:
                                db_image_name = None
                                pass
                            pageView.image(db_image_name)
                        else:
                            pageView.image('PNG/pngwing.com (20).png')
                            pass
            registerMonitor()


    elif ss.view == 'HTTP Request Performance Monitoring':
        @st.fragment
        def requestOutput():
            place1, place2, place3, place4 = st.columns([1,1,1,3], gap='large')
            try:
                with sqlite3.connect('SyntheticDB') as conn:
                    c = conn.cursor()
                    df = pd.read_sql_query('SELECT * FROM oneLinkMonitor', conn)
                if 'chosenTag' not in ss:
                    try: 
                        ss.chosenTag = df['registeredTags'].tolist()[0]
                    except Exception: 
                        ss.choseTag = None
                if 'chosenURL' not in ss:
                    try: 
                        ss.chosenURL = df['registeredURL'].tolist()[0]
                    except Exception: 
                        ss.chosenURL = None
                if 'tags' not in ss:
                    try: 
                        ss.tags = df['registeredTags'].tolist()
                    except Exception: 
                        ss.tags = None
            except Exception:
                df = None


            if df.empty:
                callbacks.dialoguebox('You dont have any URL registered. Pls register one')

            ss.tagsSet = list(set(ss.tags)) if ss.tags is not None else None

            place1.markdown(f"""
                <div class=" metrics text-center">
                    <p style="font-size: 18px; font-weight: bold; text-align: center; align-items: center;" >Tag Name</p>
                    <p style="margin-top: -15px; font-size: 14px; text-align: center; align-items: center; font-family: Tahoma, Verdana;">{f"{'No Data' if not ss.chosenTag else ss.chosenTag}"}</p>
                </div> """, unsafe_allow_html= True)
            place2.markdown(f"""
                <div class=" metrics text-center">
                    <p style="font-size: 18px; font-weight: bold; text-align: center; align-items: center;" >Monitored URL</p>
                    <p style="margin-top: -15px; font-size: 14px; text-align: center; align-items: center; font-family: Tahoma, Verdana;">{f"{'No Data' if not ss.chosenURL else ss.chosenURL[8:40] }..."}</p>
                </div> """, unsafe_allow_html= True)
                
                # st.write(ss.urlSet)
            # place3.
            out1, out2 = st.columns([1,3], border=True, )
            out11, out12 = out1.columns([1,1])
            out11.selectbox(label='Choose Tag', options=[i for i in ss.tagsSet ] if ss.tagsSet is not None else None, key='chosenTag', on_change=callbacks.updateSelectedTag)
            ss.possibleURL = df[df['registeredTags'] == ss.chosenTag]['registeredURL'].tolist() if not df.empty else None
            out12.selectbox(label='Choose URL', options=list(set([i for i in ss.possibleURL ])) if ss.possibleURL is not None else None, key='chosenURL', on_change=callbacks.updateSelectedURL)
            
            
            with out1:
                one, two = out1.columns([4,1], gap='small')
                one.info('Availability:')
                two.info(3)
                one.info('Average Load Time:')
                two.info(2)
                one.info('Monitored Location:')
                two.info(3)
                one.info('Monitored Browsers:')
                two.info(4)
            with out2:
                with st.container(height=400):
                    if ss.chosenURL is not None:
                        image_name2 = ss.chosenURL
                        image_name2 = image_name2[:-4] # Remove .png
                        image_name2 = image_name2.replace('.','_') # Replace all . with _
                        image_name2+='.png' # Add .png back to it

                    try:
                        with sqlite3.connect('SyntheticDB') as conn:
                            c = conn.cursor()
                            c.execute("SELECT * FROM SNIPPETS WHERE imageName = ?", (f'{image_name2}',))
                            row = c.fetchone()[1]
                            if row:
                                st.image(row)
                    except Exception:
                        st.image('PNG/pngwing.com (20).png')

                    #     st.image(r'/Users/Ehiz/Documents/Nathan Claire/Edge/Dashboards/Infrastructure/SyntheticMonitoring/snippet.png', caption='Snippet of the URL')
                        # else:
                       #     st.image(r'/Users/Ehiz/Documents/Nathan Claire/Edge/Dashboards/Infrastructure/SyntheticMonitoring/PNG/pngwing.com (19).png', caption='Select a URL') 
        requestOutput()

# st.write(ss)



# import pydeck as pdk
# df = pd.read_csv('nigerianStatesCoordinates.csv')
# # Define Map Layer
# layer = pdk.Layer(
#     "ScatterplotLayer",
#     data=df,
#     get_position=["Longitude", "Latitude"],
#     get_radius=50000,  # Adjust the size of the points
#     get_color=[255, 0, 0, 160],  # Red color with transparency
#     pickable=True,
# )

# # Define Map View
# view_state = pdk.ViewState(
#     latitude=9.0579, longitude=7.4951, zoom=5, pitch=0
# )

# # Create Pydeck Deck
# map_deck = pdk.Deck(layers=[layer], initial_view_state=view_state, tooltip={"text": "{State}, {Capital}"})

# # Display Map
# st.write("## Nigeria States Map")
# st.pydeck_chart(map_deck)




























