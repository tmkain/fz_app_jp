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

def ensure_sheet_headers():
    # Get all values from the sheet
    existing_data = sheet.get_all_values()

    # If the sheet is completely empty, add headers
    if not existing_data or len(existing_data) < 1:
        headers = [["日付", "名前", "金額", "高速道路", "補足"]]
        sheet.append_rows(headers, value_input_option="USER_ENTERED")

ensure_sheet_headers()

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
            # ✅ Ensure checkboxes default to False when not selected
            one_way = st.session_state.one_way.get(driver, False)
            toll_round_trip = st.session_state.toll_round_trip.get(driver, False)
            toll_one_way = st.session_state.toll_one_way.get(driver, False)

            # ✅ Ensure toll_cost defaults to 0 instead of "未定"
            toll_cost = st.session_state.toll_cost.get(driver, "0")  
            toll_cost_numeric = pd.to_numeric(toll_cost, errors="coerce")
            toll_cost = int(toll_cost_numeric) if not pd.isna(toll_cost_numeric) else "未定"

            # ✅ Start with the base amount
            amount = st.session_state.amount  
            
            # ✅ Adjust reimbursement calculations correctly
            if one_way:  
                amount /= 2  # 一般道路片道 → 半額
            if toll_round_trip:  
                amount = toll_cost  # 高速道路往復 → Only reimburse toll
            elif toll_one_way:  
                amount = (st.session_state.amount / 2) + (toll_cost if toll_cost != "未定" else 0)  # 半額 + Toll

            # ✅ Ensure clean values for Google Sheets
            highway_use = "あり" if toll_round_trip or toll_one_way else "なし"
            one_way_status = "あり" if one_way else "なし"

            # ✅ Only apply "未定" in 補足 if toll_cost was actually "未定"
            supplement = "未定*" if toll_cost == "未定" else ""

            new_entries.append([
                st.session_state.date.strftime("%Y-%m-%d"), 
                driver, 
                int(amount) if toll_cost != "未定" else "未定", 
                highway_use,  # ✅ Stores "あり" or "なし"
                one_way_status,  # ✅ Stores "あり" or "なし"
                supplement
            ])

        append_data(new_entries)
        st.success("✅ データが保存されました！")
        st.rerun()



def load_from_sheets():
    records = sheet.get_all_values()

    required_columns = ["日付", "名前", "金額", "高速道路", "補足"]

    # ✅ If the sheet is empty or missing headers, return a DataFrame with correct headers
    if not records or len(records) < 2:
        return pd.DataFrame(columns=required_columns)

    df = pd.DataFrame(records[1:], columns=records[0])

    # ✅ Ensure all required columns exist
    for col in required_columns:
        if col not in df.columns:
            df[col] = ""  # Default missing columns to an empty string

    df["金額"] = pd.to_numeric(df["金額"], errors="coerce").fillna(0).astype(int)
    df["日付"] = pd.to_datetime(df["日付"], errors="coerce").dt.strftime("%Y-%m-%d")

    return df

# ==============================
# Monthly Summary Section
# ==============================
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

    # ✅ Check if "補足" exists before trying to use it
    if "補足" in df.columns:
        df["未定フラグ"] = df["補足"].apply(lambda x: True if "未定" in str(x) else False)
    else:
        df["未定フラグ"] = False  # Default to False if "補足" column is missing

    # ✅ Create a summary table
    pivot_summary = df.pivot_table(index="年-月", columns="名前", values="金額", aggfunc="sum", fill_value=0)

    # ✅ Apply formatting for "未定" cells
    def format_cell(value, is_pending):
        if is_pending:
            return f"<b>{value}</b>"  # Bold formatting
        return f"{value}"  # Regular formatting

    # ✅ Convert the DataFrame to HTML with formatted cells
    styled_df = pivot_summary.copy()
    for col in styled_df.columns:
        for index, value in styled_df[col].items():
            is_pending = df[(df["年-月"] == index) & (df["名前"] == col)]["未定フラグ"].any()
            styled_df.at[index, col] = format_cell(value, is_pending)

    # ✅ Convert to HTML & Render with Markdown
    styled_html = styled_df.to_html(escape=False)  # escape=False allows HTML formatting
    st.markdown(styled_html, unsafe_allow_html=True)


    # ==============================
    # ✅ Process User Input for "未定" Fields
    # ==============================
    if st.button("更新", key="update_pending"):
        for (index, col), new_value in pending_inputs.items():
            if new_value.strip():  # If the user entered a value
                # ✅ Find and update the Google Sheet entry
                all_records = sheet.get_all_values()
                for i, row in enumerate(all_records):
                    if i > 0 and row[0] == index and row[1] == col:  # Match "年-月" and "名前"
                        sheet.update_cell(i + 1, 3, new_value)  # Update 金額 column
                        sheet.update_cell(i + 1, 5, "")  # Clear "未定" in 補足 column

        st.success("✅ 高速料金が更新されました！")
        st.rerun()


# ==============================
# ✅ Logout & Reset Button (Moved to the bottom)
# ==============================
if st.button("✅ 完了"):
    st.session_state.logged_in = False  # ✅ Logs the user out
    st.session_state.selected_drivers.clear()
    st.session_state.confirmed_drivers = False
    st.session_state.amount = 200
    st.session_state.one_way.clear()
    st.session_state.toll_round_trip.clear()
    st.session_state.toll_one_way.clear()
    st.session_state.toll_cost.clear()
    st.success("✅ ログアウトしました。")
    st.rerun()
