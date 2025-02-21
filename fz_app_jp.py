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

USERNAME = os.getenv("APP_USERNAME", "kuruma")  
PASSWORD = os.getenv("APP_PASSWORD", "5sho")  

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.markdown("<div style='text-align:center'><h2>🔑 ログイン</h2></div>", unsafe_allow_html=True)
    entered_username = st.text_input("ユーザー名", value="", key="username")
    entered_password = st.text_input("パスワード", value="", type="password", key="password")
    if st.button("ログイン"):
        if entered_username == USERNAME and entered_password == PASSWORD:
            st.session_state.logged_in = True
            st.rerun()
        else:
            st.error("🚫 ユーザー名またはパスワードが違います")
    st.stop()

# ==============================
# Google Sheets Authentication (Cached)
# ==============================
SHEET_ID = "1upehCYwnGEcKg_zVQG7jlnNUykFmvNbuAtnxzqvSEcA"
SHEET_NAME = "Sheet1"

@st.cache_resource
def get_google_sheet():
    creds_json = os.getenv("GOOGLE_CREDENTIALS")
    if creds_json:
        creds_dict = json.loads(creds_json)
        creds = Credentials.from_service_account_info(creds_dict, scopes=["https://www.googleapis.com/auth/spreadsheets"])
        return gspread.authorize(creds).open_by_key(SHEET_ID).worksheet(SHEET_NAME)
    else:
        raise ValueError("GOOGLE_CREDENTIALS environment variable not found")

sheet = get_google_sheet()

# ==============================
# Initialize Session State
# ==============================
if "date" not in st.session_state:
    st.session_state.date = datetime.today()
if "selected_drivers" not in st.session_state:
    st.session_state.selected_drivers = set()
if "confirmed_drivers" not in st.session_state:
    st.session_state.confirmed_drivers = False
if "toll_road" not in st.session_state:
    st.session_state.toll_road = {}
if "one_way" not in st.session_state:
    st.session_state.one_way = {}
if "amount" not in st.session_state:
    st.session_state.amount = 200  

# ==============================
# Data Entry Section
# ==============================
st.title("🚗 Fz 車代管理アプリ")
st.header("データ入力")

st.session_state.date = st.date_input("試合日を選択してください", value=st.session_state.date)

# Driver selection using a static table
driver_list = ["平野", "ケイン", "山﨑", "萩原", "仙波し", "仙波ち", "久保", "落合", "浜島", "野波",
               "末田", "芳本", "鈴木", "山田", "佐久間", "今井", "西川"]

st.write("### 運転手を選択してください")
columns = st.columns(3)
new_selected_drivers = set()

for i, driver in enumerate(driver_list):
    with columns[i % 3]:
        if st.checkbox(driver, key=f"select_{driver}", value=(driver in st.session_state.selected_drivers)):
            new_selected_drivers.add(driver)

st.session_state.selected_drivers = new_selected_drivers

# Confirm Drivers Button
if st.button("運転手を確定する"):
    st.session_state.confirmed_drivers = True
    st.rerun()

# Only show amount selection & checkboxes after drivers are confirmed
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
# Load Data from Google Sheets (No Caching for Instant Updates)
# ==============================
def load_data():
    records = sheet.get_all_records()
    df = pd.DataFrame(records)

    # 🔹 Fix: Handle empty DataFrame case
    if df.empty:
        return pd.DataFrame(columns=["日付", "名前", "金額", "高速道路", "片道"])  # Return empty DataFrame with correct headers

    # 🔹 Fix: Check if "日付" column exists before using it
    if "日付" in df.columns:
        df["日付"] = pd.to_datetime(df["日付"], errors='coerce')
        df["年-月"] = df["日付"].dt.strftime("%Y-%m")
    else:
        st.warning("🚨 '日付' column not found in Google Sheets. Check if column names match exactly.")

    return df

df = load_data()

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
    st.session_state.date = datetime.today()
    st.session_state.selected_drivers = set()
    st.session_state.confirmed_drivers = False
    st.session_state.amount = 200  
    st.session_state.toll_road = {}  
    st.session_state.one_way = {}  
    st.rerun()

# ==============================
# Monthly Summary Section (Updates Instantly)
# ==============================
st.header("📊 月ごとの集計")

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
