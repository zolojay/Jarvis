# technician_qb_app.py
# Streamlit app for Quarter Bench technicians to update load times

import streamlit as st
import pandas as pd
import sqlalchemy
from datetime import datetime

# === CONFIG ===
SUPABASE_CONN = st.secrets["supabase_connection"]
TABLE_NAME = "load_queue"
BENCH_TYPE = "Quarter Bench"

# === Load data ===
engine = sqlalchemy.create_engine(SUPABASE_CONN)
df = pd.read_sql(f"SELECT * FROM {TABLE_NAME} WHERE status = 'Backlog' AND testing_area = '{BENCH_TYPE}' ORDER BY priority ASC", engine)

st.title("Quarter Bench Load Updates")
st.write(f"Showing {len(df)} backlog loads for {BENCH_TYPE}, sorted by priority")

if df.empty:
    st.info("No loads to show.")
    st.stop()

# === Edit Table ===
df_editable = df.copy()
df_editable['load_start'] = pd.to_datetime(df_editable['load_start']).dt.strftime('%Y-%m-%d %H:%M')
df_editable['load_end'] = pd.to_datetime(df_editable['load_end']).dt.strftime('%Y-%m-%d %H:%M')

df_edit = st.data_editor(
    df_editable,
    num_rows="dynamic",
    use_container_width=True,
    hide_index=True,
    column_config={
        "load_start": st.column_config.DatetimeColumn("Start Time", format="YYYY-MM-DD HH:mm"),
        "load_end": st.column_config.DatetimeColumn("End Time", format="YYYY-MM-DD HH:mm")
    }
)

if st.button("💾 Save Updates"):
    with engine.connect() as conn:
        updates = 0
        for _, row in df_edit.iterrows():
            if row['load_start'] or row['load_end']:
                conn.execute(
                    sqlalchemy.text(f"""
                        UPDATE {TABLE_NAME}
                        SET load_start = :start, load_end = :end
                        WHERE load_id = :id
                    """),
                    {"start": row['load_start'], "end": row['load_end'], "id": row['load_id']}
                )
                updates += 1
    st.success(f"✅ Saved updates for {updates} load(s)")
