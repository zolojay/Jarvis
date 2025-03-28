# technician_qb_app.py
# Streamlit app for Quarter Bench technicians to update load times with better UX

import streamlit as st
import pandas as pd
import sqlalchemy
from datetime import datetime

# === CONFIG ===
SUPABASE_CONN = st.secrets["supabase_connection"]
TABLE_NAME = "load_queue"
BENCH_TYPE = "Quarter Bench"

# === Load Data ===
engine = sqlalchemy.create_engine(SUPABASE_CONN)
df = pd.read_sql(
    f"""
    SELECT * FROM {TABLE_NAME}
    WHERE status = 'Backlog' AND testing_area = '{BENCH_TYPE}'
    ORDER BY priority ASC
    """,
    engine
)

st.title("Quarter Bench Load Updates")

if df.empty:
    st.info("No backlog loads found for Quarter Bench.")
    st.stop()

# === Format select options ===
df['display'] = df.apply(lambda row: f"{row['load_id']} - {row['job']} - PCN {row['pcn']} - Priority {row['priority']}", axis=1)
selected_row = st.selectbox("Select a load to update:", df['display'])
selected = df[df['display'] == selected_row].iloc[0]

# === Show Summary Card ===
st.markdown("""
### Load Info
---
**Load ID:** {load_id}  
**Description:** {description}  
**Priority:** {priority}  
**Request Type:** {req_type}  
**PCN:** {pcn}  
**Job:** {job}  
**Lab Request #:** {lab_req}  
**Created By:** {user}  
""".format(
    load_id=selected['load_id'],
    description=selected['description'],
    priority=selected['priority'],
    req_type=selected['request_type'],
    pcn=selected['pcn'],
    job=selected['job'],
    lab_req=selected['lab_request_number'],
    user=selected['username']
))

# === Editable Fields ===
def default_or_parsed(val):
    return pd.to_datetime(val) if pd.notnull(val) else datetime(2025, 1, 1, 8, 0)

with st.form("load_update_form"):
    start_time = st.datetime_input("Load Start Time", value=default_or_parsed(selected['load_start']))
    end_time = st.datetime_input("Load End Time", value=default_or_parsed(selected['load_end']))

    submitted = st.form_submit_button("💾 Save Load Times")

    if submitted:
        with engine.connect() as conn:
            conn.execute(
                sqlalchemy.text(f"""
                    UPDATE {TABLE_NAME}
                    SET load_start = :start, load_end = :end
                    WHERE load_id = :id
                """),
                {"start": start_time, "end": end_time, "id": selected['load_id']}
            )
        st.success(f"✅ Load times updated for Load ID {selected['load_id']}")
