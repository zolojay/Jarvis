import os
import pyodbc
import pandas as pd
import sqlalchemy
import sqlite3
import shutil

# Directories
SCRIPT_DIR = r"C:\Jarvis\Script"
DB_DIR = r"C:\Jarvis\Database"
os.makedirs(DB_DIR, exist_ok=True)

# SQLite Database path
LOCAL_DB_PATH = os.path.join(DB_DIR, "lemur_full_clone.db")

# Lemur Database connection (your verified connection string)
LEMUR_CONN_STR = (
    "mssql+pyodbc://CTTR-SQL-05/LEMUR?driver=ODBC+Driver+17+for+SQL+Server"
    "&trusted_connection=yes"
    "&TrustServerCertificate=yes"
)

# Connect to Lemur SQL DB
lemur_engine = sqlalchemy.create_engine(LEMUR_CONN_STR)
sqlite_engine = sqlalchemy.create_engine(f"sqlite:///{LOCAL_DB_PATH}")

# Fetch table names
tables_query = """
SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES
WHERE TABLE_TYPE = 'BASE TABLE'
"""
table_names = pd.read_sql(tables_query, lemur_engine)['TABLE_NAME'].tolist()

# Rapidly clone using bulk writes
with sqlite3.connect(LOCAL_DB_PATH) as sqlite_conn:
    for table in table_names:
        print(f"Cloning table {table}...")
        df = pd.read_sql(f"SELECT * FROM {table}", lemur_engine)

        # Fast bulk insert
        df.to_sql(table, sqlite_conn, if_exists='replace', index=False, method='multi', chunksize=5000)

print("\n🎉 Cloning completed successfully!")
