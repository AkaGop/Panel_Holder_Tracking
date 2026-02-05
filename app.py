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

# --- 1. DATA ENGINE FUNCTIONS ---

def load_technicians():
    if not os.path.exists(TECH_FILE):
        with open(TECH_FILE, 'w') as f: f.write("Admin\nTechnician 1")
    with open(TECH_FILE, 'r') as f:
        return [line.strip() for line in f.readlines() if line.strip()]

def load_data():
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

# --- 2. THE UI ---

st.set_page_config(layout="wide", page_title="Scientific Panel Tracker")
df_inv, df_hist = load_data()
tech_names = load_technicians()

st.title("🔬 Advanced Panel Holder Control Center")

# --- TOP LAYER: MANAGEMENT KPIs ---
kpi_cols = st.columns(len(MACHINES) + 1)
with kpi_cols[0]:
    st.metric("Total Inventory", len(df_inv))

for i, m in enumerate(MACHINES):
    count = len(df_inv[(df_inv['Location'] == m) & (df_inv['Status'] == 'In Use')])
    # Highlight in red if machine has less than 24 holders
    color = "normal" if count >= 24 else "inverse"
    kpi_cols[i+1].metric(f"{m} Load", f"{count}/24", delta=count-24, delta_color=color)

st.divider()

# --- MIDDLE LAYER: OPERATIONS ---
col_id, col_action = st.columns([1, 1])

with col_id:
    st.subheader("1. Identification")
    user = st.selectbox("Current Technician", tech_names)
    pid = st.text_input("Scan or Type Panel ID", placeholder="54R15564").strip()
    
    # Validation Logic
    exists = pid in df_inv['Panel_ID'].values
    
    if pid and not exists:
        st.warning(f"⚠️ ID {pid} not found in system.")
        if st.button(f"➕ Register {pid} as New Asset"):
            new_row = {'Panel_ID': pid, 'Status': 'In Use', 'Location': 'Storage', 'Last_Updated': datetime.now()}
            df_inv = pd.concat([df_inv, pd.DataFrame([new_row])], ignore_index=True)
            save_data(df_inv, df_hist)
            st.success("Registered! You can now perform actions.")
            st.rerun()
    elif pid and exists:
        row = df_inv[df_inv['Panel_ID'] == pid].iloc[0]
        st.success(f"ID Verified: {row['Status']} at {row['Location']}")

with col_action:
    st.subheader("2. Action Management")
    if not pid or not exists:
        st.info("Waiting for valid Panel ID Identification...")
    else:
        # Action Interface
        mode = st.radio("Select Operation", ["Move to Machine (Install)", "Remove for Maintenance/Repair"], horizontal=True)
        
        with st.form("action_form"):
            if mode == "Move to Machine (Install)":
                target = st.selectbox("Install to:", MACHINES + ["Storage"])
                reason = "Production"
                status = "In Use"
            else:
                target = "Workshop"
                reason = st.selectbox("Reason for Removal", ["Preventive Maintenance", "Repair", "Unknown"])
                status = f"Under {reason}" if "Unknown" not in reason else "Unknown"
            
            comment = st.text_area("Observations / Damage Comments")
            
            if st.form_submit_button("EXECUTE TRANSACTION"):
                # Update Inventory
                df_inv.loc[df_inv['Panel_ID'] == pid, ['Status', 'Location', 'Last_Updated']] = [status, target, datetime.now()]
                
                # Update History
                new_log = {
                    'Date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'Panel_ID': pid,
                    'Action': mode,
                    'User': user,
                    'Reason': reason,
                    'Comments': comment
                }
                df_hist = pd.concat([df_hist, pd.DataFrame([new_log])], ignore_index=True)
                
                save_data(df_inv, df_hist)
                st.balloons()
                st.rerun()

st.divider()

# --- BOTTOM LAYER: ANALYTICS ---
st.subheader("📊 Executive Analytics")
tab1, tab2, tab3 = st.tabs(["Real-Time Status", "Trend Analysis", "Full Logs"])

with tab1:
    c1, c2 = st.columns(2)
    with c1:
        fig_status = px.pie(df_inv, names='Status', title="Inventory Health Distribution",
                           color='Status', color_discrete_map={"In Use":"#2ecc71", "Under Repair":"#e74c3c", "Under PM":"#f1c40f"})
        st.plotly_chart(fig_status)
    with c2:
        # Show which machine is missing holders
        machine_stats = df_inv[df_inv['Status'] == 'In Use']['Location'].value_counts().reset_index()
        fig_machine = px.bar(machine_stats, x='Location', y='count', title="Current Machine Loading")
        st.plotly_chart(fig_machine)

with tab2:
    if not df_hist.empty:
        df_hist['Date'] = pd.to_datetime(df_hist['Date'])
        # Breakdown by reason over time
        trend = df_hist.groupby([df_hist['Date'].dt.date, 'Reason']).size().reset_index(name='Count')
        fig_trend = px.line(trend, x='Date', y='Count', color='Reason', title="Maintenance Events Trend")
        st.plotly_chart(fig_trend, use_container_width=True)

with tab3:
    st.dataframe(df_hist.sort_values(by='Date', ascending=False), use_container_width=True)
    # Download buttons
    csv_inv = df_inv.to_csv(index=False).encode('utf-8')
    st.download_button("Export Inventory to CSV", csv_inv, "inventory.csv", "text/csv")
