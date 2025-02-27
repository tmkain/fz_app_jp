import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import os
import json
import time

# ==============================
# Google Sheets Authentication
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
# Load Data from Google Sheets
# ==============================
def load_from_sheets():
    records = sheet.get_all_values()
    if not records or len(records) < 2:
        return pd.DataFrame(columns=["日付", "名前", "金額", "高速道路", "高速料金", "片道"])  

    df = pd.DataFrame(records[1:], columns=records[0])

    # Ensure numerical columns exist before converting
    df["金額"] = pd.to_numeric(df["金額"], errors="coerce").fillna(0).astype(int)

    if "高速料金" in df.columns:
        df["高速料金"] = pd.to_numeric(df["高速料金"], errors="coerce").fillna(0).astype(int)
    else:
        df["高速料金"] = 0  # Default to 0 if the column doesn't exist

    df["日付"] = pd.to_datetime(df["日付"], errors="coerce").dt.strftime("%Y-%m-%d")
    
    return df


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
    st.session_state.amount = st.radio("金額を選択してください", [200, 400, 600, 800, 1000, 1200], key="amount_selection")

    # Show checkboxes for each driver and input fields for toll costs
    for driver in st.session_state.selected_drivers:
        if driver not in st.session_state.one_way:
            st.session_state.one_way[driver] = False
        if driver not in st.session_state.toll_round_trip:
            st.session_state.toll_round_trip[driver] = False
        if driver not in st.session_state.toll_one_way:
            st.session_state.toll_one_way[driver] = False
        if driver not in st.session_state.toll_cost:
            st.session_state.toll_cost[driver] = "未定"  # Default to "未定"

        st.session_state.one_way[driver] = st.checkbox(f"{driver} の一般道路片道", value=st.session_state.one_way[driver], key=f"one_way_{driver}_chk")
        st.session_state.toll_round_trip[driver] = st.checkbox(f"{driver} の高速道路往復", value=st.session_state.toll_round_trip[driver], key=f"toll_round_trip_{driver}_chk")
        st.session_state.toll_one_way[driver] = st.checkbox(f"{driver} の高速道路片道", value=st.session_state.toll_one_way[driver], key=f"toll_one_way_{driver}_chk")

        # Show input field for toll cost if either toll option is selected
        if st.session_state.toll_round_trip[driver] or st.session_state.toll_one_way[driver]:
            st.session_state.toll_cost[driver] = st.text_input(f"{driver} の高速料金（円）", value=st.session_state.toll_cost[driver], key=f"toll_cost_{driver}_input")

    # クリアボタン: Reset the form
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

    if st.button("送信"):  
        if st.session_state.selected_drivers:
            batch_id = int(time.time())
            game_date = st.session_state.date.strftime("%Y-%m-%d")

            new_entries = []
            for driver in st.session_state.selected_drivers:
                # Convert toll cost if it's a number, otherwise keep "未定"
                toll_cost = st.session_state.toll_cost.get(driver, "未定")
                toll_cost_numeric = pd.to_numeric(toll_cost, errors="coerce")
                toll_cost = int(toll_cost_numeric) if not pd.isna(toll_cost_numeric) else "未定"

                # Calculate amount based on toll road settings
                amount = st.session_state.amount
                if st.session_state.one_way.get(driver, False):  
                    amount /= 2  
                if st.session_state.toll_round_trip.get(driver, False):  
                    amount = toll_cost  # Ignore base amount, only reimburse toll
                elif st.session_state.toll_one_way.get(driver, False):  
                    amount = (st.session_state.amount / 2) + (toll_cost if toll_cost != "未定" else 0)  # Half base amount + full toll

                new_entries.append([
                    game_date,  
                    driver,  
                    int(amount) if toll_cost != "未定" else "未定",  
                    "あり" if st.session_state.toll_round_trip.get(driver, False) or st.session_state.toll_one_way.get(driver, False) else "なし",
                    toll_cost,
                    "あり" if st.session_state.one_way.get(driver, False) else "なし",
                    batch_id
                ])

            save_to_sheets(new_entries)

            st.success("✅ データが保存されました！")
            st.rerun()

# ==============================
# Monthly Summary Section
# ==============================
st.header("📊 月ごとの集計")

df = load_from_sheets()  # Reload data every time

if df.empty:
    st.warning("データがありません。")
else:
    df["年-月"] = pd.to_datetime(df["日付"]).dt.strftime("%Y-%m")

    # Ensure numerical columns exist and are properly formatted
    df["金額"] = pd.to_numeric(df["金額"], errors="coerce").fillna(0).astype(int)
    df["高速料金"] = df["高速料金"].replace("未定", 0)  # Convert "未定" to 0 for calculations
    df["高速料金"] = pd.to_numeric(df["高速料金"], errors="coerce").fillna(0).astype(int)

    # Summarize data
    summary = df.groupby(["年-月", "名前"], as_index=False).agg({"金額": "sum", "高速料金": "sum"})

    # Ensure numerical values before adding
    summary["金額"] = summary["金額"].astype(int)
    summary["高速料金"] = summary["高速料金"].astype(int)

    # Compute final total
    summary["合計金額"] = summary["金額"] + summary["高速料金"]

    # Drop unnecessary columns dynamically
    if "高速料金" in summary.columns:
        summary = summary.drop(columns=["高速料金"])

    # Print column names for debugging
    st.write("📌 Debugging: Current summary columns:", summary.columns.tolist())

    # Ensure proper renaming dynamically
    expected_columns = ["年-月", "名前", "合計金額"]
    if len(summary.columns) == len(expected_columns):
        summary.columns = expected_columns
    else:
        st.warning(f"⚠️ Column count mismatch! Expected {len(expected_columns)}, but found {len(summary.columns)}. Adjusting dynamically.")
        if "合計金額" in summary.columns:
            summary.rename(columns={"合計金額": "金額"}, inplace=True)  # Rename dynamically if needed

    # Ensure 合計金額 is numeric before pivoting
    summary["合計金額"] = pd.to_numeric(summary["合計金額"], errors="coerce").fillna(0).astype(int)

    # Ensure all missing values are properly handled
    summary.fillna(0, inplace=True)

    # 🚀 Correct the column used in pivot (was "金額", now "合計金額")
    pivot_summary = summary.pivot(index="年-月", columns="名前", values="合計金額").fillna(0).astype(int)

    st.write(pivot_summary)
