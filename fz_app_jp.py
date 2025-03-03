import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import os
import json
import time
import googlemaps

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

# Load API Key from environment variables
API_KEY = os.getenv("GMAPS_API_KEY")  # ✅ Fetch from Render's environment settings

if not API_KEY:
    raise ValueError("⚠️ Missing Google Maps API Key! Set GMAPS_API_KEY in environment variables.")

# Initialize Google Maps client
gmaps = googlemaps.Client(key=API_KEY)

# ==============================
# Google Sheets Authentication (Cached)
# ==============================
SHEET_ID = "1upehCYwnGEcKg_zVQG7jlnNUykFmvNbuAtnxzqvSEcA"
SHEET_NAME_1 = "Sheet1"
SHEET_NAME_2 = "Sheet2"

@st.cache_resource
def get_google_sheets():
    creds_json = os.getenv("GOOGLE_CREDENTIALS")
    if not creds_json:
        raise ValueError("🚨 GOOGLE_CREDENTIALS environment variable not found.")

    creds_dict = json.loads(creds_json)
    creds = Credentials.from_service_account_info(creds_dict, scopes=["https://www.googleapis.com/auth/spreadsheets"])
    client = gspread.authorize(creds)
    spreadsheet = client.open_by_key(SHEET_ID)

    try:
        sheet1 = spreadsheet.worksheet(SHEET_NAME_1)  # ✅ Sheet1 (Payments)
        sheet2 = spreadsheet.worksheet(SHEET_NAME_2)  # ✅ Sheet2 (Car Assignments)
    except gspread.WorksheetNotFound:
        raise ValueError(f"🚨 Worksheet '{SHEET_NAME_1}' or '{SHEET_NAME_2}' not found in Google Sheet.")

    return sheet1, sheet2

# ✅ Correctly load both sheets
sheet1, sheet2 = get_google_sheets()

    else:
        raise ValueError("GOOGLE_CREDENTIALS environment variable not found")

sheet1, sheet2 = get_google_sheet()

def ensure_sheet_headers(sheet, headers):
    # Get all values from the sheet
    existing_data = sheet.get_all_values()

    # If the sheet is completely empty, add headers
    if not existing_data or len(existing_data) < 1:
        headers_sheet1 = [["日付", "名前", "金額", "高速道路", "補足"]]
        headers_sheet2 = [["名前", "学年", "運転手", "定員"]] # Car Assignments
        sheet.append_row(headers[0], value_input_option="USER_ENTERED")  # ✅ Use append_row() with a single list

# Apply headers check
ensure_sheet_headers(sheet1, headers_sheet1)
ensure_sheet_headers(sheet2, headers_sheet2)

# ------------------- 🔹 Create Tabs for Features 🔹 -------------------
tab1, tab2 = st.tabs(["🚗 車代管理", "🎯 車両割り当て"])  # 🔹 Create tabs

# ---- TAB 1: 車代管理 (Your existing feature) ----
with tab1:
    st.subheader("🚗 車代管理システム")

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
    # Google Maps Distance Calculation
    # ==============================
    
    BASE_LOCATION = "埼玉県和光市南1丁目5番10号"  # ⚠️ Change to your base location (e.g., your office)
    
    def get_distance(destination):
        """
        Returns the driving distance in kilometers from BASE_LOCATION to the destination.
        """
        BASE_LOCATION = "埼玉県和光市南1丁目5番10号"  # ✅ Change to your actual base location
        
        try:
            result = gmaps.distance_matrix(
                origins=BASE_LOCATION,
                destinations=destination,
                mode="driving",
                avoid="tolls",
            )
            distance_meters = result["rows"][0]["elements"][0]["distance"]["value"]
            distance_km = distance_meters / 1000  # Convert meters to km
            return distance_km
        except Exception as e:
            st.error(f"エラー: {e}")
            return None
    
    def calculate_reimbursement(distance_km):
        """
        Returns the reimbursement amount based on distance.
        ⚠️ Modify tiers based on your reimbursement policy.
        """
        if distance_km < 5:
            return 200
        elif distance_km < 10:
            return 400
        elif distance_km < 20:
            return 600
        elif distance_km < 30:
            return 800
        elif distance_km < 40:
            return 1000
        else:
            return 1200
    
    
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
    
    # ✅ Show distance input only AFTER confirming drivers
    if st.session_state.confirmed_drivers:
        st.write("### 目的地を入力してください")
        destination = st.text_input("目的地を入力（例: 大阪駅）", key="destination_input")
    
        if st.button("距離を計算"):
            if destination:
                distance = get_distance(destination)
                if distance is not None:
                    reimbursement = calculate_reimbursement(distance)
                    st.session_state.amount = reimbursement
                    st.session_state.distance = distance  # ✅ Save calculated distance persistently
                    st.success(f"🚗 距離: {distance:.1f} km")
                    st.success(f"💴 車代: ¥{reimbursement}")
            else:
                st.error("⚠️ 目的地を入力してください！")
    
    # ✅ Move 高速道路 options outside the "距離を計算" button block
    #    → This ensures they don't disappear after clicking "距離を計算"
    if "distance" in st.session_state:
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
                # ✅ Set defaults properly
                one_way = st.session_state.one_way.get(driver, False)
                toll_round_trip = st.session_state.toll_round_trip.get(driver, False)
                toll_one_way = st.session_state.toll_one_way.get(driver, False)
    
                # ✅ Ensure toll_cost is handled properly
                toll_cost = st.session_state.toll_cost.get(driver, "0")  
                toll_cost_numeric = pd.to_numeric(toll_cost, errors="coerce")
                toll_cost = int(toll_cost_numeric) if not pd.isna(toll_cost_numeric) else "未定"
    
                # ✅ Compute amount correctly
                amount = st.session_state.amount  
                if one_way:  
                    amount /= 2  
                if toll_round_trip:  
                    amount = toll_cost  
                elif toll_one_way:  
                    amount = (st.session_state.amount / 2) + (toll_cost if toll_cost != "未定" else 0)  
    
                # ✅ Ensure "補足" (Notes) correctly saves "未定"
                supplement = "未定" if toll_cost == "未定" else ""
    
                new_entries.append([
                    st.session_state.date.strftime("%Y-%m-%d"), 
                    driver, 
                    int(amount) if toll_cost != "未定" else "未定", 
                    "あり" if toll_round_trip or toll_one_way else "なし", 
                    supplement  # ✅ Now properly updates "補足"
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
    
        # ✅ Initialize updated_values at the beginning
        updated_values = {}
    
        # ✅ Copy pivot table and convert to strings to allow formatting
        styled_df = pivot_summary.astype(str)
    
        for col in styled_df.columns:
            for index, value in styled_df[col].items():
                # ✅ Correctly filter df to check if "未定" exists for that driver and month
                filtered_df = df[(df["年-月"] == index) & (df["名前"] == col)]
                is_pending = filtered_df["未定フラグ"].any() if not filtered_df.empty else False
    
                # ✅ Apply formatting for "未定" cells **after** determining is_pending
                def format_cell(value, is_pending):
                    return f"<b>{value}</b>" if is_pending else f"{value}"  # Bold formatting if "未定"
    
                styled_df.at[index, col] = format_cell(value, is_pending)
    
                # ✅ Add an input field for "未定" updates
                if is_pending:
                    pending_inputs[(index, col)] = st.text_input(f"{index} - {col} の高速料金を入力", "")
    
        # ✅ Convert to HTML & Render with Markdown
    styled_html = styled_df.to_html(escape=False)
    st.markdown(styled_html, unsafe_allow_html=True)
    
    # ✅ Normalize user input keys by removing ALL spaces
    cleaned_pending_inputs = {
        ("".join(index.split()), "".join(col.split())): value.strip()
        for (index, col), value in pending_inputs.items()
    }
    
    # ✅ Replace pending_inputs with the cleaned version
    pending_inputs = cleaned_pending_inputs
    
    # ✅ Collect user inputs BEFORE the button check
    for (index, col), user_input in pending_inputs.items():
        if user_input.strip():  # Only store non-empty inputs
            updated_values[(index, col)] = user_input.strip()
    
    # ✅ Update Google Sheets when "更新" button is clicked
    if st.button("更新", key="update_pending"):
        if len(updated_values) > 0:  # ✅ Ensure `updated_values` exists before proceeding
            all_records = sheet.get_all_values()
    
            for i, row in enumerate(all_records):
                if i == 0:
                    continue  # ✅ Skip headers
    
                # ✅ Extract and clean up data from the row
                row_date_clean = pd.to_datetime(row[0], errors="coerce").strftime("%Y-%m")  # Convert Google Sheets date to YYYY-MM
                row_driver_clean = row[1].strip()  # ✅ Extract driver name
              
                for (index, col), new_value in updated_values.items():
                    formatted_index_clean = pd.to_datetime(index, errors="coerce").strftime("%Y-%m")  # Ensure comparison is YYYY-MM
    
                    # ✅ Compare cleaned values
                    if row_date_clean == formatted_index_clean and row_driver_clean == col:
                        # ✅ Update 金額 column
                        sheet.update_cell(i + 1, 3, new_value)  # ✅ Update "金額" (Column C)
                        sheet.update_cell(i + 1, 5, "")  # ✅ Clear "補足" (Column E)
            
            st.success("✅ 高速料金が更新されました！")
            st.rerun()  # ✅ Instant refresh to update the displayed table
        else:
            st.warning("🚨 変更された値がありません。更新するには値を入力してください。")
    
    
    
    
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

# ---- TAB 2: 車両割り当て (New Player-to-Car Assignment) ----
with tab2:
    st.subheader("🎯 車両割り当てシステム")
    
    # ---- 出席確認 (Player Attendance) ----
    st.subheader("👥 出席確認（選択してください）")
    players = df[['名前', '学年']].dropna().to_dict(orient="records")
    selected_players = st.multiselect(
        "出席する選手を選択してください:", 
        [f"{p['名前']}（{p['学年']}年）" for p in players], 
        default=[]
    )

    # ---- 運転手選択 (Driver Selection) ----
    st.subheader("🚘 運転手（選択してください）")
    if not df.empty:
        drivers = df[['運転手', '定員']].dropna().to_dict(orient="records")
    else:
        drivers = []  # ✅ Return an empty list if no data
    selected_drivers = st.multiselect(
        "利用可能な運転手を選択してください:", 
        [f"{d['運転手']}（{d['定員']}人乗り）" for d in drivers], 
        default=[]
    )

    # ---- 最大車両数設定 (Max Cars Allowed) ----
    max_cars = st.number_input("🔢 最大車両数:", min_value=1, max_value=len(drivers), value=len(drivers))

    # ---- 自動割り当てボタン ----
    if st.button("🖱️ 自動割り当て"):
        if not selected_players or not selected_drivers:
            st.warning("選手と運転手を選択してください！")
        else:
            # Parse selected players and drivers
            selected_player_list = [p.split("（")[0] for p in selected_players]
            selected_driver_list = [d.split("（")[0] for d in selected_drivers]

            # Sort players by grade level
            grade_5 = [p for p in selected_player_list if "5年" in p]
            grade_6 = [p for p in selected_player_list if "6年" in p]

            # Sort drivers by capacity (larger cars first)
            driver_capacities = {d['運転手']: int(d['定員']) for d in drivers if d['運転手'] in selected_driver_list}
            sorted_drivers = sorted(driver_capacities.items(), key=lambda x: x[1], reverse=True)

            # Limit to max cars allowed
            sorted_drivers = sorted_drivers[:max_cars]

            # Assign players
            assignments = {}
            player_queue = grade_5 + grade_6  # Prioritize grade grouping

            for driver, capacity in sorted_drivers:
                assignments[driver] = player_queue[:capacity]
                player_queue = player_queue[capacity:]

            # ---- 結果表示 (Show Results) ----
            st.subheader("📝 割り当て結果")
            for driver, players in assignments.items():
                st.markdown(f"🚗 **{driver} の車** ({driver_capacities[driver]}人乗り)")
                for player in players:
                    st.write(f"- {player}")
            
            # Warn if players remain unassigned
            if player_queue:
                st.warning(f"⚠️ 割り当てできなかった選手: {', '.join(player_queue)}")

