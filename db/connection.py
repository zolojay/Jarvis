"""
Database connection and initialization module.
"""
import os
import sqlite3
import streamlit as st

# Database path - in production, this would be configurable
DB_PATH = r"C:\Jarvis\Database\lemur_full_clone.db"

def get_db_connection():
    """
    Create a connection to the SQLite database with row factory enabled.
    Creates a new connection each time to avoid threading issues with SQLite.
    
    Returns:
        sqlite3.Connection: Connection to the database
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_database():
    """
    Initialize database tables if they don't exist.
    Ensure required columns exist in LoadBench table.
    """
    conn = get_db_connection()
    
    # Create LoadBench table if it doesn't exist
    conn.execute('''
    CREATE TABLE IF NOT EXISTS LoadBench (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        load_id INTEGER NOT NULL,
        testing_area TEXT NOT NULL,
        assigned_date DATE DEFAULT CURRENT_DATE,
        FOREIGN KEY (load_id) REFERENCES ReactorLoads(id)
    )
    ''')
    
    # Check for and add status column if needed
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(LoadBench)")
    columns = cursor.fetchall()
    status_exists = any(column[1] == 'status' for column in columns)
    
    if not status_exists:
        try:
            cursor.execute("ALTER TABLE LoadBench ADD COLUMN status TEXT DEFAULT 'Backlog'")
            st.success("Status column added to LoadBench table.")
        except sqlite3.OperationalError:
            # Column might already exist
            pass
    
    # Check for and add priority column if needed
    priority_exists = any(column[1] == 'priority' for column in columns)
    
    if not priority_exists:
        try:
            cursor.execute("ALTER TABLE LoadBench ADD COLUMN priority INTEGER DEFAULT 100")
            st.success("Priority column added to LoadBench table.")
        except sqlite3.OperationalError:
            # Column might already exist
            pass
    
    conn.commit()
    conn.close()