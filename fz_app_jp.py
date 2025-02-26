import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import os
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
# SQLite Database Setup
# ==============================
DB_FILE = "fz_data.db"

def create_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT, 
            name TEXT, 
            amount REAL, 
            toll TEXT, 
            toll_cost REAL,
            one_way TEXT, 
            batch_id INTEGER
        )
    """)
    conn.commit()
    conn.close()

create_db()

# ==============================
# ✅ Define load_from_db() BEFORE using it
# ==============================
def load_from_db():
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT date, name, amount, toll, toll_cost, one_way FROM data", conn)  # Removed batch_id
    conn.close()

    # Convert date format and ensure amounts are whole numbers
    df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
    df["amount"] = df["amount"].astype(int)  # No decimal points
    df["toll_cost"] = df["toll_cost"].astype(int)  # Toll should also be an integer

    return df

# ==============================
# Initialize Session State AFTER Login
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
    st.session_state.toll_cost = {}  # Store toll cost per driver
if "amount" not in st.session_state:
    st.session_state.amount = 200  

# ==============================
# Data Entry Section
# ==============================
st.title("🚗 Fz 車代管理アプリ")
st.header("データ入力")

st.session_state.date = st.date_input("試合日を選択してください", value=datetime.today())

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

    # Show checkboxes for each driver and input fields for toll costs
    for driver in st.session_state.selected_drivers:
        st.session_state.one_way[driver] = st.checkbox(f"{driver} の一般道路片道", value=st.session_state.one_way.get(driver, False), key=f"one_way_{driver}")
        st.session_state.toll_round_trip[driver] = st.checkbox(f"{driver} の高速道路往復", value=st.session_state.toll_round_trip.get(driver, False), key=f"toll_round_trip_{driver}")
        st.session_state.toll_one_way[driver] = st.checkbox(f"{driver} の高速道路片道", value=st.session_state.toll_one_way.get(driver, False), key=f"toll_one_way_{driver}")

        # Show input field for toll cost if either toll option is selected
        if st.session_state.toll_round_trip[driver] or st.session_state.toll_one_way[driver]:
            st.session_state.toll_cost[driver] = st.number_input(f"{driver} の高速料金（円）", min_value=0, value=st.session_state.toll_cost.get(driver, 0), key=f"toll_cost_{driver}")

def save_to_db(entries):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    formatted_entries = [(e[0], e[1], e[2], e[3], e[4], e[5], e[6]) for e in entries]

    c.executemany("""
        INSERT INTO data (date, name, amount, toll, toll_cost, one_way, batch_id)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, formatted_entries)

    conn.commit()
    conn.close()

if st.session_state.confirmed_drivers:
    if st.button("送信"):  
    if st.session_state.selected_drivers:
        batch_id = int(time.time())
        game_date = st.session_state.date.strftime("%Y-%m-%d")

        new_entries = []
        for driver in st.session_state.selected_drivers:
            amount = st.session_state.amount + st.session_state.toll_cost.get(driver, 0)
            if st.session_state.one_way.get(driver, False):  
                amount /= 2  
            if st.session_state.toll_round_trip.get(driver, False):  
                amount = 0 + st.session_state.toll_cost.get(driver, 0)
            elif st.session_state.toll_one_way.get(driver, False):  
                amount /= 2  

            new_entries.append([
                game_date,  
                driver,  
                int(amount),  
                "あり" if st.session_state.toll_round_trip.get(driver, False) or st.session_state.toll_one_way.get(driver, False) else "なし",
                st.session_state.toll_cost.get(driver, 0),
                "あり" if st.session_state.one_way.get(driver, False) else "なし",
                batch_id
            ])

        save_to_db(new_entries)
        
        # 🔹 Load fresh data immediately after saving
        df = load_from_db()

        st.success("✅ データが保存されました！")
        st.rerun()  # Ensures the UI refreshes properly

