# push_to_supabase.py
# Push summarized load info from local SQLite DB to Supabase

import pandas as pd
import sqlalchemy
import sqlite3
from sqlalchemy import inspect
from datetime import datetime

# === CONFIG ===
SQLITE_DB_PATH = r"C:\Jarvis\Database\lemur_full_clone.db"
SUPABASE_CONN = "postgresql://postgres:pqALDR^EPhi5hE@db.annkdlllotvqnmbaedor.supabase.co:5432/postgres"
TABLE_NAME = "load_queue"

# === SQL QUERY: Define what you want to push ===
query = '''
SELECT
    lb.load_id,
    lb.status,
    lb.testing_area,
    lb.priority,
    GROUP_CONCAT(rtc.description, '; ') AS description,
    rtc.pcn,
    rtc.job,
    rt.request_type,
    au.username,
    lr.number AS lab_request_number
FROM LoadBench lb
JOIN ReactorLoads rl ON lb.load_id = rl.id
JOIN LabRequests lr ON rl.lab_request_id = lr.id
LEFT JOIN auth_user au ON lr.created_by_id = au.id
LEFT JOIN RequestTypes rt ON lr.request_type_id = rt.id
LEFT JOIN ReactorTests rtest ON rtest.load_id = rl.id
LEFT JOIN ReactorTestConditions rtc ON rtest.test_condition_id = rtc.id
WHERE lb.status IN ('Backlog', 'In Reactor')
GROUP BY lb.load_id;
'''

# === STEP 1: Read from local SQLite ===
print("Connecting to local SQLite DB...")
conn = sqlite3.connect(SQLITE_DB_PATH)
df_local = pd.read_sql(query, conn)
conn.close()

# Add blank columns for load_start/load_end if missing
for col in ['load_start', 'load_end']:
    if col not in df_local.columns:
        df_local[col] = None

print(f"Fetched {len(df_local)} rows to sync with Supabase")

# === STEP 2: Read existing data and check for missing columns ===
print("Connecting to Supabase...")
supabase_engine = sqlalchemy.create_engine(SUPABASE_CONN)
inspector = inspect(supabase_engine)
columns = []
if inspector.has_table(TABLE_NAME):
    columns = [col['name'] for col in inspector.get_columns(TABLE_NAME)]
    print(f"Found existing table with columns: {columns}")
else:
    print("No existing table found — will create new one.")

# If table exists and has timestamp columns, preserve technician inputs
if 'load_start' in columns and 'load_end' in columns:
    df_existing = pd.read_sql(f"SELECT load_id, load_start, load_end FROM {TABLE_NAME}", supabase_engine)
    merged = pd.merge(df_local, df_existing, on='load_id', how='left', suffixes=('', '_supabase'))
    df_local['load_start'] = merged['load_start_supabase']
    df_local['load_end'] = merged['load_end_supabase']

print(f"Pushing data to table: {TABLE_NAME}")
df_local.to_sql(TABLE_NAME, supabase_engine, if_exists='replace', index=False, method='multi', chunksize=5000)

print("✅ Push to Supabase complete!")
