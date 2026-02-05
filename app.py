import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import os

# --- FILE CONFIGURATION ---
INVENTORY_FILE = 'inventory.xlsx'
HISTORY_FILE = 'history.xlsx'
TECH_FILE = 'Technicians.txt'
MACHINES = ["Machine 1", "Machine 2", "Machine 3"]

# --- 1. DATA & LOGIC ENGINE ---

def load_technicians():
    """Reads technician names from the txt file."""
    if not os.path.exists(TECH_FILE):
        with open(TECH_FILE, 'w') as f:
            f.write("Admin\nTechnician 1")
    with open(TECH_FILE, 'r') as f:
        return [line.strip() for line in f.readlines() if line.strip()]

def load_data():
    """Initializes Excel database files."""
    if not os.path.exists(INVENTORY_FILE):
        df_inv = pd.DataFrame(columns=['Panel_ID', 'Status', 'Location', 'Last_Updated'])
        df_inv.to_excel(INVENTORY_FILE, index=False)
    else:
        df_inv = pd.read_excel(INVENTORY_FILE)
    
    if not os.path.exists(HISTORY_FILE):
        df_hist = pd.DataFrame(columns=['Date', 'Panel_ID', 'Action', 'User', 'Reason', 'Comments'])
        df_hist.to_excel(HISTORY_FILE, index=False)
    else:
        df_hist = pd.read_excel(HISTORY_FILE)
    return df_inv, df_hist

def save_data(df_inv, df_hist):
    df_inv.to_excel(INVENTORY_FILE, index=False)
    df_hist.to_excel(HISTORY_FILE, index=False)

# --- 2. USER INTERFACE ---

st.set_page_config(layout="wide", page_title="Panel Holder Control Center")
df_inv, df_hist = load_data()
tech_names = load_technicians()

st.title("🔬 Scientific Panel Holder Tracking System")

# --- TOP LAYER: CAPACITY MANAGEMENT (For Management Reporting) ---
kpi_cols = st.columns(len(MACHINES) + 1)
with kpi_cols[0]:
    st.metric("Fleet Size", len(df_inv))

for i, m in enumerate(MACHINES):
    count = len(df_inv[(df_inv['Location'] == m) & (df_inv['Status'] == 'In Use')])
    # Science: Capacity Warning if machine is below 24
    delta_val = count - 24
    kpi_cols[i+1].metric(f"{m} Load", f"{count}/24", delta=delta_val, delta_color="normal" if delta_val >= 0 else "inverse")

st.divider()

# --- MIDDLE LAYER: DAILY OPERATIONS ---
col_id, col_action = st.columns([1, 1])

with col_id:
    st.subheader("1. Identify Agent & Asset")
    
    # Technician Dropdown from txt file
    selected_tech = st.selectbox("Select Your Name", options=tech_names)
    
    # Panel ID Input
    pid_input = st.text_input("Scan / Type Panel ID (e.g. 54R15564)").strip()
    
    exists = pid_input in df_inv['Panel_ID'].values
    
    if pid_input:
        if exists:
            current_status = df_inv[df_inv['Panel_ID'] == pid_input].iloc[0]['Status']
            current_loc = df_inv[df_inv['Panel_ID'] == pid_input].iloc[0]['Location']
            st.success(f"Verified: {pid_input} is currently {current_status} at {current_loc}")
        else:
            # MANUAL REGISTRATION FEATURE
            st.error(f"Panel ID '{pid_input}' not found in database.")
            if st.button(f"➕ Add '{pid_input}' to System Manually"):
                new_asset = {
                    'Panel_ID': pid_input, 
                    'Status': 'Unknown', 
                    'Location': 'Registration Office', 
                    'Last_Updated': datetime.now()
                }
                df_inv = pd.concat([df_inv, pd.DataFrame([new_asset])], ignore_index=True)
                save_data(df_inv, df_hist)
                st.info(f"Asset {pid_input} Registered. Refreshing...")
                st.rerun()

with col_action:
    st.subheader("2. Execute Operation")
    if not pid_input or not exists:
        st.warning("Please identify a valid Panel ID to perform actions.")
    else:
        # Simplified operational logic
        operation = st.radio("Choose Operation:", ["Install to Machine", "Remove from Machine"], horizontal=True)
        
        with st.form("operation_form"):
            if operation == "Install to Machine":
                target_loc = st.selectbox("Install into:", MACHINES)
                new_status = "In Use"
                reason = "Production"
            else:
                target_loc = "Workshop"
                reason = st.selectbox("Reason for Removal:", ["Preventive Maintenance", "Repair", "Unknown"])
                new_status = f"Under {reason}" if "Unknown" not in reason else "Unknown"
            
            damage_notes = st.text_area("Observations / Damage Comments (Required for Repairs)")
            
            if st.form_submit_button("COMMIT TRANSACTION"):
                if "Repair" in reason and not damage_notes:
                    st.error("Please provide damage comments for Repair items.")
                else:
                    # Update snapshot
                    df_inv.loc[df_inv['Panel_ID'] == pid_input, ['Status', 'Location', 'Last_Updated']] = [new_status, target_loc, datetime.now()]
                    
                    # Log history
                    new_log = {
                        'Date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        'Panel_ID': pid_input,
                        'Action': operation,
                        'User': selected_tech,
                        'Reason': reason,
                        'Comments': damage_notes
                    }
                    df_hist = pd.concat([df_hist, pd.DataFrame([new_log])], ignore_index=True)
                    
                    save_data(df_inv, df_hist)
                    st.success("Database Updated Successfully!")
                    st.rerun()

st.divider()

# --- BOTTOM LAYER: ANALYTICS & REPORTING (Management View) ---
st.subheader("📊 Executive Intelligence Dashboard")
tab_charts, tab_logs = st.tabs(["Performance Charts", "Audit Logs"])

with tab_charts:
    c1, c2 = st.columns(2)
    with c1:
        # Status Distribution
        fig_pie = px.pie(df_inv, names='Status', title="Current Fleet Health",
                         color='Status', color_discrete_map={"In Use":"#2ecc71", "Under Repair":"#e74c3c", "Under PM":"#f1c40f", "Unknown":"#95a5a6"})
        st.plotly_chart(fig_pie, use_container_width=True)
    with c2:
        # Machine Load
        load_df = df_inv[df_inv['Status'] == 'In Use']['Location'].value_counts().reset_index()
        fig_bar = px.bar(load_df, x='Location', y='count', title="Current Machine Loadings", labels={'count':'Quantity'})
        st.plotly_chart(fig_bar, use_container_width=True)

    if not df_hist.empty:
        # Trend Analysis
        df_hist['Date'] = pd.to_datetime(df_hist['Date'])
        trend = df_hist.groupby([df_hist['Date'].dt.date, 'Reason']).size().reset_index(name='Events')
        fig_trend = px.line(trend, x='Date', y='Events', color='Reason', title="Maintenance/Repair Event Trends")
        st.plotly_chart(fig_trend, use_container_width=True)

with tab_logs:
    st.dataframe(df_hist.sort_values(by='Date', ascending=False), use_container_width=True)
    # Science: Export for Reporting
    csv = df_hist.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Export Audit Log to CSV", csv, "panel_holder_history.csv", "text/csv")
