import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from PIL import Image

st.set_page_config(
    page_title="Login Page",
    layout="centered"
)

st.title("NEMUKUNAI 😴🗡️")
st.subheader("Please log in to continue")

SUCCESS_GIF = "https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExazk4MG1qenhkdmRjYXlpMjBjZTFjZXZoNzVyOXhlM3J5dWpqb2RlNyZlcD12MV9naWZzX3NlYXJjaCZjdD1n/GeimqsH0TLDt4tScGw/giphy.gif"
WARNING_GIF = "https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExazk4MG1qenhkdmRjYXlpMjBjZTFjZXZoNzVyOXhlM3J5dWpqb2RlNyZlcD12MV9naWZzX3NlYXJjaCZjdD1n/nR4L10XlJcSeQ/giphy.gif" 
if "LoginState" not in st.session_state:
    st.session_state.login = None

#USER_CREDENTIALS = {databases(username:password)}

with st.form("login_form"):
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    submit_button = st.form_submit_button("Login")

    if submit_button:
        #if username in USER_CREDENTIALS and USER_CREDENTIALS[username] == password:
        if username and password:
            st.success(f"Welcome back, {username}!")
            st.session_state.login = SUCCESS_GIF
        else:
            st.warning("Please enter both username and password")
            st.session_state.login = WARNING_GIF

if st.session_state.login:
    st.image(st.session_state.login, width=300)
else:
    st.image("https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExazk4MG1qenhkdmRjYXlpMjBjZTFjZXZoNzVyOXhlM3J5dWpqb2RlNyZlcD12MV9naWZzX3NlYXJjaCZjdD1n/MDJ9IbxxvDUQM/giphy.gif", 
             width=300, 
             caption="Waiting for login...")