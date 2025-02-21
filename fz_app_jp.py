import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import os
import json

# ==============================
# Secure Full-Screen Login System
# ==============================

# 🔐 Use environment variables for better security
USERNAME = os.getenv("APP_USERNAME", "admin")  # Default: "admin"
PASSWORD = os.getenv("APP_PASSWORD", "secret123")  # Default: "secret123"

# Check if the user is already logged in
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.markdown("<div style='text-align:center'><h2>🔑 ログイン</h2></div>", unsafe_allow_html=True)

    # Login form
    entered_username = st.text_input("ユーザー名", value="", key="username")
    entered_password = st.text_input("パスワード", value="", type="password", key="password")

    if st.button("ログイン"):
        if entered_username == USERNAME and entered_password == PASSWORD:
            st.session_state.logged_in = True
            st.rerun()  # Refresh to show the main app
        else:
            st.error("🚫 ユーザー名またはパスワードが違います")

    st.stop()  # Stop execution here if login fails

# ==============================
# Google Sheets Authentication (Runs only after login)
# ==============================
SHEET_ID = "1upehCYwnGEcKg_zVQG7jlnNUykFmvNbuAtnxzqvSEcA"
SHEET_NAME = "Sheet1"

def authenticate_google_sheets():
    creds_json = os.getenv("GOOGLE_CREDENTIALS")
    if creds_json:
        creds_dict = json.loads(creds_json)
        creds = Credentials.from_service_account_info(creds_dict, scopes=["https://www.googleapis.com/auth/spreadsheets"])
        return gspread.authorize(creds)
    else:
        raise ValueError("GOOGLE_CREDENTIALS environment variable not found")

client = authenticate_google_sheets()
sheet = client.open_by_key(SHEET_ID).worksheet(SHEET_NAME)

# ==============================
# Initialize Session State
# ==============================
if "date" not in st.session_state:
    st.session_state.date = datetime.today()  # Default to today’s date
if "selected_drivers" not in st.session_state:
    st.session_state.selected_drivers = []
if "confirmed_drivers" not in st.session_state:
    st.session_state.confirmed_drivers = False  # Controls when checkboxes appear
if "toll_road" not in st.session_state:
    st.session_state.toll_road = {}  # Stores 高速道路利用 checkboxes
if "one_way" not in st.session_state:
    st.session_state.one_way = {}  # Stores 片道 checkboxes
if "amount" not in st.session_state:
    st.session_state.amount = 200  # Default yen amount

# ==============================
# Data Entry Section
# ==============================
st.title("🚗 Fz 車代管理アプリ")
st.header("データ入力")

# User Inputs
st.session_state.date = st.date_input("試合日を選択してください", value=st.session_state.date)

driver_list = ["平野", "ケイン", "山﨑", "萩原", "仙波し", "仙波ち", "久保田", "落合", "浜島", "野波",
               "末田", "芳本", "鈴木", "山田", "佐久間", "今井", "西川"]

st.session_state.selected_drivers = st.multiselect(
    "運転手を選択してください", driver_list, default=st.session_state.selected_drivers
)

# "Confirm Drivers" Button
if st.button("運転手を確定する"):
    st.session_state.confirmed_drivers = True
    st.rerun()

# Only show checkboxes after drivers are confirmed
if st.session_state.confirmed_drivers:
    st.session_state.amount = st.radio("金額を選択してください", [200, 400, 600, 800], index=[200, 400, 600, 800].index(st.session_state.amount))

    for driver in st.session_state.selected_drivers:
        if driver not in st.session_state.toll_road:
            st.session_state.toll_road[driver] = False
        if driver not in st.session_state.one_way:
            st.session_state.one_way[driver] = False

        st.session_state.toll_road[driver] = st.checkbox(f"{driver} の高速道路利用", value=st.session_state.toll_road[driver], key=f"toll_{driver}")
        st.session_state.one_way[driver] = st.checkbox(f"{driver} の片道利用", value=st.session_state.one_way[driver], key=f"one_way_{driver}")

# ==============================
# Save Data to Google Sheets
# ==============================
def save_data(new_entries):
    existing_data = sheet.get_all_records()
    df = pd.DataFrame(existing_data)
    new_df = pd.DataFrame(new_entries, columns=["日付", "名前", "金額", "高速道路", "片道"])
    updated_df = pd.concat([df, new_df], ignore_index=True)
    sheet.clear()
    sheet.update([updated_df.columns.values.tolist()] + updated_df.values.tolist())

# Submit Data
if st.button("送信"):  
    if st.session_state.selected_drivers:
        new_entries = [[st.session_state.date.strftime("%Y-%m-%d"), driver, 
                        (st.session_state.amount + (1000 if st.session_state.toll_road[driver] else 0)) / (2 if st.session_state.one_way[driver] else 1), 
                         "あり" if st.session_state.toll_road[driver] else "なし", 
                         "あり" if st.session_state.one_way[driver] else "なし"] 
                        for driver in st.session_state.selected_drivers]
        save_data(new_entries)
        st.success("データが保存されました！")
        st.rerun()
    else:
        st.warning("運転手を選択してください。")

# ==============================
# Clear Button Functionality (Resets Everything)
# ==============================
if st.button("クリア"):
    st.session_state.date = datetime.today()  # Reset date to today
    st.session_state.selected_drivers = []  # Clear selected drivers
    st.session_state.confirmed_drivers = False  # Reset confirmation
    st.session_state.amount = 200  # Reset amount selection to default
    st.session_state.toll_road = {}  # Clear checkboxes
    st.session_state.one_way = {}  # Clear checkboxes
    st.rerun()  # Force Streamlit to refresh the UI

# ==============================
# Monthly Summary Section
# ==============================
st.header("📊 月ごとの集計")

def load_data():
    try:
        records = sheet.get_all_records()
        df = pd.DataFrame(records)
        df["日付"] = pd.to_datetime(df["日付"], errors='coerce')
        df.dropna(subset=["日付"], inplace=True)
        df["年-月"] = df["日付"].dt.strftime("%Y-%m")
        return df
    except:
        return pd.DataFrame(columns=["日付", "名前", "金額", "年-月", "高速道路", "片道"])

df = load_data()
if df.empty:
    st.warning("データがありません。")
else:
    summary = df.groupby(["年-月", "名前"], as_index=False)["金額"].sum()
    summary["年-月"] = summary["年-月"].astype(str)
    summary = summary.pivot(index="年-月", columns="名前", values="金額").fillna(0)
    st.write(summary)

# ==============================
# CSV Download Option
# ==============================
st.header("📥 CSVダウンロード")
if not df.empty:
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(label="CSVをダウンロード", data=csv, file_name="fz_data.csv", mime="text/csv")
