import sqlite3
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
import plotly.express as px
from dateutil.relativedelta import relativedelta

# **Page Configuration**
st.set_page_config(page_title="Bench Area Metrics Dashboard", layout="wide")
st.title("Bench Area Metrics Dashboard")
st.markdown("Business metrics for Quarter Bench and Full Bench.")

# **Database Path**
# Update this path to your actual database file location
DB_PATH = r"C:\Jarvis\Database\lemur_full_clone.db"

# **Database Connection**
@st.cache_resource
def get_db_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

# **Generate Time Buckets**
def get_time_buckets(start_date, end_date, granularity):
    buckets = []
    if granularity == 'day':
        current = start_date
        while current <= end_date:
            bucket_start = datetime(current.year, current.month, current.day, 0, 0, 0)
            bucket_end = datetime(current.year, current.month, current.day, 23, 59, 59)
            buckets.append({
                'label': current.strftime('%Y-%m-%d'),
                'start': bucket_start,
                'end': min(bucket_end, end_date)
            })
            current += timedelta(days=1)
    elif granularity == 'month':
        current = datetime(start_date.year, start_date.month, 1)
        while current <= end_date:
            bucket_start = current
            next_month = current + relativedelta(months=1)
            bucket_end = (next_month - timedelta(days=1)).replace(hour=23, minute=59, second=59)
            if bucket_start <= end_date:
                buckets.append({
                    'label': current.strftime('%Y-%m'),
                    'start': bucket_start,
                    'end': min(bucket_end, end_date)
                })
            current = next_month
    elif granularity == 'quarter':
        quarter_month = ((start_date.month - 1) // 3 * 3 + 1)
        current = datetime(start_date.year, quarter_month, 1)
        while current <= end_date:
            bucket_start = current
            next_quarter = current + relativedelta(months=3)
            bucket_end = (next_quarter - timedelta(days=1)).replace(hour=23, minute=59, second=59)
            if bucket_start <= end_date:
                quarter_label = f"{current.year}-Q{(current.month - 1) // 3 + 1}"
                buckets.append({
                    'label': quarter_label,
                    'start': bucket_start,
                    'end': min(bucket_end, end_date)
                })
            current = next_quarter
    elif granularity == 'year':
        current = datetime(start_date.year, 1, 1)
        while current <= end_date:
            bucket_start = current
            next_year = current + relativedelta(years=1)
            bucket_end = (next_year - timedelta(days=1)).replace(hour=23, minute=59, second=59)
            if bucket_start <= end_date:
                buckets.append({
                    'label': current.strftime('%Y'),
                    'start': bucket_start,
                    'end': min(bucket_end, end_date)
                })
            current = next_year
    return buckets

# **Merge Intervals for Utilization**
def merge_intervals(intervals):
    if not intervals:
        return []
    intervals.sort(key=lambda x: x[0])
    merged = [intervals[0]]
    for current in intervals[1:]:
        previous = merged[-1]
        if current[0] <= previous[1]:
            merged[-1] = (previous[0], max(previous[1], current[1]))
        else:
            merged.append(current)
    return merged

# **Fetch Test Data**
@st.cache_data(ttl=600)
def fetch_test_data(start_date, end_date):
    conn = get_db_connection()
    query = """
    SELECT 
        strftime('%Y-%m-%d', LS.load_start) as day,
        LB.testing_area,
        RQ.request_type,
        COALESCE(TCT.test_condition_type, 'Unknown') as condition_type,
        RT.id as test_id,
        LS.load_start,
        LS.load_end
    FROM ReactorTests RT
    JOIN ReactorLoads RL ON RT.load_id = RL.id
    JOIN LoadSchedules LS ON LS.load_id = RL.id
    JOIN LoadBench LB ON LB.load_id = RL.id
    JOIN ReactorTestConditions RTC ON RT.test_condition_id = RTC.id
    JOIN TestConditionTypes TCT ON RTC.test_type_id = TCT.id
    JOIN LabRequests LR ON RL.lab_request_id = LR.id
    JOIN RequestTypes RQ ON LR.request_type_id = RQ.id
    WHERE LS.load_start >= ? AND LS.load_start <= ?
    """
    df = pd.read_sql_query(query, conn, params=[start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')])
    return df

# **Fetch Load Data for Utilization**
@st.cache_data(ttl=600)
def fetch_load_data(start_date, end_date):
    conn = get_db_connection()
    query = """
    SELECT 
        LS.load_id,
        LS.load_start,
        LS.load_end,
        LB.testing_area,
        LS.reactor
    FROM LoadSchedules LS
    JOIN LoadBench LB ON LB.load_id = LS.load_id
    WHERE LS.load_start <= ? AND (LS.load_end >= ? OR LS.load_end IS NULL)
    """
    df = pd.read_sql_query(query, conn, params=[end_date.strftime('%Y-%m-%d'), start_date.strftime('%Y-%m-%d')])
    return df

# **Process Test Data**
def process_test_data(df, granularity, bench_area, buckets):
    df = df[df['testing_area'] == bench_area].copy()
    df['load_start'] = pd.to_datetime(df['load_start'])
    
    # Assign each test to its time bucket
    df['time_bucket'] = df['load_start'].apply(
        lambda x: next((b['label'] for b in buckets if b['start'] <= x <= b['end']), None)
    )
    df = df.dropna(subset=['time_bucket'])
    
    # All tests
    all_tests = df[['test_id', 'time_bucket', 'request_type', 'condition_type', 'load_start', 'load_end']]
    
    # Test counts
    test_counts = df.groupby('time_bucket').size().reset_index(name='test_count')
    
    # Request type breakdown
    request_breakdown = df.groupby(['time_bucket', 'request_type']).size().reset_index(name='test_count')
    
    # Condition type breakdown
    condition_breakdown = df.groupby(['time_bucket', 'condition_type']).size().reset_index(name='test_count')
    
    return all_tests, test_counts, request_breakdown, condition_breakdown

# **Process Utilization Data**
def process_utilization_data(df, granularity, bench_area, buckets):
    df = df.copy()
    df['load_start'] = pd.to_datetime(df['load_start'])
    df['load_end'] = df['load_end'].apply(lambda x: pd.to_datetime(x) if x else None)
    
    if bench_area == "Quarter Bench":
        df = df[df['testing_area'] == "Quarter Bench"]
        reactors = ["Quarter Bench"]
    else:
        df = df[(df['testing_area'] == "Full Bench") & (df['reactor'].isin(['r1', 'r2', 'r3']))]
        reactors = ['r1', 'r2', 'r3']
    
    utilization_data = []
    
    for bucket in buckets:
        bucket_start = bucket['start']
        bucket_end = bucket['end']
        now = datetime.now()
        effective_bucket_end = min(bucket_end, now)
        total_hours = (effective_bucket_end - bucket_start).total_seconds() / 3600 if bucket_start < now else 0
        
        for reactor in reactors:
            if bench_area == "Quarter Bench":
                reactor_df = df
            else:
                reactor_df = df[df['reactor'] == reactor]
            
            intervals = []
            for _, row in reactor_df.iterrows():
                load_start = row['load_start']
                load_end = row['load_end'] if row['load_end'] else now
                effective_start = max(load_start, bucket_start)
                effective_end = min(load_end, effective_bucket_end)
                if effective_start < effective_end:
                    intervals.append((effective_start, effective_end))
            
            merged = merge_intervals(intervals)
            total_hours_in_use = sum((end - start).total_seconds() / 3600 for start, end in merged if start < end)
            utilization = (total_hours_in_use / total_hours) * 100 if total_hours > 0 else 0
            utilization_data.append({
                'time_bucket': bucket['label'],
                'reactor': reactor,
                'utilization': utilization
            })
    
    return pd.DataFrame(utilization_data)

# **Streamlit UI**
with st.sidebar:
    st.header("Filters")
    start_date = st.date_input("Start Date", value=datetime(2024, 1, 1))
    end_date = st.date_input("End Date", value=datetime.today())
    granularity = st.selectbox("Group By", ["day", "month", "quarter", "year"])

# Convert to datetime with proper time boundaries
start_date = datetime.combine(start_date, datetime.min.time())
end_date = datetime.combine(end_date, datetime.max.time())

# Generate time buckets
buckets = get_time_buckets(start_date, end_date, granularity)

# Fetch data
test_df = fetch_test_data(start_date, end_date)
load_df = fetch_load_data(start_date, end_date)

# Tabs for each bench area
tabs = st.tabs(["Quarter Bench", "Full Bench"])
for tab, bench_area in zip(tabs, ["Quarter Bench", "Full Bench"]):
    with tab:
        st.header(f"{bench_area} Metrics")
        
        # Process data
        all_tests, test_counts, request_breakdown, condition_breakdown = process_test_data(test_df, granularity, bench_area, buckets)
        utilization_df = process_utilization_data(load_df, granularity, bench_area, buckets)
        
        # **All Tests**
        st.subheader("All Tests")
        if not all_tests.empty:
            st.dataframe(all_tests)
        else:
            st.info("No tests found.")
        
        # **Test Counts**
        st.subheader("Test Counts")
        if not test_counts.empty:
            fig = px.bar(test_counts, x="time_bucket", y="test_count", title=f"Test Counts by {granularity.capitalize()}")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No test counts available.")
        
        # **Request Type Breakdown**
        st.subheader("Breakdown by Request Type")
        if not request_breakdown.empty:
            fig = px.bar(request_breakdown, x="time_bucket", y="test_count", color="request_type", 
                         title=f"Tests by Request Type ({granularity.capitalize()})")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No request type data.")
        
        # **Condition Type Breakdown**
        st.subheader("Breakdown by Condition Type")
        if not condition_breakdown.empty:
            fig = px.bar(condition_breakdown, x="time_bucket", y="test_count", color="condition_type", 
                         title=f"Tests by Condition Type ({granularity.capitalize()})")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No condition type data.")
        
        # **Utilization**
        st.subheader("Utilization")
        if not utilization_df.empty:
            if bench_area == "Quarter Bench":
                fig = px.line(utilization_df, x="time_bucket", y="utilization", 
                              title=f"Quarter Bench Utilization (%) by {granularity.capitalize()}")
            else:
                fig = px.line(utilization_df, x="time_bucket", y="utilization", color="reactor", 
                              title=f"Full Bench Utilization (%) by {granularity.capitalize()}")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No utilization data.")
