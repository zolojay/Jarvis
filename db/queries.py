"""
Database queries module.
Contains all direct database access functions.
"""
import sqlite3
import pandas as pd
import streamlit as st
from datetime import datetime
from .connection import get_db_connection

def get_reactor_loads():
    """
    Fetch all reactor loads from the database with detailed information.
    
    Returns:
        pd.DataFrame: DataFrame containing all reactor loads
    """
    conn = get_db_connection()
    
    # The SQL query with minor modifications for SQLite compatibility
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
    
    # Format the timestamp column
    if 'time_submitted' in df.columns and not df.empty:
        # Handle timestamp conversion with flexible format
        df['time_submitted'] = pd.to_datetime(df['time_submitted'], format='mixed', errors='coerce')
        # Format for display
        df['time_submitted'] = df['time_submitted'].dt.strftime('%Y-%m-%d %H:%M')
    
    return df

def get_load_info(load_id):
    """
    Get testing area, status, and priority for a specific load.
    
    Args:
        load_id (int): The load ID to query
        
    Returns:
        dict: Dictionary containing testing_area, status, and priority
    """
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

def get_testing_area(load_id):
    """
    Get testing area for a specific load (backward compatibility function).
    
    Args:
        load_id (int): The load ID to query
        
    Returns:
        str: Testing area or None
    """
    load_info = get_load_info(load_id)
    return load_info["testing_area"]

def get_load_status(load_id):
    """
    Get status for a specific load.
    
    Args:
        load_id (int): The load ID to query
        
    Returns:
        str: Status (defaults to "Backlog" if not set)
    """
    load_info = get_load_info(load_id)
    return load_info["status"] or "Backlog"

def get_load_priority(load_id):
    """
    Get priority for a specific load.
    
    Args:
        load_id (int): The load ID to query
        
    Returns:
        int: Priority (defaults to 100 if not set)
    """
    load_info = get_load_info(load_id)
    return load_info["priority"] or 100

def load_scheduled_loads(testing_area, status_filter=None):
    """
    Load scheduled loads for a specific testing area with optional status filter.
    
    Args:
        testing_area (str): Testing area to filter by
        status_filter (str, optional): Status to filter by
        
    Returns:
        pd.DataFrame: DataFrame containing scheduled loads
    """
    conn = get_db_connection()
    
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
    
    conn.close()
    return df

def get_loads_by_testing_area(testing_area):
    """
    Get detailed load information for loads assigned to a specific testing area.
    
    Args:
        testing_area (str): Testing area to filter by
        
    Returns:
        pd.DataFrame: DataFrame containing loads with detailed information
    """
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

def get_unscheduled_loads():
    """
    Get loads that are not assigned to any testing area.
    
    Returns:
        pd.DataFrame: DataFrame containing unscheduled loads
    """
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

def update_loadbench_status(load_id, status, priority=None):
    """
    Update status and optionally priority for a load in the LoadBench table.
    
    Args:
        load_id (int): Load ID to update
        status (str): New status value
        priority (int, optional): New priority value
        
    Returns:
        bool: True if successful, False otherwise
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        if priority is not None:
            cursor.execute(
                "UPDATE LoadBench SET status = ?, priority = ? WHERE load_id = ?",
                (status, priority, load_id)
            )
        else:
            cursor.execute(
                "UPDATE LoadBench SET status = ? WHERE load_id = ?",
                (status, load_id)
            )
            
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        conn.rollback()
        conn.close()
        return False

def save_priority_updates(df, testing_area):
    """
    Save updated priorities to the database for a specific testing area.
    
    Args:
        df (pd.DataFrame): DataFrame containing load_id and priority columns
        testing_area (str): Testing area these priorities apply to
        
    Returns:
        bool: True if successful, False otherwise
    """
    if df.empty or 'load_id' not in df.columns or 'priority' not in df.columns:
        return False
    
    conn = get_db_connection()
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
        conn.close()
        return True
    except Exception as e:
        conn.rollback()
        conn.close()
        return False

def insert_or_update_loadbench(load_id, testing_area, status=None, priority=None):
    """
    Insert a new entry into LoadBench or update an existing one.
    
    Args:
        load_id (int): Load ID
        testing_area (str): Testing area
        status (str, optional): Status (defaults to 'Backlog')
        priority (int, optional): Priority
        
    Returns:
        bool: True if successful, False otherwise
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Check if entry exists
        cursor.execute("SELECT id FROM LoadBench WHERE load_id = ?", (load_id,))
        exists = cursor.fetchone()
        
        if status is None:
            status = 'Backlog'
        
        if exists:
            # Update existing entry
            if priority is not None:
                cursor.execute(
                    "UPDATE LoadBench SET testing_area = ?, status = ?, priority = ? WHERE load_id = ?",
                    (testing_area, status, priority, load_id)
                )
            else:
                cursor.execute(
                    "UPDATE LoadBench SET testing_area = ?, status = ? WHERE load_id = ?",
                    (testing_area, status, load_id)
                )
        else:
            # Insert new entry
            if priority is not None:
                cursor.execute(
                    "INSERT INTO LoadBench (load_id, testing_area, assigned_date, status, priority) VALUES (?, ?, DATE('now'), ?, ?)",
                    (load_id, testing_area, status, priority)
                )
            else:
                cursor.execute(
                    "INSERT INTO LoadBench (load_id, testing_area, assigned_date, status) VALUES (?, ?, DATE('now'), ?)",
                    (load_id, testing_area, status)
                )
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        conn.rollback()
        conn.close()
        return False

def delete_loadbench_entry(load_id):
    """
    Delete an entry from LoadBench table.
    
    Args:
        load_id (int): Load ID to delete
        
    Returns:
        bool: True if successful, False otherwise
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("DELETE FROM LoadBench WHERE load_id = ?", (load_id,))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        conn.rollback()
        conn.close()
        return False

def get_max_priority_for_testing_area(testing_area, status="Backlog"):
    """
    Get the maximum priority value for a specific testing area and status.
    
    Args:
        testing_area (str): Testing area to query
        status (str, optional): Status to filter by (defaults to 'Backlog')
        
    Returns:
        int: Maximum priority value or None if no records found
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT MAX(priority) FROM LoadBench WHERE testing_area = ? AND UPPER(status) = UPPER(?)",
        (testing_area, status)
    )
    result = cursor.fetchone()
    conn.close()
    
    return result[0] if result and result[0] is not None else None