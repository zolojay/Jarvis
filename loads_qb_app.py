# technician_qb_app.py
import streamlit as st
import pandas as pd
import sqlalchemy
from datetime import datetime

# === PAGE CONFIG ===
st.set_page_config(page_title="Quarter Bench Load Updates", layout="wide")

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

# === Prep Data ===

# Format datetime for editing
for col in ["load_start", "load_end"]:
    df[col] = pd.to_datetime(df[col], errors='coerce').dt.strftime('%Y-%m-%d %H:%M')

# Remove unused column
df.drop(columns=["testing_area"], inplace=True)

# Desired column order
ordered_cols = [
    "status", "priority", "lab_request_number", "load_id", "request_type",
    "username", "pcn", "job", "description", "load_start", "load_end"
]
df = df[ordered_cols]

# === Editable Table ===

st.write("Edit start/end times below and click save:")

edited_df = st.data_editor(
    df.copy(),
    use_container_width=True,
    num_rows="dynamic",
    hide_index=True,
    column_config={
        "status": "Status",
        "priority": "Priority",
        "lab_request_number": "LRF",
        "load_id": "Load #",
        "request_type": "Type",
        "username": "Requestor",
        "pcn": "PCN",
        "job": "Job #",
        "description": "Description",
        "load_start": st.column_config.DatetimeColumn("Start Time", format="YYYY-MM-DD HH:mm"),
        "load_end": st.column_config.DatetimeColumn("End Time", format="YYYY-MM-DD HH:mm"),
    },
    disabled=[col for col in df.columns if col not in ["load_start", "load_end"]]
)

# === Save Button Centered ===

col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    if st.button("💾 Save All Changes", use_container_width=True):
        updated = 0
        with engine.connect() as conn:
            sql = sqlalchemy.text(
                f"UPDATE {TABLE_NAME} SET load_start = :start, load_end = :end WHERE load_id = :id"
            )
            for _, row in edited_df.iterrows():
                start = pd.to_datetime(row['load_start'], errors='coerce') if row['load_start'] else None
                end = pd.to_datetime(row['load_end'], errors='coerce') if row['load_end'] else None

                if pd.notnull(start) or pd.notnull(end):
                    conn.execute(sql, {
                        "start": start,
                        "end": end,
                        "id": row['load_id']
                    })
                    updated += 1
        st.success(f"✅ Updated {updated} load(s) successfully.")
