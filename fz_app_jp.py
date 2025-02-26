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
    conn = sqlite3.connect(DB_FILE)  # Connects to the existing DB or creates a new one if missing
    c = conn.cursor()

    # Create table if it does not exist
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

    # Check if table is empty before inserting default row
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
    
    return df


# ==============================
# Edit & Delete Entries
# ==============================
st.header("📝 データ編集")

df = load_from_db()

if df.empty:
    st.warning("データがありません。")
else:
    df["date"] = pd.to_datetime(df["date"])  # Convert to date format for filtering
    selected_date = st.date_input("編集する日付を選択", value=datetime.today())
    selected_date_str = selected_date.strftime("%Y-%m-%d")  # Convert date to string format
    filtered_df = df[df["date"] == selected_date_str]  # Compare as string

    if filtered_df.empty:
        st.warning("選択した日付のデータがありません。")
    else:
        st.write("📋 編集可能なエントリ")
        edited_entries = []

        for index, row in filtered_df.iterrows():
            col1, col2, col3, col4, col5, col6, col7 = st.columns(7)
            
            new_name = col1.text_input("名前", value=row["name"], key=f"name_{row['id']}")
            new_amount = col2.number_input("金額", value=row["amount"], step=100, key=f"amount_{row['id']}")
            new_toll = col3.selectbox("高速道路", ["あり", "なし"], index=0 if row["toll"] == "あり" else 1, key=f"toll_{row['id']}")
            new_one_way = col4.selectbox("片道", ["あり", "なし"], index=0 if row["one_way"] == "あり" else 1, key=f"one_way_{row['id']}")
            new_notes = col5.text_input("補足", value=row["notes"] or "", key=f"notes_{row['id']}")

            # Save edited row
            edited_entries.append((new_name, new_amount, new_toll, new_one_way, new_notes, row["id"]))

            # Delete button
            if col6.button("❌ 削除", key=f"delete_{row['id']}"):
                conn = sqlite3.connect(DB_FILE)
                c = conn.cursor()
                c.execute("DELETE FROM data WHERE id = ?", (row["id"],))
                conn.commit()
                conn.close()
                st.success("✅ エントリが削除されました！")
                st.rerun()

        # Apply updates
        if st.button("💾 変更を保存"):
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            for entry in edited_entries:
                c.execute("""
                    UPDATE data 
                    SET name = ?, amount = ?, toll = ?, one_way = ?, notes = ? 
                    WHERE id = ?
                """, entry)
            conn.commit()
            conn.close()
            st.success("✅ データが更新されました！")
            st.rerun()

# ==============================
# Monthly Summary Section (Always Fresh)
# ==============================
st.header("📊 月ごとの集計")

df = load_from_db()

if df.empty:
    st.warning("データがありません。")
else:
    df["年-月"] = pd.to_datetime(df["date"], errors="coerce").dt.strftime("%Y-%m")
    summary = df.groupby(["年-月", "name"], as_index=False)["amount"].sum()
    
    if "notes" in df.columns:
        summary["補足"] = df.groupby(["年-月", "name"])["notes"].apply(lambda x: " ".join(x.dropna().unique())).reset_index(drop=True)
    else:
        summary["補足"] = ""

    # Ensure at least one row is always displayed
    if summary.empty:
        summary = pd.DataFrame({"年-月": ["2000-01"], "name": ["サンプル"], "amount": [0], "補足": ["なし"]})

    summary = summary.pivot(index="年-月", columns="name", values=["amount", "補足"]).fillna(0)
    st.write(summary)


# ==============================
# Logout
# ==============================
if st.button("✅ 完了"):
    st.session_state.logged_in = False
    st.session_state.selected_drivers = set()
    st.success("✅ ログアウトしました。")
    st.rerun()
