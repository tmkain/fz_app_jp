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
# ✅ Initialize Session State AFTER Login
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
            one_way TEXT, 
            batch_id INTEGER,
            notes TEXT
        )
    """)

    # Insert a default row if the table is empty
    c.execute("SELECT COUNT(*) FROM data")
    if c.fetchone()[0] == 0:
        c.execute("""
            INSERT INTO data (date, name, amount, toll, one_way, batch_id, notes)
            VALUES ('2000-01-01', 'サンプル', 0, 'なし', 'なし', 0, '初期データ')
        """)
    
    conn.commit()
    conn.close()

create_db()

# ==============================
# Load Data from SQLite
# ==============================

def load_from_db():
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT * FROM data", conn)
    conn.close()
    
    if df.empty:
        df = pd.DataFrame({
            "id": [0],
            "date": ["2000-01-01"],
            "name": ["サンプル"],
            "amount": [0],
            "toll": ["なし"],
            "one_way": ["なし"],
            "batch_id": [0],
            "notes": ["初期データ"]
        })
    
    df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")  # Ensure correct format
    return df

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

# ==============================
# Edit & Delete Entries
# ==============================
st.header("📝 データ編集")

df = load_from_db()

if df.empty:
    st.warning("データがありません。")
else:
    selected_date = st.date_input("編集する日付を選択", value=datetime.today())
    selected_date_str = selected_date.strftime("%Y-%m-%d")

    # Debugging: Show stored dates
    st.write(f"📌 Selected Date: {selected_date_str}")
    st.write("📌 Available Dates in DB:", df["date"].unique())

    filtered_df = df[df["date"] == selected_date_str]

    if filtered_df.empty:
        st.warning("選択した日付のデータがありません。")
    else:
        st.write("📋 編集可能なエントリ")
        edited_entries = []

        for index, row in filtered_df.iterrows():
            col1, col2, col3, col4, col5 = st.columns(5)
            new_name = col1.text_input("名前", value=row["name"], key=f"name_{row['id']}")
            new_amount = col2.number_input("金額", value=row["amount"], step=100, key=f"amount_{row['id']}")
            new_toll = col3.selectbox("高速道路", ["あり", "なし"], index=0 if row["toll"] == "あり" else 1, key=f"toll_{row['id']}")
            new_notes = col4.text_input("補足", value=row["notes"] or "", key=f"notes_{row['id']}")

            edited_entries.append((new_name, new_amount, new_toll, new_notes, row["id"]))

            if col5.button("❌ 削除", key=f"delete_{row['id']}"):
                conn = sqlite3.connect(DB_FILE)
                c = conn.cursor()
                c.execute("DELETE FROM data WHERE id = ?", (row["id"],))
                conn.commit()
                conn.close()
                st.success("✅ エントリが削除されました！")
                st.rerun()

        if st.button("💾 変更を保存"):
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            for entry in edited_entries:
                c.execute("""
                    UPDATE data 
                    SET name = ?, amount = ?, toll = ?, notes = ? 
                    WHERE id = ?
                """, entry)
            conn.commit()
            conn.close()
            st.success("✅ データが更新されました！")
            st.rerun()

# ==============================
# Monthly Summary Section
# ==============================
st.header("📊 月ごとの集計")

if df.empty:
    st.warning("データがありません。")
else:
    df["年-月"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m")
    summary = df.groupby(["年-月", "name"], as_index=False)["amount"].sum()

    if "notes" in df.columns:
        summary["補足"] = df.groupby(["年-月", "name"])["notes"].apply(lambda x: " ".join(x.dropna().unique())).reset_index(drop=True)
    else:
        summary["補足"] = ""

    st.write(summary.pivot(index="年-月", columns="name", values=["amount", "補足"]).fillna(""))

if st.button("✅ 完了"):
    st.session_state.logged_in = False
    st.success("✅ ログアウトしました。")
    st.rerun()
