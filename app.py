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
from plotly.subplots import make_subplots

# ======= Constants =======
DB_PATH = r"C:\Jarvis\Database\lemur_full_clone.db"
STATUS_OPTIONS = ["Backlog", "In Reactor", "Test Complete", "QC Complete", "Report Delivered", "Cancelled"]
TESTING_AREAS = ["Quarter Bench", "Full Bench", "Cancelled"]

# ======= Page Configuration =======
st.set_page_config(
    page_title="Lab Load Scheduler",
    page_icon="🧪",
    layout="wide"
)

# ======= Custom CSS =======
def apply_custom_css():
    """Apply custom CSS styling to enhance the app appearance"""
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
            padding: 10px;
            background-color: #f8f9fa;
            border-radius: 8px;
            border: 1px solid #e9ecef;
        }
        
        /* Success and error message styling */
        .success-message {
            background-color: #E8F5E9;
            color: #2E7D32;
            padding: 10px 15px;
            border-radius: 4px;
            border-left: 5px solid #2E7D32;
            margin: 10px 0;
            font-weight: 500;
        }
        
        .error-message {
            background-color: #FFEBEE;
            color: #C62828;
            padding: 10px 15px;
            border-radius: 4px;
            border-left: 5px solid #C62828;
            margin: 10px 0;
            font-weight: 500;
        }
        
        /* Completion date pill styling */
        .completion-date-pill {
            display: inline-block;
            background-color: #E3F2FD;
            color: #0D47A1;
            padding: 6px 12px;
            border-radius: 20px;
            font-size: 0.9em;
            font-weight: 500;
            margin: 3px;
        }
        
        /* Dashboard card styling */
        .dashboard-card {
            background-color: white;
            border-radius: 8px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            padding: 15px;
            margin-bottom: 20px;
        }
        
        .dashboard-card-header {
            font-size: 1.2em;
            font-weight: 600;
            margin-bottom: 10px;
            color: #333;
        }
        
        .dashboard-stat {
            font-size: 2em;
            font-weight: 700;
            color: #0D47A1;
        }
        
        /* Sidebar styling */
        .sidebar-header {
            font-size: 1.3em;
            font-weight: 600;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 1px solid #e9ecef;
        }
        
        /* Date range quick select buttons */
        .date-quick-select {
            display: inline-block;
            background-color: #f1f3f5;
            color: #495057;
            border: 1px solid #ced4da;
            border-radius: 4px;
            padding: 5px 10px;
            margin: 2px;
            font-size: 0.9em;
            cursor: pointer;
        }
        
        .date-quick-select:hover {
            background-color: #e9ecef;
        }
        
        .date-quick-select.active {
            background-color: #0D47A1;
            color: white;
            border-color: #0D47A1;
        }
    </style>
    """, unsafe_allow_html=True)

# ======= Database Connection and Helper Functions =======
@st.cache_resource
def get_db_connection_pool():
    """
    Create and cache a SQLite database connection for reuse
    
    Returns:
    sqlite3.Connection: Cached database connection
    """
    try:
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        st.error(f"Database connection error: {e}")
        return None

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
            if conn is None:
                return None
            # Call the function with the connection
            return func(conn, *args, **kwargs)
        except sqlite3.OperationalError as e:
            # If the connection is invalid (e.g., "database is locked")
            if "database is locked" in str(e):
                try:
                    # Clear the connection from cache and retry
                    st.cache_resource.clear()
                    conn = get_db_connection_pool()
                    if conn is None:
                        return None
                    return func(conn, *args, **kwargs)
                except Exception as retry_error:
                    st.error(f"Error during connection retry: {retry_error}")
                    return None
            else:
                # For other operational errors, show error and reraise
                st.error(f"Database operation error: {e}")
                return None
        except Exception as e:
            st.error(f"Unexpected error: {e}")
            return None
    return wrapper

def execute_query(conn, query, params=None, fetchall=True):
    """
    Execute a SQL query with proper error handling and return results
    
    Parameters:
    conn (sqlite3.Connection): Database connection
    query (str): SQL query to execute
    params (tuple, list, dict, optional): Parameters to bind to the query
    fetchall (bool): Whether to fetch all results or just one row
    
    Returns:
    list, dict, or None: Query results or None if error occurs
    """
    if conn is None:
        return None
        
    cursor = conn.cursor()
    
    try:
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
            
        if fetchall:
            return cursor.fetchall()
        else:
            return cursor.fetchone()
    except Exception as e:
        st.error(f"Error executing query: {e}")
        return None

def execute_query_to_df(conn, query, params=None):
    """
    Execute a SQL query and return results as a pandas DataFrame
    
    Parameters:
    conn (sqlite3.Connection): Database connection
    query (str): SQL query to execute
    params (tuple, list, dict, optional): Parameters to bind to the query
    
    Returns:
    DataFrame: Query results as DataFrame or empty DataFrame if error occurs
    """
    try:
        if params:
            df = pd.read_sql_query(query, conn, params=params)
        else:
            df = pd.read_sql_query(query, conn)
        return df
    except Exception as e:
        st.error(f"Error executing query to DataFrame: {e}")
        return pd.DataFrame()

def execute_transaction(conn, queries_and_params):
    """
    Execute multiple SQL queries as a transaction
    
    Parameters:
    conn (sqlite3.Connection): Database connection
    queries_and_params (list): List of (query, params) tuples to execute
    
    Returns:
    bool: True if transaction succeeded, False otherwise
    """
    if conn is None:
        return False
        
    cursor = conn.cursor()
    
    try:
        conn.execute("BEGIN TRANSACTION")
        
        for query, params in queries_and_params:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
                
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        st.error(f"Error executing transaction: {e}")
        return False

# ======= Date Helper Functions =======
def get_date_range(range_type, offset=0):
    """
    Get start and end dates for different range types
    
    Parameters:
    range_type (str): Type of date range ('day', 'week', 'month', 'year')
    offset (int): Number of periods to go back from current period
    
    Returns:
    tuple: (start_date, end_date) for the requested range
    """
    today = datetime.now().date()
    
    if range_type == 'day':
        # Specific day
        day = today - timedelta(days=offset)
        return day, day
    
    elif range_type == 'week':
        # Start on Monday, end on Sunday
        current_weekday = today.weekday()  # Monday is 0, Sunday is 6
        days_since_monday = current_weekday
        most_recent_monday = today - timedelta(days=days_since_monday)
        
        # Calculate the start and end dates for the requested week
        week_start = most_recent_monday - timedelta(weeks=offset)
        week_end = week_start + timedelta(days=6)  # Sunday is 6 days after Monday
        
        return week_start, week_end
    
    elif range_type == 'month':
        # Start on 1st of month, end on last day of month
        # Calculate the first day of the current month
        first_day_current_month = date(today.year, today.month, 1)
        
        # Calculate the first day of the requested month
        if offset == 0:
            first_day = first_day_current_month
        else:
            # For past months
            year = today.year
            month = today.month - offset
            
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
    
    elif range_type == 'year':
        # Start on January 1, end on December 31
        year = today.year - offset
        return date(year, 1, 1), date(year, 12, 31)
    
    else:
        # Default to today
        return today, today

# ======= Data Access Layer (SQL Queries Abstracted into Functions) =======
@st.cache_data(ttl=300)  # Cache for 5 minutes
@with_db_connection
def get_reactor_loads(conn, date_range=None):
    """
    Get all reactor loads with optional date filtering
    
    Parameters:
    conn (sqlite3.Connection): Database connection
    date_range (tuple, optional): (start_date, end_date) for filtering
    
    Returns:
    DataFrame: DataFrame containing reactor load information
    """
    if conn is None:
        return pd.DataFrame()
    
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
    
    # Add date range filter if specified
    params = []
    if date_range:
        start_date, end_date = date_range
        query += " AND LR.time_submitted >= ? AND LR.time_submitted <= ?"
        params.append(start_date.strftime('%Y-%m-%d'))
        params.append(end_date.strftime('%Y-%m-%d 23:59:59'))  # Include end date fully
    
    # Add grouping and ordering
    query += """
    GROUP BY RL.id
    ORDER BY LR.time_submitted DESC
    """
    
    # Execute query
    df = execute_query_to_df(conn, query, params if params else None)
    
    # Process time_submitted once
    if 'time_submitted' in df.columns and not df.empty:
        df['time_submitted'] = pd.to_datetime(df['time_submitted'], format='mixed', errors='coerce')
        # Format for display
        df['time_submitted'] = df['time_submitted'].dt.strftime('%Y-%m-%d %H:%M')
    
    return df

@st.cache_data(ttl=300)  # Cache for 5 minutes
@with_db_connection
def get_bench_loads(conn, bench_type, status_filter=None, date_range=None):
    """
    Get loads by bench type with expanded schedule information
    
    Parameters:
    conn (sqlite3.Connection): Database connection
    bench_type (str): Bench type ("Quarter Bench", "Full Bench", or "Cancelled")
    status_filter (list, optional): List of statuses to filter by
    date_range (tuple, optional): (start_date, end_date) for filtering
    
    Returns:
    DataFrame: DataFrame containing loads for the specified bench type
    """
    if conn is None:
        return pd.DataFrame()
    
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
        (SELECT COUNT(DISTINCT RTST_inner.id) 
         FROM ReactorTests RTST_inner 
         LEFT JOIN ReactorTestConditions RTC_inner ON RTST_inner.test_condition_id = RTC_inner.id
         LEFT JOIN TestConditionTypes TCT_inner ON RTC_inner.test_type_id = TCT_inner.id
         WHERE RTST_inner.load_id = RL.id 
         AND (TCT_inner.test_condition_type IS NULL OR TRIM(UPPER(TCT_inner.test_condition_type)) <> 'PRESSURE DROP')
         AND EXISTS (SELECT 1 FROM LoadSchedules LS_inner WHERE LS_inner.load_id = RL.id AND LS_inner.load_start IS NOT NULL)
        ) AS test_count,
        (SELECT GROUP_CONCAT(description, '; ') FROM (SELECT DISTINCT RTC_inner.description FROM ReactorTests RTST_inner 
         LEFT JOIN ReactorTestConditions RTC_inner ON RTST_inner.test_condition_id = RTC_inner.id 
         WHERE RTST_inner.load_id = RL.id)) AS test_condition_description,
        MAX(CASE WHEN RP.reactor_parameter = 'SO2' THEN RTCP.value END) AS SO2,
        MAX(CASE WHEN RP.reactor_parameter = 'CO' THEN RTCP.value END) AS CO,
        MAX(CASE WHEN RP.reactor_parameter = 'NO' THEN RTCP.value END) AS NO,
        MAX(CASE WHEN RP.reactor_parameter = 'NO2' THEN RTCP.value END) AS NO2,
        LB.priority,
        LS.load_start AS start_time,
        LS.load_end AS end_time,
        LS.reactor_id AS reactor
    FROM ReactorLoads RL
    INNER JOIN LabRequests LR ON RL.lab_request_id = LR.id
    INNER JOIN LoadBench LB ON RL.id = LB.load_id
    LEFT JOIN LoadSchedules LS ON RL.id = LS.load_id
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
    
    # Parameters list starting with bench_type
    params = [bench_type]
    
    # Add status filter to SQL if provided
    if status_filter and len(status_filter) > 0:  # Only apply filter if list is non-empty
        placeholders = ', '.join('?' for _ in status_filter)
        query += f" AND LB.status IN ({placeholders})"
        params.extend(status_filter)
    
    # Add date range filter if specified
    if date_range:
        start_date, end_date = date_range
        query += " AND LR.time_submitted >= ? AND LR.time_submitted <= ?"
        params.append(start_date.strftime('%Y-%m-%d'))
        params.append(end_date.strftime('%Y-%m-%d 23:59:59'))  # Include end date fully
    
    # Add grouping and ordering
    query += """
    GROUP BY RL.id
    ORDER BY 
        CASE WHEN LS.load_start IS NULL THEN 1 ELSE 0 END,
        LS.load_start ASC
    """
    
    # Execute query
    df = execute_query_to_df(conn, query, params)
    
    # Process timestamps once
    for time_col in ['time_submitted', 'start_time', 'end_time']:
        if time_col in df.columns and not df.empty:
            df[time_col] = pd.to_datetime(df[time_col], format='mixed', errors='coerce')
            df[time_col] = df[time_col].dt.strftime('%Y-%m-%d %H:%M')
    
    # Update status field for loads without tests - fixed with emptiness checks
    if not df.empty:
        # Initialize display_status column
        df['display_status'] = df['status'].copy()
        
        # For loads with null start_time, set status display to "Not Tested" if status is "Backlog"
        mask = (df['start_time'].isna() | (df['start_time'] == '')) & (df['status'] == 'Backlog')
        if mask.any():
            df.loc[mask, 'display_status'] = 'Not Tested'
        
        # For loads with start_time but no end_time, set status display to "In Reactor" if not already marked as completed
        mask = (df['start_time'].notna() & df['start_time'] != '') & (df['end_time'].isna() | df['end_time'] == '') & (~df['status'].isin(['Test Complete', 'QC Complete', 'Report Delivered']))
        if mask.any():
            df.loc[mask, 'display_status'] = 'In Reactor'
        
        # Fill NaN values in status column
        df['status'].fillna('Backlog', inplace=True)
        
        # Fill NaN values in priority column
        df['priority'].fillna(100, inplace=True)
    else:
        # Create empty columns with proper data types
        df['display_status'] = pd.Series(dtype='object')
        df['status'] = pd.Series(dtype='object')
        df['priority'] = pd.Series(dtype='float')
    
    return df

@st.cache_data(ttl=300)  # Cache for 5 minutes
@with_db_connection
def get_unscheduled_loads(conn, date_range=None):
    """
    Get unscheduled loads with direct SQL filtering
    
    Parameters:
    conn (sqlite3.Connection): Database connection
    date_range (tuple, optional): (start_date, end_date) for filtering
    
    Returns:
    DataFrame: DataFrame containing unscheduled loads
    """
    if conn is None:
        return pd.DataFrame()
    
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
        (SELECT COUNT(DISTINCT TCT_inner.id) FROM ReactorTests RTST_inner LEFT JOIN ReactorTestConditions RTC_inner ON RTST_inner.test_condition_id = RTC_inner.id LEFT JOIN TestConditionTypes TCT_inner ON RTC_inner.test_type_id = TCT_inner.id WHERE RTST_inner.load_id = RL.id AND (TCT_inner.test_condition_type IS NULL OR TRIM(UPPER(TCT_inner.test_condition_type)) <> 'PRESSURE DROP') GROUP BY RTST_inner.load_id) AS test_count,
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
    
    # Add date range filter if specified
    params = []
    if date_range:
        start_date, end_date = date_range
        query += " AND LR.time_submitted >= ? AND LR.time_submitted <= ?"
        params.append(start_date.strftime('%Y-%m-%d'))
        params.append(end_date.strftime('%Y-%m-%d 23:59:59'))  # Include end date fully
    
    # Add grouping and ordering
    query += """
    GROUP BY RL.id
    ORDER BY LR.time_submitted DESC
    """
    
    # Execute query
    df = execute_query_to_df(conn, query, params if params else None)
    
    # Process timestamps once
    if 'time_submitted' in df.columns and not df.empty:
        df['time_submitted'] = pd.to_datetime(df['time_submitted'], format='mixed', errors='coerce')
        df['time_submitted'] = df['time_submitted'].dt.strftime('%Y-%m-%d %H:%M')
    
    return df

@st.cache_data(ttl=300)  # Cache for 5 minutes
@with_db_connection
def get_current_in_reactor_load(conn):
    """
    Get the current load that is in the reactor (has start time but no end time)
    
    Parameters:
    conn (sqlite3.Connection): Database connection
    
    Returns:
    dict: Dictionary containing load information or None if no load is in the reactor
    """
    if conn is None:
        return None
    
    # Query to get current in-reactor load
    query = """
    SELECT 
        RL.id AS ReactorLoadID,
        LR.number AS LabRequestNumber,
        LR.job_number,
        LR.pcn,
        LB.testing_area,
        RT.request_type,
        COUNT(DISTINCT S.id) AS sample_count,
        (SELECT GROUP_CONCAT(sample_type, ', ') FROM (SELECT DISTINCT ST_inner.sample_type FROM ReactorLoadSamples RLS_inner 
         LEFT JOIN LabRequestSample LRS_inner ON RLS_inner.lab_request_sample_id = LRS_inner.id 
         LEFT JOIN Samples S_inner ON LRS_inner.sample_id = S_inner.id 
         LEFT JOIN SampleTypes ST_inner ON S_inner.sample_type_id = ST_inner.id 
         WHERE RLS_inner.load_id = RL.id)) AS sample_types,
        LS.load_start AS start_time,
        LS.reactor_id AS reactor
    FROM ReactorLoads RL
    INNER JOIN LabRequests LR ON RL.lab_request_id = LR.id
    INNER JOIN LoadBench LB ON RL.id = LB.load_id
    INNER JOIN LoadSchedules LS ON RL.id = LS.load_id
    LEFT JOIN RequestTypes RT ON LR.request_type_id = RT.id
    LEFT JOIN ReactorLoadSamples RLS ON RL.id = RLS.load_id
    LEFT JOIN LabRequestSample LRS ON RLS.lab_request_sample_id = LRS.id
    LEFT JOIN Samples S ON LRS.sample_id = S.id
    WHERE LS.load_start IS NOT NULL 
    AND (LS.load_end IS NULL OR LS.load_end = '')
    AND LB.status NOT IN ('Test Complete', 'QC Complete', 'Report Delivered', 'Cancelled')
    GROUP BY RL.id
    ORDER BY LS.load_start DESC
    LIMIT 1
    """
    
    # Execute query
    df = execute_query_to_df(conn, query)
    
    # Return load info
    if df.empty:
        return None
    
    # Process start_time
    if 'start_time' in df.columns:
        df['start_time'] = pd.to_datetime(df['start_time'], format='mixed', errors='coerce')
        df['start_time'] = df['start_time'].dt.strftime('%Y-%m-%d %H:%M')
    
    # Convert first row to dictionary
    load_info = df.iloc[0].to_dict()
    
    return load_info

# ======= Data Modification Functions =======
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
    if conn is None:
        return 100
    
    # Query to get max priority
    query = "SELECT MAX(priority) FROM LoadBench WHERE testing_area = ? AND UPPER(status) = 'BACKLOG'"
    params = (testing_area,)
    
    # Execute query
    result = execute_query(conn, query, params, fetchall=False)
    
    # Return next priority
    max_priority = result[0] if result and result[0] is not None else 99
    return max_priority + 1

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
    if conn is None:
        return {"testing_area": None, "status": None, "priority": 100}
    
    # Query to get load info
    query = "SELECT testing_area, status, priority FROM LoadBench WHERE load_id = ?"
    params = (load_id,)
    
    # Execute query
    result = execute_query(conn, query, params, fetchall=False)
    
    # Return load info
    if result:
        return {
            "testing_area": result[0], 
            "status": result[1] if len(result) > 1 and result[1] else "Backlog",
            "priority": result[2] if len(result) > 2 and result[2] is not None else 100
        }
    else:
        return {"testing_area": None, "status": None, "priority": 100}

@with_db_connection
def assign_testing_area(conn, load_id, testing_area, status=None, priority=None, reactor_id=None):
    """
    Assign a testing area to a load with updated priority logic
    
    Parameters:
    conn (sqlite3.Connection): Database connection
    load_id (int): Load ID to assign
    testing_area (str): Testing area to assign to
    status (str, optional): Status to set (defaults to 'Backlog')
    priority (int, optional): Priority to set
    reactor_id (int, optional): Reactor ID to assign
    
    Returns:
    bool: True if successful, False otherwise
    """
    if conn is None:
        return False
    
    try:
        # Begin transaction
        conn.execute("BEGIN TRANSACTION")
        
        # Check if load is already assigned
        query = "SELECT id, status, priority FROM LoadBench WHERE load_id = ?"
        params = (load_id,)
        existing = execute_query(conn, query, params, fetchall=False)
        
        # Default status to 'Backlog' if not provided
        if status is None:
            status = 'Backlog'
        
        # Priority calculation logic for Backlog status
        if status.upper() == 'BACKLOG' and priority is None:
            # Use centralized function to get next priority
            priority = get_next_backlog_priority(conn, testing_area)
        
        if existing:
            # If no status provided, use existing status or default to 'Backlog'
            if status is None:
                status = existing[1] if existing[1] else 'Backlog'
            
            # If no priority provided and not a Backlog transition, use existing priority
            if priority is None and status.upper() != 'BACKLOG':
                priority = existing[2] if existing[2] is not None else 100
            
            # Update existing assignment
            update_query = "UPDATE LoadBench SET testing_area = ?, assigned_date = DATE('now'), status = ?, priority = ? WHERE load_id = ?"
            update_params = (testing_area, status, priority, load_id)
            execute_query(conn, update_query, update_params, fetchall=False)
        else:
            # Create new assignment with calculated or provided priority
            insert_query = "INSERT INTO LoadBench (load_id, testing_area, assigned_date, status, priority) VALUES (?, ?, DATE('now'), ?, ?)"
            insert_params = (load_id, testing_area, status, priority)
            execute_query(conn, insert_query, insert_params, fetchall=False)
        
        # Update load schedule if status is "In Reactor"
        if status == "In Reactor":
            update_load_schedule(conn, load_id, status, reactor_id)
        
        # Commit transaction
        conn.commit()
        st.success(f"Successfully assigned load {load_id} to {testing_area} with status '{status}'.")
        return True
    
    except Exception as e:
        # Rollback transaction on error
        conn.rollback()
        st.error(f"Error assigning testing area: {e}")
        return False

@with_db_connection
def batch_assign_testing_area(conn, load_ids, testing_area, status=None, reactor_id=None):
    """
    Assign multiple loads to a testing area with updated priority logic
    
    Parameters:
    conn (sqlite3.Connection): Database connection
    load_ids (list): List of load IDs to assign
    testing_area (str): Testing area to assign to
    status (str, optional): Status to set (defaults to 'Backlog')
    reactor_id (int, optional): Reactor ID to assign
    
    Returns:
    bool: True if successful, False otherwise
    """
    if conn is None:
        return False
    
    if not load_ids:
        return False
    
    # Default status to 'Backlog' if not provided
    if status is None:
        status = 'Backlog'
    
    # Begin transaction
    conn.execute("BEGIN TRANSACTION")
    
    try:
        # For backlog status, get the next available priority at the start
        if status.upper() == 'BACKLOG':
            next_priority = get_next_backlog_priority(conn, testing_area)
        
        updated_count = 0
        for load_id in load_ids:
            # Check if load is already assigned
            query = "SELECT id, status, priority FROM LoadBench WHERE load_id = ?"
            params = (load_id,)
            existing = execute_query(conn, query, params, fetchall=False)
            
            if existing:
                current_status = existing[1] if existing[1] else 'Backlog'
                
                # If transitioning to 'Backlog' from non-backlog or new assignment, use calculated priority
                if status.upper() == 'BACKLOG' and current_status.upper() != 'BACKLOG':
                    update_query = "UPDATE LoadBench SET testing_area = ?, assigned_date = DATE('now'), status = ?, priority = ? WHERE load_id = ?"
                    update_params = (testing_area, status, next_priority, load_id)
                    execute_query(conn, update_query, update_params, fetchall=False)
                    # Increment priority for next load if it's backlog
                    next_priority += 1
                else:
                    # Use existing priority if not transitioning to backlog
                    current_priority = existing[2] if existing[2] is not None else 100
                    update_query = "UPDATE LoadBench SET testing_area = ?, assigned_date = DATE('now'), status = ? WHERE load_id = ?"
                    update_params = (testing_area, status, load_id)
                    execute_query(conn, update_query, update_params, fetchall=False)
            else:
                # Create new assignment
                if status.upper() == 'BACKLOG':
                    # Use calculated priority for backlog
                    insert_query = "INSERT INTO LoadBench (load_id, testing_area, assigned_date, status, priority) VALUES (?, ?, DATE('now'), ?, ?)"
                    insert_params = (load_id, testing_area, status, next_priority)
                    execute_query(conn, insert_query, insert_params, fetchall=False)
                    # Increment priority for next load
                    next_priority += 1
                else:
                    # Use default priority for non-backlog
                    insert_query = "INSERT INTO LoadBench (load_id, testing_area, assigned_date, status, priority) VALUES (?, ?, DATE('now'), ?, ?)"
                    insert_params = (load_id, testing_area, status, 100)
                    execute_query(conn, insert_query, insert_params, fetchall=False)
            
            # Update load schedule if status is "In Reactor"
            if status == "In Reactor":
                update_load_schedule(conn, load_id, status, reactor_id)
                
            updated_count += 1
        
        # Commit transaction
        conn.execute("COMMIT")
        
        if updated_count > 0:
            st.success(f"Successfully assigned {updated_count} loads to {testing_area} with status '{status}'.")
        else:
            st.warning("No loads were assigned.")
            
        return True
    
    except Exception as e:
        # Rollback in case of error
        conn.execute("ROLLBACK")
        st.error(f"Error assigning loads: {e}")
        return False

@with_db_connection
def update_load_schedule(conn, load_id, status, reactor_id=None):
    """
    Update load schedule based on status changes
    
    Parameters:
    conn (sqlite3.Connection): Database connection
    load_id (int): Load ID to update
    status (str): New status
    reactor_id (int, optional): Reactor ID to assign
    
    Returns:
    bool: True if successful, False otherwise
    """
    if conn is None:
        return False
    
    try:
        # Check if there's an existing entry
        query = "SELECT id, load_start, load_end FROM LoadSchedules WHERE load_id = ?"
        params = (load_id,)
        result = execute_query(conn, query, params, fetchall=False)
        
        # If transitioning to "In Reactor", set the start time
        if status == "In Reactor":
            if result:
                # Only update start time if it doesn't exist
                if result[1] is None or result[1] == '':
                    if reactor_id is not None:
                        update_query = "UPDATE LoadSchedules SET load_start = CURRENT_TIMESTAMP, reactor_id = ? WHERE load_id = ?"
                        update_params = (reactor_id, load_id)
                    else:
                        update_query = "UPDATE LoadSchedules SET load_start = CURRENT_TIMESTAMP WHERE load_id = ?"
                        update_params = (load_id,)
                    execute_query(conn, update_query, update_params, fetchall=False)
            else:
                # Create new record
                if reactor_id is not None:
                    insert_query = "INSERT INTO LoadSchedules (load_id, load_start, reactor_id) VALUES (?, CURRENT_TIMESTAMP, ?)"
                    insert_params = (load_id, reactor_id)
                else:
                    insert_query = "INSERT INTO LoadSchedules (load_id, load_start) VALUES (?, CURRENT_TIMESTAMP)"
                    insert_params = (load_id,)
                execute_query(conn, insert_query, insert_params, fetchall=False)
        
        # If transitioning to "Test Complete", "QC Complete", or "Report Delivered", set the end time if not already set
        elif status in ["Test Complete", "QC Complete", "Report Delivered"]:
            if result:
                # Check if end time is already set
                if result[2] is None or result[2] == '':
                    # Update end time if not set
                    update_query = "UPDATE LoadSchedules SET load_end = CURRENT_TIMESTAMP WHERE load_id = ?"
                    update_params = (load_id,)
                    execute_query(conn, update_query, update_params, fetchall=False)
            else:
                # If there's no record yet but status is completed, create one with both times (unusual case)
                if reactor_id is not None:
                    insert_query = "INSERT INTO LoadSchedules (load_id, load_start, load_end, reactor_id) VALUES (?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, ?)"
                    insert_params = (load_id, reactor_id)
                else:
                    insert_query = "INSERT INTO LoadSchedules (load_id, load_start, load_end) VALUES (?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
                    insert_params = (load_id,)
                execute_query(conn, insert_query, insert_params, fetchall=False)
        
        return True
    
    except Exception as e:
        st.error(f"Error updating load schedule: {e}")
        return False

@with_db_connection
def update_load_status(conn, load_id, status, reactor_id=None):
    """
    Update load status with priority recalculation for backlog transitions
    
    Parameters:
    conn (sqlite3.Connection): Database connection
    load_id (int): Load ID to update
    status (str): New status
    reactor_id (int, optional): Reactor ID to assign
    
    Returns:
    bool: True if successful, False otherwise
    """
    if conn is None:
        return False
    
    try:
        # Begin transaction
        conn.execute("BEGIN TRANSACTION")
        
        # Get current status and testing area
        query = "SELECT id, status, testing_area FROM LoadBench WHERE load_id = ?"
        params = (load_id,)
        result = execute_query(conn, query, params, fetchall=False)
        
        if result:
            entry_id, current_status, testing_area = result
            
            # If transitioning to Backlog, assign a new priority at the end of the queue
            if status.upper() == 'BACKLOG' and (current_status is None or current_status.upper() != 'BACKLOG'):
                # Use centralized function to get next priority
                next_priority = get_next_backlog_priority(conn, testing_area)
                
                # Update with new status and recalculated priority
                update_query = "UPDATE LoadBench SET status = ?, priority = ? WHERE load_id = ?"
                update_params = (status, next_priority, load_id)
                execute_query(conn, update_query, update_params, fetchall=False)
            else:
                # For other status transitions, just update the status
                update_query = "UPDATE LoadBench SET status = ? WHERE load_id = ?"
                update_params = (status, load_id)
                execute_query(conn, update_query, update_params, fetchall=False)
            
            # Update load schedule based on status change
            update_load_schedule(conn, load_id, status, reactor_id)
            
            # Commit transaction
            conn.commit()
            st.success(f"Updated status for load {load_id} to '{status}'.")
            return True
        else:
            # Cannot update status for non-existing entry
            st.warning(f"Load {load_id} does not exist in LoadBench.")
            conn.rollback()
            return False
    
    except Exception as e:
        # Rollback transaction on error
        conn.rollback()
        st.error(f"Error updating load status: {e}")
        return False

@with_db_connection
def batch_update_status(conn, status_updates, reactor_id=None):
    """
    Batch update statuses with priority recalculation for backlog transitions
    
    Parameters:
    conn (sqlite3.Connection): Database connection
    status_updates (dict): Dictionary mapping load_id to status
    reactor_id (int, optional): Reactor ID to assign
    
    Returns:
    bool: True if successful, False otherwise
    """
    if conn is None:
        return False
    
    if not status_updates:
        return False
    
    # Begin transaction
    conn.execute("BEGIN TRANSACTION")
    
    try:
        updated_count = 0
        for load_id, status in status_updates.items():
            # Get current status and testing area
            query = "SELECT status, testing_area FROM LoadBench WHERE load_id = ?"
            params = (load_id,)
            result = execute_query(conn, query, params, fetchall=False)
            
            if result:
                current_status, testing_area = result
                
                # If transitioning to 'Backlog', assign a new priority at the end of the queue
                if status.upper() == 'BACKLOG' and (current_status is None or current_status.upper() != 'BACKLOG'):
                    # Use centralized function to get next priority
                    next_priority = get_next_backlog_priority(conn, testing_area)
                    
                    # Update with new status and priority
                    update_query = "UPDATE LoadBench SET status = ?, priority = ? WHERE load_id = ?"
                    update_params = (status, next_priority, load_id)
                    execute_query(conn, update_query, update_params, fetchall=False)
                else:
                    # For other status transitions, just update the status
                    update_query = "UPDATE LoadBench SET status = ? WHERE load_id = ?"
                    update_params = (status, load_id)
                    execute_query(conn, update_query, update_params, fetchall=False)
                
                # Update load schedule based on status change
                update_load_schedule(conn, load_id, status, reactor_id)
                updated_count += 1
        
        # Commit transaction
        conn.execute("COMMIT")
        
        if updated_count > 0:
            st.success(f"Successfully updated status for {updated_count} loads.")
        else:
            st.warning("No loads were updated.")
            
        return True
    
    except Exception as e:
        # Rollback in case of error
        conn.execute("ROLLBACK")
        st.error(f"Error updating statuses: {e}")
        return False

@with_db_connection
def unschedule_load(conn, load_id):
    """
    Unschedule a load (remove from LoadBench)
    
    Parameters:
    conn (sqlite3.Connection): Database connection
    load_id (int): Load ID to unschedule
    
    Returns:
    bool: True if successful, False otherwise
    """
    if conn is None:
        return False
    
    try:
        # Delete from LoadBench
        query = "DELETE FROM LoadBench WHERE load_id = ?"
        params = (load_id,)
        result = execute_query(conn, query, params, fetchall=False)
        
        # Check if any rows were affected
        if conn.total_changes > 0:
            st.success(f"Successfully unscheduled load {load_id}.")
            return True
        else:
            st.warning(f"Load {load_id} was not found in the schedule.")
            return False
    
    except Exception as e:
        st.error(f"Error unscheduling load: {e}")
        return False

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
    if conn is None:
        return False
    
    if not load_ids:
        return False
    
    # Begin transaction
    conn.execute("BEGIN TRANSACTION")
    
    try:
        total_deleted = 0
        for load_id in load_ids:
            query = "DELETE FROM LoadBench WHERE load_id = ?"
            params = (load_id,)
            execute_query(conn, query, params, fetchall=False)
            total_deleted += conn.total_changes
        
        # Commit transaction
        conn.execute("COMMIT")
        
        if total_deleted > 0:
            st.success(f"Successfully unscheduled {total_deleted} loads.")
        else:
            st.warning("No loads were unscheduled.")
            
        return True
    
    except Exception as e:
        # Rollback in case of error
        conn.execute("ROLLBACK")
        st.error(f"Error unscheduling loads: {e}")
        return False

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
    if conn is None:
        return False
    
    if df.empty:
        return False
    
    # Begin transaction
    conn.execute("BEGIN TRANSACTION")
    
    try:
        # Update the priorities for each load
        updated_count = 0
        for index, row in df.iterrows():
            load_id = row['load_id']
            new_priority = row['priority']
            
            query = "UPDATE LoadBench SET priority = ? WHERE load_id = ? AND testing_area = ?"
            params = (new_priority, load_id, testing_area)
            execute_query(conn, query, params, fetchall=False)
            updated_count += conn.total_changes
        
        # Commit transaction
        conn.commit()
        
        if updated_count > 0:
            st.success(f"Successfully updated priorities for {updated_count} loads.")
        else:
            st.warning("No priorities were changed.")
            
        return True
    
    except Exception as e:
        # Rollback in case of error
        conn.rollback()
        st.error(f"Error saving priorities: {e}")
        return False

# ======= Helper Functions =======
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

def run_excel_import_script():
    """
    Run the Excel import script using subprocess
    
    Returns:
    tuple: (success, message)
    """
    # Define paths to script and Excel file
    script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "excel_to_db.py")
    excel_path = r"C:\Users\s.jay\OneDrive - Cormetech\Hub\Reactor Loadsv1.xlsm"
    
    try:
        # Show spinner during import
        with st.spinner("Importing data from Excel..."):
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

# ======= UI Components =======
def display_date_range_filter(key_prefix=""):
    """
    Display an enhanced date range filter with predefined options
    
    Parameters:
    key_prefix (str): Prefix for Streamlit widget keys to ensure uniqueness
    
    Returns:
    tuple: (start_date, end_date) selected date range
    """
    # Check if state keys exist, initialize if they don't
    if f"date_range_{key_prefix}" not in st.session_state:
        # Default to last 30 days
        today = datetime.now().date()
        default_start = today - timedelta(days=30)
        st.session_state[f"date_range_{key_prefix}"] = (default_start, today)
    
    if f"date_range_option_{key_prefix}" not in st.session_state:
        st.session_state[f"date_range_option_{key_prefix}"] = "last_30_days"
    
    # Display date filter controls with improved layout
    st.markdown(f"""
    <div class="date-filter-container">
        <span style="font-weight: 600; margin-right: 10px;">Date Range:</span>
    </div>
    """, unsafe_allow_html=True)
    
    # Quick select options and date input in columns
    col1, col2 = st.columns([2, 3])
    
    with col1:
        # Quick select buttons
        st.markdown("#### Quick Select")
        option = st.radio(
            "Select a predefined range:",
            options=[
                "Today",
                "This Week",
                "This Month",
                "Last Month",
                "Last 30 Days",
                "Last 90 Days",
                "This Year",
                "All Time",
                "Custom Range"
            ],
            index=4,  # Default to "Last 30 Days"
            key=f"date_quick_select_{key_prefix}"
        )
    
    with col2:
        st.markdown("#### Date Range")
        # Date input for custom selection
        date_range = st.date_input(
            "Select date range:",
            value=st.session_state[f"date_range_{key_prefix}"],
            key=f"date_input_{key_prefix}"
        )
        
        # Apply button with improved styling
        apply_filter = st.button(
            "Apply Filter",
            key=f"apply_filter_{key_prefix}",
            use_container_width=True
        )
    
    # Get today's date and calculate other dates
    today = datetime.now().date()
    
    # Handle quick select options
    if option != "Custom Range":
        if option == "Today":
            date_range = (today, today)
        elif option == "This Week":
            date_range = get_date_range('week')
        elif option == "This Month":
            date_range = get_date_range('month')
        elif option == "Last Month":
            date_range = get_date_range('month', 1)
        elif option == "Last 30 Days":
            date_range = (today - timedelta(days=30), today)
        elif option == "Last 90 Days":
            date_range = (today - timedelta(days=90), today)
        elif option == "This Year":
            date_range = get_date_range('year')
        elif option == "All Time":
            # Use a very old date as "all time" starting point
            date_range = (datetime(2000, 1, 1).date(), today)
    
    # Ensure date_range is a tuple of two dates
    if isinstance(date_range, tuple) and len(date_range) == 2:
        start_date, end_date = date_range
    else:
        # If a single date is selected, use it as both start and end
        start_date = end_date = date_range
    
    # Update session state if Apply is clicked or a quick option is selected
    if apply_filter or option != "Custom Range":
        st.session_state[f"date_range_{key_prefix}"] = (start_date, end_date)
        st.session_state[f"date_range_option_{key_prefix}"] = option
    
    # Display selected date range
    st.info(f"Selected date range: {start_date} to {end_date}")
    
    return start_date, end_date

def display_status_checkboxes(key_prefix=""):
    """
    Renders a row of checkboxes for each status and returns the list of selected statuses.
    
    Parameters:
    key_prefix (str): Prefix for Streamlit widget keys to ensure uniqueness
    
    Returns:
    list: List of selected status options
    """
    # Initialize session state for the status checkboxes if not already present
    session_key = f"selected_statuses_{key_prefix}"
    if session_key not in st.session_state:
        # Default: all statuses checked except Report Delivered
        st.session_state[session_key] = {status: (status != "Report Delivered") for status in STATUS_OPTIONS}
    
    st.markdown("### Filter by Status")
    
    # Create columns side by side for the checkboxes
    cols = st.columns(len(STATUS_OPTIONS))
    
    # Update session_state based on user interactions
    for idx, status in enumerate(STATUS_OPTIONS):
        # By passing the current value from session_state, we can keep track of toggles
        new_value = cols[idx].checkbox(
            status,
            value=st.session_state[session_key][status],
            key=f"checkbox_{status}_{key_prefix}"
        )
        st.session_state[session_key][status] = new_value
    
    # Build final list of checked statuses
    checked_statuses = [stat for stat, is_checked in st.session_state[session_key].items() if is_checked]
    
    # Handle case when no statuses are selected
    if not checked_statuses:
        st.warning("⚠️ No statuses selected. Please select at least one status to view loads.")
    
    return checked_statuses

def display_unscheduled_loads(date_range=None):
    """
    Display unscheduled loads with options to assign to testing areas
    
    Parameters:
    date_range (tuple, optional): (start_date, end_date) for filtering
    """
    # Get filtered loads
    filtered_unscheduled_loads = get_unscheduled_loads(date_range)
    
    # Display count information
    records_count = len(filtered_unscheduled_loads) if not filtered_unscheduled_loads.empty else 0
    if date_range:
        start_date, end_date = date_range
        st.info(f"Showing {records_count} unscheduled loads from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    else:
        st.info(f"Showing {records_count} unscheduled loads")
    
    if not filtered_unscheduled_loads.empty:
        # Create a copy for display
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
        
        # Use data_editor with improved height
        edited_df = st.data_editor(
            display_df[column_order],
            use_container_width=True,
            height=600,
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
            
            # Allow selection of initial status when assigning
            st.markdown("#### Select Initial Status")
            initial_status = st.radio(
                "Set initial status for selected loads:",
                options=STATUS_OPTIONS,
                index=0,  # Default to "Backlog"
                horizontal=True,
                key="initial_status_unscheduled"
            )
            
            # Optional reactor ID input for In Reactor status
            reactor_id = None
            if initial_status == "In Reactor":
                reactor_id_input = st.text_input(
                    "Reactor ID (optional):",
                    key="reactor_id_unscheduled"
                )
                # Convert to int or None
                reactor_id = int(reactor_id_input) if reactor_id_input and reactor_id_input.strip().isdigit() else None
            
            with col1:
                if st.button("Assign to Quarter Bench", key="batch_qb_unscheduled", use_container_width=True):
                    try:
                        if batch_assign_testing_area(selected_load_ids, "Quarter Bench", initial_status, reactor_id):
                            operation_performed = True
                        else:
                            st.error("Failed to assign loads to Quarter Bench")
                    except Exception as e:
                        st.error(f"Error assigning loads to Quarter Bench: {e}")
            
            with col2:
                if st.button("Assign to Full Bench", key="batch_fb_unscheduled", use_container_width=True):
                    try:
                        if batch_assign_testing_area(selected_load_ids, "Full Bench", initial_status, reactor_id):
                            operation_performed = True
                        else:
                            st.error("Failed to assign loads to Full Bench")
                    except Exception as e:
                        st.error(f"Error assigning loads to Full Bench: {e}")
            
            with col3:
                if st.button("Mark as Cancelled", key="batch_cancel_unscheduled", use_container_width=True):
                    try:
                        if batch_assign_testing_area(selected_load_ids, "Cancelled", "Cancelled"):
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
                
                # Allow selection of initial status
                status = st.radio(
                    "Set status:",
                    options=STATUS_OPTIONS,
                    index=0,  # Default to "Backlog"
                    horizontal=True,
                    key=f"status_select_{load_id}_unscheduled"
                )
                
                # Optional reactor ID input for In Reactor status
                reactor_id = None
                if status == "In Reactor":
                    reactor_id_input = st.text_input(
                        "Reactor ID (optional):",
                        key=f"reactor_id_{load_id}_unscheduled"
                    )
                    # Convert to int or None
                    reactor_id = int(reactor_id_input) if reactor_id_input and reactor_id_input.strip().isdigit() else None
                
                individual_cols = st.columns(3)
                
                with individual_cols[0]:
                    if st.button("Assign to Quarter Bench", key=f"ind_qb_{load_id}", use_container_width=True):
                        try:
                            assign_testing_area(load_id, "Quarter Bench", status, None, reactor_id)
                            st.cache_data.clear()
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error assigning load to Quarter Bench: {e}")
                
                with individual_cols[1]:
                    if st.button("Assign to Full Bench", key=f"ind_fb_{load_id}", use_container_width=True):
                        try:
                            assign_testing_area(load_id, "Full Bench", status, None, reactor_id)
                            st.cache_data.clear()
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error assigning load to Full Bench: {e}")
                
                with individual_cols[2]:
                    if st.button("Mark as Cancelled", key=f"ind_cancel_{load_id}", use_container_width=True):
                        try:
                            assign_testing_area(load_id, "Cancelled", "Cancelled")
                            st.cache_data.clear()
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error marking load as Cancelled: {e}")
    else:
        st.info("No unscheduled loads found matching the date filter.")

def display_bench_loads(bench_type, status_filter=None, date_range=None):
    """
    Display loads for a specific bench type with simplified columns and expandable details
    
    Parameters:
    bench_type (str): Bench type ("Quarter Bench", "Full Bench", or "Cancelled")
    status_filter (list, optional): List of statuses to filter by
    date_range (tuple, optional): (start_date, end_date) for filtering
    """
    # Get loads for the bench type
    df = get_bench_loads(bench_type, status_filter, date_range)
    
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
        'start_time', 'end_time'
    ]
    
    # Add reactor column
    display_columns = common_columns.copy()
    display_columns.append('reactor')
    
    # Ensure all display columns exist in the dataframe
    for col in display_columns:
        if col not in display_df.columns:
            display_df[col] = None
    
    # Column order - put Selection first, then the display columns
    column_order = ['Selected'] + display_columns
    
    # Configure columns
    column_config = {
        'Selected': st.column_config.CheckboxColumn("Select", help="Check to select this load", width="small"),
        'ReactorLoadID': st.column_config.NumberColumn("Load ID", disabled=True, width="small"),
        'status': st.column_config.SelectboxColumn("Status", options=STATUS_OPTIONS, width="medium"),
        'LabRequestNumber': st.column_config.TextColumn("Lab Request #", disabled=True, width="medium"),
        'pcn': st.column_config.TextColumn("PCN", disabled=True, width="small"),
        'request_type': st.column_config.TextColumn("Request Type", disabled=True, width="medium"),
        'sample_count': st.column_config.NumberColumn("Sample Count", disabled=True, width="small"),
        'test_count': st.column_config.NumberColumn("Test Count", disabled=True, width="small"),
        'test_condition_description': st.column_config.TextColumn("Test Condition Description", disabled=True, width="large"),
        'start_time': st.column_config.TextColumn("Start Time", disabled=True, width="medium"),
        'end_time': st.column_config.TextColumn("End Time", disabled=True, width="medium"),
        'priority': st.column_config.NumberColumn("Priority", disabled=True, width="small"),
        'reactor': st.column_config.TextColumn("Reactor", disabled=True, width="small")
    }
    
    # Save original statuses to detect changes
    original_statuses = {}
    if 'status' in display_df.columns and 'ReactorLoadID' in display_df.columns:
        original_statuses = display_df.set_index('ReactorLoadID')['status'].to_dict()
    
    # Use data_editor with improved height
    editor_key = f"{bench_type.lower().replace(' ', '_')}_editor"
    edited_df = st.data_editor(
        display_df[column_order],
        use_container_width=True,
        height=600,
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
                        operation_performed = True
                    else:
                        st.error("Failed to move loads to Quarter Bench")
                except Exception as e:
                    st.error(f"Error moving loads to Quarter Bench: {e}")
        
        with col2:
            if bench_type != "Full Bench" and st.button("Move to Full Bench", key=f"batch_fb_{bench_type}", use_container_width=True):
                try:
                    if batch_assign_testing_area(selected_load_ids, "Full Bench"):
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
                        operation_performed = True
                    else:
                        st.error("Failed to mark loads as Cancelled")
                except Exception as e:
                    st.error(f"Error marking loads as Cancelled: {e}")
        
        if st.button("Unschedule Selected Loads", key=f"batch_unschedule_{bench_type}", use_container_width=True):
            try:
                if batch_unschedule_loads(selected_load_ids):
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
                    st.write(f"**Lab Request:** {load_row.get('LabRequestNumber',