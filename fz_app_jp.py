import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import os
import json
import hashlib

# ==============================
# Secure Login System
# ==============================

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

@st.cache_resource
def get_credentials():
    username = os.getenv("APP_USERNAME")
    password = os.getenv("APP_PASSWORD")
    if not username or not password:
        st.error("環境変数 `APP_USERNAME` と `APP_PASSWORD` が設定されていません。")
        st.stop()
    return username, hash_password(password)

USERNAME, PASSWORD_HASH = get_credentials()

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.markdown("<h2 style='text-align:center'>🔑 ログイン</h2>", unsafe_allow_html=True)
    entered_username = st.text_input("ユーザー名", "", key="username")
    entered_password = st.text_input("パスワード", "", type="password", key="password")
    
    if st.button("ログイン"):
        if entered_username == USERNAME and hash_password(entered_password) == PASSWORD_HASH:
            st.session_state.logged_in = True
            st.rerun()
        else:
            st.error("🚫 ユーザー名またはパスワードが違います")
    st.stop()

# ==============================
# Google Sheets Authentication
# ==============================
SHEET_ID = "1upehCYwnGEcKg_zVQG7jlnNUykFmvNbuAtnxzqvSEcA"
SHEET_NAME = "Sheet1"

@st.cache_resource
def get_google_sheet():
    creds_json = os.getenv("GOOGLE_CREDENTIALS")
    if not creds_json:
        st.error("環境変数 `GOOGLE_CREDENTIALS` が設定されていません。")
        st.stop()
    
    creds_dict = json.loads(creds_json)
    creds = Credentials.from_service_account_info(creds_dict, scopes=["https://www.googleapis.com/auth/spreadsheets"])
    return gspread.authorize(creds).open_by_key(SHEET_ID).worksheet(SHEET_NAME)

sheet = get_google_sheet()

def ensure_sheet_headers():
    existing_data = sheet.get_all_values()
    if not existing_data or existing_data[0] != ["日付", "名前", "金額", "高速道路", "補足"]:
        sheet.insert_row(["日付", "名前", "金額", "高速道路", "補足"], 1)

ensure_sheet_headers()

# ==============================
# Initialize Session State
# ==============================

def initialize_session_state():
    defaults = {
        "date": datetime.today(),
        "selected_drivers": set(),
        "confirmed_drivers": False,
        "one_way": {},
        "toll_round_trip": {},
        "toll_one_way": {},
        "toll_cost": {},
        "amount": 200
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

initialize_session_state()

# ==============================
# UI: Driver Selection & Expense Entry
# ==============================
st.title("🚗 Fz 車代管理アプリ")
st.header("データ入力")
st.session_state.date = st.date_input("試合日を選択してください", value=st.session_state.date)

driver_list = ["平野", "ケイン", "山﨑", "萩原", "仙波し", "仙波ち", "久保", "落合", "浜島", "野波", "末田", "芳本", "鈴木", "山田", "佐久間", "今井", "西川"]

st.write("### 運転手を選択してください")
columns = st.columns(3)
new_selected_drivers = set()

for i, driver in enumerate(driver_list):
    with columns[i % 3]:
        if st.checkbox(driver, key=f"select_{driver}", value=(driver in st.session_state.selected_drivers)):
            new_selected_drivers.add(driver)

st.session_state.selected_drivers = new_selected_drivers

col1, col2 = st.columns(2)
with col1:
    if st.button("運転手を確定する"):
        st.session_state.confirmed_drivers = True
with col2:
    if st.button("クリア"):
        initialize_session_state()
        st.rerun()

if st.session_state.confirmed_drivers:
    st.session_state.amount = st.radio("金額を選択してください", [200, 400, 600, 800, 1000, 1200])
    for driver in st.session_state.selected_drivers:
        st.session_state.toll_cost[driver] = st.text_input(f"{driver} の高速料金（円）", value=st.session_state.toll_cost.get(driver, "未定"))

# ==============================
# UI: Monthly Summary
# ==============================
st.header("📊 月ごとの集計")
df = pd.DataFrame(sheet.get_all_records())
if df.empty:
    st.warning("データがありません。")
else:
    df["年-月"] = pd.to_datetime(df["日付"]).dt.strftime("%Y-%m")
    df["金額"] = pd.to_numeric(df["金額"], errors="coerce").fillna(0).astype(int)
    pivot_summary = df.pivot_table(index="年-月", columns="名前", values="金額", aggfunc="sum", fill_value=0)
    st.dataframe(pivot_summary.style.format("{:,.0f}"))

# ==============================
# Logout Button
# ==============================
if st.button("✅ 完了"):
    st.session_state.logged_in = False
    initialize_session_state()
    st.success("✅ ログアウトしました。")
    st.rerun()
