# technician_qb_app.py
# Streamlit app for Quarter Bench technicians to update load times (table-based interface)

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

# === Editable Table ===
editable_cols = ["load_start", "load_end"]

# Convert to string for display purposes
for col in editable_cols:
    df[col] = pd.to_datetime(df[col], errors='coerce').dt.strftime('%Y-%m-%d %H:%M')

st.write("Edit start/end times below and click save:")
edited_df = st.data_editor(
    df,
    use_container_width=True,
    num_rows="dynamic",
    hide_index=True,
    column_config={
        "load_start": st.column_config.DatetimeColumn("Start Time", format="YYYY-MM-DD HH:mm"),
        "load_end": st.column_config.DatetimeColumn("End Time", format="YYYY-MM-DD HH:mm")
    },
    disabled=[col for col in df.columns if col not in editable_cols]
)

if st.button("💾 Save All Changes"):
    updated = 0
    with engine.connect() as conn:
        for _, row in edited_df.iterrows():
            if row['load_start'] or row['load_end']:
                conn.execute(
                    sqlalchemy.text(f"""
                        UPDATE {TABLE_NAME}
                        SET load_start = :start, load_end = :end
                        WHERE load_id = :id
                    """),
                    {
                        "start": row['load_start'],
                        "end": row['load_end'],
                        "id": row['load_id']
                    }
                )
                updated += 1
    st.success(f"✅ Updated {updated} load(s) successfully.")
