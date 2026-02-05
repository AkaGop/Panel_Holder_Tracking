import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import os

# --- SCIENTIFIC CONFIGURATION ---
INVENTORY_FILE = 'inventory.xlsx'
HISTORY_FILE = 'history.xlsx'
TECH_FILE = 'Technicians.txt'
HOLDER_LIST_FILE = 'PanelID.txt'  # UPDATED FILENAME
MACHINES = ["ECP 101", "ECp 102", "ECp 103"]

# --- 1. DATA ENGINE ---

def load_list_from_txt(filepath, default_content=""):
    """Generic loader for technician and ID master lists."""
    if not os.path.exists(filepath):
        with open(filepath, 'w') as f: f.write(default_content)
    with open(filepath, 'r') as f:
        return [line.strip() for line in f.readlines() if line.strip()]

def load_data():
    """Initializes and repairs the live tracking databases."""
    if not os.path.exists(INVENTORY_FILE):
        df_inv = pd.DataFrame(columns=['Panel_ID', 'Status', 'Sub_Status', 'Location', 'Last_Updated'])
    else:
        df_inv = pd.read_excel(INVENTORY_FILE)
        # Structural Integrity Check
        if 'Sub_Status' not in df_inv.columns: df_inv['Sub_Status'] = "N/A"
    
    if not os.path.exists(HISTORY_FILE):
        df_hist = pd.DataFrame(columns=['Date', 'Panel_ID', 'Action', 'User', 'Category', 'Sub_Status', 'Comments'])
    else:
        df_hist = pd.read_excel(HISTORY_FILE)
    return df_inv, df_hist

def save_data(df_inv, df_hist):
    """Saves the digital twin state back to Excel."""
    df_inv.to_excel(INVENTORY_FILE, index=False)
    df_hist.to_excel(HISTORY_FILE, index=False)

# --- 2. THE CONTROL CENTER INTERFACE ---

st.set_page_config(layout="wide", page_title="Scientific Panel Tracking System")

# Load external data
tech_names = load_list_from_txt(TECH_FILE, "Admin\nAnand")
# Load the renamed PanelID file
master_id_list = load_list_from_txt(HOLDER_LIST_FILE, "54R15564")
df_inv, df_hist = load_data()

st.title("Panel Holder Tracking System")

# --- TOP LAYER: MANAGEMENT KPIs ---
kpis = st.columns(5)
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

# --- MIDDLE LAYER: DAILY OPERATIONS ---
col_id, col_action = st.columns([1, 1.2])

with col_id:
    st.subheader("1. Identify Agent & Asset")
    selected_tech = st.selectbox("Select Technician", options=tech_names)
    
    # Search input accepts manual typing, barcode, or ID copy-paste
    pid_input = st.text_input("Scan or Type Panel ID (from PanelID.txt)").strip()
    
    if pid_input:
        exists_in_db = pid_input in df_inv['Panel_ID'].values
        exists_in_master = pid_input in master_id_list
        
        if exists_in_db:
            row = df_inv[df_inv['Panel_ID'] == pid_input].iloc[0]
            st.success(f"ID Verified: **{pid_input}**")
            st.info(f"Current State: {row['Status']} at {row['Location']}")
        else:
            # NEW ID HANDLING
            st.warning(f"ID **{pid_input}** is not yet in the tracking database.")
            if not exists_in_master:
                st.error(f"Warning: {pid_input} is also missing from {HOLDER_LIST_FILE} list.")
            
            if st.button(f"➕ Register {pid_input} to System"):
                new_asset = {
                    'Panel_ID': pid_input, 
                    'Status': 'Storage', 
                    'Sub_Status': 'N/A', 
                    'Location': 'Storage', 
                    'Last_Updated': datetime.now()
                }
                df_inv = pd.concat([df_inv, pd.DataFrame([new_asset])], ignore_index=True)
                
                # Auto-append to PanelID.txt if it was missing to keep sync
                if not exists_in_master:
                    with open(HOLDER_LIST_FILE, "a") as f:
                        f.write(f"\n{pid_input}")
                
                save_data(df_inv, df_hist)
                st.success("Registration Complete!")
                st.rerun()

with col_action:
    st.subheader("2. Execute Action")
    if not pid_input or pid_input not in df_inv['Panel_ID'].values:
        st.write("⬅️ *Identify or Register a Panel ID on the left to unlock actions.*")
    else:
        op_type = st.radio("What is the activity?", ["Install to Machine", "Remove from Machine"], horizontal=True)
        
        with st.form("lifecycle_form"):
            category = "Production"
            
            if op_type == "Install to Machine":
                final_location = st.selectbox("Install into Machine:", MACHINES)
                final_status = "In Use"
                final_sub_status = "N/A"
            else:
                # REMOVAL LOGIC
                final_location = "Workshop"
                reason_main = st.selectbox("Removal Reason:", ["Repair", "Preventive Maintenance", "Damaged", "Other"])
                category = st.selectbox("Failure Source Category:", ["CSS", "Tape", "Other"])
                
                # Logic for 'Other' comment
                other_comment = ""
                if category == "Other":
