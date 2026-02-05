import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import os

# --- FILE CONFIGURATION ---
INVENTORY_FILE = 'inventory.xlsx'
HISTORY_FILE = 'history.xlsx'
TECH_FILE = 'technicians.txt'
MACHINES = ["Machine 1", "Machine 2", "Machine 3"]

# --- 1. BACKEND FUNCTIONS ---

def load_technicians():
    """Load list of technicians from txt file."""
    if not os.path.exists(TECH_FILE):
        # Create default file if missing
        with open(TECH_FILE, 'w') as f:
            f.write("Technician 1\nTechnician 2\nSupervisor")
    
    with open(TECH_FILE, 'r') as f:
        # Read lines and remove empty ones
        names = [line.strip() for line in f.readlines() if line.strip()]
    return names

def load_data():
    """Create Excel files if they don't exist, otherwise load them."""
    # A. Inventory File (Snapshot)
    if not os.path.exists(INVENTORY_FILE):
        data = []
        # Generate dummy IDs using the format 54R155xx
        counter = 1
        for m in range(1, 4):
            for i in range(1, 25):
                # Creating IDs like 54R15501, 54R15502...
                pid = f"54R155{counter:02d}" 
                data.append({
                    'Panel_ID': pid,
                    'Status': 'In Use',
                    'Location': f'Machine {m}',
                    'Last_Reason': 'Initial Setup'
                })
                counter += 1
        
        df_inv = pd.DataFrame(data)
        df_inv.to_excel(INVENTORY_FILE, index=False)
    else:
        df_inv = pd.read_excel(INVENTORY_FILE)
        # Ensure column name is correct if file existed before
        if 'Jig_ID' in df_inv.columns:
            df_inv.rename(columns={'Jig_ID': 'Panel_ID'}, inplace=True)

    # B. History File (Log)
    if not os.path.exists(HISTORY_FILE):
        df_hist = pd.DataFrame(columns=['Date', 'Panel_ID', 'Action', 'User', 'Reason', 'Comments'])
        df_hist.to_excel(HISTORY_FILE, index=False)
    else:
        df_hist = pd.read_excel(HISTORY_FILE)
        if 'Jig_ID' in df_hist.columns:
            df_hist.rename(columns={'Jig_ID': 'Panel_ID'}, inplace=True)
        
    return df_inv, df_hist

def update_panel(panel_id, action, user, reason, comments, new_status, new_location):
    df_inv, df_hist = load_data()
    
    # Update Inventory
    idx = df_inv.index[df_inv['Panel_ID'] == panel_id].tolist()
    if not idx:
        return False # Should be caught by UI validation
    
    df_inv.at[idx[0], 'Status'] = new_status
    df_inv.at[idx[0], 'Location'] = new_location
    df_inv.at[idx[0], 'Last_Reason'] = reason
    df_inv.to_excel(INVENTORY_FILE, index=False)
    
    # Update History
    new_entry = {
        'Date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'Panel_ID': panel_id,
        'Action': action,
        'User': user,
        'Reason': reason,
        'Comments': comments
    }
    df_hist = pd.concat([df_hist, pd.DataFrame([new_entry])], ignore_index=True)
    df_hist.to_excel(HISTORY_FILE, index=False)
    return True

# --- 2. FRONTEND ---

st.set_page_config(layout="wide", page_title="Panel Holder Tracking")
tech_names = load_technicians()

# Sidebar for Downloads
with st.sidebar:
    st.header("📂 Data Management")
    # Load data for download buttons
    df_inv, df_hist = load_data()
    
    with open(INVENTORY_FILE, "rb") as f:
        st.download_button("📥 Download Inventory", f, file_name="panel_inventory.xlsx")
        
    with open(HISTORY_FILE, "rb") as f:
        st.download_button("📥 Download History Log", f, file_name="history_log.xlsx")

# Top KPI Section
st.title("🏭 Panel Holder Tracker")
kpi1, kpi2, kpi3, kpi4 = st.columns(4)

total_items = len(df_inv)
in_use = len(df_inv[df_inv['Status'] == 'In Use'])
repair = len(df_inv[df_inv['Status'] == 'Under Repair'])
pm = len(df_inv[df_inv['Status'] == 'Under PM'])

kpi1.metric("Total Panel Holders", total_items)
kpi2.metric("🟢 In Use", in_use)
kpi3.metric("🔴 Under Repair", repair)
kpi4.metric("🟠 Under PM", pm)

st.divider()

# --- MAIN INTERFACE ---
col_scan, col_action = st.columns([1, 2])

# 1. SCAN SECTION
with col_scan:
    st.subheader("1. Identify")
    
    # A. Technician Selection
    user_name = st.selectbox("Select Technician", tech_names)
    
    # B. ID Input
    if 'scan_input' not in st.session_state:
        st.session_state.scan_input = ""
        
    panel_id_input = st.text_input("Scan Panel ID (e.g., 54R15564)", key="scan_input")
    
    valid_id = False
    
    if panel_id_input:
        # VALIDATION LOGIC
        curr_row = df_inv[df_inv['Panel_ID'] == panel_id_input]
        
        if not curr_row.empty:
            valid_id = True
            s = curr_row.iloc[0]['Status']
            l = curr_row.iloc[0]['Location']
            st.success(f"✅ ID Found: **{panel_id_input}**")
            st.info(f"Status: **{s}** | Location: **{l}**")
        else:
            st.error(f"❌ INVALID ID: '{panel_id_input}'")
            st.markdown("**Please check the number and try again.**")

# 2. ACTION SECTION
with col_action:
    st.subheader("2. Action")
    
    if not valid_id:
        st.write("🚫 *Enter a valid Panel ID to see actions.*")
    else:
        # We use Tabs so both actions are always available
        tab_remove, tab_add = st.tabs(["🔴 REMOVE / REPAIR", "🟢 ADD / INSTALL"])
        
        # --- TAB 1: REMOVE ---
        with tab_remove:
            with st.form("remove_form"):
                r_reason = st.selectbox("Reason", ["Preventive Maintenance", "Repair", "Unknown"])
                r_comment = st.text_input("Damage Details (Required for Repair)")
                btn_remove = st.form_submit_button("Submit Removal")
                
                if btn_remove:
                    new_stat = "Under Repair" if r_reason == "Repair" else "Under PM"
                    if r_reason == "Unknown": new_stat = "Unknown"
                    
                    update_panel(panel_id_input, "REMOVE", user_name, r_reason, r_comment, new_stat, "Workshop")
                    st.success(f"✅ {panel_id_input} removed for {r_reason}")
                    st.rerun()

        # --- TAB 2: ADD ---
        with tab_add:
            with st.form("add_form"):
                a_machine = st.selectbox("Select Target Machine", MACHINES)
                a_comment = st.text_input("Comments (Optional)", value="Returned to service")
                btn_add = st.form_submit_button("Submit Installation")
                
                if btn_add:
                    update_panel(panel_id_input, "ADD", user_name, "Production", a_comment, "In Use", a_machine)
                    st.success(f"✅ {panel_id_input} installed on {a_machine}")
                    st.rerun()

st.divider()

# --- CHARTS SECTION ---
st.subheader("📊 Analytics & Trends")

c1, c2 = st.columns(2)

with c1:
    st.markdown("**Real-Time Status**")
    status_counts = df_inv['Status'].value_counts().reset_index()
    status_counts.columns = ['Status', 'Count']
    
    fig_bar = px.bar(status_counts, x='Status', y='Count', color='Status',
                     color_discrete_map={"In Use": "green", "Under Repair": "red", "Under PM": "orange", "Unknown": "gray"})
    st.plotly_chart(fig_bar, use_container_width=True)

with c2:
    st.markdown("**Repair Trend (Last 30 Days)**")
    if not df_hist.empty:
        df_hist['Date'] = pd.to_datetime(df_hist['Date'])
        # Filter only "Remove" actions related to Repair/PM
        trend_data = df_hist[df_hist['Action'] == 'REMOVE'].groupby(df_hist['Date'].dt.date).size().reset_index(name='Count')
        fig_line = px.line(trend_data, x='Date', y='Count', markers=True, title="Items Removed per Day")
        st.plotly_chart(fig_line, use_container_width=True)
    else:
        st.info("No history data available yet for trends.")
