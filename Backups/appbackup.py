import os
import sqlite3
import pandas as pd
import streamlit as st
import subprocess
from datetime import datetime, timedelta, date
from functools import wraps
import calendar
import plotly.express as px
import plotly.graph_objects as go

# Database path
DB_PATH = r"C:\Jarvis\Database\lemur_full_clone.db"

# Page configuration
st.set_page_config(
    page_title="Lab Load Scheduler",
    page_icon="🧪",
    layout="wide"
)

# Cached database connection
@st.cache_resource
def get_db_connection_pool():
    """
    Create and cache a SQLite database connection for reuse
    
    Returns:
    sqlite3.Connection: Cached database connection
    """
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

# Connection manager with error handling
def with_db_connection(func):
    """
    Decorator to handle database connections with error recovery
    
    Parameters:
    func: Function that requires a database connection
    
    Returns:
    Function wrapped with connection handling
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            # Get the cached connection
            conn = get_db_connection_pool()
            # Call the function with the connection
            return func(conn, *args, **kwargs)
        except sqlite3.OperationalError as e:
            # If the connection is invalid (e.g., "database is locked")
            if "database is locked" in str(e):
                # Clear the connection from cache and retry
                st.cache_resource.clear()
                conn = get_db_connection_pool()
                return func(conn, *args, **kwargs)
            else:
                # For other operational errors, reraise
                raise
    return wrapper

# Apply custom CSS for typography improvements
def apply_custom_css():
    st.markdown("""
    <style>
        /* Typography enhancements */
        h1 {
            font-size: 2.4em !important;
            font-weight: 700 !important;
            margin-bottom: 0.8em !important;
        }
        
        h2 {
            font-size: 1.8em !important;
            font-weight: 600 !important;
            margin-top: 1em !important;
            margin-bottom: 0.6em !important;
        }
        
        h3 {
            font-size: 1.38em !important;
            font-weight: 600 !important;
            margin-top: 1em !important;
            margin-bottom: 0.5em !important;
        }
        
        /* Table enhancements */
        .stDataFrame {
            font-size: 1.05em !important;
        }
        
        /* Increase cell padding */
        .stDataFrame [data-testid="stDataFrameResizable"] div[data-testid="stHorizontalBlock"] {
            padding-top: 8px !important;
            padding-bottom: 8px !important;
        }
        
        /* Enhance table headers */
        .stDataFrame thead tr th {
            font-size: 1.1em !important;
            font-weight: 600 !important;
            padding: 10px !important;
        }
        
        /* Button styling */
        .stButton button {
            font-weight: 500 !important;
            padding: 0.5em 1em !important;
        }
        
        /* Consistent spacing */
        .block-container {
            padding-top: 2rem !important;
        }
        
        /* Save button highlighting */
        .save-button {
            background-color: #4CAF50 !important;
            color: white !important;
            font-weight: bold !important;
            border-radius: 4px !important;
            padding: 0.6em 1.2em !important;
            font-size: 1.1em !important;
        }
        
        /* Status colors */
        .status-backlog {
            background-color: #FFF9C4 !important;
            color: #5D4037 !important;
            padding: 4px 8px !important;
            border-radius: 4px !important;
        }
        .status-in-reactor {
            background-color: #E3F2FD !important;
            color: #0D47A1 !important;
            padding: 4px 8px !important;
            border-radius: 4px !important;
        }
        .status-test-complete {
            background-color: #E8F5E9 !important;
            color: #2E7D32 !important;
            padding: 4px 8px !important;
            border-radius: 4px !important;
        }
        .status-qc-complete {
            background-color: #F3E5F5 !important;
            color: #6A1B9A !important;
            padding: 4px 8px !important;
            border-radius: 4px !important;
        }
        .status-report-delivered {
            background-color: #EFEBE9 !important;
            color: #4E342E !important;
            padding: 4px 8px !important;
            border-radius: 4px !important;
        }
        
        /* Date filter style */
        .date-filter-container {
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 15px;
        }
        
        /* Dashboard styles */
        .metric-card {
            background-color: #f8f9fa;
            border-radius: 8px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            padding: 15px;
            margin-bottom: 15px;
        }
        
        .metric-title {
            font-size: 1.1em;
            font-weight: 500;
            margin-bottom: 10px;
        }
        
        .metric-value {
            font-size: 1.8em;
            font-weight: 700;
            color: #0366d6;
        }
        
        .metric-caption {
            font-size: 0.9em;
            color: #666;
            margin-top: 5px;
        }
    </style>
    """, unsafe_allow_html=True)

# Initialize LoadBench table if it doesn't exist
@with_db_connection
def init_loadbench_table(conn):
    """
    Initialize LoadBench table with required columns
    
    Parameters:
    conn (sqlite3.Connection): Database connection
    """
    cursor = conn.cursor()
    
    # Create LoadBench table if it doesn't exist
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS LoadBench (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        load_id INTEGER NOT NULL,
        testing_area TEXT NOT NULL,
        assigned_date DATE DEFAULT CURRENT_DATE,
        FOREIGN KEY (load_id) REFERENCES ReactorLoads(id)
    )
    ''')
    
    # Check if status column exists in LoadBench table
    cursor.execute("PRAGMA table_info(LoadBench)")
    columns = cursor.fetchall()
    
    # Add status and priority columns if they don't exist
    column_names = [column[1] for column in columns]
    
    if 'status' not in column_names:
        try:
            cursor.execute("ALTER TABLE LoadBench ADD COLUMN status TEXT DEFAULT 'Backlog'")
            st.success("Status column added to LoadBench table.")
        except sqlite3.OperationalError:
            # Column might already exist
            pass
    
    if 'priority' not in column_names:
        try:
            cursor.execute("ALTER TABLE LoadBench ADD COLUMN priority INTEGER DEFAULT 100")
            st.success("Priority column added to LoadBench table.")
        except sqlite3.OperationalError:
            # Column might already exist
            pass
    
    # Create indexes if they don't exist
    try:
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_loadbench_load_id ON LoadBench(load_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_loadbench_testing_area ON LoadBench(testing_area)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_loadbench_status ON LoadBench(status)")
    except sqlite3.OperationalError:
        # Indexes might already exist
        pass
    
    conn.commit()

# Centralized function to calculate next backlog priority
@with_db_connection
def get_next_backlog_priority(conn, testing_area):
    """
    Get the next available priority number for backlog items
    
    Parameters:
    conn (sqlite3.Connection): Database connection
    testing_area (str): Testing area to calculate priority for
    
    Returns:
    int: Next available priority number
    """
    cursor = conn.cursor()
    cursor.execute(
        "SELECT MAX(priority) FROM LoadBench WHERE testing_area = ? AND UPPER(status) = 'BACKLOG'",
        (testing_area,)
    )
    max_priority = cursor.fetchone()[0]
    return (max_priority + 1) if max_priority is not None else 100

# Get all reactor loads with optimized query
@st.cache_data(ttl=300)  # Cache for 5 minutes
@with_db_connection
def get_reactor_loads(conn, start_date=None):
    """
    Get all reactor loads with optional date filtering
    
    Parameters:
    conn (sqlite3.Connection): Database connection
    start_date (datetime, optional): Start date for filtering
    
    Returns:
    DataFrame: DataFrame containing reactor load information
    """
    # Base query
    query = """
    SELECT
        RL.id AS ReactorLoadID,
        LR.number AS LabRequestNumber,
        LR.job_number,
        LR.pcn,
        LR.time_submitted,
        AU.username AS created_by,
        RT.request_type,
        COUNT(DISTINCT S.id) AS sample_count,
        (SELECT GROUP_CONCAT(number, ', ') FROM (SELECT DISTINCT S_inner.number FROM ReactorLoadSamples RLS_inner LEFT JOIN LabRequestSample LRS_inner ON RLS_inner.lab_request_sample_id = LRS_inner.id LEFT JOIN Samples S_inner ON LRS_inner.sample_id = S_inner.id WHERE RLS_inner.load_id = RL.id)) AS sample_numbers,
        (SELECT GROUP_CONCAT(sample_type, ', ') FROM (SELECT DISTINCT ST_inner.sample_type FROM ReactorLoadSamples RLS_inner LEFT JOIN LabRequestSample LRS_inner ON RLS_inner.lab_request_sample_id = LRS_inner.id LEFT JOIN Samples S_inner ON LRS_inner.sample_id = S_inner.id LEFT JOIN SampleTypes ST_inner ON S_inner.sample_type_id = ST_inner.id WHERE RLS_inner.load_id = RL.id)) AS sample_types,
        (SELECT COUNT(DISTINCT TCT_inner.id) FROM ReactorTests RTST_inner LEFT JOIN ReactorTestConditions RTC_inner ON RTST_inner.test_condition_id = RTC_inner.id LEFT JOIN TestConditionTypes TCT_inner ON RTC_inner.test_type_id = TCT_inner.id WHERE RTST_inner.load_id = RL.id AND (TCT_inner.test_condition_type IS NULL OR TRIM(UPPER(TCT_inner.test_condition_type)) <> 'PRESSURE DROP')) AS test_count,
        (SELECT GROUP_CONCAT(test_condition_type, ', ') FROM (SELECT DISTINCT TCT_inner.test_condition_type FROM ReactorTests RTST_inner LEFT JOIN ReactorTestConditions RTC_inner ON RTST_inner.test_condition_id = RTC_inner.id LEFT JOIN TestConditionTypes TCT_inner ON RTC_inner.test_type_id = TCT_inner.id WHERE RTST_inner.load_id = RL.id AND (TCT_inner.test_condition_type IS NULL OR TRIM(UPPER(TCT_inner.test_condition_type)) <> 'PRESSURE DROP'))) AS test_conditions,
        (SELECT GROUP_CONCAT(description, '; ') FROM (SELECT DISTINCT RTC_inner.description FROM ReactorTests RTST_inner LEFT JOIN ReactorTestConditions RTC_inner ON RTST_inner.test_condition_id = RTC_inner.id LEFT JOIN TestConditionTypes TCT_inner ON RTC_inner.test_type_id = TCT_inner.id WHERE RTST_inner.load_id = RL.id AND (TCT_inner.test_condition_type IS NULL OR TRIM(UPPER(TCT_inner.test_condition_type)) <> 'PRESSURE DROP'))) AS test_condition_description,
        MAX(CASE WHEN RP.reactor_parameter = 'SO2' THEN RTCP.value END) AS SO2,
        MAX(CASE WHEN RP.reactor_parameter = 'CO' THEN RTCP.value END) AS CO,
        MAX(CASE WHEN RP.reactor_parameter = 'NO' THEN RTCP.value END) AS NO,
        MAX(CASE WHEN RP.reactor_parameter = 'NO2' THEN RTCP.value END) AS NO2
    FROM ReactorLoads RL
    INNER JOIN LabRequests LR ON RL.lab_request_id = LR.id
    LEFT JOIN auth_user AU ON LR.created_by_id = AU.id
    LEFT JOIN RequestTypes RT ON LR.request_type_id = RT.id
    LEFT JOIN ReactorLoadSamples RLS ON RL.id = RLS.load_id
    LEFT JOIN LabRequestSample LRS ON RLS.lab_request_sample_id = LRS.id
    LEFT JOIN Samples S ON LRS.sample_id = S.id
    LEFT JOIN SampleTypes ST ON S.sample_type_id = ST.id
    LEFT JOIN ReactorTests RTST ON RTST.load_id = RL.id
    LEFT JOIN ReactorTestConditions RTC ON RTST.test_condition_id = RTC.id
    LEFT JOIN TestConditionTypes TCT ON RTC.test_type_id = TCT.id
    LEFT JOIN ReactorTestConditionParameters RTCP ON RTC.id = RTCP.condition_id
    LEFT JOIN ReactorParameters RP ON RTCP.reactor_parameter_id = RP.id
    WHERE (TCT.test_condition_type IS NULL OR TRIM(UPPER(TCT.test_condition_type)) <> 'PRESSURE DROP')
    """
    
    # Add date filter directly to SQL if specified
    params = []
    if start_date is not None:
        query += " AND LR.time_submitted >= ?"
        params.append(start_date.strftime('%Y-%m-%d'))
    
    # Add grouping and ordering
    query += """
    GROUP BY RL.id
    ORDER BY LR.time_submitted DESC
    """
    
    # Execute query with parameters if any
    if params:
        df = pd.read_sql_query(query, conn, params=params)
    else:
        df = pd.read_sql_query(query, conn)
    
    # Process time_submitted once
    if 'time_submitted' in df.columns and not df.empty:
        df['time_submitted'] = pd.to_datetime(df['time_submitted'], format='mixed', errors='coerce')
        # Format for display
        df['time_submitted'] = df['time_submitted'].dt.strftime('%Y-%m-%d %H:%M')
    
    return df

# Get load info from database
@with_db_connection
def get_load_info(conn, load_id):
    """
    Get assigned testing area, status, and priority for a load
    
    Parameters:
    conn (sqlite3.Connection): Database connection
    load_id (int): Load ID to get info for
    
    Returns:
    dict: Dictionary containing testing_area, status, and priority
    """
    cursor = conn.cursor()
    cursor.execute("SELECT testing_area, status, priority FROM LoadBench WHERE load_id = ?", (load_id,))
    result = cursor.fetchone()
    
    if result:
        return {
            "testing_area": result[0], 
            "status": result[1] if len(result) > 1 and result[1] else "Backlog",
            "priority": result[2] if len(result) > 2 and result[2] is not None else 100
        }
    else:
        return {"testing_area": None, "status": None, "priority": 100}

# Get bench loads with optimized query including schedule information
@st.cache_data(ttl=300)  # Cache for 5 minutes
@with_db_connection
def get_bench_loads(conn, bench_type, status_filter=None):
    """
    Get loads by bench type with expanded schedule information
    
    Parameters:
    conn (sqlite3.Connection): Database connection
    bench_type (str): Bench type ("Quarter Bench" or "Full Bench")
    status_filter (list, optional): List of statuses to filter by
    
    Returns:
    DataFrame: DataFrame containing loads for the specified bench type
    """
    # Base query with joined tables for scheduling info
    query = """
    SELECT
        RL.id AS ReactorLoadID,
        LB.status,
        LR.number AS LabRequestNumber,
        LR.job_number,
        LR.pcn,
        LR.time_submitted,
        AU.username AS created_by,
        RT.request_type,
        COUNT(DISTINCT S.id) AS sample_count,
        (SELECT GROUP_CONCAT(sample_type, ', ') FROM (SELECT DISTINCT ST_inner.sample_type FROM ReactorLoadSamples RLS_inner 
         LEFT JOIN LabRequestSample LRS_inner ON RLS_inner.lab_request_sample_id = LRS_inner.id 
         LEFT JOIN Samples S_inner ON LRS_inner.sample_id = S_inner.id 
         LEFT JOIN SampleTypes ST_inner ON S_inner.sample_type_id = ST_inner.id 
         WHERE RLS_inner.load_id = RL.id)) AS sample_types,
        (SELECT COUNT(DISTINCT TCT_inner.id) FROM ReactorTests RTST_inner 
         LEFT JOIN ReactorTestConditions RTC_inner ON RTST_inner.test_condition_id = RTC_inner.id 
         LEFT JOIN TestConditionTypes TCT_inner ON RTC_inner.test_type_id = TCT_inner.id 
         WHERE RTST_inner.load_id = RL.id AND (TCT_inner.test_condition_type IS NULL OR TRIM(UPPER(TCT_inner.test_condition_type)) <> 'PRESSURE DROP')) AS test_count,
        (SELECT GROUP_CONCAT(description, '; ') FROM (SELECT DISTINCT RTC_inner.description FROM ReactorTests RTST_inner 
         LEFT JOIN ReactorTestConditions RTC_inner ON RTST_inner.test_condition_id = RTC_inner.id 
         WHERE RTST_inner.load_id = RL.id)) AS test_condition_description,
        MAX(CASE WHEN RP.reactor_parameter = 'SO2' THEN RTCP.value END) AS SO2,
        MAX(CASE WHEN RP.reactor_parameter = 'CO' THEN RTCP.value END) AS CO,
        MAX(CASE WHEN RP.reactor_parameter = 'NO' THEN RTCP.value END) AS NO,
        MAX(CASE WHEN RP.reactor_parameter = 'NO2' THEN RTCP.value END) AS NO2,
        LB.priority,
        MIN(RTST.start_time) AS start_time,
        MAX(RTST.stop_time) AS end_time
    """
    
    # Add reactor column for Full Bench
    if bench_type == "Full Bench":
        query += ", RTST.reactor_id AS reactor "
    
    # Continue with FROM clause
    query += """
    FROM ReactorLoads RL
    INNER JOIN LabRequests LR ON RL.lab_request_id = LR.id
    INNER JOIN LoadBench LB ON RL.id = LB.load_id
    LEFT JOIN ReactorTests RTST ON RL.id = RTST.load_id
    LEFT JOIN auth_user AU ON LR.created_by_id = AU.id
    LEFT JOIN RequestTypes RT ON LR.request_type_id = RT.id
    LEFT JOIN ReactorLoadSamples RLS ON RL.id = RLS.load_id
    LEFT JOIN LabRequestSample LRS ON RLS.lab_request_sample_id = LRS.id
    LEFT JOIN Samples S ON LRS.sample_id = S.id
    LEFT JOIN ReactorTestConditions RTC ON RTST.test_condition_id = RTC.id
    LEFT JOIN ReactorTestConditionParameters RTCP ON RTC.id = RTCP.condition_id
    LEFT JOIN ReactorParameters RP ON RTCP.reactor_parameter_id = RP.id
    WHERE LB.testing_area = ?
    """
    
    # Add status filter to SQL if provided
    params = [bench_type]
    if status_filter and len(status_filter) > 0:  # Only apply filter if list is non-empty
        placeholders = ', '.join('?' for _ in status_filter)
        query += f" AND LB.status IN ({placeholders})"
        params.extend(status_filter)
    
    # Add grouping and ordering
    query += """
    GROUP BY RL.id
    ORDER BY start_time ASC
    """
    
    df = pd.read_sql_query(query, conn, params=params)
    
    # Process timestamps once
    for time_col in ['time_submitted', 'start_time', 'end_time']:
        if time_col in df.columns and not df.empty:
            df[time_col] = pd.to_datetime(df[time_col], format='mixed', errors='coerce')
            df[time_col] = df[time_col].dt.strftime('%Y-%m-%d %H:%M')
    
    # Fill NaN values in status column
    if 'status' in df.columns:
        df['status'].fillna('Backlog', inplace=True)
    
    # Fill NaN values in priority column
    if 'priority' in df.columns:
        df['priority'].fillna(100, inplace=True)
    
    return df

# Get loads by testing area with optimized query (original method, kept for compatibility)
@st.cache_data(ttl=300)  # Cache for 5 minutes
@with_db_connection
def get_loads_by_testing_area(conn, testing_area, status_filter=None):
    """
    Get loads by testing area with priority order using a single query
    
    Parameters:
    conn (sqlite3.Connection): Database connection
    testing_area (str): Testing area to get loads for
    status_filter (list, optional): List of statuses to filter by
    
    Returns:
    DataFrame: DataFrame containing loads for the specified testing area
    """
    # Query to join LoadBench with ReactorLoads and other necessary tables
    query = """
    SELECT
        RL.id AS ReactorLoadID,
        LR.number AS LabRequestNumber,
        LR.job_number,
        LR.pcn,
        LR.time_submitted,
        AU.username AS created_by,
        RT.request_type,
        COUNT(DISTINCT S.id) AS sample_count,
        (SELECT GROUP_CONCAT(number, ', ') FROM (SELECT DISTINCT S_inner.number FROM ReactorLoadSamples RLS_inner LEFT JOIN LabRequestSample LRS_inner ON RLS_inner.lab_request_sample_id = LRS_inner.id LEFT JOIN Samples S_inner ON LRS_inner.sample_id = S_inner.id WHERE RLS_inner.load_id = RL.id)) AS sample_numbers,
        (SELECT GROUP_CONCAT(sample_type, ', ') FROM (SELECT DISTINCT ST_inner.sample_type FROM ReactorLoadSamples RLS_inner LEFT JOIN LabRequestSample LRS_inner ON RLS_inner.lab_request_sample_id = LRS_inner.id LEFT JOIN Samples S_inner ON LRS_inner.sample_id = S_inner.id LEFT JOIN SampleTypes ST_inner ON S_inner.sample_type_id = ST_inner.id WHERE RLS_inner.load_id = RL.id)) AS sample_types,
        (SELECT COUNT(DISTINCT TCT_inner.id) FROM ReactorTests RTST_inner LEFT JOIN ReactorTestConditions RTC_inner ON RTST_inner.test_condition_id = RTC_inner.id LEFT JOIN TestConditionTypes TCT_inner ON RTC_inner.test_type_id = TCT_inner.id WHERE RTST_inner.load_id = RL.id AND (TCT_inner.test_condition_type IS NULL OR TRIM(UPPER(TCT_inner.test_condition_type)) <> 'PRESSURE DROP')) AS test_count,
        (SELECT GROUP_CONCAT(test_condition_type, ', ') FROM (SELECT DISTINCT TCT_inner.test_condition_type FROM ReactorTests RTST_inner LEFT JOIN ReactorTestConditions RTC_inner ON RTST_inner.test_condition_id = RTC_inner.id LEFT JOIN TestConditionTypes TCT_inner ON RTC_inner.test_type_id = TCT_inner.id WHERE RTST_inner.load_id = RL.id AND (TCT_inner.test_condition_type IS NULL OR TRIM(UPPER(TCT_inner.test_condition_type)) <> 'PRESSURE DROP'))) AS test_conditions,
        (SELECT GROUP_CONCAT(description, '; ') FROM (SELECT DISTINCT RTC_inner.description FROM ReactorTests RTST_inner LEFT JOIN ReactorTestConditions RTC_inner ON RTST_inner.test_condition_id = RTC_inner.id LEFT JOIN TestConditionTypes TCT_inner ON RTC_inner.test_type_id = TCT_inner.id WHERE RTST_inner.load_id = RL.id AND (TCT_inner.test_condition_type IS NULL OR TRIM(UPPER(TCT_inner.test_condition_type)) <> 'PRESSURE DROP'))) AS test_condition_description,
        MAX(CASE WHEN RP.reactor_parameter = 'SO2' THEN RTCP.value END) AS SO2,
        MAX(CASE WHEN RP.reactor_parameter = 'CO' THEN RTCP.value END) AS CO,
        MAX(CASE WHEN RP.reactor_parameter = 'NO' THEN RTCP.value END) AS NO,
        MAX(CASE WHEN RP.reactor_parameter = 'NO2' THEN RTCP.value END) AS NO2,
        LB.status,
        LB.priority
    FROM ReactorLoads RL
    INNER JOIN LabRequests LR ON RL.lab_request_id = LR.id
    INNER JOIN LoadBench LB ON RL.id = LB.load_id
    LEFT JOIN auth_user AU ON LR.created_by_id = AU.id
    LEFT JOIN RequestTypes RT ON LR.request_type_id = RT.id
    LEFT JOIN ReactorLoadSamples RLS ON RL.id = RLS.load_id
    LEFT JOIN LabRequestSample LRS ON RLS.lab_request_sample_id = LRS.id
    LEFT JOIN Samples S ON LRS.sample_id = S.id
    LEFT JOIN SampleTypes ST ON S.sample_type_id = ST.id
    LEFT JOIN ReactorTests RTST ON RTST.load_id = RL.id
    LEFT JOIN ReactorTestConditions RTC ON RTST.test_condition_id = RTC.id
    LEFT JOIN TestConditionTypes TCT ON RTC.test_type_id = TCT.id
    LEFT JOIN ReactorTestConditionParameters RTCP ON RTC.id = RTCP.condition_id
    LEFT JOIN ReactorParameters RP ON RTCP.reactor_parameter_id = RP.id
    WHERE LB.testing_area = ? AND (TCT.test_condition_type IS NULL OR TRIM(UPPER(TCT.test_condition_type)) <> 'PRESSURE DROP')
    """
    
    # Add status filter to SQL if provided
    params = [testing_area]
    if status_filter and len(status_filter) > 0:  # Only apply filter if list is non-empty
        placeholders = ', '.join('?' for _ in status_filter)
        query += f" AND LB.status IN ({placeholders})"
        params.extend(status_filter)
    
    # Add grouping and ordering
    query += """
    GROUP BY RL.id
    ORDER BY LB.priority ASC
    """
    
    df = pd.read_sql_query(query, conn, params=params)
    
    # Process timestamps once
    if 'time_submitted' in df.columns and not df.empty:
        df['time_submitted'] = pd.to_datetime(df['time_submitted'], format='mixed', errors='coerce')
        df['time_submitted'] = df['time_submitted'].dt.strftime('%Y-%m-%d %H:%M')
    
    # Fill NaN values in status and priority columns
    if 'status' in df.columns:
        df['status'].fillna('Backlog', inplace=True)
    
    if 'priority' in df.columns:
        df['priority'].fillna(100, inplace=True)
    
    return df

# Get unscheduled loads with optimized query
@st.cache_data(ttl=300)  # Cache for 5 minutes
@with_db_connection
def get_unscheduled_loads(conn, start_date=None):
    """
    Get unscheduled loads with direct SQL filtering
    
    Parameters:
    conn (sqlite3.Connection): Database connection
    start_date (datetime, optional): Start date for filtering
    
    Returns:
    DataFrame: DataFrame containing unscheduled loads
    """
    # Build query with LEFT JOIN and IS NULL condition to find unscheduled loads
    query = """
    SELECT
        RL.id AS ReactorLoadID,
        LR.number AS LabRequestNumber,
        LR.job_number,
        LR.pcn,
        LR.time_submitted,
        AU.username AS created_by,
        RT.request_type,
        COUNT(DISTINCT S.id) AS sample_count,
        (SELECT GROUP_CONCAT(number, ', ') FROM (SELECT DISTINCT S_inner.number FROM ReactorLoadSamples RLS_inner LEFT JOIN LabRequestSample LRS_inner ON RLS_inner.lab_request_sample_id = LRS_inner.id LEFT JOIN Samples S_inner ON LRS_inner.sample_id = S_inner.id WHERE RLS_inner.load_id = RL.id)) AS sample_numbers,
        (SELECT GROUP_CONCAT(sample_type, ', ') FROM (SELECT DISTINCT ST_inner.sample_type FROM ReactorLoadSamples RLS_inner LEFT JOIN LabRequestSample LRS_inner ON RLS_inner.lab_request_sample_id = LRS_inner.id LEFT JOIN Samples S_inner ON LRS_inner.sample_id = S_inner.id LEFT JOIN SampleTypes ST_inner ON S_inner.sample_type_id = ST_inner.id WHERE RLS_inner.load_id = RL.id)) AS sample_types,
        (SELECT COUNT(DISTINCT TCT_inner.id) FROM ReactorTests RTST_inner LEFT JOIN ReactorTestConditions RTC_inner ON RTST_inner.test_condition_id = RTC_inner.id LEFT JOIN TestConditionTypes TCT_inner ON RTC_inner.test_type_id = TCT_inner.id WHERE RTST_inner.load_id = RL.id AND (TCT_inner.test_condition_type IS NULL OR TRIM(UPPER(TCT_inner.test_condition_type)) <> 'PRESSURE DROP')) AS test_count,
        (SELECT GROUP_CONCAT(test_condition_type, ', ') FROM (SELECT DISTINCT TCT_inner.test_condition_type FROM ReactorTests RTST_inner LEFT JOIN ReactorTestConditions RTC_inner ON RTST_inner.test_condition_id = RTC_inner.id LEFT JOIN TestConditionTypes TCT_inner ON RTC_inner.test_type_id = TCT_inner.id WHERE RTST_inner.load_id = RL.id AND (TCT_inner.test_condition_type IS NULL OR TRIM(UPPER(TCT_inner.test_condition_type)) <> 'PRESSURE DROP'))) AS test_conditions,
        (SELECT GROUP_CONCAT(description, '; ') FROM (SELECT DISTINCT RTC_inner.description FROM ReactorTests RTST_inner LEFT JOIN ReactorTestConditions RTC_inner ON RTST_inner.test_condition_id = RTC_inner.id LEFT JOIN TestConditionTypes TCT_inner ON RTC_inner.test_type_id = TCT_inner.id WHERE RTST_inner.load_id = RL.id AND (TCT_inner.test_condition_type IS NULL OR TRIM(UPPER(TCT_inner.test_condition_type)) <> 'PRESSURE DROP'))) AS test_condition_description,
        MAX(CASE WHEN RP.reactor_parameter = 'SO2' THEN RTCP.value END) AS SO2,
        MAX(CASE WHEN RP.reactor_parameter = 'CO' THEN RTCP.value END) AS CO,
        MAX(CASE WHEN RP.reactor_parameter = 'NO' THEN RTCP.value END) AS NO,
        MAX(CASE WHEN RP.reactor_parameter = 'NO2' THEN RTCP.value END) AS NO2
    FROM ReactorLoads RL
    INNER JOIN LabRequests LR ON RL.lab_request_id = LR.id
    LEFT JOIN LoadBench LB ON RL.id = LB.load_id
    LEFT JOIN auth_user AU ON LR.created_by_id = AU.id
    LEFT JOIN RequestTypes RT ON LR.request_type_id = RT.id
    LEFT JOIN ReactorLoadSamples RLS ON RL.id = RLS.load_id
    LEFT JOIN LabRequestSample LRS ON RLS.lab_request_sample_id = LRS.id
    LEFT JOIN Samples S ON LRS.sample_id = S.id
    LEFT JOIN SampleTypes ST ON S.sample_type_id = ST.id
    LEFT JOIN ReactorTests RTST ON RTST.load_id = RL.id
    LEFT JOIN ReactorTestConditions RTC ON RTST.test_condition_id = RTC.id
    LEFT JOIN TestConditionTypes TCT ON RTC.test_type_id = TCT.id
    LEFT JOIN ReactorTestConditionParameters RTCP ON RTC.id = RTCP.condition_id
    LEFT JOIN ReactorParameters RP ON RTCP.reactor_parameter_id = RP.id
    WHERE LB.id IS NULL AND (TCT.test_condition_type IS NULL OR TRIM(UPPER(TCT.test_condition_type)) <> 'PRESSURE DROP')
    """
    
    # Add date filter directly to SQL if specified
    params = []
    if start_date is not None:
        query += " AND LR.time_submitted >= ?"
        params.append(start_date.strftime('%Y-%m-%d'))
    
    # Add grouping and ordering
    query += """
    GROUP BY RL.id
    ORDER BY LR.time_submitted DESC
    """
    
    # Execute query with parameters if any
    if params:
        df = pd.read_sql_query(query, conn, params=params)
    else:
        df = pd.read_sql_query(query, conn)
    
    # Process timestamps once
    if 'time_submitted' in df.columns and not df.empty:
        df['time_submitted'] = pd.to_datetime(df['time_submitted'], format='mixed', errors='coerce')
        df['time_submitted'] = df['time_submitted'].dt.strftime('%Y-%m-%d %H:%M')
    
    return df

# Load scheduled loads with optimized query for specific testing area and status
@st.cache_data(ttl=300)  # Cache for 5 minutes
@with_db_connection
def load_scheduled_loads(conn, testing_area, status_filter=None):
    """
    Get scheduled loads for specific testing area with optional status filter
    
    Parameters:
    conn (sqlite3.Connection): Database connection
    testing_area (str): Testing area to get loads for
    status_filter (str, optional): Filter by status
    
    Returns:
    DataFrame: DataFrame containing scheduled loads
    """
    if status_filter:
        query = """
        SELECT lb.load_id as load_id, lb.priority, lb.status, 
               lr.number as LabRequestNumber, lr.job_number, lr.pcn,
               au.username as created_by
        FROM LoadBench lb
        JOIN ReactorLoads rl ON lb.load_id = rl.id
        JOIN LabRequests lr ON rl.lab_request_id = lr.id
        LEFT JOIN auth_user au ON lr.created_by_id = au.id
        WHERE lb.testing_area = ? AND UPPER(lb.status) = UPPER(?)
        ORDER BY lb.priority ASC
        """
        df = pd.read_sql_query(query, conn, params=(testing_area, status_filter))
    else:
        query = """
        SELECT lb.load_id as load_id, lb.priority, lb.status, 
               lr.number as LabRequestNumber, lr.job_number, lr.pcn,
               au.username as created_by
        FROM LoadBench lb
        JOIN ReactorLoads rl ON lb.load_id = rl.id
        JOIN LabRequests lr ON rl.lab_request_id = lr.id
        LEFT JOIN auth_user au ON lr.created_by_id = au.id
        WHERE lb.testing_area = ?
        ORDER BY lb.priority ASC
        """
        df = pd.read_sql_query(query, conn, params=(testing_area,))
    
    return df

# Save updated priorities to the database
@with_db_connection
def save_new_priorities(conn, df, testing_area):
    """
    Save updated priorities to the database
    
    Parameters:
    conn (sqlite3.Connection): Database connection
    df (DataFrame): DataFrame containing load_id and new priority values
    testing_area (str): The testing area these priorities apply to
    
    Returns:
    bool: True if successful, False otherwise
    """
    if df.empty:
        return False
    
    cursor = conn.cursor()
    
    try:
        conn.execute("BEGIN TRANSACTION")
        
        # Update the priorities for each load
        for index, row in df.iterrows():
            load_id = row['load_id']
            new_priority = row['priority']
            
            cursor.execute(
                "UPDATE LoadBench SET priority = ? WHERE load_id = ? AND testing_area = ?",
                (new_priority, load_id, testing_area)
            )
        
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        st.error(f"Error saving priorities: {e}")
        return False

# Assign a testing area to a load with updated priority logic
@with_db_connection
def assign_testing_area(conn, load_id, testing_area, status=None, priority=None):
    """
    Assign a testing area to a load with updated priority logic
    
    Parameters:
    conn (sqlite3.Connection): Database connection
    load_id (int): Load ID to assign
    testing_area (str): Testing area to assign to
    status (str, optional): Status to set (defaults to 'Backlog')
    priority (int, optional): Priority to set
    
    Returns:
    bool: True if successful
    """
    cursor = conn.cursor()
    
    # Check if load is already assigned
    cursor.execute("SELECT id, status, priority FROM LoadBench WHERE load_id = ?", (load_id,))
    existing = cursor.fetchone()
    
    # Default status to 'Backlog' if not provided
    if status is None:
        status = 'Backlog'
    
    # Priority calculation logic for Backlog status
    if status.upper() == 'BACKLOG' and priority is None:
        # Use centralized function to get next priority
        priority = get_next_backlog_priority(testing_area)
    
    if existing:
        # If no status provided, use existing status or default to 'Backlog'
        if status is None:
            status = existing[1] if existing[1] else 'Backlog'
        
        # If no priority provided and not a Backlog transition, use existing priority
        if priority is None and status.upper() != 'BACKLOG':
            priority = existing[2] if existing[2] is not None else 100
        
        # Update existing assignment
        cursor.execute(
            "UPDATE LoadBench SET testing_area = ?, assigned_date = DATE('now'), status = ?, priority = ? WHERE load_id = ?",
            (testing_area, status, priority, load_id)
        )
    else:
        # Create new assignment with calculated or provided priority
        cursor.execute(
            "INSERT INTO LoadBench (load_id, testing_area, assigned_date, status, priority) VALUES (?, ?, DATE('now'), ?, ?)",
            (load_id, testing_area, status, priority)
        )
    
    conn.commit()
    return True

# Update load status with priority recalculation for backlog transitions
@with_db_connection
def update_load_status(conn, load_id, status):
    """
    Update load status with priority recalculation for backlog transitions
    
    Parameters:
    conn (sqlite3.Connection): Database connection
    load_id (int): Load ID to update
    status (str): New status
    
    Returns:
    bool: True if successful, False otherwise
    """
    cursor = conn.cursor()
    
    # Get current status and testing area
    cursor.execute("SELECT id, status, testing_area FROM LoadBench WHERE load_id = ?", (load_id,))
    result = cursor.fetchone()
    
    if result:
        entry_id, current_status, testing_area = result
        
        # If transitioning to Backlog, assign a new priority at the end of the queue
        if status.upper() == 'BACKLOG' and (current_status is None or current_status.upper() != 'BACKLOG'):
            # Use centralized function to get next priority
            next_priority = get_next_backlog_priority(testing_area)
            
            # Update with new status and recalculated priority
            cursor.execute(
                "UPDATE LoadBench SET status = ?, priority = ? WHERE load_id = ?",
                (status, next_priority, load_id)
            )
        else:
            # For other status transitions, just update the status
            cursor.execute(
                "UPDATE LoadBench SET status = ? WHERE load_id = ?",
                (status, load_id)
            )
        
        conn.commit()
        return True
    else:
        # Cannot update status for non-existing entry
        return False

# Batch update statuses with priority recalculation for backlog transitions
@with_db_connection
def batch_update_status(conn, status_updates):
    """
    Batch update statuses with priority recalculation for backlog transitions
    
    Parameters:
    conn (sqlite3.Connection): Database connection
    status_updates (dict): Dictionary mapping load_id to status
    
    Returns:
    bool: True if successful, False otherwise
    """
    if not status_updates:
        return False
    
    cursor = conn.cursor()
    
    try:
        # Begin transaction
        conn.execute("BEGIN TRANSACTION")
        
        for load_id, status in status_updates.items():
            # Get current status and testing area
            cursor.execute("SELECT status, testing_area FROM LoadBench WHERE load_id = ?", (load_id,))
            result = cursor.fetchone()
            
            if result:
                current_status, testing_area = result
                
                # If transitioning to 'Backlog', assign a new priority at the end of the queue
                if status.upper() == 'BACKLOG' and (current_status is None or current_status.upper() != 'BACKLOG'):
                    # Use centralized function to get next priority
                    next_priority = get_next_backlog_priority(testing_area)
                    
                    # Update with new status and priority
                    cursor.execute(
                        "UPDATE LoadBench SET status = ?, priority = ? WHERE load_id = ?",
                        (status, next_priority, load_id)
                    )
                else:
                    # For other status transitions, just update the status
                    cursor.execute(
                        "UPDATE LoadBench SET status = ? WHERE load_id = ?",
                        (status, load_id)
                    )
        
        # Commit transaction
        conn.execute("COMMIT")
        return True
    
    except Exception as e:
        # Rollback in case of error
        conn.execute("ROLLBACK")
        st.error(f"Error updating statuses: {e}")
        return False

# Assign multiple loads to a testing area with updated priority logic
@with_db_connection
def batch_assign_testing_area(conn, load_ids, testing_area, status=None):
    """
    Assign multiple loads to a testing area with updated priority logic
    
    Parameters:
    conn (sqlite3.Connection): Database connection
    load_ids (list): List of load IDs to assign
    testing_area (str): Testing area to assign to
    status (str, optional): Status to set (defaults to 'Backlog')
    
    Returns:
    bool: True if successful, False otherwise
    """
    if not load_ids:
        return False
    
    cursor = conn.cursor()
    
    # Default status to 'Backlog' if not provided
    if status is None:
        status = 'Backlog'
    
    # Begin transaction
    conn.execute("BEGIN TRANSACTION")
    
    try:
        # For backlog status, get the next available priority at the start
        if status.upper() == 'BACKLOG':
            next_priority = get_next_backlog_priority(testing_area)
        
        for load_id in load_ids:
            # Check if load is already assigned
            cursor.execute("SELECT id, status, priority FROM LoadBench WHERE load_id = ?", (load_id,))
            existing = cursor.fetchone()
            
            if existing:
                current_status = existing[1] if existing[1] else 'Backlog'
                
                # If transitioning to 'Backlog' from non-backlog or new assignment, use calculated priority
                if status.upper() == 'BACKLOG' and current_status.upper() != 'BACKLOG':
                    cursor.execute(
                        "UPDATE LoadBench SET testing_area = ?, assigned_date = DATE('now'), status = ?, priority = ? WHERE load_id = ?",
                        (testing_area, status, next_priority, load_id)
                    )
                    # Increment priority for next load if it's backlog
                    next_priority += 1
                else:
                    # Use existing priority if not transitioning to backlog
                    current_priority = existing[2] if existing[2] is not None else 100
                    cursor.execute(
                        "UPDATE LoadBench SET testing_area = ?, assigned_date = DATE('now'), status = ? WHERE load_id = ?",
                        (testing_area, status, load_id)
                    )
            else:
                # Create new assignment
                if status.upper() == 'BACKLOG':
                    # Use calculated priority for backlog
                    cursor.execute(
                        "INSERT INTO LoadBench (load_id, testing_area, assigned_date, status, priority) VALUES (?, ?, DATE('now'), ?, ?)",
                        (load_id, testing_area, status, next_priority)
                    )
                    # Increment priority for next load
                    next_priority += 1
                else:
                    # Use default priority for non-backlog
                    cursor.execute(
                        "INSERT INTO LoadBench (load_id, testing_area, assigned_date, status, priority) VALUES (?, ?, DATE('now'), ?, ?)",
                        (load_id, testing_area, status, 100)
                    )
        
        # Commit transaction
        conn.execute("COMMIT")
        return True
    
    except Exception as e:
        # Rollback in case of error
        conn.execute("ROLLBACK")
        st.error(f"Error assigning loads: {e}")
        return False

# Unschedule a load (remove from LoadBench)
@with_db_connection
def unschedule_load(conn, load_id):
    """
    Unschedule a load (remove from LoadBench)
    
    Parameters:
    conn (sqlite3.Connection): Database connection
    load_id (int): Load ID to unschedule
    
    Returns:
    bool: True if successful
    """
    cursor = conn.cursor()
    cursor.execute("DELETE FROM LoadBench WHERE load_id = ?", (load_id,))
    conn.commit()
    return True

# Unschedule multiple loads
@with_db_connection
def batch_unschedule_loads(conn, load_ids):
    """
    Unschedule multiple loads
    
    Parameters:
    conn (sqlite3.Connection): Database connection
    load_ids (list): List of load IDs to unschedule
    
    Returns:
    bool: True if successful, False otherwise
    """
    if not load_ids:
        return False
    
    cursor = conn.cursor()
    
    # Begin transaction
    conn.execute("BEGIN TRANSACTION")
    
    try:
        for load_id in load_ids:
            cursor.execute("DELETE FROM LoadBench WHERE load_id = ?", (load_id,))
        
        # Commit transaction
        conn.execute("COMMIT")
        return True
    
    except Exception as e:
        # Rollback in case of error
        conn.execute("ROLLBACK")
        st.error(f"Error unscheduling loads: {e}")
        return False

# Auto-adjust priorities when one or more have been changed
def auto_adjust_priorities(df, changed_items):
    """
    Automatically adjust priorities to maintain proper sequence
    
    Parameters:
    df (DataFrame): DataFrame with edited priorities
    changed_items (list): List of dictionaries with load_id, old_priority, and new_priority
    
    Returns:
    DataFrame: DataFrame with adjusted priorities
    """
    # Make a copy of the dataframe to avoid modifying the original
    adjusted_df = df.copy()
    
    # If no changes, return the original dataframe
    if not changed_items:
        return adjusted_df
    
    # Get the list of all load_ids
    load_ids = adjusted_df['load_id'].tolist()
    
    # First, handle each changed item one by one
    for change in changed_items:
        load_id = change['load_id']
        old_priority = change['old_priority']
        new_priority = change['new_priority']
        
        # Skip if no actual change
        if old_priority == new_priority:
            continue
        
        # Get all current priorities for other items (as they may have been adjusted already)
        current_priorities = {}
        for _, row in adjusted_df.iterrows():
            if row['load_id'] != load_id:  # Skip the changed item
                current_priorities[row['load_id']] = row['priority']
        
        # Adjust priorities for other items
        for other_id, current_priority in current_priorities.items():
            # If moving up in priority (e.g. from 8 to 3)
            if new_priority < old_priority:
                # If this item's priority is between the new and old (inclusive of new, exclusive of old)
                if current_priority >= new_priority and current_priority < old_priority:
                    # Increment this item's priority
                    adjusted_df.loc[adjusted_df['load_id'] == other_id, 'priority'] = current_priority + 1
            # If moving down in priority (e.g. from 3 to 8)
            elif new_priority > old_priority:
                # If this item's priority is between the old and new (exclusive of old, inclusive of new)
                if current_priority > old_priority and current_priority <= new_priority:
                    # Decrement this item's priority
                    adjusted_df.loc[adjusted_df['load_id'] == other_id, 'priority'] = current_priority - 1
    
    # Sort the dataframe by priority for display
    adjusted_df = adjusted_df.sort_values('priority')
    
    return adjusted_df

# Display simple date filter UI and apply to loads
def display_simple_date_filter(key_prefix=""):
    """
    Display a simple date filter with just a From Date field and Apply button
    
    Parameters:
    key_prefix (str): Prefix for Streamlit widget keys to ensure uniqueness
    
    Returns:
    datetime.date: Selected start date
    """
    # Check if state keys exist, initialize if they don't
    if f"start_date_{key_prefix}" not in st.session_state:
        # Default to October 1, 2024
        st.session_state[f"start_date_{key_prefix}"] = datetime(2024, 10, 1).date()
    
    # Create the filter UI using columns for layout
    col1, col2 = st.columns([3, 1])
    
    with col1:
        # Date input with default value
        start_date = st.date_input(
            "From Date:", 
            value=st.session_state[f"start_date_{key_prefix}"],
            key=f"date_input_{key_prefix}"
        )
    
    with col2:
        # Apply button
        apply_filter = st.button("Apply Filter", key=f"apply_filter_{key_prefix}")
    
    # Save selected date to session state if Apply is clicked
    if apply_filter:
        st.session_state[f"start_date_{key_prefix}"] = start_date
    
    return st.session_state[f"start_date_{key_prefix}"]

# Display status filter as a row of checkboxes
def display_status_checkboxes(key_prefix=""):
    """
    Renders a row of checkboxes for each status and returns the list of selected statuses.
    
    Parameters:
    key_prefix (str): Prefix for Streamlit widget keys to ensure uniqueness
    
    Returns:
    list: List of selected status options
    """
    status_options = ["Backlog", "In Reactor", "Test Complete", "QC Complete", "Report Delivered"]
    
    # Initialize session state for the status checkboxes if not already present
    session_key = f"selected_statuses_{key_prefix}"
    if session_key not in st.session_state:
        # Default: all statuses checked except Report Delivered
        st.session_state[session_key] = {status: (status != "Report Delivered") for status in status_options}
    
    # Create columns side by side for the checkboxes
    cols = st.columns(len(status_options))
    
    # Update session_state based on user interactions
    for idx, status in enumerate(status_options):
        # By passing the current value from session_state, we can keep track of toggles
        new_value = cols[idx].checkbox(
            status,
            value=st.session_state[session_key][status],
            key=f"checkbox_{status}_{key_prefix}"
        )
        st.session_state[session_key][status] = new_value
    
    # Build final list of checked statuses
    checked_statuses = [stat for stat, is_checked in st.session_state[session_key].items() if is_checked]
    
    return checked_statuses

# Display bench loads with simplified columns
def display_bench_loads(bench_type, status_filter=None):
    """
    Display loads for a specific bench type with simplified columns and expandable details
    
    Parameters:
    bench_type (str): Bench type ("Quarter Bench" or "Full Bench")
    status_filter (list, optional): List of statuses to filter by
    """
    # Get loads for the bench type
    df = get_bench_loads(bench_type, status_filter)
    
    if df.empty:
        st.info(f"No loads to display for {bench_type}.")
        return
    
    # Display count information
    records_count = len(df)
    st.info(f"Showing {records_count} loads for {bench_type} with selected statuses")
    
    # Create a copy for display
    display_df = df.copy()
    
    # Add a selection column
    display_df['Selected'] = False
    
    # Configure columns for display
    common_columns = [
        'priority', 'status', 'LabRequestNumber', 'pcn', 'request_type',
        'sample_count', 'test_count', 'test_condition_description',
        'start_time', 'end_time',
    ]
    
    # Add reactor column for Full Bench
    if bench_type == "Full Bench" and 'reactor' in display_df.columns:
        display_columns = common_columns.copy()
        # Insert reactor column after end_time
        display_columns.insert(-1, 'reactor')
    else:
        display_columns = common_columns
    
    # Ensure all display columns exist in the dataframe
    for col in display_columns:
        if col not in display_df.columns:
            display_df[col] = None
    
    # Column order - put Selection first, then the display columns
    column_order = ['Selected'] + display_columns
    
    # Define status options
    status_options = ["Backlog", "In Reactor", "Test Complete", "QC Complete", "Report Delivered", "Cancelled"]
    
    # Configure columns
    column_config = {
        'Selected': st.column_config.CheckboxColumn("Select", help="Check to select this load", width="small"),
        'ReactorLoadID': st.column_config.NumberColumn("Load ID", disabled=True, width="small"),
        'status': st.column_config.SelectboxColumn("Status", options=status_options, width="medium"),
        'LabRequestNumber': st.column_config.TextColumn("Lab Request #", disabled=True, width="medium"),
        'pcn': st.column_config.TextColumn("PCN", disabled=True, width="small"),
        'request_type': st.column_config.TextColumn("Request Type", disabled=True, width="medium"),
        'sample_count': st.column_config.NumberColumn("Sample Count", disabled=True, width="small"),
        'test_count': st.column_config.NumberColumn("Test Count", disabled=True, width="small"),
        'test_condition_description': st.column_config.TextColumn("Test Condition Description", disabled=True, width="large"),
        'start_time': st.column_config.TextColumn("Start Time", disabled=True, width="medium"),
        'end_time': st.column_config.TextColumn("End Time", disabled=True, width="medium"),
        'priority': st.column_config.NumberColumn("Priority", disabled=True, width="small")
    }
    
    # Add reactor column config for Full Bench
    if bench_type == "Full Bench":
        column_config['reactor'] = st.column_config.TextColumn("Reactor", disabled=True, width="small")
    
    # Save original statuses to detect changes
    original_statuses = {}
    if 'status' in display_df.columns and 'ReactorLoadID' in display_df.columns:
        original_statuses = display_df.set_index('ReactorLoadID')['status'].to_dict()
    
    # Use data_editor with doubled height
    editor_key = f"{bench_type.lower().replace(' ', '_')}_editor"
    edited_df = st.data_editor(
        display_df[column_order],
        use_container_width=True,
        height=800,  # Doubled height as requested
        key=editor_key,
        column_config=column_config,
        hide_index=True,
        column_order=column_order,
        disabled=[col for col in column_order if col not in ['Selected', 'status']]  # Only Selected and status are editable
    )
    
    # Get selected rows from the edited dataframe
    selected_indices = edited_df.index[edited_df['Selected']].tolist()
    selected_load_ids = edited_df.loc[selected_indices, 'ReactorLoadID'].tolist() if selected_indices else []
    
    # Check for status changes
    status_updates = {}
    if 'status' in edited_df.columns and 'ReactorLoadID' in edited_df.columns:
        # Compare current statuses with original
        for idx, row in edited_df.iterrows():
            load_id = row['ReactorLoadID']
            new_status = row['status']
            
            # Check if this load_id was in our original data and if status changed
            if load_id in original_statuses and original_statuses[load_id] != new_status:
                status_updates[load_id] = new_status
    
    # Display batch operations if loads are selected
    if selected_load_ids:
        st.markdown(f"""
        <div style="background-color: #f8f9fa; padding: 15px; border-radius: 10px; 
                    border-left: 5px solid #4CAF50; margin-bottom: 20px;">
            <h4 style="margin-top: 0; color: #2E7D32;">✅ {len(selected_load_ids)} Loads Selected</h4>
            <p><strong>Selected Load IDs:</strong> {', '.join(map(str, selected_load_ids))}</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Assignment buttons in a row
        col1, col2, col3 = st.columns(3)
        operation_performed = False
        
        with col1:
            if bench_type != "Quarter Bench" and st.button("Move to Quarter Bench", key=f"batch_qb_{bench_type}", use_container_width=True):
                try:
                    if batch_assign_testing_area(selected_load_ids, "Quarter Bench"):
                        st.success(f"Successfully moved {len(selected_load_ids)} loads to Quarter Bench")
                        operation_performed = True
                    else:
                        st.error("Failed to move loads to Quarter Bench")
                except Exception as e:
                    st.error(f"Error moving loads to Quarter Bench: {e}")
        
        with col2:
            if bench_type != "Full Bench" and st.button("Move to Full Bench", key=f"batch_fb_{bench_type}", use_container_width=True):
                try:
                    if batch_assign_testing_area(selected_load_ids, "Full Bench"):
                        st.success(f"Successfully moved {len(selected_load_ids)} loads to Full Bench")
                        operation_performed = True
                    else:
                        st.error("Failed to move loads to Full Bench")
                except Exception as e:
                    st.error(f"Error moving loads to Full Bench: {e}")
        
        with col3:
            if st.button("Mark as Cancelled", key=f"batch_cancel_{bench_type}", use_container_width=True):
                try:
                    status_updates = {load_id: "Cancelled" for load_id in selected_load_ids}
                    if batch_update_status(status_updates):
                        st.success(f"Successfully marked {len(selected_load_ids)} loads as Cancelled")
                        operation_performed = True
                    else:
                        st.error("Failed to mark loads as Cancelled")
                except Exception as e:
                    st.error(f"Error marking loads as Cancelled: {e}")
        
        if st.button("Unschedule Selected Loads", key=f"batch_unschedule_{bench_type}", use_container_width=True):
            try:
                if batch_unschedule_loads(selected_load_ids):
                    st.success(f"Successfully unscheduled {len(selected_load_ids)} loads")
                    operation_performed = True
                else:
                    st.error("Failed to unschedule loads")
            except Exception as e:
                st.error(f"Error unscheduling loads: {e}")
        
        # If operations were performed, refresh the data
        if operation_performed:
            st.cache_data.clear()
            st.rerun()
    
    # Handle status updates if any
    if status_updates:
        if st.button("Save Status Changes", key=f"save_status_{bench_type}", use_container_width=True):
            if batch_update_status(status_updates):
                st.success(f"Successfully updated {len(status_updates)} load statuses")
                st.cache_data.clear()  # Clear cache to refresh data
                st.rerun()
            else:
                st.error("Failed to update statuses")
    
    # Individual load details in expander
    if not df.empty:
        with st.expander("Individual Load Details", expanded=False):
            # Create a selectbox for individual load selection
            load_options = [f"{row['ReactorLoadID']} - {row.get('LabRequestNumber', 'N/A')}" 
                        for idx, row in df.iterrows()]
            
            selected_load = st.selectbox("Select a load for detailed view:", load_options, key=f"load_select_{bench_type}")
            if selected_load:
                load_id = int(selected_load.split(' - ')[0])
                
                # Get the row data for this load
                load_row = df[df['ReactorLoadID'] == load_id].iloc[0]
                
                # Display load details in columns
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("#### Basic Information")
                    st.write(f"**Load ID:** {load_id}")
                    st.write(f"**Lab Request:** {load_row.get('LabRequestNumber', 'N/A')}")
                    st.write(f"**Job Number:** {load_row.get('job_number', 'N/A')}")
                    st.write(f"**PCN:** {load_row.get('pcn', 'N/A')}")
                    st.write(f"**Submitted:** {load_row.get('time_submitted', 'N/A')}")
                    st.write(f"**Created By:** {load_row.get('created_by', 'N/A')}")
                
                with col2:
                    st.markdown("#### Technical Details")
                    st.write(f"**Request Type:** {load_row.get('request_type', 'N/A')}")
                    st.write(f"**Sample Count:** {load_row.get('sample_count', 'N/A')}")
                    st.write(f"**Sample Types:** {load_row.get('sample_types', 'N/A')}")
                    st.write(f"**Test Count:** {load_row.get('test_count', 'N/A')}")
                    st.write(f"**SO2:** {load_row.get('SO2', 'N/A')}")
                    st.write(f"**CO:** {load_row.get('CO', 'N/A')}")
                    st.write(f"**NO:** {load_row.get('NO', 'N/A')}")
                    st.write(f"**NO2:** {load_row.get('NO2', 'N/A')}")
                
                # Status update for individual load
                st.markdown("#### Update Status")
                new_status = st.selectbox(
                    "Set Status:",
                    options=["Backlog", "In Reactor", "Test Complete", "QC Complete", "Report Delivered", "Cancelled"],
                    index=["Backlog", "In Reactor", "Test Complete", "QC Complete", "Report Delivered", "Cancelled"].index(load_row.get('status', 'Backlog')) if load_row.get('status', 'Backlog') in ["Backlog", "In Reactor", "Test Complete", "QC Complete", "Report Delivered", "Cancelled"] else 0,
                    key=f"status_select_{load_id}_{bench_type}"
                )
                
                if new_status != load_row.get('status', 'Backlog') and st.button("Update Status", key=f"update_status_{load_id}_{bench_type}"):
                    if update_load_status(load_id, new_status):
                        st.success(f"Updated Load {load_id} status to {new_status}")
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        st.error(f"Failed to update status for Load {load_id}")
                
                # Individual re-assignment controls
                st.markdown("#### Reassign Load")
                reassign_cols = st.columns(3)
                
                with reassign_cols[0]:
                    if bench_type != "Quarter Bench" and st.button("Move to Quarter Bench", key=f"ind_qb_{load_id}", use_container_width=True):
                        try:
                            assign_testing_area(load_id, "Quarter Bench", load_row.get('status', 'Backlog'))
                            st.success(f"Moved Load {load_id} to Quarter Bench")
                            st.cache_data.clear()
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error moving load to Quarter Bench: {e}")
                
                with reassign_cols[1]:
                    if bench_type != "Full Bench" and st.button("Move to Full Bench", key=f"ind_fb_{load_id}", use_container_width=True):
                        try:
                            assign_testing_area(load_id, "Full Bench", load_row.get('status', 'Backlog'))
                            st.success(f"Moved Load {load_id} to Full Bench")
                            st.cache_data.clear()
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error moving load to Full Bench: {e}")
                
                with reassign_cols[2]:
                    if st.button("Unschedule Load", key=f"ind_unschedule_{load_id}", use_container_width=True):
                        try:
                            unschedule_load(load_id)
                            st.success(f"Unscheduled Load {load_id}")
                            st.cache_data.clear()
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error unscheduling load: {e}")

# Display priority reordering function
@with_db_connection
def display_priority_reordering(conn, testing_area):
    """
    Display load dataframe with manual priority number editing and automatic adjustment
    
    Parameters:
    conn (sqlite3.Connection): Database connection
    testing_area (str): The testing area to display loads for
    """
    # Load the data for the selected testing area with 'Backlog' status only
    df = load_scheduled_loads(testing_area, status_filter='Backlog')
    
    if df.empty:
        st.info(f"No backlog loads scheduled for {testing_area}.")
        return
    
    # Sort by priority
    df = df.sort_values('priority')
    
    # Information header with clear instructions
    st.markdown("""
    ## Backlog Priority Editor
    
    1. **Edit any priority number** to change the order
    2. **All other priorities will automatically adjust** when you save
    3. Lowest number = highest priority (will be tested first)
    4. Click **SAVE PRIORITIES** when done
    """)
    
    # Convert columns for editing
    edit_df = df.copy()
    
    # Create a copy of the original priorities to detect changes
    original_priorities = dict(zip(edit_df['load_id'], edit_df['priority']))
    
    # Select columns for display
    display_columns = ['load_id', 'LabRequestNumber', 'job_number', 'pcn', 'created_by', 'priority']
    display_columns = [col for col in display_columns if col in edit_df.columns]
    
    # Create editable dataframe with only needed columns
    display_df = edit_df[display_columns].copy()
    
    # Set column configuration
    column_config = {
        'load_id': st.column_config.NumberColumn("Load ID", disabled=True, width="small"),
        'LabRequestNumber': st.column_config.TextColumn("Lab Request #", disabled=True, width="medium"),
        'job_number': st.column_config.TextColumn("Job #", disabled=True, width="small"),
        'pcn': st.column_config.TextColumn("PCN", disabled=True, width="small"),
        'created_by': st.column_config.TextColumn("Created By", disabled=True, width="medium"),
        'priority': st.column_config.NumberColumn(
            "Priority", 
            help="Enter a number to set priority (lower number = higher priority)",
            min_value=1,
            max_value=1000,
            step=1,
            format="%d",
            width="small",
            disabled=False  # This column is editable
        )
    }
    
    # Create a list of disabled columns (all except priority)
    disabled_columns = [col for col in display_columns if col != 'priority']
    
    # Display the editor
    edited_df = st.data_editor(
        display_df,
        column_config=column_config,
        use_container_width=True,
        hide_index=True,
        num_rows="fixed",
        key=f"priority_editor_{testing_area}",
        disabled=disabled_columns  # Only priority column is editable
    )
    
    # Check if priorities have been changed
    changes_made = False
    changed_items = []
    for _, row in edited_df.iterrows():
        load_id = row['load_id']
        new_priority = row['priority']
        if load_id in original_priorities and original_priorities[load_id] != new_priority:
            changes_made = True
            changed_items.append({
                "load_id": load_id,
                "old_priority": original_priorities[load_id],
                "new_priority": new_priority
            })
    
    # Add an explanation of the auto-adjustment
    if changes_made:
        st.info("☝️ You've changed some priorities. When you save, other priorities will automatically adjust to maintain the sequence.")
    
    # Show save button (with appropriate styling)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("💾 SAVE PRIORITIES", key=f"save_priorities_{testing_area}", use_container_width=True):
            try:
                # Apply priority adjustments before saving
                adjusted_df = auto_adjust_priorities(edited_df, changed_items)
                
                # Show preview of adjusted priorities
                st.write("Adjusting priorities...")
                
                # Save the priorities to the database
                save_result = save_new_priorities(adjusted_df, testing_area)
                
                if save_result:
                    st.success("✅ Priorities saved successfully with automatic adjustment!")
                    # Clear cache and force app refresh to show the new priorities
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error("❌ Failed to save priorities.")
            except Exception as e:
                st.error(f"Error saving priorities: {e}")

# Run Excel import script
def run_excel_import_script():
    """
    Run the Excel import script using subprocess
    
    Returns:
    bool: True if successful, False otherwise
    """
    # Define paths to script and Excel file
    script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "excel_to_db.py")
    excel_path = r"C:\Users\s.jay\OneDrive - Cormetech\Hub\Reactor Loadsv1.xlsm"
    
    try:
        # Run the script with subprocess
        result = subprocess.run(
            ["python", script_path, excel_path],
            capture_output=True,
            text=True
        )
        
        # Check if script ran successfully
        if result.returncode == 0:
            return True, result.stdout
        else:
            return False, result.stderr
    except Exception as e:
        return False, str(e)

# NEW FUNCTIONS FOR DASHBOARD

# Helper function to get week start and end dates
def get_week_dates(weeks_ago=0):
    """
    Get the start and end dates for a week
    
    Parameters:
    weeks_ago (int): Number of weeks ago (0 = current week)
    
    Returns:
    tuple: (start_date, end_date) for the week
    """
    today = datetime.now().date()
    # Find the most recent Monday (start of week)
    current_weekday = today.weekday()  # Monday is 0, Sunday is 6
    days_since_monday = current_weekday
    most_recent_monday = today - timedelta(days=days_since_monday)
    
    # Calculate the start and end dates for the requested week
    week_start = most_recent_monday - timedelta(weeks=weeks_ago)
    week_end = week_start + timedelta(days=6)  # Sunday is 6 days after Monday
    
    return week_start, week_end

# Helper function to get month start and end dates
def get_month_dates(months_ago=0):
    """
    Get the start and end dates for a month
    
    Parameters:
    months_ago (int): Number of months ago (0 = current month)
    
    Returns:
    tuple: (start_date, end_date) for the month
    """
    today = datetime.now().date()
    
    # Calculate the first day of the current month
    first_day_current_month = date(today.year, today.month, 1)
    
    # Calculate the first day of the requested month
    if months_ago == 0:
        first_day = first_day_current_month
    else:
        # For past months
        year = today.year
        month = today.month - months_ago
        
        # Adjust year if we go to previous year
        while month <= 0:
            year -= 1
            month += 12
        
        first_day = date(year, month, 1)
    
    # Calculate the last day of the requested month
    if first_day.month == 12:
        next_month = date(first_day.year + 1, 1, 1)
    else:
        next_month = date(first_day.year, first_day.month + 1, 1)
    
    last_day = next_month - timedelta(days=1)
    
    return first_day, last_day

# Query for weekly test completions
@st.cache_data(ttl=600)  # Cache for 10 minutes
@with_db_connection
def get_weekly_completions(conn, weeks_ago=0):
    """
    Get completed tests and loads for a specific week
    
    Parameters:
    conn (sqlite3.Connection): Database connection
    weeks_ago (int): Number of weeks ago (0 = current week)
    
    Returns:
    dict: Dictionary with test and load counts
    """
    week_start, week_end = get_week_dates(weeks_ago)
    
    # Query to get completed tests
    test_query = """
    SELECT COUNT(DISTINCT RT.id) as test_count
    FROM ReactorTests RT
    INNER JOIN ReactorLoads RL ON RT.load_id = RL.id
    INNER JOIN LoadBench LB ON RL.id = LB.load_id
    WHERE RT.stop_time BETWEEN ? AND ?
    AND (LB.status = 'Test Complete' OR LB.status = 'QC Complete' OR LB.status = 'Report Delivered')
    """
    
    # Query to get completed loads
    load_query = """
    SELECT COUNT(DISTINCT RL.id) as load_count
    FROM ReactorLoads RL
    INNER JOIN LoadBench LB ON RL.id = LB.load_id
    WHERE LB.status IN ('Test Complete', 'QC Complete', 'Report Delivered')
    AND EXISTS (
        SELECT 1 FROM ReactorTests RT 
        WHERE RT.load_id = RL.id 
        AND RT.stop_time BETWEEN ? AND ?
    )
    """
    
    # Format dates for SQL
    start_str = week_start.strftime('%Y-%m-%d 00:00:00')
    end_str = week_end.strftime('%Y-%m-%d 23:59:59')
    
    # Execute queries
    cursor = conn.cursor()
    cursor.execute(test_query, (start_str, end_str))
    test_result = cursor.fetchone()
    test_count = test_result[0] if test_result else 0
    
    cursor.execute(load_query, (start_str, end_str))
    load_result = cursor.fetchone()
    load_count = load_result[0] if load_result else 0
    
    return {
        'week_label': f"{week_start.strftime('%b %d')} - {week_end.strftime('%b %d')}",
        'test_count': test_count,
        'load_count': load_count
    }

# Query for monthly test completions
@st.cache_data(ttl=600)  # Cache for 10 minutes
@with_db_connection
def get_monthly_completions(conn, months_ago=0):
    """
    Get completed tests and loads for a specific month
    
    Parameters:
    conn (sqlite3.Connection): Database connection
    months_ago (int): Number of months ago (0 = current month)
    
    Returns:
    dict: Dictionary with test and load counts
    """
    month_start, month_end = get_month_dates(months_ago)
    
    # Query to get completed tests
    test_query = """
    SELECT COUNT(DISTINCT RT.id) as test_count
    FROM ReactorTests RT
    INNER JOIN ReactorLoads RL ON RT.load_id = RL.id
    INNER JOIN LoadBench LB ON RL.id = LB.load_id
    WHERE RT.stop_time BETWEEN ? AND ?
    AND (LB.status = 'Test Complete' OR LB.status = 'QC Complete' OR LB.status = 'Report Delivered')
    """
    
    # Query to get completed loads
    load_query = """
    SELECT COUNT(DISTINCT RL.id) as load_count
    FROM ReactorLoads RL
    INNER JOIN LoadBench LB ON RL.id = LB.load_id
    WHERE LB.status IN ('Test Complete', 'QC Complete', 'Report Delivered')
    AND EXISTS (
        SELECT 1 FROM ReactorTests RT 
        WHERE RT.load_id = RL.id 
        AND RT.stop_time BETWEEN ? AND ?
    )
    """
    
    # Format dates for SQL
    start_str = month_start.strftime('%Y-%m-%d 00:00:00')
    end_str = month_end.strftime('%Y-%m-%d 23:59:59')
    
    # Execute queries
    cursor = conn.cursor()
    cursor.execute(test_query, (start_str, end_str))
    test_result = cursor.fetchone()
    test_count = test_result[0] if test_result else 0
    
    cursor.execute(load_query, (start_str, end_str))
    load_result = cursor.fetchone()
    load_count = load_result[0] if load_result else 0
    
    return {
        'month_label': month_start.strftime('%B %Y'),
        'test_count': test_count,
        'load_count': load_count
    }

# Query for weekly completions by request type
@st.cache_data(ttl=600)  # Cache for 10 minutes
@with_db_connection
def get_weekly_completions_by_request_type(conn, weeks_ago=0):
    """
    Get weekly completions broken down by request type
    
    Parameters:
    conn (sqlite3.Connection): Database connection
    weeks_ago (int): Number of weeks ago (0 = current week)
    
    Returns:
    DataFrame: DataFrame with completions by request type
    """
    week_start, week_end = get_week_dates(weeks_ago)
    
    # Query to get completed tests by request type
    query = """
    SELECT 
        RT.request_type, 
        COUNT(DISTINCT RTest.id) as test_count,
        COUNT(DISTINCT RL.id) as load_count
    FROM ReactorTests RTest
    INNER JOIN ReactorLoads RL ON RTest.load_id = RL.id
    INNER JOIN LabRequests LR ON RL.lab_request_id = LR.id
    INNER JOIN RequestTypes RT ON LR.request_type_id = RT.id
    INNER JOIN LoadBench LB ON RL.id = LB.load_id
    WHERE RTest.stop_time BETWEEN ? AND ?
    AND (LB.status = 'Test Complete' OR LB.status = 'QC Complete' OR LB.status = 'Report Delivered')
    GROUP BY RT.request_type
    ORDER BY test_count DESC
    """
    
    # Format dates for SQL
    start_str = week_start.strftime('%Y-%m-%d 00:00:00')
    end_str = week_end.strftime('%Y-%m-%d 23:59:59')
    
    # Execute query
    df = pd.read_sql_query(query, conn, params=(start_str, end_str))
    
    # Handle empty result
    if df.empty:
        df = pd.DataFrame(columns=['request_type', 'test_count', 'load_count'])
    
    return df

# Query for weekly completions by test condition type
@st.cache_data(ttl=600)  # Cache for 10 minutes
@with_db_connection
def get_weekly_completions_by_condition_type(conn, weeks_ago=0):
    """
    Get weekly completions broken down by test condition type
    
    Parameters:
    conn (sqlite3.Connection): Database connection
    weeks_ago (int): Number of weeks ago (0 = current week)
    
    Returns:
    DataFrame: DataFrame with completions by test condition type
    """
    week_start, week_end = get_week_dates(weeks_ago)
    
    # Query to get completed tests by test condition type
    query = """
    SELECT 
        TCT.test_condition_type, 
        COUNT(DISTINCT RTest.id) as test_count,
        COUNT(DISTINCT RL.id) as load_count
    FROM ReactorTests RTest
    INNER JOIN ReactorTestConditions RTC ON RTest.test_condition_id = RTC.id
    INNER JOIN TestConditionTypes TCT ON RTC.test_type_id = TCT.id
    INNER JOIN ReactorLoads RL ON RTest.load_id = RL.id
    INNER JOIN LoadBench LB ON RL.id = LB.load_id
    WHERE RTest.stop_time BETWEEN ? AND ?
    AND (LB.status = 'Test Complete' OR LB.status = 'QC Complete' OR LB.status = 'Report Delivered')
    AND (TCT.test_condition_type IS NULL OR TRIM(UPPER(TCT.test_condition_type)) <> 'PRESSURE DROP')
    GROUP BY TCT.test_condition_type
    ORDER BY test_count DESC
    """
    
    # Format dates for SQL
    start_str = week_start.strftime('%Y-%m-%d 00:00:00')
    end_str = week_end.strftime('%Y-%m-%d 23:59:59')
    
    # Execute query
    df = pd.read_sql_query(query, conn, params=(start_str, end_str))
    
    # Handle empty result
    if df.empty:
        df = pd.DataFrame(columns=['test_condition_type', 'test_count', 'load_count'])
    
    return df

# Query for monthly completions by request type
@st.cache_data(ttl=600)  # Cache for 10 minutes
@with_db_connection
def get_monthly_completions_by_request_type(conn, months_ago=0):
    """
    Get monthly completions broken down by request type
    
    Parameters:
    conn (sqlite3.Connection): Database connection
    months_ago (int): Number of months ago (0 = current month)
    
    Returns:
    DataFrame: DataFrame with completions by request type
    """
    month_start, month_end = get_month_dates(months_ago)
    
    # Query to get completed tests by request type
    query = """
    SELECT 
        RT.request_type, 
        COUNT(DISTINCT RTest.id) as test_count,
        COUNT(DISTINCT RL.id) as load_count
    FROM ReactorTests RTest
    INNER JOIN ReactorLoads RL ON RTest.load_id = RL.id
    INNER JOIN LabRequests LR ON RL.lab_request_id = LR.id
    INNER JOIN RequestTypes RT ON LR.request_type_id = RT.id
    INNER JOIN LoadBench LB ON RL.id = LB.load_id
    WHERE RTest.stop_time BETWEEN ? AND ?
    AND (LB.status = 'Test Complete' OR LB.status = 'QC Complete' OR LB.status = 'Report Delivered')
    GROUP BY RT.request_type
    ORDER BY test_count DESC
    """
    
    # Format dates for SQL
    start_str = month_start.strftime('%Y-%m-%d 00:00:00')
    end_str = month_end.strftime('%Y-%m-%d 23:59:59')
    
    # Execute query
    df = pd.read_sql_query(query, conn, params=(start_str, end_str))
    
    # Handle empty result
    if df.empty:
        df = pd.DataFrame(columns=['request_type', 'test_count', 'load_count'])
    
    return df

# Query for monthly completions by test condition type
@st.cache_data(ttl=600)  # Cache for 10 minutes
@with_db_connection
def get_monthly_completions_by_condition_type(conn, months_ago=0):
    """
    Get monthly completions broken down by test condition type
    
    Parameters:
    conn (sqlite3.Connection): Database connection
    months_ago (int): Number of months ago (0 = current month)
    
    Returns:
    DataFrame: DataFrame with completions by test condition type
    """
    month_start, month_end = get_month_dates(months_ago)
    
    # Query to get completed tests by test condition type
    query = """
    SELECT 
        TCT.test_condition_type, 
        COUNT(DISTINCT RTest.id) as test_count,
        COUNT(DISTINCT RL.id) as load_count
    FROM ReactorTests RTest
    INNER JOIN ReactorTestConditions RTC ON RTest.test_condition_id = RTC.id
    INNER JOIN TestConditionTypes TCT ON RTC.test_type_id = TCT.id
    INNER JOIN ReactorLoads RL ON RTest.load_id = RL.id
    INNER JOIN LoadBench LB ON RL.id = LB.load_id
    WHERE RTest.stop_time BETWEEN ? AND ?
    AND (LB.status = 'Test Complete' OR LB.status = 'QC Complete' OR LB.status = 'Report Delivered')
    AND (TCT.test_condition_type IS NULL OR TRIM(UPPER(TCT.test_condition_type)) <> 'PRESSURE DROP')
    GROUP BY TCT.test_condition_type
    ORDER BY test_count DESC
    """
    
    # Format dates for SQL
    start_str = month_start.strftime('%Y-%m-%d 00:00:00')
    end_str = month_end.strftime('%Y-%m-%d 23:59:59')
    
    # Execute query
    df = pd.read_sql_query(query, conn, params=(start_str, end_str))
    
    # Handle empty result
    if df.empty:
        df = pd.DataFrame(columns=['test_condition_type', 'test_count', 'load_count'])
    
    return df

# Display dashboard metrics
def display_dashboard():
    """Display dashboard with weekly and monthly metrics"""
    st.header("📊 Dashboard")
    
    # Weekly metrics
    st.subheader("Weekly Completion Metrics")
    
    # Get weekly data for current and past 3 weeks
    current_week = get_weekly_completions(0)
    week_1 = get_weekly_completions(1)
    week_2 = get_weekly_completions(2)
    week_3 = get_weekly_completions(3)
    
    # Create data for charts
    weekly_data = [
        {"week": current_week['week_label'], "test_count": current_week['test_count'], "load_count": current_week['load_count']},
        {"week": week_1['week_label'], "test_count": week_1['test_count'], "load_count": week_1['load_count']},
        {"week": week_2['week_label'], "test_count": week_2['test_count'], "load_count": week_2['load_count']},
        {"week": week_3['week_label'], "test_count": week_3['test_count'], "load_count": week_3['load_count']},
    ]
    
    # Create a pandas DataFrame for visualization
    weekly_df = pd.DataFrame(weekly_data)
    
    # Display metrics in columns
    col1, col2 = st.columns(2)
    
    with col1:
        # Create tests completed chart
        fig_tests = px.bar(
            weekly_df,
            x="week",
            y="test_count",
            title="Tests Completed by Week",
            labels={"week": "Week", "test_count": "Number of Tests"},
            color_discrete_sequence=["#1f77b4"],
            text="test_count"
        )
        fig_tests.update_traces(texttemplate='%{text:.0f}', textposition='outside')
        fig_tests.update_layout(
            height=350,
            margin=dict(l=20, r=20, t=40, b=20),
            yaxis_title="Number of Tests",
            xaxis_title=""
        )
        st.plotly_chart(fig_tests, use_container_width=True)
    
    with col2:
        # Create loads completed chart
        fig_loads = px.bar(
            weekly_df,
            x="week",
            y="load_count",
            title="Loads Completed by Week",
            labels={"week": "Week", "load_count": "Number of Loads"},
            color_discrete_sequence=["#ff7f0e"],
            text="load_count"
        )
        fig_loads.update_traces(texttemplate='%{text:.0f}', textposition='outside')
        fig_loads.update_layout(
            height=350,
            margin=dict(l=20, r=20, t=40, b=20),
            yaxis_title="Number of Loads",
            xaxis_title=""
        )
        st.plotly_chart(fig_loads, use_container_width=True)
    
    # Weekly breakdown options
    st.subheader("Weekly Breakdown")
    weekly_tab1, weekly_tab2 = st.tabs(["By Request Type", "By Test Condition Type"])
    
    with weekly_tab1:
        # Get weekly breakdown by request type
        weekly_request_type_df = get_weekly_completions_by_request_type(0)
        
        if not weekly_request_type_df.empty and len(weekly_request_type_df) > 0:
            # Create bar chart for request type breakdown
            fig_request = px.bar(
                weekly_request_type_df,
                x="request_type",
                y=["test_count", "load_count"],
                title=f"Current Week Completion by Request Type ({current_week['week_label']})",
                labels={"value": "Count", "request_type": "Request Type", "variable": "Metric"},
                barmode="group",
                color_discrete_map={"test_count": "#1f77b4", "load_count": "#ff7f0e"}
            )
            fig_request.update_layout(
                height=400,
                margin=dict(l=20, r=20, t=40, b=100),
                xaxis_tickangle=-45,
                legend_title_text="Metric"
            )
            st.plotly_chart(fig_request, use_container_width=True)
        else:
            st.info("No data available for weekly request type breakdown.")
    
    with weekly_tab2:
        # Get weekly breakdown by test condition type
        weekly_condition_type_df = get_weekly_completions_by_condition_type(0)
        
        if not weekly_condition_type_df.empty and len(weekly_condition_type_df) > 0:
            # Create bar chart for test condition type breakdown
            fig_condition = px.bar(
                weekly_condition_type_df,
                x="test_condition_type",
                y=["test_count", "load_count"],
                title=f"Current Week Completion by Test Condition Type ({current_week['week_label']})",
                labels={"value": "Count", "test_condition_type": "Test Condition Type", "variable": "Metric"},
                barmode="group",
                color_discrete_map={"test_count": "#1f77b4", "load_count": "#ff7f0e"}
            )
            fig_condition.update_layout(
                height=400,
                margin=dict(l=20, r=20, t=40, b=100),
                xaxis_tickangle=-45,
                legend_title_text="Metric"
            )
            st.plotly_chart(fig_condition, use_container_width=True)
        else:
            st.info("No data available for weekly test condition type breakdown.")
    
    # Monthly metrics
    st.subheader("Monthly Completion Metrics")
    
    # Get current month data
    current_month = get_monthly_completions(0)
    
    # Create metrics cards for current month
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric(
            label=f"Tests Completed in {current_month['month_label']}",
            value=current_month['test_count']
        )
    
    with col2:
        st.metric(
            label=f"Loads Completed in {current_month['month_label']}",
            value=current_month['load_count']
        )
    
    # Monthly breakdown options
    st.subheader("Monthly Breakdown")
    monthly_tab1, monthly_tab2 = st.tabs(["By Request Type", "By Test Condition Type"])
    
    with monthly_tab1:
        # Get monthly breakdown by request type
        monthly_request_type_df = get_monthly_completions_by_request_type(0)
        
        if not monthly_request_type_df.empty and len(monthly_request_type_df) > 0:
            # Create bar chart for request type breakdown
            fig_request = px.bar(
                monthly_request_type_df,
                x="request_type",
                y=["test_count", "load_count"],
                title=f"Current Month Completion by Request Type ({current_month['month_label']})",
                labels={"value": "Count", "request_type": "Request Type", "variable": "Metric"},
                barmode="group",
                color_discrete_map={"test_count": "#1f77b4", "load_count": "#ff7f0e"}
            )
            fig_request.update_layout(
                height=400,
                margin=dict(l=20, r=20, t=40, b=100),
                xaxis_tickangle=-45,
                legend_title_text="Metric"
            )
            st.plotly_chart(fig_request, use_container_width=True)
        else:
            st.info("No data available for monthly request type breakdown.")
    
    with monthly_tab2:
        # Get monthly breakdown by test condition type
        monthly_condition_type_df = get_monthly_completions_by_condition_type(0)
        
        if not monthly_condition_type_df.empty and len(monthly_condition_type_df) > 0:
            # Create bar chart for test condition type breakdown
            fig_condition = px.bar(
                monthly_condition_type_df,
                x="test_condition_type",
                y=["test_count", "load_count"],
                title=f"Current Month Completion by Test Condition Type ({current_month['month_label']})",
                labels={"value": "Count", "test_condition_type": "Test Condition Type", "variable": "Metric"},
                barmode="group",
                color_discrete_map={"test_count": "#1f77b4", "load_count": "#ff7f0e"}
            )
            fig_condition.update_layout(
                height=400,
                margin=dict(l=20, r=20, t=40, b=100),
                xaxis_tickangle=-45,
                legend_title_text="Metric"
            )
            st.plotly_chart(fig_condition, use_container_width=True)
        else:
            st.info("No data available for monthly test condition type breakdown.")

# Main app function
def main():
    # Apply custom CSS for typography enhancements
    apply_custom_css()
    
    st.title("Lab Load Scheduler App")
    st.markdown("---")
    
    # Initialize LoadBench table if it doesn't exist
    try:
        init_loadbench_table()
    except Exception as e:
        st.error(f"Error initializing database: {e}")
        return
    
    # Add Excel import button in the sidebar
    st.sidebar.title("Excel Import")
    
    if st.sidebar.button("🔄 Sync Excel Schedules", use_container_width=True):
        with st.sidebar:
            with st.spinner("Syncing Excel schedules..."):
                success, message = run_excel_import_script()
                
                if success:
                    st.success("Load schedules synced successfully!")
                    # Clear cache to refresh data
                    st.cache_data.clear()
                else:
                    st.error(f"Failed to sync schedules: {message}")
    
    # Create tabs for different views - Dashboard is now the first tab
    tabs = st.tabs(["Dashboard", "Quarter Bench", "Full Bench", "Unscheduled Loads", "Cancelled", "Priority Scheduler"])
    
    try:
        # Tab 1: Dashboard (new first tab)
        with tabs[0]:
            display_dashboard()
            
        # Tab 2: Quarter Bench (now second tab)
        with tabs[1]:
            st.header("Quarter Bench Loads")
            
            # Display status filter checkboxes
            selected_statuses = display_status_checkboxes(key_prefix="quarter_bench")
            
            # Handle the case when no statuses are selected
            if not selected_statuses:
                st.warning("No statuses selected. No data to display.")
            else:
                # Display bench loads with simplified columns
                display_bench_loads("Quarter Bench", status_filter=selected_statuses)
        
        # Tab 3: Full Bench (now third tab)
        with tabs[2]:
            st.header("Full Bench Loads")
            
            # Display status filter checkboxes
            selected_statuses = display_status_checkboxes(key_prefix="full_bench")
            
            # Handle the case when no statuses are selected
            if not selected_statuses:
                st.warning("No statuses selected. No data to display.")
            else:
                # Display bench loads with simplified columns
                display_bench_loads("Full Bench", status_filter=selected_statuses)
                
        # Tab 4: Unscheduled Loads (now fourth tab)
        with tabs[3]:
            st.header("Unscheduled Reactor Loads")
            
            # Display simple date filter and get selected date
            start_date = display_simple_date_filter(key_prefix="unscheduled")
            
            # Get filtered loads directly from database with date filter
            filtered_unscheduled_loads = get_unscheduled_loads(start_date)
            
            # Display count information
            records_count = len(filtered_unscheduled_loads) if not filtered_unscheduled_loads.empty else 0
            st.info(f"Showing {records_count} loads from {start_date} to today")
            
            # Create a copy for display
            if not filtered_unscheduled_loads.empty:
                display_df = filtered_unscheduled_loads.copy()
                
                # Add a selection column
                display_df['Selected'] = False
                
                # Configure columns for display
                display_columns = [
                    'ReactorLoadID', 'LabRequestNumber', 'pcn', 'job_number',
                    'time_submitted', 'created_by', 'request_type', 'sample_count',
                    'test_count', 'test_condition_description'
                ]
                
                # Column order - put Selection first, then other columns
                column_order = ['Selected'] + display_columns
                
                # Configure columns
                column_config = {
                    'Selected': st.column_config.CheckboxColumn("Select", help="Check to select this load"),
                    'ReactorLoadID': st.column_config.NumberColumn("Load ID", disabled=True),
                    'LabRequestNumber': st.column_config.TextColumn("Lab Request #", disabled=True),
                    'pcn': st.column_config.TextColumn("PCN", disabled=True),
                    'job_number': st.column_config.TextColumn("Job #", disabled=True),
                    'time_submitted': st.column_config.TextColumn("Submitted", disabled=True),
                    'created_by': st.column_config.TextColumn("Created By", disabled=True),
                    'request_type': st.column_config.TextColumn("Request Type", disabled=True),
                    'sample_count': st.column_config.NumberColumn("Sample Count", disabled=True),
                    'test_count': st.column_config.NumberColumn("Test Count", disabled=True),
                    'test_condition_description': st.column_config.TextColumn("Test Condition Description", disabled=True)
                }
                
                # Use data_editor with doubled height
                edited_df = st.data_editor(
                    display_df[column_order],
                    use_container_width=True,
                    height=800,  # Doubled height as requested
                    key="unscheduled_editor",
                    column_config=column_config,
                    hide_index=True,
                    column_order=column_order,
                    disabled=[col for col in column_order if col != 'Selected']  # Only Selected is editable
                )
                
                # Get selected rows from the edited dataframe
                selected_indices = edited_df.index[edited_df['Selected']].tolist()
                selected_load_ids = edited_df.loc[selected_indices, 'ReactorLoadID'].tolist() if selected_indices else []
                
                # Display batch operations if loads are selected
                if selected_load_ids:
                    st.markdown(f"""
                    <div style="background-color: #f8f9fa; padding: 15px; border-radius: 10px; 
                                border-left: 5px solid #4CAF50; margin-bottom: 20px;">
                        <h4 style="margin-top: 0; color: #2E7D32;">✅ {len(selected_load_ids)} Loads Selected</h4>
                        <p><strong>Selected Load IDs:</strong> {', '.join(map(str, selected_load_ids))}</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Assignment buttons in a row
                    col1, col2, col3 = st.columns(3)
                    operation_performed = False
                    
                    with col1:
                        if st.button("Assign to Quarter Bench", key="batch_qb_unscheduled", use_container_width=True):
                            try:
                                if batch_assign_testing_area(selected_load_ids, "Quarter Bench"):
                                    st.success(f"Successfully assigned {len(selected_load_ids)} loads to Quarter Bench")
                                    operation_performed = True
                                else:
                                    st.error("Failed to assign loads to Quarter Bench")
                            except Exception as e:
                                st.error(f"Error assigning loads to Quarter Bench: {e}")
                    
                    with col2:
                        if st.button("Assign to Full Bench", key="batch_fb_unscheduled", use_container_width=True):
                            try:
                                if batch_assign_testing_area(selected_load_ids, "Full Bench"):
                                    st.success(f"Successfully assigned {len(selected_load_ids)} loads to Full Bench")
                                    operation_performed = True
                                else:
                                    st.error("Failed to assign loads to Full Bench")
                            except Exception as e:
                                st.error(f"Error assigning loads to Full Bench: {e}")
                    
                    with col3:
                        if st.button("Mark as Cancelled", key="batch_cancel_unscheduled", use_container_width=True):
                            try:
                                if batch_assign_testing_area(selected_load_ids, "Cancelled"):
                                    st.success(f"Successfully marked {len(selected_load_ids)} loads as Cancelled")
                                    operation_performed = True
                                else:
                                    st.error("Failed to mark loads as Cancelled")
                            except Exception as e:
                                st.error(f"Error marking loads as Cancelled: {e}")
                    
                    # If operations were performed, refresh the data
                    if operation_performed:
                        st.cache_data.clear()
                        st.rerun()
                
                # Individual load details in expander
                with st.expander("Individual Load Details", expanded=False):
                    # Create a selectbox for individual load selection
                    load_options = [f"{row['ReactorLoadID']} - {row.get('LabRequestNumber', 'N/A')}" 
                                for idx, row in filtered_unscheduled_loads.iterrows()]
                    
                    selected_load = st.selectbox("Select a load for detailed view:", load_options, key="load_select_unscheduled")
                    if selected_load:
                        load_id = int(selected_load.split(' - ')[0])
                        
                        # Get the row data for this load
                        load_row = filtered_unscheduled_loads[filtered_unscheduled_loads['ReactorLoadID'] == load_id].iloc[0]
                        
                        # Display load details in columns
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.markdown("#### Basic Information")
                            st.write(f"**Load ID:** {load_id}")
                            st.write(f"**Lab Request:** {load_row.get('LabRequestNumber', 'N/A')}")
                            st.write(f"**Job Number:** {load_row.get('job_number', 'N/A')}")
                            st.write(f"**PCN:** {load_row.get('pcn', 'N/A')}")
                            st.write(f"**Submitted:** {load_row.get('time_submitted', 'N/A')}")
                            st.write(f"**Created By:** {load_row.get('created_by', 'N/A')}")
                        
                        with col2:
                            st.markdown("#### Technical Details")
                            st.write(f"**Request Type:** {load_row.get('request_type', 'N/A')}")
                            st.write(f"**Sample Count:** {load_row.get('sample_count', 'N/A')}")
                            st.write(f"**Sample Types:** {load_row.get('sample_types', 'N/A')}")
                            st.write(f"**Test Count:** {load_row.get('test_count', 'N/A')}")
                            st.write(f"**SO2:** {load_row.get('SO2', 'N/A')}")
                            st.write(f"**CO:** {load_row.get('CO', 'N/A')}")
                            st.write(f"**NO:** {load_row.get('NO', 'N/A')}")
                            st.write(f"**NO2:** {load_row.get('NO2', 'N/A')}")
                        
                        # Individual assignment controls
                        st.markdown("#### Assignment")
                        
                        individual_cols = st.columns(3)
                        
                        with individual_cols[0]:
                            if st.button("Assign to Quarter Bench", key=f"ind_qb_{load_id}", use_container_width=True):
                                try:
                                    assign_testing_area(load_id, "Quarter Bench", "Backlog")
                                    st.success(f"Assigned Load {load_id} to Quarter Bench")
                                    st.cache_data.clear()
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error assigning load to Quarter Bench: {e}")
                        
                        with individual_cols[1]:
                            if st.button("Assign to Full Bench", key=f"ind_fb_{load_id}", use_container_width=True):
                                try:
                                    assign_testing_area(load_id, "Full Bench", "Backlog")
                                    st.success(f"Assigned Load {load_id} to Full Bench")
                                    st.cache_data.clear()
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error assigning load to Full Bench: {e}")
                        
                        with individual_cols[2]:
                            if st.button("Mark as Cancelled", key=f"ind_cancel_{load_id}", use_container_width=True):
                                try:
                                    assign_testing_area(load_id, "Cancelled", "Cancelled")
                                    st.success(f"Marked Load {load_id} as Cancelled")
                                    st.cache_data.clear()
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error marking load as Cancelled: {e}")
            else:
                st.info("No unscheduled loads found matching the date filter.")
        
        # Tab 5: Cancelled (now fifth tab)
        with tabs[4]:
            st.header("Cancelled Loads")
            
            # Display status filter checkboxes for Cancelled tab as well
            selected_statuses = display_status_checkboxes(key_prefix="cancelled")
            
            # Handle the case when no statuses are selected
            if not selected_statuses:
                st.warning("No statuses selected. No data to display.")
            else:
                # Display bench loads with simplified columns
                display_bench_loads("Cancelled", status_filter=selected_statuses)
        
        # Tab 6: Priority Scheduler (now sixth tab)
        with tabs[5]:
            st.header("🔄 Backlog Priority Scheduler")
            st.info("This view shows only loads with 'Backlog' status and allows you to set testing priorities by reordering them.")
            
            # Select testing area for priority scheduling
            testing_area = st.selectbox(
                "Select Testing Area", 
                ["Quarter Bench", "Full Bench"],
                key="priority_area_select"
            )
            
            # Display the reordering interface with improved implementation
            display_priority_reordering(testing_area)
    
    except Exception as e:
        st.error(f"An error occurred: {e}")
        st.error("Please make sure the database path is correct and contains the required tables.")

if __name__ == "__main__":
    main()