# pull_from_supabase.py
# Pull technician-updated load_start/load_end times from Supabase into local SQLite

import pandas as pd
import sqlalchemy
import sqlite3

# === CONFIG ===
SQLITE_DB_PATH = r"C:\Jarvis\Database\lemur_full_clone.db"
SUPABASE_CONN = "postgresql://postgres:pqALDR^EPhi5hE@db.annkdlllotvqnmbaedor.supabase.co:5432/postgres"
TABLE_NAME = "load_queue"

# === STEP 1: Pull from Supabase ===
print("Connecting to Supabase...")
supabase_engine = sqlalchemy.create_engine(SUPABASE_CONN)
df_remote = pd.read_sql(f"SELECT load_id, load_start, load_end FROM {TABLE_NAME}", supabase_engine)

print(f"Fetched {len(df_remote)} technician updates from Supabase")

# === STEP 2: Update local SQLite ===
print("Connecting to local SQLite DB...")
conn = sqlite3.connect(SQLITE_DB_PATH)
cursor = conn.cursor()

updated_rows = 0
for _, row in df_remote.iterrows():
    if row['load_start'] or row['load_end']:
        cursor.execute('''
            UPDATE LoadSchedules
            SET load_start = COALESCE(?, load_start),
                load_end = COALESCE(?, load_end)
            WHERE load_id = ?
        ''', (row['load_start'], row['load_end'], row['load_id']))
        updated_rows += cursor.rowcount

conn.commit()
conn.close()

print(f"✅ Updated {updated_rows} rows in local SQLite DB")
