import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import os

# --- FILE CONFIGURATION ---
INVENTORY_FILE = 'inventory.xlsx'
HISTORY_FILE = 'history.xlsx'
TECH_FILE = 'Technicians.txt'
HOLDER_LIST_FILE = 'PanelHolders.txt' # The new master list
MACHINES = ["Machine 1", "Machine 2", "Machine 3"]

# --- 1. DATA ENGINE ---

def load_list_from_txt(filepath, default_content=""):
    """Generic loader for txt files."""
    if not os.path.exists(filepath):
        with open(filepath, 'w') as f:
            f.write(default_content)
    with open(filepath, 'r') as f:
        return [line.strip() for line in f.readlines() if line.strip()]

def load_data():
    """Initializes Excel database files."""
    if not os.path.exists(INVENTORY_FILE):
        df_inv = pd.DataFrame(columns=['Panel_ID', 'Status', 'Location', 'Last_Updated'])
    else:
        df_inv = pd.read_excel(INVENTORY_FILE)
    
    if not os.path.exists(HISTORY_FILE):
        df_hist = pd.DataFrame(columns=['Date', 'Panel_ID', 'Action', 'User', 'Reason', 'Comments'])
    else:
        df_hist = pd.read_excel(HISTORY_FILE)
    return df_inv, df_hist

def save_data(df_inv, df_hist):
    df_inv.to_excel(INVENTORY_FILE, index=False)
    df_hist.to_excel(HISTORY_FILE, index=False)

# --- 2. USER INTERFACE ---

st.set_page_config(layout="wide", page_title="Master Panel Tracker")

# Load external lists
tech_names = load_list_from_txt(TECH_FILE, "Admin\nTechnician 1")
master_holder_list = load_list_from_txt(HOLDER_LIST_FILE, "54R15564\n54R15565")
df_inv, df_hist = load_data()

# --- SIDEBAR: SYSTEM ADMIN ---
with st.sidebar:
    st.header("⚙️ System Control")
    if st.button("🔄 Sync Master List from TXT"):
        # Find IDs in TXT that are not in EXCEL
        existing_ids = df_inv['Panel_ID'].tolist()
        new_entries = []
        for pid in master_holder_list:
            if pid not in existing_ids:
                new_entries.append({
                    'Panel_ID': pid, 
                    'Status': 'Unknown', 
                    'Location': 'Storage', 
                    'Last_Updated': datetime.now()
                })
        
        if new_entries:
            df_inv = pd.concat([df_inv, pd.DataFrame(new_entries)], ignore_index=True)
            save_data(df_inv, df_hist)
            st.success(f"Imported {len(new_entries)} new Panel Holders!")
            st.rerun()
        else:
            st.info("Inventory is already synced with Master List.")

    st.divider()
    st.write("**Export Data**")
    csv = df_hist.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Download Audit Log (CSV)", csv, "history.csv", "text/csv")

st.title("Panel Holder Tracking System")

# --- TOP LAYER: CAPACITY KPIs ---
kpi_cols = st.columns(len(MACHINES) + 1)
with kpi_cols[0]:
    st.metric("Total Active Fleet", len(df_inv))

for i, m in enumerate(MACHINES):
    count = len(df_inv[(df_inv['Location'] == m) & (df_inv['Status'] == 'In Use')])
    delta_val = count - 24
    kpi_cols[i+1].metric(f"{m} Load", f"{count}/24", delta=delta_val, delta_color="normal" if delta_val >= 0 else "inverse")

st.divider()

# --- MIDDLE LAYER: OPERATIONS ---
col_id, col_action = st.columns([1, 1])

with col_id:
    st.subheader("1. Identification")
    selected_tech = st.selectbox("Select Your Name", options=tech_names)
    
    # Use autocomplete/select box or text input
    pid_input = st.selectbox("Search/Scan Panel ID", options=[""] + master_holder_list, help="Start typing the Panel ID")
    
    if pid_input:
        # Check if it's already in the tracking database
        exists_in_db = pid_input in df_inv['Panel_ID'].values
        
        if exists_in_db:
            current_row = df_inv[df_inv['Panel_ID'] == pid_input].iloc[0]
            st.success(f"Status: {current_row['Status']} | Location: {current_row['Location']}")
        else:
            st.warning(f"ID {pid_input} is in Master List but not yet initialized in Database.")
            if st.button("Initialize this Panel ID"):
                new_asset = {'Panel_ID': pid_input, 'Status': 'Unknown', 'Location': 'Storage', 'Last_Updated': datetime.now()}
                df_inv = pd.concat([df_inv, pd.DataFrame([new_asset])], ignore_index=True)
                save_data(df_inv, df_hist)
                st.rerun()

with col_action:
    st.subheader("2. Execute Operation")
    # Only allow actions if ID exists in our active tracking
    if not pid_input or pid_input not in df_inv['Panel_ID'].values:
        st.info("Select a valid Panel ID to enable actions.")
    else:
        operation = st.radio("Operation Type:", ["Install to Machine", "Remove from Machine"], horizontal=True)
        
        with st.form("op_form"):
            if operation == "Install to Machine":
                target_loc = st.selectbox("Target Machine:", MACHINES)
                new_status = "In Use"
                reason = "Production"
            else:
                target_loc = "Workshop"
                reason = st.selectbox("Reason:", ["Preventive Maintenance", "Repair", "Unknown"])
                new_status = f"Under {reason}" if "Unknown" not in reason else "Unknown"
            
            notes = st.text_area("Observations / Damage Comments")
            
            if st.form_submit_button("SUBMIT"):
                # Update Inventory
                df_inv.loc[df_inv['Panel_ID'] == pid_input, ['Status', 'Location', 'Last_Updated']] = [new_status, target_loc, datetime.now()]
                
                # Update Log
                new_log = {
                    'Date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'Panel_ID': pid_input,
                    'Action': operation,
                    'User': selected_tech,
                    'Reason': reason,
                    'Comments': notes
                }
                df_hist = pd.concat([df_hist, pd.DataFrame([new_log])], ignore_index=True)
                
                save_data(df_inv, df_hist)
                st.toast(f"Updated {pid_input} successfully!")
                st.rerun()

st.divider()

# --- BOTTOM LAYER: ANALYTICS ---
tab_charts, tab_data = st.tabs(["📊 Performance Analytics", "📜 Detailed History"])

with tab_charts:
    c1, c2 = st.columns(2)
    with c1:
        fig_pie = px.pie(df_inv, names='Status', title="Inventory Health Distribution",
                         color='Status', color_discrete_map={"In Use":"#2ecc71", "Under Repair":"#e74c3c", "Under PM":"#f1c40f"})
        st.plotly_chart(fig_pie, use_container_width=True)
    with c2:
        trend_df = df_hist.copy()
        if not trend_df.empty:
            trend_df['Date'] = pd.to_datetime(trend_df['Date'])
            daily = trend_df.groupby([trend_df['Date'].dt.date, 'Reason']).size().reset_index(name='Events')
            fig_line = px.line(daily, x='Date', y='Events', color='Reason', title="Activity Trends")
            st.plotly_chart(fig_line, use_container_width=True)

with tab_data:
    st.dataframe(df_hist.sort_values(by='Date', ascending=False), use_container_width=True)
