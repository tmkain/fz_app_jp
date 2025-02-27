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
# Monthly Summary Section
# ==============================
st.header("📊 月ごとの集計")

df = pd.DataFrame(sheet.get_all_records())

if df.empty:
    st.warning("データがありません。")
else:
    df["年-月"] = pd.to_datetime(df["日付"]).dt.strftime("%Y-%m")
    df["金額"] = pd.to_numeric(df["金額"], errors="coerce").fillna(0).astype(int)

    # ✅ Ensure "補足" column exists before checking for "未定"
    if "補足" in df.columns:
        df["未定フラグ"] = df["補足"].apply(lambda x: "未定" in str(x))
    else:
        df["未定フラグ"] = False  # Default to False if "補足" column is missing

    # ✅ Create a summary table
    pivot_summary = df.pivot_table(index="年-月", columns="名前", values="金額", aggfunc="sum", fill_value=0)

    # ✅ Define `pending_inputs` BEFORE using it
    pending_inputs = {}

    # ✅ Define a function to apply formatting for "未定" cells
    def format_cell(value, is_pending):
        return f"<b>{value}</b>" if is_pending else f"{value}"  # Bold formatting if "未定"

    # ✅ Copy pivot table and convert to strings to allow formatting
    styled_df = pivot_summary.astype(str)

    # ✅ Create a separate list for inputs (displayed later)
    inputs_section = []

    for col in styled_df.columns:
        for index, value in styled_df[col].items():
            # ✅ Correctly filter df to check if "未定" exists for that driver and month
            filtered_df = df[(df["年-月"] == index) & (df["名前"] == col)]
            is_pending = filtered_df["未定フラグ"].any() if not filtered_df.empty else False

            # ✅ Store formatted values in the table
            styled_df.at[index, col] = format_cell(value, is_pending)

            # ✅ Store input fields for later display
            if is_pending:
                pending_inputs[(index, col)] = True  # Mark for input field generation
                inputs_section.append((index, col))  # Store for later

    # ✅ Convert to HTML & Render with Markdown
    styled_html = styled_df.to_html(escape=False)
    st.markdown(styled_html, unsafe_allow_html=True)

    # ✅ Initialize updated_values at the beginning
    updated_values = {}

    # ✅ Create a container for input fields to ensure only one instance
    input_container = st.container()

    with input_container:
        for (index, col) in pending_inputs.keys():
            input_key = f"final_input_{index}_{col}"
            
            # ✅ Ensure each input field has a unique session key
            if input_key not in st.session_state:
                st.session_state[input_key] = ""
            
            # ✅ Display a single text input field above "更新" button
            updated_value = st.text_input(
                f"{index} - {col} の高速料金を入力", 
                st.session_state[input_key], 
                key=input_key
            ).strip()
            
            # ✅ Store latest user input in session state (only if different)
            if updated_value and updated_value != st.session_state[input_key]:
                st.session_state[input_key] = updated_value
                updated_values[(index, col)] = updated_value  # ✅ Add to update list

    # ✅ Update Google Sheets when "更新" button is clicked
    if st.button("更新", key="update_pending"):
        if updated_values:  # ✅ Only proceed if there are actual changes
            all_records = sheet.get_all_values()

            for i, row in enumerate(all_records):
                if i == 0:
                    continue  # ✅ Skip headers
                
                row_date = row[0].strip()
                row_driver = row[1].strip()
                existing_amount = row[2].strip()
                existing_note = row[4].strip()  # "補足" column (which contains "未定")

                for (index, col), new_value in updated_values.items():
                    formatted_index = str(index)  # Ensure consistent date formatting

                    # ✅ Match both the date and driver name
                    if row_date == formatted_index and row_driver == col:
                        # ✅ Only update if existing value is "未定"
                        if existing_note == "未定":
                            sheet.update_cell(i + 1, 3, new_value)  # ✅ Update 金額 column
                            sheet.update_cell(i + 1, 5, "")  # ✅ Clear "未定" from 補足 column

            st.success("✅ 高速料金が更新されました！")

            # ✅ Force Streamlit to reload the updated data
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
