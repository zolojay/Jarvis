import sqlite3
import os
from datetime import datetime

# Define paths (your provided paths)
DB_PATH = r"C:\Jarvis\Database\lemur_full_clone.db"
OUTPUT_FILE_PATH = r"C:\Jarvis\Database\lemur_db_schema.txt"

# Connect to the SQLite database
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Start writing schema details to file
with open(OUTPUT_FILE_PATH, 'w', encoding='utf-8') as f:
    f.write("Lemur SQLite Database Schema Report\n")
    f.write("="*80 + "\n")
    f.write(f"Database Path: {DB_PATH}\nGenerated on: {datetime.now()}\n")
    f.write("="*70 + "\n\n")

    # Fetch all table names
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()

    for (table_name,) in tables:
        f.write(f"Table: {table_name}\n")
        f.write("-" * 70 + "\n")

        # Fetch column details correctly
        cursor.execute(f"PRAGMA table_info('{table_name}')")
        columns = cursor.fetchall()

        f.write(f"{'Column':25} | {'Data Type':15} | {'NotNull':7} | {'Default':10} | {'PK':2}\n")
        f.write("-" * 70 + "\n")

        for column in columns:
            col_name = col_type = notnull = default_val = pk = None
            cid, col_name, col_type, notnull, default_val, pk = column
            notnull = "YES" if notnull else "NO"
            pk = "✅" if pk else ""
            default_val = default_val if default_val is not None else "—"

            f.write(f"{col_name:25} | {col_type:15} | {notnull:^7} | {default_val:10} | {pk:^3}\n")

        f.write("\n")

        # Index details
        cursor.execute(f"PRAGMA index_list('{table_name}')")
        indexes = cursor.fetchall()
        if indexes:
            f.write(f"Indexes:\n")
            for idx in indexes:
                idx_name, unique = idx[1], "Unique" if idx[2] else "Non-Unique"
                f.write(f"  - {idx_name} ({unique})\n")
            f.write("\n")

        # Foreign keys details (if present)
        cursor.execute(f"PRAGMA foreign_key_list('{table_name}')")
        foreign_keys = cursor.fetchall()
        if foreign_keys:
            f.write(f"Foreign Keys:\n")
            for fk in foreign_keys:
                f.write(f"From {fk[3]} → {fk[2]}({fk[4]})\n")
            f.write("\n")

        f.write("\n\n")

cursor.close()
conn.close()

print(f"\n🎉 Schema report created successfully at:\n{OUTPUT_FILE_PATH}")
