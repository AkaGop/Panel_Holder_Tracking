import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import os

# --- FILE CONFIGURATION ---
# These files will be created automatically in the same folder
INVENTORY_FILE = 'inventory.xlsx'
HISTORY_FILE = 'history.xlsx'

# --- 1. BACKEND FUNCTIONS (Data Handling) ---

def load_data():
    """Create Excel files if they don't exist, otherwise load them."""
    # A. Inventory File (The Real-Time Snapshot)
    if not os.path.exists(INVENTORY_FILE):
        data = []
        # Create 3 Machines x 24 Jigs
        for m in range(1, 4):
            for j in range(1, 25):
                data.append({
                    'Jig_ID': f'M{m}-JIG-{j:02d}', # e.g., M1-JIG-01
                    'Status': 'In Use',
                    'Location': f'Machine {m}',
                    'Last_Reason': 'Initial Setup'
                })
        # Create Trolleys
        for t in range(1, 6):
            data.append({'Jig_ID': f'TRLY-{t:02d}', 'Status': 'In Use', 'Location': 'Floor', 'Last_Reason': 'Initial Setup'})
        
        df_inv = pd.DataFrame(data)
        df_inv.to_excel(INVENTORY_FILE, index=False)
    else:
        df_inv = pd.read_excel(INVENTORY_FILE)

    # B. History File (The Log)
    if not os.path.exists(HISTORY_FILE):
        df_hist = pd.DataFrame(columns=['Date', 'Jig_ID', 'Action', 'User', 'Reason', 'Comments'])
        df_hist.to_excel(HISTORY_FILE, index=False)
    else:
        df_hist = pd.read_excel(HISTORY_FILE)
        
    return df_inv, df_hist

def update_jig(jig_id, action, user, reason, comments, new_status, new_location):
    """Updates both Excel files and saves them."""
    df_inv, df_hist = load_data()
    
    # 1. Update Inventory Snapshot
    idx = df_inv.index[df_inv['Jig_ID'] == jig_id].tolist()
    if not idx:
        st.error("Jig ID not found!")
        return
    
    df_inv.at[idx[0], 'Status'] = new_status
    df_inv.at[idx[0], 'Location'] = new_location
    df_inv.at[idx[0], 'Last_Reason'] = reason
    df_inv.to_excel(INVENTORY_FILE, index=False)
    
    # 2. Add to History Log
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

# --- 2. FRONTEND (The User Interface) ---

st.set_page_config(layout="wide", page_title="Jig Automation")

# Header
st.title("🏭 Real-Time Jig Tracker")

# Initialize Session State for the "Search"
if 'scanned_jig' not in st.session_state:
    st.session_state.scanned_jig = ""

# --- SECTION A: THE SEARCH BAR ---
col_input, col_info = st.columns([1, 2])

with col_input:
    st.markdown("### 1. Identify Jig")
    # This text input acts as your search bar (and barcode destination)
    jig_query = st.text_input("Enter/Scan Jig ID", value=st.session_state.scanned_jig, placeholder="e.g. M1-JIG-01")
    user_name = st.text_input("Technician Name", "Tech-1") # Defaulting for speed

# Load data immediately to check status
df_inv, df_hist = load_data()
target_jig = df_inv[df_inv['Jig_ID'] == jig_query]

# --- SECTION B: CONTEXT-AWARE ACTION BUTTONS ---
with col_info:
    st.markdown("### 2. Action")
    
    if not target_jig.empty:
        # Get current status
        curr_status = target_jig.iloc[0]['Status']
        curr_loc = target_jig.iloc[0]['Location']
        
        st.info(f"**{jig_query}** is currently: **{curr_status}** ({curr_loc})")
        
        # LOGIC: If it's IN USE, we want to REMOVE it
        if curr_status == "In Use":
            with st.form("remove_form"):
                reason = st.selectbox("Why are you removing it?", ["Preventive Maintenance", "Repair", "Unknown"])
                comments = st.text_input("Damage Comments (Optional)")
                submit_remove = st.form_submit_button("🔴 REMOVE JIG")
                
                if submit_remove:
                    new_stat = "Under Repair" if reason == "Repair" else "Under PM"
                    if reason == "Unknown": new_stat = "Unknown"
                    
                    update_jig(jig_query, "REMOVE", user_name, reason, comments, new_stat, "Workshop")
                    st.success(f"{jig_query} Removed for {reason}")
                    st.session_state.scanned_jig = "" # Clear input
                    st.rerun() # REFRESH CHART INSTANTLY

        # LOGIC: If it's NOT IN USE, we want to ADD it back
        else:
            with st.form("add_form"):
                target_machine = st.selectbox("Select Machine", ["Machine 1", "Machine 2", "Machine 3"])
                submit_add = st.form_submit_button("🟢 ADD / INSTALL JIG")
                
                if submit_add:
                    update_jig(jig_query, "ADD", user_name, "Production", "Returned to Line", "In Use", target_machine)
                    st.success(f"{jig_query} Returned to {target_machine}")
                    st.session_state.scanned_jig = "" # Clear input
                    st.rerun() # REFRESH CHART INSTANTLY
                    
    elif jig_query:
        st.warning("❌ Jig ID not found in database. Check spelling.")

st.divider()

# --- SECTION C: REAL-TIME CHARTS (Updates Automatically) ---
st.markdown("### 📊 Real-Time Status")

# Calculate Counts
status_counts = df_inv['Status'].value_counts().reset_index()
status_counts.columns = ['Status', 'Count']

# Create 2 Columns for visuals
chart_col, data_col = st.columns([2, 1])

with chart_col:
    # Plotly Bar Chart
    fig = px.bar(status_counts, x='Status', y='Count', 
                 color='Status', 
                 title="Live Jig Status",
                 color_discrete_map={
                     "In Use": "green", 
                     "Under Repair": "red", 
                     "Under PM": "orange", 
                     "Unknown": "gray"
                 })
    st.plotly_chart(fig, use_container_width=True)

with data_col:
    st.markdown("#### Recent Activity Log")
    # Show last 5 transactions
    if not df_hist.empty:
        st.dataframe(df_hist.sort_values(by='Date', ascending=False).head(5)[['Date', 'Jig_ID', 'Action', 'Reason']], hide_index=True)
    else:
        st.write("No activity yet.")
