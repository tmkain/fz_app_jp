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

# Driver selection
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

# Only show amount selection & checkboxes after drivers are confirmed
if st.session_state.confirmed_drivers:
    st.session_state.amount = st.radio("金額を選択してください", [200, 400, 600, 800, 1000, 1200])

    for driver in st.session_state.selected_drivers:
        st.session_state.toll_road[driver] = st.checkbox(f"{driver} の高速道路利用", value=st.session_state.toll_road.get(driver, False), key=f"toll_{driver}")
        st.session_state.one_way[driver] = st.checkbox(f"{driver} の片道利用", value=st.session_state.one_way.get(driver, False), key=f"one_way_{driver}")

# ==============================
# Load Data from Google Sheets (Optimized)
# ==============================
@st.cache_data(ttl=60)
def load_data():
    records = sheet.get_all_values()
    if not records or len(records) < 2:
        return pd.DataFrame(columns=["日付", "名前", "金額", "高速道路", "片道", "送信グループID", "補足"])

    df = pd.DataFrame(records[1:], columns=records[0])
    if "日付" in df.columns:
        df["日付"] = pd.to_datetime(df["日付"], errors="coerce")
    
    return df

df = load_data()

# ==============================
# Save Data to Google Sheets (Appending instead of Overwriting)
# ==============================
def append_data(new_entries):
    sheet.append_rows(new_entries, value_input_option="USER_ENTERED")

# Submit Data
if st.button("送信"):  
    if st.session_state.selected_drivers:
        batch_id = int(time.time())

        new_entries = [[st.session_state.date.strftime("%Y-%m-%d"), driver, 
                        st.session_state.amount / (2 if st.session_state.one_way[driver] else 1),  
                        "あり" if st.session_state.toll_road[driver] else "なし", 
                        "あり" if st.session_state.one_way[driver] else "なし",
                        batch_id,
                        "+" if st.session_state.toll_road[driver] else ""
                       ] 
                       for driver in st.session_state.selected_drivers]

        append_data(new_entries)
        st.success("データが保存されました！")

# ==============================
# Monthly Summary Section (Cached for Speed)
# ==============================
st.header("📊 月ごとの集計")

if df.empty:
    st.warning("データがありません。")
else:
    df["年-月"] = df["日付"].dt.strftime("%Y-%m")
    
    summary = df.groupby(["年-月", "名前"], as_index=False)["金額"].sum()
    summary["補足"] = df.groupby(["年-月", "名前"])["補足"].apply(lambda x: "+" if "+" in x.values else "").reset_index(drop=True)
    
    summary = summary.pivot(index="年-月", columns="名前", values=["金額", "補足"]).fillna("")
    st.write(summary)

# ==============================
# CSV Download Option
# ==============================
st.header("📥 CSVダウンロード")
if not df.empty:
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False, encoding="cp932", columns=["日付", "名前", "金額", "高速道路", "片道", "補足"])
    st.download_button("CSVをダウンロード", data=csv_buffer.getvalue().encode("cp932"), file_name="fz_data.csv", mime="text/csv")

# ==============================
# Logout
# ==============================
if st.button("✅ 完了"):
    st.session_state.logged_in = False
    st.session_state.selected_drivers = set()
    st.success("✅ ログアウトしました。")
    st.rerun()
