import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import os
import json
import time

# ==============================
# Secure Full-Screen Login System
# ==============================

@st.cache_resource
def get_credentials():
    return os.getenv("APP_USERNAME"), os.getenv("APP_PASSWORD")

USERNAME, PASSWORD = get_credentials()

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
# Google Sheets Authentication (Delayed Until After Login)
# ==============================

@st.cache_resource
def get_google_credentials():
    creds_json = os.getenv("GOOGLE_CREDENTIALS")
    if creds_json:
        return json.loads(creds_json)
    else:
        raise ValueError("GOOGLE_CREDENTIALS environment variable not found")

@st.cache_resource
def get_google_sheet():
    creds_dict = get_google_credentials()
    creds = Credentials.from_service_account_info(creds_dict, scopes=["https://www.googleapis.com/auth/spreadsheets"])
    return gspread.authorize(creds).open_by_key("1upehCYwnGEcKg_zVQG7jlnNUykFmvNbuAtnxzqvSEcA").worksheet("Sheet1")

if st.session_state.logged_in:
    sheet = get_google_sheet()  # 🔹 Load Google Sheets **ONLY after login**

# ==============================
# Initialize Session State
# ==============================
if "date" not in st.session_state:
    st.session_state.date = datetime.today()
if "selected_drivers" not in st.session_state:
    st.session_state.selected_drivers = set()
if "confirmed_drivers" not in st.session_state:
    st.session_state.confirmed_drivers = False
if "one_way" not in st.session_state:
    st.session_state.one_way = {}
if "toll_round_trip" not in st.session_state:
    st.session_state.toll_round_trip = {}
if "toll_one_way" not in st.session_state:
    st.session_state.toll_one_way = {}
if "amount" not in st.session_state:
    st.session_state.amount = 200  

# ==============================
# Data Entry Section
# ==============================
st.title("🚗 Fz 車代管理アプリ")
st.header("データ入力")

st.session_state.date = st.date_input("試合日を選択してください", value=st.session_state.date)

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

if st.button("運転手を確定する"):
    st.session_state.confirmed_drivers = True

if st.session_state.confirmed_drivers:
    st.session_state.amount = st.radio("金額を選択してください", [200, 400, 600, 800, 1000, 1200])

    for driver in st.session_state.selected_drivers:
        st.session_state.one_way[driver] = st.checkbox(f"{driver} の一般道路片道", value=st.session_state.one_way.get(driver, False), key=f"one_way_{driver}")
        st.session_state.toll_round_trip[driver] = st.checkbox(f"{driver} の高速道路往復", value=st.session_state.toll_round_trip.get(driver, False), key=f"toll_round_trip_{driver}")
        st.session_state.toll_one_way[driver] = st.checkbox(f"{driver} の高速道路片道", value=st.session_state.toll_one_way.get(driver, False), key=f"toll_one_way_{driver}")

# ==============================
# Save Data to Google Sheets
# ==============================
def append_data(new_entries):
    sheet.append_rows(new_entries, value_input_option="USER_ENTERED")

if st.button("送信"):  
    if st.session_state.selected_drivers:
        batch_id = int(time.time())
        game_date = st.session_state.date.strftime("%m/%d")

        new_entries = []
        for driver in st.session_state.selected_drivers:
            amount = st.session_state.amount
            supplement = ""

            if st.session_state.one_way[driver]:  
                amount /= 2  
            if st.session_state.toll_round_trip[driver]:  
                amount = 0  
                supplement = f"++{game_date}"  
            elif st.session_state.toll_one_way[driver]:  
                amount /= 2  
                supplement = f"+{game_date}"  

            new_entries.append([
                st.session_state.date.strftime("%Y-%m-%d"), 
                driver, 
                amount, 
                "あり" if st.session_state.toll_round_trip[driver] or st.session_state.toll_one_way[driver] else "なし",
                "あり" if st.session_state.one_way[driver] else "なし",
                batch_id,
                supplement
            ])

        append_data(new_entries)
        st.success("データが保存されました！")

# ==============================
# Monthly Summary Section (Lazy Loading for Speed)
# ==============================
st.header("📊 月ごとの集計")

@st.cache_data(ttl=60)
def load_summary():
    records = sheet.get_values("A1:G50")  # Load only first 50 rows for speed
    df = pd.DataFrame(records[1:], columns=records[0]) if records else pd.DataFrame()
    
    if not df.empty:
        df["年-月"] = pd.to_datetime(df["日付"], errors="coerce").dt.strftime("%Y-%m")
        summary = df.groupby(["年-月", "名前"], as_index=False)["金額"].sum()
        if "補足" in df.columns:
            summary["補足"] = df.groupby(["年-月", "名前"])["補足"].apply(lambda x: " ".join(x.dropna().unique())).reset_index(drop=True)
        else:
            summary["補足"] = ""
        return summary.pivot(index="年-月", columns="名前", values=["金額", "補足"]).fillna("")
    return pd.DataFrame()

if st.session_state.logged_in:
    summary = load_summary()
    if not summary.empty:
        st.write(summary)
    else:
        st.warning("データがありません。")

# ==============================
# Logout
# ==============================
if st.button("✅ 完了"):
    st.session_state.logged_in = False
    st.session_state.selected_drivers = set()
    st.success("✅ ログアウトしました。")
    st.rerun()
