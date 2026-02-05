import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import os

# --- CONFIGURATION ---
INVENTORY_FILE = 'inventory.xlsx'
HISTORY_FILE = 'history.xlsx'
TECH_FILE = 'Technicians.txt'
HOLDER_LIST_FILE = 'PanelID.txt' 
MACHINES = ["Machine 1", "Machine 2", "Machine 3"]

# --- 1. DATA ENGINE (ROBUST VERSION) ---

def load_list_from_txt(filepath, default_content=""):
    """Reads txt files, strips hidden spaces, and forces uppercase."""
    if not os.path.exists(filepath):
        with open(filepath, 'w') as f: f.write(default_content)
    with open(filepath, 'r', encoding='utf-8') as f:
        # The .strip().upper() ensures " 54r123 " becomes "54R123"
        return [line.strip().upper() for line in f.readlines() if line.strip()]

def load_data():
    """Initializes Excel and cleans column data."""
    if not os.path.exists(INVENTORY_FILE):
        df_inv = pd.DataFrame(columns=['Panel_ID', 'Status', 'Sub_Status', 'Location', 'Last_Updated'])
    else:
        df_inv = pd.read_excel(INVENTORY_FILE)
        # Force the Panel_ID column to be Clean Strings
        df_inv['Panel_ID'] = df_inv['Panel_ID'].astype(str).str.strip().str.upper()
        if 'Sub_Status' not in df_inv.columns: df_inv['Sub_Status'] = "N/A"
    
    if not os.path.exists(HISTORY_FILE):
        df_hist = pd.DataFrame(columns=['Date', 'Panel_ID', 'Action', 'User', 'Category', 'Sub_Status', 'Comments'])
    else:
        df_hist = pd.read_excel(HISTORY_FILE)
        df_hist['Panel_ID'] = df_hist['Panel_ID'].astype(str).str.strip().str.upper()
        
    return df_inv, df_hist

def save_data(df_inv, df_hist):
    df_inv.to_excel(INVENTORY_FILE, index=False)
    df_hist.to_excel(HISTORY_FILE, index=False)

# --- 2. INTERFACE ---

st.set_page_config(layout="wide", page_title="Scientific Panel Tracking System")

# Load Cleaned Data
tech_names = load_list_from_txt(TECH_FILE, "Admin\nAnand")
master_id_list = load_list_from_txt(HOLDER_LIST_FILE, "54R15564")
df_inv, df_hist = load_data()

st.title("Panel Holder Tracking System")

# --- TOP LAYER: KPIs ---
kpis = st.columns(5)
# Re-calculate counts from cleaned data
total = len(df_inv)
in_use = len(df_inv[df_inv['Status'] == 'In Use'])
repair = len(df_inv[df_inv['Status'] == 'Under Repair'])
pm = len(df_inv[df_inv['Status'] == 'Under PM'])
damaged = len(df_inv[df_inv['Status'] == 'Damaged'])

kpis[0].metric("Total Fleet", total)
kpis[1].metric("🟢 In Use", in_use)
kpis[2].metric("🔴 Under Repair", repair)
kpis[3].metric("🟠 Under PM", pm)
kpis[4].metric("⚠️ Damaged", damaged)

st.divider()

# --- MIDDLE LAYER: OPERATIONS ---
col_id, col_action = st.columns([1, 1.2])

with col_id:
    st.subheader("1. Identify Agent & Asset")
    selected_tech = st.selectbox("Select Technician", options=tech_names)
    
    # Input is cleaned immediately
    raw_input = st.text_input("Scan or Type Panel ID").strip().upper()
    
    if raw_input:
        exists_in_db = raw_input in df_inv['Panel_ID'].values
        exists_in_master = raw_input in master_id_list
        
        if exists_in_db:
            row = df_inv[df_inv['Panel_ID'] == raw_input].iloc[0]
            st.success(f"ID Verified: **{raw_input}**")
            st.info(f"Current State: {row['Status']} at {row['Location']}")
        else:
            st.warning(f"ID **{raw_input}** is not yet in the tracking database.")
            if not exists_in_master:
                st.error(f"Warning: {raw_input} is also missing from {HOLDER_LIST_FILE} list.")
            
            if st.button(f"➕ Register {raw_input} to System"):
                new_asset = {
                    'Panel_ID': raw_input, 
                    'Status': 'Storage', 
                    'Sub_Status': 'N/A', 
                    'Location': 'Storage', 
                    'Last_Updated': datetime.now()
                }
                df_inv = pd.concat([df_inv, pd.DataFrame([new_asset])], ignore_index=True)
                
                # Auto-append to PanelID.txt if missing
                if not exists_in_master:
                    with open(HOLDER_LIST_FILE, "a") as f:
                        f.write(f"\n{raw_input}")
                
                save_data(df_inv, df_hist)
                st.success("Registration Complete!")
                st.rerun()

with col_action:
    st.subheader("2. Execute Action")
    if not raw_input or raw_input not in df_inv['Panel_ID'].values:
        st.write("⬅️ *Identify or Register a Panel ID on the left to unlock actions.*")
        
        # HELP SECTION FOR USER
        with st.expander("Why is my ID not showing up?"):
            st.write("1. **Check the Excel:** Open `inventory.xlsx`. Is the ID there?")
            st.write("2. **Case Sensitivity:** The app converts everything to UPPERCASE automatically now.")
            st.write("3. **Master List:** Check `PanelID.txt`. Ensure there is only one ID per line.")
            if st.checkbox("Show all IDs currently in Database"):
                st.write(df_inv['Panel_ID'].tolist())
    else:
        # [The rest of the form logic remains the same as v7.0]
        op_type = st.radio("Activity:", ["Install to Machine", "Remove from Machine"], horizontal=True)
        with st.form("lifecycle_form"):
            category = "Production"
            if op_type == "Install to Machine":
                final_location = st.selectbox("Machine:", MACHINES)
                final_status = "In Use"
                final_sub_status = "N/A"
            else:
                final_location = "Workshop"
                reason_main = st.selectbox("Reason:", ["Repair", "Preventive Maintenance", "Damaged", "Other"])
                category = st.selectbox("Category:", ["CSS", "Tape", "Other"])
                other_comment = st.text_input("Other Detail:") if category == "Other" else ""
                
                if reason_main == "Repair":
                    final_sub_status = st.selectbox("Repair Status:", ["To check", "Waiting Parts", "Ready to Install"])
                    final_status = "Under Repair"
                elif reason_main == "Preventive Maintenance": final_status = "Under PM"; final_sub_status = "N/A"
                elif reason_main == "Damaged": final_status = "Damaged"; final_sub_status = "N/A"
                else: final_status = "Other"; final_sub_status = "N/A"

            notes = st.text_area("Notes")
            if st.form_submit_button("SUBMIT"):
                full_comment = f"[{category}] {other_comment} | {notes}" if category == "Other" else f"[{category}] {notes}"
                df_inv.loc[df_inv['Panel_ID'] == raw_input, ['Status', 'Sub_Status', 'Location', 'Last_Updated']] = [final_status, final_sub_status, final_location, datetime.now()]
                new_log = {'Date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 'Panel_ID': raw_input, 'Action': op_type, 'User': selected_tech, 'Category': category, 'Sub_Status': final_sub_status, 'Comments': full_comment}
                df_hist = pd.concat([df_hist, pd.DataFrame([new_log])], ignore_index=True)
                save_data(df_inv, df_hist)
                st.rerun()

st.divider()
st.subheader("📊 Analytics")
# [Charts tabs code remains the same]
