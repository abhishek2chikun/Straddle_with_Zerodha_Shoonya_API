import streamlit as st
import pandas as pd
import datetime
from PIL import Image
import json
import base64
import hashlib
import algo

#configurando página
logo_image = Image.open("./logo.png")
st.set_page_config(page_title='Straddle Terminal' , page_icon=logo_image,layout="wide")


def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password,hashed_text):
    if make_hashes(password) == hashed_text:
        return hashed_text
    return False

# DB Management
import sqlite3
conn = sqlite3.connect('data.db')
c = conn.cursor()

# DB  Functions
def create_usertable():
    c.execute('CREATE TABLE IF NOT EXISTS userstable(Username TEXT,Password TEXT,ClientId TEXT,ZerodhaPassword TEXT,APIKey TEXT,APISecret TEXT,TOTP TEXT)')


def add_userdata(username,password,ClientId,ZerodhaPassword,APIKey,APISecret,Totp):
    c.execute('INSERT INTO userstable(username,password,ClientId,ZerodhaPassword,APIKey,APISecret,TOTP) VALUES (?,?,?,?,?,?,?)',(username,password,ClientId,ZerodhaPassword,APIKey,APISecret,Totp))
    conn.commit()

def login_user(username,password):
    c.execute('SELECT * FROM userstable WHERE username =? AND password = ?',(username,password))
    data = c.fetchall()
    return data


def view_all_users():
    c.execute('SELECT * FROM userstable')
    data = c.fetchall()
    return data



def main():
    """Simple Login App"""

    st.sidebar.image(logo_image, width=150)

    menu = ["Login","SignUp"]
    choice = st.sidebar.selectbox("Menu",menu)


    if choice == "Login":
        # st.subheader("Login Section")

        
        username = st.sidebar.text_input("User Name")
        password = st.sidebar.text_input("Password",type='password')
        if st.sidebar.checkbox("Login"):
            # if password == '12345':
            create_usertable()
            hashed_pswd = make_hashes(password)

            result = login_user(username,check_hashes(password,hashed_pswd))
            # print(result)
            if result:

                st.sidebar.success("Logged In as {}".format(username))

                st.write('<style>div.row-widget.stRadio > div{flex-direction:row;justify-content: center;} </style>', unsafe_allow_html=True)

                # st.write('<style>div.st-bf{flex-direction:column;} div.st-ag{font-weight:bold;padding-left:2px;}</style>', unsafe_allow_html=True)
                st.markdown("<h1 style='text-align: Center; color: blue;'>Straddle</h1>", unsafe_allow_html=True)                            

                task=st.radio('',("Terminal","Dashboard"))

                # task = st.rad("Tabs",["Terminal","Dashboard","Profiles"])
                if task == "Terminal":
#                     {
#  "EntryTime":"9,16,0",
#  "ExitTime":"3,00,0",
#  "StopLossPoint":40,
#  "Index":"BANKNIFTY",
#  "Qty":25,
#  "MaxRetry":4
# }                   
                    col1,col2,col3 = st.columns(3)
                    with col1:
                        EntryTime = st.time_input("Select Entry Time",value=datetime.time(9,16))
                        ''
                        MaxRetry = st.number_input('Enter Max Retry',value=4,step=1)

                    with col3:
                        ExitTime = st.time_input("Select Exit Time",value=datetime.time(3,00))
                        ''
                        Qty = st.number_input('Enter Qty',value=25,step=25)

                        
                    
                    with col2:
                        ''
                        ''
                        Index = st.selectbox("Select the Index",['BANKNIFTY','NIFTY'])
                        ''
                        StopLossPoint = st.number_input('Enter the Stoploss point in',value=40,step=10)
                        ''
                        ''
                        startButton = st.button("Click to Start the Straddle",help='Please review before Starting')
                        with open(f'./INFO/Algostatus.json','r') as f:
                                    Algostatus= json.load(f)
                        if startButton:
                            print(Algostatus['status'])
                            if Algostatus['status'] != "Active": 
                                Param = {'EntryTime':str(EntryTime).replace(':',','),'ExitTime':str(ExitTime).replace(':',','),"Symbol": Index, "Qty": Qty,'StopLossPoint':StopLossPoint, "MaxRetry": MaxRetry}
                                with open(f'./INFO/Strategy.json','w') as f:
                                    json.dump(Param,f)
                                
                                #---Call the Algo

                                Algostatus['status'] = "Active"
                                

                                st.success('Straddle Parameter Saved, Algo is Active Now!')

                                with open(f'./INFO/Algostatus.json','w') as f:
                                    json.dump(Algostatus,f)
                                
                            else:
                                st.warning("Algo has already started, if something went wrong, Stop the Algo below👇 ")
                            

                            
                        StopAlgo = st.button(f'Click to Exit All Position',help='All the position will be Closed')
                        if StopAlgo:
                            st.warning("Algo has stopped, All the position will be Closed if any")

                            Algostatus['status'] = "Free"
                            with open(f'./INFO/Algostatus.json','w') as f:
                                json.dump(Algostatus,f)
                        



                    
                        
                        
                    

                elif task == "Dashboard":
                    import plotly.express as px
                    path ='.'

                    
                    st.markdown("<h4 style='text-align: left; color: red;'>Graph</h4>", unsafe_allow_html=True)

                    df = px.data.stocks()
                    fig = px.line(df, x='date', y="GOOG")

                    # Plot!
                    st.plotly_chart(fig, use_container_width=True)

                    position = pd.read_csv(f'{path}/position.csv',index_col=[0])

                    def get_table_download_link_csv(df):
                        #csv = df.to_csv(index=False)
                        csv = df.to_csv().encode()
                        #b64 = base64.b64encode(csv.encode()).decode() 
                        b64 = base64.b64encode(csv).decode()
                        href = f'<a href="data:file/csv;base64,{b64}" download="Positions.csv" target="_blank">Download csv file</a>'
                        return href

                    col1,col2= st.columns([1,1])
                    def highlight_cols(s):
                        color = 'red'
                        return f'background-color:{color}'

                    df = position.style.applymap(highlight_cols, subset=pd.IndexSlice[:, ['P&L']])

                    
                    #with col1:
                    st.markdown("<h4 style='text-align: left; color: red;'>Position</h4>", unsafe_allow_html=True)

                    st.dataframe(df)
                    st.markdown(get_table_download_link_csv(position), unsafe_allow_html=True)


        
            else:
                st.warning("Incorrect Username/Password")





    elif choice == "SignUp":
        st.markdown("<h3 style='text-align: center; color: red;'>Create New Account</h3>", unsafe_allow_html=True)

        col1,col2,col3= st.columns(3)
        with col1:
            new_user = st.text_input("Username")
            ClientID = st.text_input("Enter Finvasia Client ID")
            APIKey = st.text_input("Enter API Key")
            Vendor_code = st.text_input("Enter Vendor Code")

        with col3:
            new_password = st.text_input("Password",type='password')
            ZerodhaPassword = st.text_input("Enter Finvasia Password",type='password')
            APISecret = st.text_input("Enter API Secret")
            imei = st.text_input("Enter imei")
        with col2:
            ''
            ''
            ''
            ''
            ''
            ''
            ''
            ''
            ''
            ''
            ''
            ''
            ''
            Totp = st.text_input("Enter TOTP")
            Signup = st.button("Signup")

        if Signup:
            create_usertable()
            user_result = view_all_users()
            # print(user_result)
            flag = False
            for user in user_result:
                if user[0] == new_user or user[2] == ClientID:
                    st.error("Username/ClientID Already exist")
                    flag = True
                    break
            if flag == False:
                add_userdata(new_user,make_hashes(new_password),ClientID,ZerodhaPassword,APIKey,APISecret,Totp)
                with open(f'./INFO/Users/{new_user}.json','w') as f:
                    json.dump({'user':new_user,'password':new_password,'ClientID':ClientID,'ZerodhaPassword':ZerodhaPassword,'APIKey':APIKey,'APISecret':APISecret,'Totp':Totp},f)
                st.success("You have successfully created a valid Account")
                st.info("Go to Login Menu to login")



if __name__ == '__main__':
    main()