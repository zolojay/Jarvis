import os
import sqlite3
import pandas as pd
import streamlit as st
from datetime import datetime
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, JsCode

# Database path
DB_PATH = r"C:\Jarvis\Database\lemur_full_clone.db"

# Page configuration
st.set_page_config(
    page_title="Lab Load Scheduler",
    page_icon="🧪",
    layout="wide"
)

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
    </style>
    """, unsafe_allow_html=True)

# Create connection to SQLite database
def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# Initialize LoadBench table if it doesn't exist and ensure priority column exists
def init_loadbench_table():
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
    
    # Check if status column exists in LoadBench table
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(LoadBench)")
    columns = cursor.fetchall()
    status_exists = any(column[1] == 'status' for column in columns)
    
    # Add status column if it doesn't exist
    if not status_exists:
        try:
            cursor.execute("ALTER TABLE LoadBench ADD COLUMN status TEXT DEFAULT 'Backlog'")
            st.success("Status column added to LoadBench table.")
        except sqlite3.OperationalError:
            # Column might already exist
            pass
    
    # Check if priority column exists in LoadBench table
    priority_exists = any(column[1] == 'priority' for column in columns)
    
    # Add priority column if it doesn't exist
    if not priority_exists:
        try:
            cursor.execute("ALTER TABLE LoadBench ADD COLUMN priority INTEGER DEFAULT 100")
            st.success("Priority column added to LoadBench table.")
        except sqlite3.OperationalError:
            # Column might already exist
            pass
    
    conn.commit()
    conn.close()

# Function to save updated priorities to the database
def save_new_priorities(df, db_path=DB_PATH):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        conn.execute("BEGIN TRANSACTION")
        for _, row in df.iterrows():
            cursor.execute(
                "UPDATE LoadBench SET priority = ? WHERE load_id = ?",
                (row['priority'], row['ReactorLoadID'])
            )
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        st.error(f"Error saving priorities: {e}")
        return False
    finally:
        conn.close()

# Get all reactor loads
def get_reactor_loads():
    conn = get_db_connection()
    
    # The provided SQL query with minor modifications for SQLite compatibility
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
        (SELECT COUNT(DISTINCT TCT_inner.id) FROM ReactorTests RTST_inner LEFT JOIN ReactorTestConditions RTC_inner ON RTST_inner.test_condition_id = RTC_inner.id LEFT JOIN TestConditionTypes TCT_inner ON RTC_inner.test_type_id = TCT_inner.id WHERE RTST_inner.load_id = RL.id AND (TCT_inner.test_condition_type IS NULL OR TRIM(UPPER(TCT_inner.test_condition_type)) <> 'PRESSURE DROP')) AS test_condition_count,
        (SELECT GROUP_CONCAT(test_condition_type, ', ') FROM (SELECT DISTINCT TCT_inner.test_condition_type FROM ReactorTests RTST_inner LEFT JOIN ReactorTestConditions RTC_inner ON RTST_inner.test_condition_id = RTC_inner.id LEFT JOIN TestConditionTypes TCT_inner ON RTC_inner.test_type_id = TCT_inner.id WHERE RTST_inner.load_id = RL.id AND (TCT_inner.test_condition_type IS NULL OR TRIM(UPPER(TCT_inner.test_condition_type)) <> 'PRESSURE DROP'))) AS test_conditions,
        (SELECT GROUP_CONCAT(description, '; ') FROM (SELECT DISTINCT RTC_inner.description FROM ReactorTests RTST_inner LEFT JOIN ReactorTestConditions RTC_inner ON RTST_inner.test_condition_id = RTC_inner.id LEFT JOIN TestConditionTypes TCT_inner ON RTC_inner.test_type_id = TCT_inner.id WHERE RTST_inner.load_id = RL.id AND (TCT_inner.test_condition_type IS NULL OR TRIM(UPPER(TCT_inner.test_condition_type)) <> 'PRESSURE DROP'))) AS testconditiondescription,
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
    WHERE TCT.test_condition_type IS NULL OR TRIM(UPPER(TCT.test_condition_type)) <> 'PRESSURE DROP'
    GROUP BY RL.id
    ORDER BY LR.time_submitted DESC
    """
    
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    # Format the timestamp column - Use a more flexible parsing approach
    if 'time_submitted' in df.columns and not df.empty:
        # Handle timestamp conversion with flexible format
        df['time_submitted'] = pd.to_datetime(df['time_submitted'], format='mixed', errors='coerce')
        # Format for display
        df['time_submitted'] = df['time_submitted'].dt.strftime('%Y-%m-%d %H:%M')
    
    return df

# Get assigned testing area, status, and priority for a load
def get_load_info(load_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT testing_area, status, priority FROM LoadBench WHERE load_id = ?", (load_id,))
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return {
            "testing_area": result[0], 
            "status": result[1] if len(result) > 1 and result[1] else "Backlog",
            "priority": result[2] if len(result) > 2 and result[2] is not None else 100
        }
    else:
        return {"testing_area": None, "status": None, "priority": 100}

# Get testing area for a load (for backward compatibility)
def get_testing_area(load_id):
    load_info = get_load_info(load_id)
    return load_info["testing_area"]

# Get status for a load
def get_load_status(load_id):
    load_info = get_load_info(load_id)
    return load_info["status"] or "Backlog"

# Get priority for a load
def get_load_priority(load_id):
    load_info = get_load_info(load_id)
    return load_info["priority"] or 100

# Load scheduled loads for a specific testing area with priority ordering
def load_scheduled_loads(testing_area, status_filter=None):
    conn = get_db_connection()
    
    if status_filter:
        query = """
        SELECT lb.load_id as ReactorLoadID, lb.priority, lb.status, 
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
        SELECT lb.load_id as ReactorLoadID, lb.priority, lb.status, 
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
    
    conn.close()
    return df

# Get loads by testing area with priority order
def get_loads_by_testing_area(testing_area):
    conn = get_db_connection()
    
    # Get all reactor loads
    all_loads = get_reactor_loads()
    
    # Query to get loads for a specific testing area
    query = """
    SELECT load_id, status, priority FROM LoadBench
    WHERE testing_area = ?
    ORDER BY priority ASC
    """
    
    area_loads = pd.read_sql_query(query, conn, params=(testing_area,))
    conn.close()
    
    # Filter the loads by those assigned to the testing area
    if not area_loads.empty and not all_loads.empty:
        filtered_loads = all_loads[all_loads['ReactorLoadID'].isin(area_loads['load_id'])]
        
        # Add status and priority columns
        if 'status' in area_loads.columns:
            # Create a mapping of load_id to status
            status_map = dict(zip(area_loads['load_id'], area_loads['status']))
            # Apply the mapping to add status column to filtered_loads
            filtered_loads['status'] = filtered_loads['ReactorLoadID'].map(status_map)
            # Fill NaN values with 'Backlog'
            filtered_loads['status'].fillna('Backlog', inplace=True)
        
        if 'priority' in area_loads.columns:
            # Create a mapping of load_id to priority
            priority_map = dict(zip(area_loads['load_id'], area_loads['priority']))
            # Apply the mapping to add priority column to filtered_loads
            filtered_loads['priority'] = filtered_loads['ReactorLoadID'].map(priority_map)
            # Fill NaN values with default priority
            filtered_loads['priority'].fillna(100, inplace=True)
            
            # Sort by priority
            filtered_loads = filtered_loads.sort_values('priority')
        
        return filtered_loads
    else:
        # Return empty DataFrame with same columns if either is empty
        return pd.DataFrame(columns=all_loads.columns if not all_loads.empty else ["ReactorLoadID"])

# Get unscheduled loads (not in LoadBench)
def get_unscheduled_loads():
    conn = get_db_connection()
    
    # Get all reactor loads
    all_loads = get_reactor_loads()
    
    # Query to get all assigned loads
    query = """
    SELECT load_id FROM LoadBench
    """
    
    assigned_loads = pd.read_sql_query(query, conn)
    conn.close()
    
    # Filter out loads that are already assigned
    if not assigned_loads.empty and not all_loads.empty:
        unscheduled_loads = all_loads[~all_loads['ReactorLoadID'].isin(assigned_loads['load_id'])]
        return unscheduled_loads
    else:
        # If no loads are assigned or no loads exist, return appropriate dataframe
        return all_loads if not all_loads.empty else pd.DataFrame(columns=["ReactorLoadID"])

# Assign a testing area to a load with updated priority logic for backlog status
def assign_testing_area(load_id, testing_area, status=None, priority=None):
    conn = get_db_connection()
    
    # Check if load is already assigned
    cursor = conn.cursor()
    cursor.execute("SELECT id, status, priority FROM LoadBench WHERE load_id = ?", (load_id,))
    existing = cursor.fetchone()
    
    # Default status to 'Backlog' if not provided
    if status is None:
        status = 'Backlog'
    
    # Priority calculation logic for Backlog status
    if status.upper() == 'BACKLOG' and priority is None:
        # If transitioning to Backlog or new Backlog assignment, assign next priority
        cursor.execute(
            "SELECT MAX(priority) FROM LoadBench WHERE testing_area = ? AND UPPER(status) = 'BACKLOG'",
            (testing_area,)
        )
        max_priority = cursor.fetchone()[0]
        priority = (max_priority + 1) if max_priority is not None else 100
    
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
    conn.close()
    return True

# Update load status with priority recalculation for backlog transitions
def update_load_status(load_id, status):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get current status and testing area
    cursor.execute("SELECT id, status, testing_area FROM LoadBench WHERE load_id = ?", (load_id,))
    result = cursor.fetchone()
    
    if result:
        entry_id, current_status, testing_area = result
        
        # If transitioning to Backlog, assign a new priority at the end of the queue
        if status.upper() == 'BACKLOG' and (current_status is None or current_status.upper() != 'BACKLOG'):
            # Get max priority for backlog items in this testing area
            cursor.execute(
                "SELECT MAX(priority) FROM LoadBench WHERE testing_area = ? AND UPPER(status) = 'BACKLOG'",
                (testing_area,)
            )
            max_priority = cursor.fetchone()[0]
            next_priority = (max_priority + 1) if max_priority is not None else 100
            
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
        conn.close()
        return True
    else:
        # Cannot update status for non-existing entry
        conn.close()
        return False

# Batch update statuses with priority recalculation for backlog transitions
def batch_update_status(status_updates):
    if not status_updates:
        return False
    
    conn = get_db_connection()
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
                    # Get maximum priority for backlog items in this testing area
                    cursor.execute(
                        "SELECT MAX(priority) FROM LoadBench WHERE testing_area = ? AND UPPER(status) = 'BACKLOG'",
                        (testing_area,)
                    )
                    max_priority = cursor.fetchone()[0]
                    next_priority = (max_priority + 1) if max_priority is not None else 100
                    
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
        conn.close()
        return True
    
    except Exception as e:
        # Rollback in case of error
        conn.execute("ROLLBACK")
        conn.close()
        st.error(f"Error updating statuses: {e}")
        return False

# Assign multiple loads to a testing area with updated priority logic
def batch_assign_testing_area(load_ids, testing_area, status=None):
    if not load_ids:
        return False
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Default status to 'Backlog' if not provided
    if status is None:
        status = 'Backlog'
    
    # Begin transaction
    conn.execute("BEGIN TRANSACTION")
    
    try:
        # For backlog status, get the next available priority at the start
        if status.upper() == 'BACKLOG':
            cursor.execute(
                "SELECT MAX(priority) FROM LoadBench WHERE testing_area = ? AND UPPER(status) = 'BACKLOG'",
                (testing_area,)
            )
            max_priority = cursor.fetchone()[0]
            next_priority = (max_priority + 1) if max_priority is not None else 100
        
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
        conn.close()
        return True
    
    except Exception as e:
        # Rollback in case of error
        conn.execute("ROLLBACK")
        conn.close()
        st.error(f"Error assigning loads: {e}")
        return False

# Unschedule a load (remove from LoadBench)
def unschedule_load(load_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM LoadBench WHERE load_id = ?", (load_id,))
    conn.commit()
    conn.close()
    return True

# Unschedule multiple loads
def batch_unschedule_loads(load_ids):
    if not load_ids:
        return False
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Begin transaction
    conn.execute("BEGIN TRANSACTION")
    
    try:
        for load_id in load_ids:
            cursor.execute("DELETE FROM LoadBench WHERE load_id = ?", (load_id,))
        
        # Commit transaction
        conn.execute("COMMIT")
        conn.close()
        return True
    
    except Exception as e:
        # Rollback in case of error
        conn.execute("ROLLBACK")
        conn.close()
        st.error(f"Error unscheduling loads: {e}")
        return False

# Display load dataframe with multi-row selection, batch assignment capability, and status editing
def display_load_dataframe_with_batch_assignment(df, is_scheduled=False, key_prefix=""):
    """
    Display load dataframe with multi-row selection, batch assignment capability, and status editing using st.data_editor
    
    Parameters:
    df (DataFrame): DataFrame containing load information
    is_scheduled (bool): Whether these loads are already scheduled (affects UI elements)
    key_prefix (str): Prefix for Streamlit widget keys to ensure uniqueness
    """
    if df.empty:
        st.info("No loads to display.")
        return
    
    # Create a copy for display
    display_df = df.copy()
    
    # Select columns for display
    display_columns = [
        'ReactorLoadID', 'LabRequestNumber', 'job_number', 'pcn', 
        'time_submitted', 'created_by', 'request_type', 'sample_count',
        'sample_types', 'test_condition_count', 'test_conditions',
        'SO2', 'CO', 'NO', 'NO2'
    ]
    
    # Add status column if it exists in df or for scheduled loads
    if 'status' in display_df.columns:
        display_columns.append('status')
    elif is_scheduled:
        # If status is not in df but loads are scheduled, fetch statuses
        status_dict = {}
        for load_id in display_df['ReactorLoadID'].unique():
            status_dict[load_id] = get_load_status(load_id)
        
        display_df['status'] = display_df['ReactorLoadID'].map(status_dict)
        display_df['status'].fillna('Backlog', inplace=True)
        display_columns.append('status')
    
    # Ensure all columns exist
    for col in display_columns:
        if col not in display_df.columns:
            display_df[col] = None
    
    # Add a selection column
    display_df['Selected'] = False
    
    # Display batch assignment header (removed instructional text as per PRD)
    st.subheader("Batch Assignment")
    
    try:
        # Define allowed status options
        status_options = ["Backlog", "In Reactor", "Test Complete", "QC Complete", "Report Delivered"]
        
        # Configure columns with column_config
        column_config = {
            'Selected': st.column_config.CheckboxColumn("Select", help="Check to select this load"),
            'ReactorLoadID': st.column_config.NumberColumn("Load ID", disabled=True),
            'LabRequestNumber': st.column_config.TextColumn("Lab Request #", disabled=True),
            'job_number': st.column_config.TextColumn("Job #", disabled=True),
            'pcn': st.column_config.TextColumn("PCN", disabled=True),
            'time_submitted': st.column_config.TextColumn("Submitted", disabled=True),
            'created_by': st.column_config.TextColumn("Created By", disabled=True),
            'request_type': st.column_config.TextColumn("Request Type", disabled=True),
            'sample_count': st.column_config.NumberColumn("Sample Count", disabled=True),
            'sample_types': st.column_config.TextColumn("Sample Types", disabled=True),
            'test_condition_count': st.column_config.NumberColumn("Test Count", disabled=True),
            'test_conditions': st.column_config.TextColumn("Test Conditions", disabled=True),
            'SO2': st.column_config.NumberColumn("SO2", disabled=True),
            'CO': st.column_config.NumberColumn("CO", disabled=True),
            'NO': st.column_config.NumberColumn("NO", disabled=True),
            'NO2': st.column_config.NumberColumn("NO2", disabled=True)
        }
        
        # Add status column configuration if this is a scheduled view
        if is_scheduled and 'status' in display_df.columns:
            column_config['status'] = st.column_config.SelectboxColumn(
                "Status", 
                options=status_options,
                help="Current processing status"
            )
        
        # Column order - put Selection first, then ID, etc.
        column_order = ['Selected'] + display_columns
        
        # Disable all columns except Selected and status (if scheduled)
        disabled_columns = [col for col in display_columns if col != 'status']
        
        # Save original statuses to detect changes
        if is_scheduled:
            original_statuses = display_df.set_index('ReactorLoadID')['status'].to_dict() if 'status' in display_df.columns else {}
        
        # Use data_editor with a unique key
        editor_key = f"{key_prefix}_load_editor"
        edited_df = st.data_editor(
            display_df[column_order],
            use_container_width=True,
            height=400,
            key=editor_key,
            column_config=column_config,
            hide_index=True,
            column_order=column_order,
            disabled=disabled_columns  # Disable all columns except Selected (and status if scheduled)
        )
        
        # Get selected rows from the edited dataframe
        selected_indices = edited_df.index[edited_df['Selected']].tolist()
        selected_load_ids = edited_df.loc[selected_indices, 'ReactorLoadID'].tolist() if selected_indices else []
        
        # Check for status changes in scheduled view
        if is_scheduled and 'status' in edited_df.columns:
            status_updates = {}
            
            # Compare current statuses with original
            for idx, row in edited_df.iterrows():
                load_id = row['ReactorLoadID']
                new_status = row['status']
                
                # Check if this load_id was in our original data and if status changed
                if load_id in original_statuses and original_statuses[load_id] != new_status:
                    status_updates[load_id] = new_status
            
            # If there are status changes, show a save button
            if status_updates:
                if st.button("Save Status Changes", key=f"save_status_{key_prefix}", use_container_width=True):
                    if batch_update_status(status_updates):
                        st.success(f"Successfully updated {len(status_updates)} load statuses")
                        st.rerun()
                    else:
                        st.error("Failed to update statuses")
        
        # Batch assignment section
        st.markdown("---")
        
        if selected_load_ids:
            # Create a visually distinct selection summary
            st.markdown(f"""
            <div style="background-color: #f8f9fa; padding: 15px; border-radius: 10px; 
                        border-left: 5px solid #4CAF50; margin-bottom: 20px;">
                <h4 style="margin-top: 0; color: #2E7D32;">✅ {len(selected_load_ids)} Loads Selected</h4>
                <p><strong>Selected Load IDs:</strong> {', '.join(map(str, selected_load_ids))}</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Assignment buttons in a row
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("Quarter Bench", key=f"batch_qb_{key_prefix}", use_container_width=True):
                    try:
                        if batch_assign_testing_area(selected_load_ids, "Quarter Bench"):
                            st.success(f"Successfully assigned {len(selected_load_ids)} loads to Quarter Bench")
                            st.rerun()
                        else:
                            st.error("Failed to assign loads to Quarter Bench")
                    except Exception as e:
                        st.error(f"Error assigning loads to Quarter Bench: {e}")
            
            with col2:
                if st.button("Full Bench", key=f"batch_fb_{key_prefix}", use_container_width=True):
                    try:
                        if batch_assign_testing_area(selected_load_ids, "Full Bench"):
                            st.success(f"Successfully assigned {len(selected_load_ids)} loads to Full Bench")
                            st.rerun()
                        else:
                            st.error("Failed to assign loads to Full Bench")
                    except Exception as e:
                        st.error(f"Error assigning loads to Full Bench: {e}")
            
            with col3:
                if st.button("Cancelled", key=f"batch_cancel_{key_prefix}", use_container_width=True):
                    try:
                        if batch_assign_testing_area(selected_load_ids, "Cancelled"):
                            st.success(f"Successfully marked {len(selected_load_ids)} loads as Cancelled")
                            st.rerun()
                        else:
                            st.error("Failed to mark loads as Cancelled")
                    except Exception as e:
                        st.error(f"Error marking loads as Cancelled: {e}")
            
            # Add unschedule button for scheduled views
            if is_scheduled:
                if st.button("Unschedule Selected Loads", key=f"batch_unschedule_{key_prefix}", use_container_width=True):
                    try:
                        if batch_unschedule_loads(selected_load_ids):
                            st.success(f"Successfully unscheduled {len(selected_load_ids)} loads")
                            st.rerun()
                        else:
                            st.error("Failed to unschedule loads")
                    except Exception as e:
                        st.error(f"Error unscheduling loads: {e}")
        else:
            st.info("No loads selected.")
        
        # Individual load details section (kept for backward compatibility)
        with st.expander("Individual Load Details", expanded=False):
            if not display_df.empty:
                try:
                    # Create a selectbox for individual load selection
                    load_options = [f"{row['ReactorLoadID']} - {row.get('LabRequestNumber', 'N/A')}" 
                                 for idx, row in display_df.iterrows()]
                    
                    selected_load = st.selectbox("Select a load for detailed view:", load_options, key=f"load_select_{key_prefix}")
                    if selected_load:
                        load_id = int(selected_load.split(' - ')[0])
                        
                        # Get current load info
                        load_info = get_load_info(load_id)
                        current_area = load_info["testing_area"]
                        current_status = load_info["status"] or "Backlog"
                        
                        # Display current assignment and status if any
                        if current_area:
                            st.success(f"Currently assigned to: {current_area}")
                            st.success(f"Current status: {current_status}")
                        else:
                            st.info("Currently unscheduled")
                        
                        # Get the row data for this load
                        load_row = display_df[display_df['ReactorLoadID'] == load_id].iloc[0]
                        
                        # Display load details
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
                            st.write(f"**Test Conditions:** {load_row.get('test_conditions', 'N/A')}")
                            
                            # Add status selection for individual loads
                            if current_area:  # Only show for scheduled loads
                                new_status = st.selectbox(
                                    "Update Status:",
                                    options=["Backlog", "In Reactor", "Test Complete", "QC Complete", "Report Delivered"],
                                    index=["Backlog", "In Reactor", "Test Complete", "QC Complete", "Report Delivered"].index(current_status) if current_status in ["Backlog", "In Reactor", "Test Complete", "QC Complete", "Report Delivered"] else 0,
                                    key=f"status_select_{load_id}_{key_prefix}"
                                )
                                
                                if new_status != current_status and st.button("Update Status", key=f"update_status_{load_id}_{key_prefix}"):
                                    if update_load_status(load_id, new_status):
                                        st.success(f"Updated Load {load_id} status to {new_status}")
                                        st.rerun()
                                    else:
                                        st.error(f"Failed to update status for Load {load_id}")
                        
                        # Individual assignment controls
                        st.markdown("#### Individual Assignment")
                        
                        individual_cols = st.columns(4)
                        
                        with individual_cols[0]:
                            if st.button("Quarter Bench", key=f"ind_qb_{load_id}_{key_prefix}", use_container_width=True):
                                try:
                                    assign_testing_area(load_id, "Quarter Bench", current_status if current_area else None)
                                    st.success(f"Assigned Load {load_id} to Quarter Bench")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error assigning load to Quarter Bench: {e}")
                        
                        with individual_cols[1]:
                            if st.button("Full Bench", key=f"ind_fb_{load_id}_{key_prefix}", use_container_width=True):
                                try:
                                    assign_testing_area(load_id, "Full Bench", current_status if current_area else None)
                                    st.success(f"Assigned Load {load_id} to Full Bench")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error assigning load to Full Bench: {e}")
                        
                        with individual_cols[2]:
                            if st.button("Cancelled", key=f"ind_c_{load_id}_{key_prefix}", use_container_width=True):
                                try:
                                    assign_testing_area(load_id, "Cancelled", current_status if current_area else None)
                                    st.success(f"Marked Load {load_id} as Cancelled")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error marking load as Cancelled: {e}")
                        
                        with individual_cols[3]:
                            if current_area and st.button("Unschedule", key=f"ind_un_{load_id}_{key_prefix}", use_container_width=True):
                                try:
                                    unschedule_load(load_id)
                                    st.success(f"Unscheduled Load {load_id}")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error unscheduling load: {e}")
                except Exception as e:
                    st.error(f"Error displaying individual load details: {e}")
    
    except Exception as e:
        st.error(f"Error displaying load dataframe: {e}")

# Display load dataframe with drag-and-drop priority reordering using AgGrid - UPDATED FOR BACKLOG ONLY
def display_priority_reordering(testing_area):
    """
    Display load dataframe with drag-and-drop priority reordering using AgGrid
    Only shows loads with 'Backlog' status
    
    Parameters:
    testing_area (str): The testing area to display loads for
    """
    # Load the data for the selected testing area with 'Backlog' status only
    df = load_scheduled_loads(testing_area, status_filter='Backlog')
    
    if df.empty:
        st.info(f"No backlog loads scheduled for {testing_area}.")
        return
    
    # Sort by priority
    df = df.sort_values('priority')
    
    # Ensure priority column exists
    if 'priority' not in df.columns:
        df['priority'] = range(1, len(df) + 1)
    
    # Select and reorder columns for display
    display_columns = [
        'ReactorLoadID', 'LabRequestNumber', 'job_number', 'pcn', 
        'created_by', 'status', 'priority'
    ]
    
    # Only include columns that exist in df
    display_columns = [col for col in display_columns if col in df.columns]
    
    # Create a copy with only the columns we want to display
    display_df = df[display_columns].copy()
    
    # Configure AgGrid options
    gb = GridOptionsBuilder.from_dataframe(display_df)
    gb.configure_default_column(
        editable=False,
        resizable=True,
        filterable=True,
        sortable=True
    )
    
    # Configure specific columns
    gb.configure_column('ReactorLoadID', header_name="Load ID", width=90)
    gb.configure_column('LabRequestNumber', header_name="Lab Request #", width=130)
    gb.configure_column('job_number', header_name="Job #", width=120)
    gb.configure_column('pcn', header_name="PCN", width=100)
    gb.configure_column('created_by', header_name="Created By", width=120)
    
    # Configure status column with custom cell renderer
    if 'status' in display_df.columns:
        gb.configure_column(
            'status',
            header_name="Status",
            width=130,
            cellStyle=JsCode("""
            function(params) {
                if (params.value === 'Backlog') {
                    return { backgroundColor: '#FFF9C4', color: '#5D4037' };
                } else if (params.value === 'In Reactor') {
                    return { backgroundColor: '#E3F2FD', color: '#0D47A1' };
                } else if (params.value === 'Test Complete') {
                    return { backgroundColor: '#E8F5E9', color: '#2E7D32' };
                } else if (params.value === 'QC Complete') {
                    return { backgroundColor: '#F3E5F5', color: '#6A1B9A' };
                } else if (params.value === 'Report Delivered') {
                    return { backgroundColor: '#EFEBE9', color: '#4E342E' };
                }
                return { backgroundColor: '#FFFFFF' };
            }
            """)
        )
    
    # Configure priority column
    gb.configure_column('priority', header_name="Priority", width=90, type=["numericColumn"])
    
    # Enable row dragging
    gb.configure_grid_options(
        rowDragManaged=True,
        animateRows=True,
        rowDragEntireRow=True
    )
    
    # Add row drag for priority column
    gb.configure_column('priority', rowDrag=True)
    
    # Build grid options
    grid_options = gb.build()
    
    # Display with drag instructions
    st.markdown("""
    ### Drag-and-Drop Priority Ordering for Backlog Items
    Drag rows up or down to change priority order. Highest priority backlog loads appear at the top.
    Only backlog items are shown and can be reordered.
    """)
    
    # Create and display AgGrid
    grid_response = AgGrid(
        display_df,
        gridOptions=grid_options,
        update_mode=GridUpdateMode.MODEL_CHANGED,
        fit_columns_on_grid_load=False,
        allow_unsafe_jscode=True,
        height=400,
        key=f"priority_grid_{testing_area}"
    )
    
    # Get updated dataframe after possible row reordering
    updated_df = pd.DataFrame(grid_response['data'])
    
    # If the dataframe has been modified (rows reordered)
    if not updated_df.equals(display_df):
        # Update priority numbers based on the new row order
        updated_df['priority'] = range(1, len(updated_df) + 1)
        
        # Show a preview of the new priorities
        st.subheader("New Priority Order Preview")
        st.dataframe(
            updated_df[['ReactorLoadID', 'LabRequestNumber', 'priority']],
            use_container_width=True,
            hide_index=True
        )
        
        # Save button for the new priority order
        if st.button("💾 Save New Priority Order", use_container_width=True):
            try:
                if save_new_priorities(updated_df):
                    st.success("✅ Priorities updated successfully!")
                    st.rerun()
                else:
                    st.error("Failed to update priorities")
            except Exception as e:
                st.error(f"Error saving priorities: {e}")

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
    
    # Create tabs for different views
    tabs = st.tabs(["All Unscheduled Loads", "Quarter Bench", "Full Bench", "Cancelled", "Priority Scheduler"])
    
    try:
        # Tab 1: All Unscheduled Loads
        with tabs[0]:
            st.header("Unscheduled Reactor Loads")
            unscheduled_loads = get_unscheduled_loads()
            display_load_dataframe_with_batch_assignment(unscheduled_loads, is_scheduled=False, key_prefix="unscheduled")
        
        # Tab 2: Quarter Bench
        with tabs[1]:
            st.header("Quarter Bench Loads")
            quarter_bench_loads = get_loads_by_testing_area("Quarter Bench")
            display_load_dataframe_with_batch_assignment(quarter_bench_loads, is_scheduled=True, key_prefix="quarter_bench")
        
        # Tab 3: Full Bench
        with tabs[2]:
            st.header("Full Bench Loads")
            full_bench_loads = get_loads_by_testing_area("Full Bench")
            display_load_dataframe_with_batch_assignment(full_bench_loads, is_scheduled=True, key_prefix="full_bench")
        
        # Tab 4: Cancelled
        with tabs[3]:
            st.header("Cancelled Loads")
            cancelled_loads = get_loads_by_testing_area("Cancelled")
            display_load_dataframe_with_batch_assignment(cancelled_loads, is_scheduled=True, key_prefix="cancelled")
        
        # Tab 5: Priority Scheduler
        with tabs[4]:
            st.header("🔄 Backlog Priority Scheduler")
            st.info("This view shows only loads with 'Backlog' status. Reorder them to set priorities.")
            
            # Select testing area for priority scheduling
            testing_area = st.selectbox(
                "Select Testing Area", 
                ["Quarter Bench", "Full Bench"],
                key="priority_area_select"
            )
            
            # Display the drag-and-drop priority reordering interface for backlog items only
            display_priority_reordering(testing_area)
    
    except Exception as e:
        st.error(f"An error occurred: {e}")
        st.error("Please make sure the database path is correct and contains the required tables.")

if __name__ == "__main__":
    main()