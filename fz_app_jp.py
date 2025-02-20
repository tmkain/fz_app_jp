import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# ==============================
# Google Sheets Authentication
# ==============================
SHEET_ID = "1upehCYwnGEcKg_zVQG7jlnNUykFmvNbuAtnxzqvSEcA"
SHEET_NAME = "Sheet1"

# Authenticate and connect to Google Sheets
def authenticate_google_sheets():
    import json
import os
from google.oauth2.service_account import Credentials

# Load JSON credentials from the environment variable
creds_json = os.getenv("GOOGLE_CREDENTIALS")
if creds_json:
    creds_dict = json.loads(creds_json)
    creds = Credentials.from_service_account_info(creds_dict, scopes=["https://www.googleapis.com/auth/spreadsheets"])
else:
    raise ValueError("GOOGLE_CREDENTIALS environment variable not found")
    return gspread.authorize(creds)

client = authenticate_google_sheets()
sheet = client.open_by_key(SHEET_ID).worksheet(SHEET_NAME)

# ==============================
# Data Entry Section
# ==============================
st.title("🚗 Fz 車代管理アプリ")
st.header("データ入力")

# Session state to handle form reset
if "reset" not in st.session_state:
    st.session_state.reset = False

# User Inputs
date = st.date_input("試合日を選択してください") if not st.session_state.reset else st.empty()
date_str = date.strftime("%Y-%m-%d") if not st.session_state.reset else ""

driver_list = ["平野", "ケイン", "山﨑", "萩原", "仙波し", "仙波ち", "久保田", "落合", "浜島", "野波",
               "末田", "芳本", "鈴木", "山田", "佐久間", "今井", "西川"]
selected_drivers = st.multiselect("運転手を選択してください", driver_list) if not st.session_state.reset else []

# Reimbursement Options
amount_options = [200, 400, 600, 800]  # You can change these values here
amount = st.radio("金額を選択してください", amount_options) if not st.session_state.reset else 200

# Highway & One-way Toggle
toll_road = {}
one_way = {}
for driver in selected_drivers:
    toll_road[driver] = st.checkbox(f"{driver} の高速道路利用", key=f"toll_{driver}") if not st.session_state.reset else False
    one_way[driver] = st.checkbox(f"{driver} の片道利用", key=f"one_way_{driver}") if not st.session_state.reset else False

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
    if selected_drivers:
        new_entries = [[date_str, driver, (amount + (1000 if toll_road[driver] else 0)) / (2 if one_way[driver] else 1), 
                         "あり" if toll_road[driver] else "なし", "あり" if one_way[driver] else "なし"] 
                        for driver in selected_drivers]
        save_data(new_entries)
        st.success("データが保存されました！")
        st.rerun()
    else:
        st.warning("運転手を選択してください。")

# Clear Button
if st.button("クリア"):
    st.session_state.reset = False  # Ensure input fields reset without disappearing
    st.rerun()

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
