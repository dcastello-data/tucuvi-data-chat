import yaml
import streamlit as st
from yaml.loader import SafeLoader
import streamlit_authenticator as stauth
from streamlit_authenticator.utilities import (CredentialsError,
                                               ForgotError,
                                               Hasher,
                                               LoginError,
                                               RegisterError,
                                               ResetError,
                                               UpdateError)
from chat import knowledge_base_chat
import os

# Configure the Streamlit page inside this app.
st.set_page_config(page_title="Knowledge Base Chat", layout="wide")

# Load the CSS
if os.path.exists("assets/style.css"):
    with open("assets/style.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

with open('config.yaml', 'r', encoding='utf-8') as file:
    config = yaml.load(file, Loader=SafeLoader)

authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days']
)

try:
    authenticator.login()
except LoginError as e:
    st.error(e)

# Creating a guest login button
try:
    authenticator.experimental_guest_login('Login with Google', provider='google',
                                            oauth2=config['oauth2'])
except LoginError as e:
    st.error(e)

# Authenticating user
if st.session_state['authentication_status']:
    #authenticator.logout()
    #st.write(f'Welcome *{st.session_state["name"]}*')
    knowledge_base_chat()
elif st.session_state['authentication_status'] is False:
    st.error('Username/password is incorrect')
elif st.session_state['authentication_status'] is None:
    st.warning('Please enter your username and password')