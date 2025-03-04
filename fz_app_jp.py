import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import time
import googlemaps

# ==============================
# 🚀 Secure Full-Screen Login System
# ==============================

USERNAME = st.secrets["app"]["username"]
PASSWORD = st.secrets["app"]["password"]

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.markdown("<div style='text-align:center'><h2>🔑 ログイン</h2></div>", unsafe_allow_html=True)
    entered_username = st.text_input("ユーザー名", value="", key="username")
    entered_password = st.text_input("パスワード", value="", type="password", key="password")

    if st.button("ログイン"):
        if entered_username == USERNAME and entered_password == PASSWORD:
            st.session_state.logged_in = True
            st.experimental_rerun()
        else:
            st.error("🚫 ユーザー名またはパスワードが違います")
    st.stop()

# Load API Key from environment variables
API_KEY = st.secrets["google_maps"]["api_key"]

if not API_KEY:
    raise ValueError("⚠️ Missing Google Maps API Key! Set GMAPS_API_KEY in environment variables.")

# Initialize Google Maps client
gmaps = googlemaps.Client(key=API_KEY)

# ==============================
# ✅ Google Sheets Authentication (Using Streamlit Secrets)
# ==============================

service_account_info = dict(st.secrets["google_credentials"])

service_account_info["private_key"] = service_account_info["private_key"].replace("\\n", "\n")

google_creds = dict(st.secrets["google_credentials"])  # ✅ Ensure it's a dictionary
creds = Credentials.from_service_account_info(service_account_info, scopes=["https://www.googleapis.com/auth/spreadsheets"])
client = gspread.authorize(creds)

SHEET_ID = "1upehCYwnGEcKg_zVQG7jlnNUykFmvNbuAtnxzqvSEcA"
spreadsheet = client.open_by_key(SHEET_ID)
sheet1 = spreadsheet.worksheet("Sheet1")  # 🚗 車代管理
sheet2 = spreadsheet.worksheet("Sheet2")  # 🎯 車両割り当て

# ==============================
# 🚀 Google Sheets Data Caching (Avoid API Rate Limits)
# ==============================
def load_google_sheet_data():
    if "sheet2_data" not in st.session_state or time.time() - st.session_state["last_fetch_time"] > 60:
        sheet2_data = sheet2.get_all_values()
        st.session_state["sheet2_data"] = sheet2_data
        st.session_state["last_fetch_time"] = time.time()
    return st.session_state["sheet2_data"]

sheet2_data = load_google_sheet_data()
df_sheet2 = pd.DataFrame(sheet2_data[1:], columns=sheet2_data[0]) if sheet2_data else pd.DataFrame(columns=["名前", "学年", "運転手", "定員", "親"])

# ==============================
# 🔹 Create Tabs for Features
# ==============================
tab1, tab2 = st.tabs(["🚗 車代管理", "🎯 車両割り当て"])

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
        sheet1.append_rows(new_entries, value_input_option="USER_ENTERED")
    
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
        records = sheet1.get_all_values()
    
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
    
    df = pd.DataFrame(sheet1.get_all_records())
    
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
            all_records = sheet1.get_all_values()
    
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
                        sheet1.update_cell(i + 1, 3, new_value)  # ✅ Update "金額" (Column C)
                        sheet1.update_cell(i + 1, 5, "")  # ✅ Clear "補足" (Column E)
            
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

import time

# ---- Google Sheets Data Caching ----
@st.cache_resource
def load_google_sheet_data():
    """Loads Google Sheet data only when necessary to avoid API rate limits."""
    if "sheet2_data" not in st.session_state or time.time() - st.session_state.get("last_fetch_time", 0) > 60:
        sheet2_data = sheet2.get_all_values()
        st.session_state["sheet2_data"] = sheet2_data
        st.session_state["last_fetch_time"] = time.time()  # ✅ Store last refresh time
    return st.session_state["sheet2_data"]

# ✅ Load Google Sheets data efficiently
sheet2_data = load_google_sheet_data()
df_sheet2 = pd.DataFrame(sheet2_data[1:], columns=sheet2_data[0]) if sheet2_data else pd.DataFrame(columns=["名前", "学年", "運転手", "定員", "親"])

# ---- TAB 2: 車両割り当て (New Player-to-Car Assignment) ----
with tab2:
    st.subheader("🎯 車両割り当てシステム")

    # ---- Google Sheets Data Caching ----
    def load_google_sheet_data():
        """Loads Google Sheet data only when necessary to avoid API rate limits."""
        if "sheet2_data" not in st.session_state or time.time() - st.session_state["last_fetch_time"] > 60:
            sheet2_data = sheet2.get_all_values()
            st.session_state["sheet2_data"] = sheet2_data
            st.session_state["last_fetch_time"] = time.time()  # ✅ Store last refresh time
        return st.session_state["sheet2_data"]

    # ✅ Load Google Sheets data efficiently
    sheet2_data = load_google_sheet_data()
    if sheet2_data:
        df_sheet2 = pd.DataFrame(sheet2_data[1:], columns=sheet2_data[0])  # ✅ Convert to DataFrame
    else:
        df_sheet2 = pd.DataFrame(columns=["名前", "学年", "運転手", "定員", "親"])  # ✅ Ensure correct columns

    # ---- 出席確認 (Player Attendance) ----
    st.subheader("👥 出席確認（チェックを入れてください）")

    # ✅ Ensure selections persist
    if "selected_players" not in st.session_state:
        st.session_state.selected_players = set()

    if not df_sheet2.empty:
        players = df_sheet2[['名前', '学年', '親']].dropna().to_dict(orient="records")

        # ✅ Handle "全員選択" properly by updating session state immediately
        if st.button("全員選択", key="select_all_players"):
            st.session_state.selected_players = {p["名前"] for p in players}  # ✅ Update session state immediately

        player_columns = st.columns(2)  # ✅ Arrange checkboxes in 2 columns
        for i, player in enumerate(players):
            with player_columns[i % 2]:  # ✅ Distribute checkboxes across two columns
                key = f"player_{player['名前'].replace(' ', '_')}"  # ✅ Ensure unique key
                checked = player['名前'] in st.session_state.selected_players
                new_value = st.checkbox(f"{player['名前']}（{player['学年']}年）", value=checked, key=key)

                # ✅ Update session state directly when checkbox is toggled
                if new_value:
                    st.session_state.selected_players.add(player['名前'])
                else:
                    st.session_state.selected_players.discard(player['名前'])

    else:
        st.warning("⚠️ 選手データがありません。")

    # ---- 運転手選択 (Driver Selection) ----
    st.subheader("🚘 運転手（チェックを入れてください）")

    # ✅ Ensure driver selections persist
    if "selected_drivers" not in st.session_state:
        st.session_state.selected_drivers = set()

    if not df_sheet2.empty:
        # ✅ Remove blank rows from the driver list
        drivers = [d for d in df_sheet2[['運転手', '定員']].dropna().to_dict(orient="records") if d["運転手"] and d["定員"]]

        driver_columns = st.columns(2)  # ✅ Arrange checkboxes in 2 columns
        for i, driver in enumerate(drivers):
            with driver_columns[i % 2]:  # ✅ Distribute checkboxes across two columns
                key = f"driver_{driver['運転手'].replace(' ', '_')}_{i}"  # ✅ Ensure unique key
                checked = driver['運転手'] in st.session_state.selected_drivers
                new_value = st.checkbox(f"{driver['運転手']}（{driver['定員']}人乗り）", value=checked, key=key)

                # ✅ Update session state directly when checkbox is toggled
                if new_value:
                    st.session_state.selected_drivers.add(driver['運転手'])
                else:
                    st.session_state.selected_drivers.discard(driver['運転手'])

    else:
        st.warning("⚠️ 運転手データがありません。")

    # ---- 最大車両数設定 (Max Cars Allowed) ----
    max_cars = min(len(st.session_state.selected_drivers), st.number_input("🔢 最大車両数:", min_value=1, max_value=len(drivers), value=10))  # ✅ Ensure it doesn’t exclude selected drivers

    # ---- 自動割り当てボタン ----
    if st.button("🖱️ 自動割り当て"):
        if not st.session_state.selected_players or not st.session_state.selected_drivers:
            st.warning("⚠️ 選手と運転手を選択してください！")
        else:
            selected_player_list = list(st.session_state.selected_players)
            selected_driver_list = list(st.session_state.selected_drivers)

            # ✅ Organize players by grade
            player_grades = {p["名前"]: p["学年"] for p in players if p["名前"] in selected_player_list}
            grade_5 = [p for p in selected_player_list if player_grades.get(p) == "5"]
            grade_6 = [p for p in selected_player_list if player_grades.get(p) == "6"]
            player_queue = grade_5 + grade_6  # ✅ Ensure player queue is correct

            # ✅ Sort drivers by capacity (largest first)
            driver_capacities = {d['運転手']: int(d['定員']) for d in drivers if d['運転手'] in selected_driver_list}
            sorted_drivers = sorted(driver_capacities.items(), key=lambda x: x[1], reverse=True)
            sorted_drivers = sorted_drivers[:max_cars]  # ✅ Apply max car limit

            # ✅ Assign parent-child first
            player_parents = {p["名前"]: p["親"] for p in players if p["名前"] in selected_player_list and p.get("親") and p["親"] in selected_driver_list}

            assignments = {}
            for driver, capacity in sorted_drivers:
                assigned_players = []

                # ✅ Assign child to their parent first
                for player, parent in player_parents.items():
                    if parent == driver and player in player_queue:
                        assigned_players.append(player)
                        player_queue.remove(player)

                # ✅ Fill remaining seats
                while len(assigned_players) < capacity and player_queue:
                    assigned_players.append(player_queue.pop(0))

                # ✅ Prevent single-kid cars by redistributing
                if len(assigned_players) == 1 and len(player_queue) >= 1:
                    assigned_players.append(player_queue.pop(0))

                assignments[driver] = assigned_players

            # ✅ Remove drivers who received no players
            assignments = {driver: players for driver, players in assignments.items() if players}

            # ---- 結果表示 (Show Results) ----
            st.subheader("📝 割り当て結果")

            for driver, players in assignments.items():
                st.markdown(f"🚗 **{driver} の車** ({driver_capacities[driver]}人乗り)")
                for player in players:
                    st.write(f"- {player}")

            # Warn if players remain unassigned
            if player_queue:
                st.warning(f"⚠️ 割り当てできなかった選手: {', '.join(player_queue)}")

