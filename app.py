# ================================
# Lab Load Scheduler - Full MVP
# ================================

import sqlite3
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
import plotly.express as px

# ====================
# Config and Constants
# ====================

st.set_page_config(page_title="Lab Load Scheduler", page_icon="🦢", layout="wide")
DB_PATH = r"C:\\Jarvis\\Database\\lemur_full_clone.db"
STATUS_OPTIONS = ["Backlog", "In Reactor", "Test Complete", "Cancelled"]
TESTING_AREAS = ["Quarter Bench", "Full Bench"]

# ==================
# Database Utilities
# ==================

@st.cache_resource
def get_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def run_query(query, params=None):
    conn = get_connection()
    return pd.read_sql_query(query, conn, params=params)

def execute_transaction(queries_with_params):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        for query, params in queries_with_params:
            cursor.execute(query, params)
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        st.error(f"Transaction failed: {e}")
        return False

# =====================
# Data Access Functions
# =====================

def get_unscheduled_loads(date_filter=None):
    query = """
    SELECT RL.id AS ReactorLoadID, LR.number AS LabRequestNumber, LR.pcn, LR.job_number,
           LR.time_submitted, RT.request_type, COUNT(S.id) AS sample_count
    FROM ReactorLoads RL
    JOIN LabRequests LR ON RL.lab_request_id = LR.id
    LEFT JOIN ReactorLoadSamples RLS ON RL.id = RLS.load_id
    LEFT JOIN LabRequestSample LRS ON RLS.lab_request_sample_id = LRS.id
    LEFT JOIN Samples S ON LRS.sample_id = S.id
    LEFT JOIN RequestTypes RT ON LR.request_type_id = RT.id
    LEFT JOIN LoadBench LB ON RL.id = LB.load_id
    WHERE LB.id IS NULL
    """
    params = []
    if date_filter:
        query += " AND LR.time_submitted BETWEEN ? AND ?"
        params = [date_filter[0], date_filter[1]]
    query += " GROUP BY RL.id ORDER BY LR.time_submitted DESC"
    return run_query(query, params)

def get_bench_loads(testing_area, statuses=None, date_filter=None):
    query = """
    SELECT RL.id AS ReactorLoadID, LB.status, LB.priority, LR.number AS LabRequestNumber,
           LR.pcn, LR.job_number, LR.time_submitted, RT.request_type, COUNT(S.id) AS sample_count
    FROM ReactorLoads RL
    JOIN LabRequests LR ON RL.lab_request_id = LR.id
    JOIN LoadBench LB ON RL.id = LB.load_id
    LEFT JOIN ReactorLoadSamples RLS ON RL.id = RLS.load_id
    LEFT JOIN LabRequestSample LRS ON RLS.lab_request_sample_id = LRS.id
    LEFT JOIN Samples S ON LRS.sample_id = S.id
    LEFT JOIN RequestTypes RT ON LR.request_type_id = RT.id
    WHERE LB.testing_area = ?
    """
    params = [testing_area]
    if statuses:
        query += " AND LB.status IN ({})".format(','.join(['?']*len(statuses)))
        params.extend(statuses)
    if date_filter:
        query += " AND LR.time_submitted BETWEEN ? AND ?"
        params.extend([date_filter[0], date_filter[1]])
    query += " GROUP BY RL.id ORDER BY LB.priority ASC"
    return run_query(query, params)

# =======================
# Data Modification Functions
# =======================

def assign_load(load_id, testing_area, status="Backlog", priority=100):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO LoadBench (load_id, testing_area, status, priority) VALUES (?, ?, ?, ?)",
                       (load_id, testing_area, status, priority))
        if status == "In Reactor":
            cursor.execute("INSERT OR REPLACE INTO LoadSchedules (load_id, load_start) VALUES (?, CURRENT_TIMESTAMP)", (load_id,))
        if status == "Test Complete":
            cursor.execute("UPDATE LoadSchedules SET load_end = CURRENT_TIMESTAMP WHERE load_id = ?", (load_id,))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        st.error(f"Assignment failed: {e}")
        return False

def update_status(load_id, status):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE LoadBench SET status = ? WHERE load_id = ?", (status, load_id))
        if status == "In Reactor":
            cursor.execute("INSERT OR REPLACE INTO LoadSchedules (load_id, load_start) VALUES (?, CURRENT_TIMESTAMP)", (load_id,))
        elif status == "Test Complete":
            cursor.execute("UPDATE LoadSchedules SET load_end = CURRENT_TIMESTAMP WHERE load_id = ?", (load_id,))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        st.error(f"Status update failed: {e}")
        return False

def unschedule_load(load_id):
    query = "DELETE FROM LoadBench WHERE load_id = ?"
    return execute_transaction([(query, (load_id,))])

def batch_unschedule_loads(load_ids):
    queries = [("DELETE FROM LoadBench WHERE load_id = ?", (lid,)) for lid in load_ids]
    return execute_transaction(queries)

# =======================
# UI Functions
# =======================

def date_filter_widget(key_prefix=""):
    col1, col2 = st.columns(2)
    with col1:
        start = st.date_input("Start Date", datetime.now() - timedelta(days=30), key=f"start_{key_prefix}")
    with col2:
        end = st.date_input("End Date", datetime.now(), key=f"end_{key_prefix}")
    return start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d')

def status_filter_widget(key_prefix=""):
    return st.multiselect("Status Filter", STATUS_OPTIONS, default=STATUS_OPTIONS, key=f"status_filter_{key_prefix}")

def show_load_table(df, title):
    st.subheader(title)
    if df.empty:
        st.info("No records to display.")
    else:
        st.dataframe(df, use_container_width=True)

def display_priority_reordering(testing_area):
    query = """
    SELECT lb.load_id, lb.priority, 
           lr.number as LabRequestNumber, lr.job_number, lr.pcn
    FROM LoadBench lb
    JOIN ReactorLoads rl ON lb.load_id = rl.id
    JOIN LabRequests lr ON rl.lab_request_id = lr.id
    WHERE lb.testing_area = ? AND UPPER(lb.status) = 'BACKLOG'
    ORDER BY lb.priority
    """
    df = run_query(query, (testing_area,))
    st.subheader(f"Reorder Priorities - {testing_area}")
    edited_df = st.data_editor(df, use_container_width=True, hide_index=True, num_rows="fixed")
    if st.button("Save Priorities"):
        updates = [("UPDATE LoadBench SET priority = ? WHERE load_id = ? AND testing_area = ?", (row['priority'], row['load_id'], testing_area)) for _, row in edited_df.iterrows()]
        if execute_transaction(updates):
            st.success("Priorities updated successfully")
            st.rerun()

def display_dashboard():
    st.subheader("Test Counts by Request Type")
    query = """
    SELECT LB.testing_area, RT.request_type, COUNT(S.id) as test_count
    FROM ReactorLoads RL
    JOIN LabRequests LR ON RL.lab_request_id = LR.id
    JOIN LoadBench LB ON RL.id = LB.load_id
    JOIN RequestTypes RT ON LR.request_type_id = RT.id
    JOIN ReactorLoadSamples RLS ON RL.id = RLS.load_id
    JOIN LabRequestSample LRS ON RLS.lab_request_sample_id = LRS.id
    JOIN Samples S ON LRS.sample_id = S.id
    GROUP BY LB.testing_area, RT.request_type
    ORDER BY LB.testing_area, RT.request_type
    """
    df = run_query(query)
    if df.empty:
        st.info("No test data available.")
    else:
        fig = px.bar(df, x="request_type", y="test_count", color="testing_area",
                     barmode="group", title="Total Test Counts by Request Type")
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Tests Per Month (Last 12 Months)")
    query_month = """
    SELECT strftime('%Y-%m', LR.time_submitted) as month, COUNT(S.id) as test_count
    FROM ReactorLoads RL
    JOIN LabRequests LR ON RL.lab_request_id = LR.id
    JOIN ReactorLoadSamples RLS ON RL.id = RLS.load_id
    JOIN LabRequestSample LRS ON RLS.lab_request_sample_id = LRS.id
    JOIN Samples S ON LRS.sample_id = S.id
    WHERE LR.time_submitted >= date('now', '-12 months')
    GROUP BY strftime('%Y-%m', LR.time_submitted)
    ORDER BY month
    """
    df_month = run_query(query_month)
    if not df_month.empty:
        fig_month = px.bar(df_month, x="month", y="test_count", title="Tests Per Month")
        st.plotly_chart(fig_month, use_container_width=True)

    st.subheader("Tests Per Week (Last 8 Weeks)")
    query_week = """
    SELECT strftime('%Y-W%W', LR.time_submitted) as week, COUNT(S.id) as test_count
    FROM ReactorLoads RL
    JOIN LabRequests LR ON RL.lab_request_id = LR.id
    JOIN ReactorLoadSamples RLS ON RL.id = RLS.load_id
    JOIN LabRequestSample LRS ON RLS.lab_request_sample_id = LRS.id
    JOIN Samples S ON LRS.sample_id = S.id
    WHERE LR.time_submitted >= date('now', '-8 weeks')
    GROUP BY strftime('%Y-W%W', LR.time_submitted)
    ORDER BY week
    """
    df_week = run_query(query_week)
    if not df_week.empty:
        fig_week = px.bar(df_week, x="week", y="test_count", title="Tests Per Week")
        st.plotly_chart(fig_week, use_container_width=True)

# ==========
# Main App
# ==========

def main():
    st.title("Lab Load Scheduler - MVP")

    tabs = st.tabs(["Dashboard", "Unscheduled", "Quarter Bench", "Full Bench", "Priority Scheduler"])

    with tabs[0]:
        display_dashboard()

    with tabs[1]:
        date_range = date_filter_widget(key_prefix="unscheduled")
        unscheduled = get_unscheduled_loads(date_range)
        show_load_table(unscheduled, "Unscheduled Loads")

        if not unscheduled.empty:
            selected_ids = st.multiselect("Select Loads to Assign", unscheduled['ReactorLoadID'])
            col1, col2 = st.columns(2)
            with col1:
                bench = st.selectbox("Assign To", TESTING_AREAS)
            with col2:
                status = st.selectbox("Initial Status", STATUS_OPTIONS)
            if st.button("Assign Selected Loads"):
                for lid in selected_ids:
                    assign_load(lid, bench, status)
                st.success("Assigned successfully")
                st.rerun()

    for i, area in enumerate(TESTING_AREAS, start=2):
        with tabs[i]:
            date_range = date_filter_widget(key_prefix=area.lower().replace(" ", "_"))
            statuses = status_filter_widget(key_prefix=area.lower().replace(" ", "_"))
            loads = get_bench_loads(area, statuses, date_range)
            # show_load_table(loads, f"{area} Loads") — removed to avoid duplicate rendering

            if not loads.empty:
                st.subheader(f"{area} Loads")
                edited = st.data_editor(
                    loads,
                    use_container_width=True,
                    height=700,
                    num_rows="fixed",
                    key=f"edit_{area}"
                )
                if st.button(f"Save Status Changes ({area})"):
                    for _, row in edited.iterrows():
                        update_status(row['ReactorLoadID'], row['status'])
                    st.success("Statuses updated")
                    st.rerun()

                selected = st.multiselect(f"Select Loads to Unschedule ({area})", loads['ReactorLoadID'])
                if selected and st.button(f"Unschedule Selected ({area})"):
                    batch_unschedule_loads(selected)
                    st.success("Unscheduled successfully")
                    st.rerun()

    with tabs[4]:
        testing_area = st.selectbox("Select Testing Area", TESTING_AREAS)
        display_priority_reordering(testing_area)

if __name__ == "__main__":
    main()
