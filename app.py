import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import os

# --- 1. CONFIGURATION & FILE PATHS ---
INVENTORY_FILE = 'inventory.xlsx'
HISTORY_FILE = 'history.xlsx'
TECH_FILE = 'Technicians.txt'
MASTER_FILE = 'PanelID.xlsx' # Your master list
MACHINES = ["ECP101", "ECP102", "ECP103"]

# --- 2. DATA ENGINE ---

def load_master_list():
    """Reads the authorized Panel IDs from the Master Excel file."""
    if os.path.exists(MASTER_FILE):
        df = pd.read_excel(MASTER_FILE)
        # Clean the column: remove spaces and make uppercase
        return df['Panel_ID'].astype(str).str.strip().str.upper().tolist()
    else:
        st.error(f"⚠️ {MASTER_FILE} missing! Please create it with a 'Panel_ID' column.")
        return []

def load_technicians():
    if not os.path.exists(TECH_FILE):
        with open(TECH_FILE, 'w') as f: f.write("Admin\nAnand")
    with open(TECH_FILE, 'r') as f:
        return [line.strip() for line in f.readlines() if line.strip()]

def load_db():
    """Loads the live tracking and history files."""
    if not os.path.exists(INVENTORY_FILE):
        df_inv = pd.DataFrame(columns=['Panel_ID', 'Status', 'Sub_Status', 'Location', 'Last_Updated'])
    else:
        df_inv = pd.read_excel(INVENTORY_FILE)
        df_inv['Panel_ID'] = df_inv['Panel_ID'].astype(str).str.strip().str.upper()
        if 'Sub_Status' not in df_inv.columns: df_inv['Sub_Status'] = "N/A"

    if not os.path.exists(HISTORY_FILE):
        df_hist = pd.DataFrame(columns=['Date', 'Panel_ID', 'Action', 'User', 'Category', 'Sub_Status', 'Comments'])
    else:
        df_hist = pd.read_excel(HISTORY_FILE)
    return df_inv, df_hist

def save_db(df_inv, df_hist):
    df_inv.to_excel(INVENTORY_FILE, index=False)
    df_hist.to_excel(HISTORY_FILE, index=False)

# --- 3. UI INITIALIZATION ---
st.set_page_config(layout="wide", page_title="Panel Holder Tracking System")
master_ids = load_master_list()
tech_names = load_technicians()
df_inv, df_hist = load_db()

st.title("Panel Holder Tracking System")

# --- 4. MANAGEMENT KPI BAR ---
kpi = st.columns(5)
total_in_master = len(master_ids)
in_use = len(df_inv[df_inv['Status'] == 'In Use'])
repair = len(df_inv[df_inv['Status'] == 'Under Repair'])
pm = len(df_inv[df_inv['Status'] == 'Under PM'])
damaged = len(df_inv[df_inv['Status'] == 'Damaged'])

kpi[0].metric("Total Fleet", total_in_master)
kpi[1].metric("🟢 In Use", in_use)
kpi[2].metric("🔴 Under Repair", repair)
kpi[3].metric("🟠 Under PM", pm)
kpi[4].metric("⚠️ Damaged", damaged)

st.divider()

# --- 5. OPERATIONS SECTION ---
col_id, col_action = st.columns([1, 1.2])

with col_id:
    st.subheader("1. Identify Agent & Asset")
    selected_tech = st.selectbox("Select Technician", options=tech_names)
    
    # Input cleaning (Case insensitive and no spaces)
    raw_pid = st.text_input("Scan or Type Panel ID").strip().upper()
    
    is_valid = False
    if raw_pid:
        if raw_pid in master_ids:
            is_valid = True
            st.success(f"✅ ID Verified: {raw_pid}")
            # Check current status from live inventory
            current_data = df_inv[df_inv['Panel_ID'] == raw_pid]
            if not current_data.empty:
                row = current_data.iloc[0]
                st.info(f"Current State: {row['Status']} at {row['Location']}")
            else:
                st.warning("First time scan. This ID is currently in 'Storage'.")
        else:
            st.error(f"❌ INVALID ID: '{raw_pid}' is not in the Master List (PanelID.xlsx).")

with col_action:
    st.subheader("2. Execute Action")
    if not is_valid:
        st.write("⬅️ *Enter a valid Panel ID to unlock actions.*")
    else:
        op_type = st.radio("Activity Type:", ["Install to Machine", "Remove from Machine"], horizontal=True)
        
        with st.form("action_form"):
            category = "Production"
            if op_type == "Install to Machine":
                final_loc = st.selectbox("Install into:", MACHINES)
                final_status = "In Use"
                final_sub = "N/A"
            else:
                # REMOVAL LOGIC
                final_loc = "Workshop"
                reason_main = st.selectbox("Reason for Removal:", ["Repair", "Preventive Maintenance", "Damaged", "Other"])
                category = st.selectbox("Failure Category:", ["CSS", "Tape", "Other"])
                
                # Dynamic Logic for 'Other' and 'Repair'
                other_comment = ""
                if category == "Other":
                    other_comment = st.text_input("Describe 'Other' Category:")
                
                if reason_main == "Repair":
                    final_sub = st.selectbox("Repair Status:", ["To check", "Waiting Parts", "Ready to Install"])
                    final_status = "Under Repair"
                elif reason_main == "Preventive Maintenance":
                    final_status = "Under PM"; final_sub = "N/A"
                elif reason_main == "Damaged":
                    final_status = "Damaged"; final_sub = "N/A"
                else:
                    final_status = "Other"; final_sub = "N/A"

            notes = st.text_area("Observations / Comments")
            
            if st.form_submit_button("COMMIT TRANSACTION"):
                # Clean comments
                full_comment = f"[{category}] {other_comment} | {notes}" if category == "Other" else f"[{category}] {notes}"
                
                # Update Snapshot (Digital Twin)
                if raw_pid in df_inv['Panel_ID'].values:
                    df_inv.loc[df_inv['Panel_ID'] == raw_pid, ['Status', 'Sub_Status', 'Location', 'Last_Updated']] = [final_status, final_sub, final_loc, datetime.now()]
                else:
                    # New Entry
                    new_row = {'Panel_ID': raw_pid, 'Status': final_status, 'Sub_Status': final_sub, 'Location': final_loc, 'Last_Updated': datetime.now()}
                    df_inv = pd.concat([df_inv, pd.DataFrame([new_row])], ignore_index=True)

                # Log to History for Trends
                new_log = {
                    'Date': datetime.now().strftime("%Y-%m-%d %H:%M"),
                    'Panel_ID': raw_pid,
                    'Action': op_type,
                    'User': selected_tech,
                    'Category': category,
                    'Sub_Status': final_sub,
                    'Comments': full_comment
                }
                df_hist = pd.concat([df_hist, pd.DataFrame([new_log])], ignore_index=True)
                
                save_db(df_inv, df_hist)
                st.toast(f"Updated {raw_pid} successfully!")
                st.rerun()

st.divider()

# --- 6. ANALYTICS & TRENDS ---
st.subheader("📊 Operational Analytics & Daily Trends")
tab1, tab2, tab3 = st.tabs(["Real-Time Health", "Daily Activity Trends", "Audit Logs"])

with tab1:
    c1, c2 = st.columns(2)
    with c1:
        st.write("**Total Fleet Health**")
        fig_pie = px.pie(df_inv, names='Status', color='Status', 
                         color_discrete_map={"In Use":"#2ecc71", "Under Repair":"#e74c3c", "Under PM":"#f1c40f", "Damaged":"#9b59b6"})
        st.plotly_chart(fig_pie, use_container_width=True)
    with c2:
        st.write("**Repair Queue Pipeline**")
        rep_df = df_inv[df_inv['Status'] == 'Under Repair']
        if not rep_df.empty:
            fig_sub = px.bar(rep_df['Sub_Status'].value_counts().reset_index(), x='Sub_Status', y='count', color='Sub_Status', title="Maintenance Status")
            st.plotly_chart(fig_sub, use_container_width=True)
        else: st.info("No items in Repair pipeline.")

with tab2:
    if not df_hist.empty:
        df_hist['Date_Only'] = pd.to_datetime(df_hist['Date']).dt.date
        # Trend Chart: Removal Category by Day
        trend = df_hist[df_hist['Action'] == "Remove from Machine"].groupby(['Date_Only', 'Category']).size().reset_index(name='Count')
        fig_trend = px.line(trend, x='Date_Only', y='Count', color='Category', markers=True, title="Failure Source Trends (CSS vs Tape)")
        st.plotly_chart(fig_trend, use_container_width=True)
    else: st.info("No history logs available yet.")

with tab3:
    st.dataframe(df_hist.sort_values(by='Date', ascending=False), use_container_width=True)
