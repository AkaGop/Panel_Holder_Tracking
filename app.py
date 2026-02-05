import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import os

# --- FILE CONFIGURATION ---
INVENTORY_FILE = 'inventory.xlsx'
HISTORY_FILE = 'history.xlsx'
MACHINES = ["ECP 101", "ECP 102", "ECP 102"]

# --- 1. BACKEND FUNCTIONS ---

def load_data():
    """Create Excel files if they don't exist, otherwise load them."""
    # A. Inventory File
    if not os.path.exists(INVENTORY_FILE):
        data = []
        for m in range(1, 4):
            for j in range(1, 25):
                data.append({
                    'Jig_ID': f'M{m}-JIG-{j:02d}',
                    'Status': 'In Use',
                    'Location': f'Machine {m}',
                    'Last_Reason': 'Initial Setup'
                })
        df_inv = pd.DataFrame(data)
        df_inv.to_excel(INVENTORY_FILE, index=False)
    else:
        df_inv = pd.read_excel(INVENTORY_FILE)

    # B. History File
    if not os.path.exists(HISTORY_FILE):
        df_hist = pd.DataFrame(columns=['Date', 'Jig_ID', 'Action', 'User', 'Reason', 'Comments'])
        df_hist.to_excel(HISTORY_FILE, index=False)
    else:
        df_hist = pd.read_excel(HISTORY_FILE)
        
    return df_inv, df_hist

def update_jig(jig_id, action, user, reason, comments, new_status, new_location):
    df_inv, df_hist = load_data()
    
    # Update Inventory
    idx = df_inv.index[df_inv['Jig_ID'] == jig_id].tolist()
    if not idx:
        st.error(f"❌ Jig {jig_id} not found in database!")
        return False
    
    df_inv.at[idx[0], 'Status'] = new_status
    df_inv.at[idx[0], 'Location'] = new_location
    df_inv.at[idx[0], 'Last_Reason'] = reason
    df_inv.to_excel(INVENTORY_FILE, index=False)
    
    # Update History
    new_entry = {
        'Date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'Jig_ID': jig_id,
        'Action': action,
        'User': user,
        'Reason': reason,
        'Comments': comments
    }
    df_hist = pd.concat([df_hist, pd.DataFrame([new_entry])], ignore_index=True)
    df_hist.to_excel(HISTORY_FILE, index=False)
    return True

# --- 2. FRONTEND ---

st.set_page_config(layout="wide", page_title="Jig Automation v2")

# Sidebar for Downloads
with st.sidebar:
    st.header("📂 Data Management")
    st.write("Download your data for Excel reporting.")
    
    # Load data for download buttons
    df_inv, df_hist = load_data()
    
    with open(INVENTORY_FILE, "rb") as f:
        st.download_button("📥 Download Inventory (Live)", f, file_name="live_inventory.xlsx")
        
    with open(HISTORY_FILE, "rb") as f:
        st.download_button("📥 Download History Log", f, file_name="history_log.xlsx")

# Top KPI Section
st.title("🏭 Real-Time Jig Tracker")
kpi1, kpi2, kpi3, kpi4 = st.columns(4)
total_jigs = len(df_inv)
in_use = len(df_inv[df_inv['Status'] == 'In Use'])
repair = len(df_inv[df_inv['Status'] == 'Under Repair'])
pm = len(df_inv[df_inv['Status'] == 'Under PM'])

kpi1.metric("Total Jigs", total_jigs)
kpi2.metric("🟢 In Use", in_use)
kpi3.metric("🔴 Under Repair", repair)
kpi4.metric("🟠 Under PM", pm)

st.divider()

# --- MAIN INTERFACE ---
col_scan, col_action = st.columns([1, 2])

# 1. SCAN SECTION
with col_scan:
    st.subheader("1. Identify")
    # Using session state to clear input after submit if needed
    if 'scan_input' not in st.session_state:
        st.session_state.scan_input = ""
        
    jig_query = st.text_input("Scan/Enter Jig ID", key="scan_input", placeholder="e.g. M1-JIG-01")
    user_name = st.text_input("Technician Name", value="Technician")
    
    if jig_query:
        # Show current status immediately
        curr_row = df_inv[df_inv['Jig_ID'] == jig_query]
        if not curr_row.empty:
            s = curr_row.iloc[0]['Status']
            l = curr_row.iloc[0]['Location']
            st.info(f"🔎 Status: **{s}** | Location: **{l}**")
        else:
            st.warning("⚠️ ID not found. Check spelling.")

# 2. ACTION SECTION (TABS)
with col_action:
    st.subheader("2. Action")
    
    # We use Tabs so both actions are always available
    tab_remove, tab_add = st.tabs(["🔴 REMOVE / REPAIR", "🟢 ADD / INSTALL"])
    
    # --- TAB 1: REMOVE ---
    with tab_remove:
        st.write("Use this to take a jig OUT of the machine.")
        with st.form("remove_form"):
            r_reason = st.selectbox("Reason", ["Preventive Maintenance", "Repair", "Unknown"])
            r_comment = st.text_input("Damage Details (Required for Repair)")
            btn_remove = st.form_submit_button("Submit Removal")
            
            if btn_remove and jig_query:
                new_stat = "Under Repair" if r_reason == "Repair" else "Under PM"
                if r_reason == "Unknown": new_stat = "Unknown"
                
                if update_jig(jig_query, "REMOVE", user_name, r_reason, r_comment, new_stat, "Workshop"):
                    st.success(f"✅ {jig_query} removed for {r_reason}")
                    st.rerun()

    # --- TAB 2: ADD ---
    with tab_add:
        st.write("Use this to put a jig BACK into a machine.")
        with st.form("add_form"):
            a_machine = st.selectbox("Select Target Machine", MACHINES)
            a_comment = st.text_input("Comments (Optional)", value="Returned to service")
            btn_add = st.form_submit_button("Submit Installation")
            
            if btn_add and jig_query:
                if update_jig(jig_query, "ADD", user_name, "Production", a_comment, "In Use", a_machine):
                    st.success(f"✅ {jig_query} installed on {a_machine}")
                    st.rerun()

st.divider()

# --- CHARTS SECTION ---
st.subheader("📊 Analytics & Trends")

c1, c2 = st.columns(2)

with c1:
    st.markdown("**Real-Time Status**")
    # Prepare Data
    status_counts = df_inv['Status'].value_counts().reset_index()
    status_counts.columns = ['Status', 'Count']
    
    fig_bar = px.bar(status_counts, x='Status', y='Count', color='Status',
                     color_discrete_map={"In Use": "green", "Under Repair": "red", "Under PM": "orange", "Unknown": "gray"})
    st.plotly_chart(fig_bar, use_container_width=True)

with c2:
    st.markdown("**Repair Trend (Last 30 Days)**")
    # Prepare Data
    if not df_hist.empty:
        df_hist['Date'] = pd.to_datetime(df_hist['Date'])
        # Filter only "Remove" actions related to Repair/PM
        trend_data = df_hist[df_hist['Action'] == 'REMOVE'].groupby(df_hist['Date'].dt.date).size().reset_index(name='Count')
        fig_line = px.line(trend_data, x='Date', y='Count', markers=True, title="Items Removed per Day")
        st.plotly_chart(fig_line, use_container_width=True)
    else:
        st.info("No history data available yet for trends.")

st.markdown("### Recent Activity Log")
st.dataframe(df_hist.sort_values(by='Date', ascending=False).head(10), use_container_width=True)
