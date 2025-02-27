import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import os
import json
import time

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
if "one_way" not in st.session_state:
    st.session_state.one_way = {}
if "toll_round_trip" not in st.session_state:
    st.session_state.toll_round_trip = {}
if "toll_one_way" not in st.session_state:
    st.session_state.toll_one_way = {}
if "toll_cost" not in st.session_state:
    st.session_state.toll_cost = {}
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

        # ✅ Add a toll cost input field with "未定" option
        if st.session_state.toll_round_trip[driver] or st.session_state.toll_one_way[driver]:
            st.session_state.toll_cost[driver] = st.text_input(
                f"{driver} の高速料金（円）", 
                value=st.session_state.toll_cost.get(driver, "未定"), 
                key=f"toll_cost_{driver}_input"
            )

# ==============================
# クリア Button (Resets Form)
# ==============================
if st.button("クリア"):
    st.session_state.date = datetime.today()
    st.session_state.selected_drivers.clear()
    st.session_state.confirmed_drivers = False
    st.session_state.amount = 200
    st.session_state.one_way.clear()
    st.session_state.toll_round_trip.clear()
    st.session_state.toll_one_way.clear()
    st.session_state.toll_cost.clear()
    st.rerun()

# ==============================
# Save Data to Google Sheets
# ==============================
def append_data(new_entries):
    sheet.append_rows(new_entries, value_input_option="USER_ENTERED")

if st.button("送信", key="submit_button"):  
    if st.session_state.selected_drivers:
        game_date = st.session_state.date.strftime("%m/%d")

        new_entries = []
        for driver in st.session_state.selected_drivers:
            toll_cost = st.session_state.toll_cost.get(driver, "未定")
            toll_cost_numeric = pd.to_numeric(toll_cost, errors="coerce")
            toll_cost = int(toll_cost_numeric) if not pd.isna(toll_cost_numeric) else "未定"

            amount = st.session_state.amount
            if st.session_state.one_way[driver]:  
                amount /= 2  
            if st.session_state.toll_round_trip[driver]:  
                amount = toll_cost  
            elif st.session_state.toll_one_way[driver]:  
                amount = (st.session_state.amount / 2) + (toll_cost if toll_cost != "未定" else 0)  

            supplement = "未定*" if toll_cost == "未定" else ""
            new_entries.append([st.session_state.date.strftime("%Y-%m-%d"), driver, int(amount) if toll_cost != "未定" else "未定", "あり" if st.session_state.toll_round_trip[driver] or st.session_state.toll_one_way[driver] else "なし", supplement])

        append_data(new_entries)
        st.success("✅ データが保存されました！")
        st.rerun()

# ==============================
# Monthly Summary Section
# ==============================
st.header("📊 月ごとの集計")

df = pd.DataFrame(sheet.get_all_records())

if df.empty:
    st.warning("データがありません。")
else:
    df["年-月"] = pd.to_datetime(df["日付"]).dt.strftime("%Y-%m")
    df["金額"] = pd.to_numeric(df["金額"], errors="coerce").fillna(0).astype(int)

    # ✅ Fix: Use pivot_table() instead of pivot() to handle duplicates
    pivot_summary = df.pivot_table(index="年-月", columns="名前", values="金額", aggfunc="sum", fill_value=0).astype(int)

    st.write(pivot_summary)

# ==============================
# Logout
# ==============================
if st.button("✅ 完了"):
    st.session_state.logged_in = False
    st.session_state.selected_drivers = set()
    st.success("✅ ログアウトしました。")
    st.rerun()
