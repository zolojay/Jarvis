import sqlite3
import pandas as pd
import json
import datetime
import os
import webbrowser
import traceback

def connect_to_db(db_path):
    """Connect to the SQLite database and return the connection object."""
    try:
        print(f"Attempting to connect to database at: {db_path}")
        conn = sqlite3.connect(db_path)
        print("Database connection successful")
        return conn
    except sqlite3.Error as e:
        print(f"Error connecting to database: {e}")
        print(traceback.format_exc())
        return None

def get_dashboard_data(conn):
    """Query the Dashboard view and return the results as a pandas DataFrame."""
    try:
        # Try different view/table names
        view_names = ["Dashboard", "LoadTestSummary", "ReactorLoads", "Loads"]
        
        for view_name in view_names:
            try:
                query = f"SELECT * FROM {view_name}"
                print(f"Trying to query from {view_name}...")
                df = pd.read_sql_query(query, conn)
                print(f"Successfully queried '{view_name}'. Found {len(df)} records.")
                return df
            except Exception as e:
                print(f"Could not query from {view_name}: {str(e)}")
                continue
        
        # If we get here, try to query all tables to see what's available
        try:
            print("Listing all available tables in the database...")
            query = "SELECT name FROM sqlite_master WHERE type='table'"
            tables_df = pd.read_sql_query(query, conn)
            print(f"Available tables: {tables_df['name'].tolist()}")
            
            if not tables_df.empty:
                # Try the first table
                first_table = tables_df['name'].iloc[0]
                print(f"Attempting to query first available table: {first_table}")
                query = f"SELECT * FROM {first_table}"
                df = pd.read_sql_query(query, conn)
                print(f"Successfully queried '{first_table}'. Found {len(df)} records.")
                return df
        except Exception as e:
            print(f"Error listing/querying tables: {e}")
        
        print("Could not find any valid table or view to query from.")
        return None
    except Exception as e:
        print(f"Error querying database: {e}")
        print(traceback.format_exc())
        return None

def process_data(df):
    """Process the data for dashboard visualization."""
    if df is None or df.empty:
        print("No data to process")
        return None
    
    try:
        print(f"Processing {len(df)} rows of data")
        print(f"Columns available: {df.columns.tolist()}")
        
        # Check if required columns exist
        required_columns = ['ReactorLoadID', 'load_status', 'testing_area']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            print(f"Warning: Missing required columns: {missing_columns}")
            
            # If ReactorLoadID is missing, try to create it as a sequential ID
            if 'ReactorLoadID' in missing_columns:
                df['ReactorLoadID'] = range(1, len(df) + 1)
                print("Created synthetic ReactorLoadID column")
            
            # If load_status is missing, set a default value
            if 'load_status' in missing_columns:
                df['load_status'] = 'Unknown'
                print("Created synthetic load_status column")
                
            # If testing_area is missing, set a default value
            if 'testing_area' in missing_columns:
                df['testing_area'] = 'Unknown'
                print("Created synthetic testing_area column")
        
        # Convert timestamp columns to datetime
        for col in ['time_submitted', 'load_start', 'load_end']:
            if col in df.columns and df[col].dtype == object:
                df[col] = pd.to_datetime(df[col], errors='coerce')
                print(f"Converted {col} to datetime")
        
        # Calculate metrics with safe handling of missing columns
        metrics = {
            'total_loads': len(df),
            'loads_in_backlog': len(df[df['load_status'] == 'Backlog']),
            'loads_in_reactor': len(df[df['load_status'] == 'In Reactor']),
            'loads_completed': len(df[df['load_status'].isin(['Test Complete', 'QC Complete', 'Report Delivered'])]),
            'avg_samples_per_load': round(df['sample_count'].fillna(0).mean(), 1) if 'sample_count' in df.columns else 0,
            'total_test_conditions': int(df['test_condition_count'].fillna(0).sum()) if 'test_condition_count' in df.columns else 0,
            'nox_removal_tests': int(df['NOx_Removal_count'].fillna(0).sum()) if 'NOx_Removal_count' in df.columns else 0,
            'so2_oxidation_tests': int(df['SO2_Oxidation_count'].fillna(0).sum()) if 'SO2_Oxidation_count' in df.columns else 0,
            'co_oxidation_tests': int(df['CO_Oxidation_count'].fillna(0).sum()) if 'CO_Oxidation_count' in df.columns else 0,
            'voc_oxidation_tests': int(df['VOC_Oxidation_count'].fillna(0).sum()) if 'VOC_Oxidation_count' in df.columns else 0,
        }
        
        # Only add these fields if they exist in the dataframe
        if 'Hg_Oxidation_count' in df.columns:
            metrics['hg_oxidation_tests'] = int(df['Hg_Oxidation_count'].fillna(0).sum())
        else:
            metrics['hg_oxidation_tests'] = 0
            
        if 'CH2O_Oxidation_count' in df.columns:
            metrics['ch2o_oxidation_tests'] = int(df['CH2O_Oxidation_count'].fillna(0).sum())
        else:
            metrics['ch2o_oxidation_tests'] = 0
        
        # Generate data for charts
        request_types = df['request_type'].value_counts().to_dict()
        
        # Process test conditions column (handle comma-separated values)
        test_conditions = []
        for tc in df['test_conditions'].dropna():
            if isinstance(tc, str) and tc.strip():
                test_conditions.extend([t.strip() for t in tc.split(',')])
        test_conditions_count = {}
        for tc in test_conditions:
            if tc in test_conditions_count:
                test_conditions_count[tc] += 1
            else:
                test_conditions_count[tc] = 1
        
        # Process sample types column
        sample_types = []
        for st in df['sample_types'].dropna():
            if isinstance(st, str) and st.strip():
                sample_types.extend([t.strip() for t in st.split(',')])
        sample_types_count = {}
        for st in sample_types:
            if st in sample_types_count:
                sample_types_count[st] += 1
            else:
                sample_types_count[st] = 1
        
        # Monthly trend data
        monthly_loads_dict = {}
        if 'load_start' in df.columns:
            # Use load_start instead of time_submitted for better analysis
            date_column = 'load_start'
            df['month'] = df[date_column].dt.strftime('%Y-%m')
            monthly_loads = df.groupby('month').size().reset_index(name='count')
            monthly_loads = monthly_loads.sort_values('month')
            monthly_loads_dict = dict(zip(monthly_loads['month'], monthly_loads['count']))
        elif 'time_submitted' in df.columns:
            date_column = 'time_submitted'
            df['month'] = df[date_column].dt.strftime('%Y-%m')
            monthly_loads = df.groupby('month').size().reset_index(name='count')
            monthly_loads = monthly_loads.sort_values('month')
            monthly_loads_dict = dict(zip(monthly_loads['month'], monthly_loads['count']))
        
        # Status distribution
        status_counts = df['load_status'].value_counts().to_dict()
        
        # Format data 
        all_loads_list = []
        for _, row in df.iterrows():
            load_dict = {
                'ReactorLoadID': str(row['ReactorLoadID']),
                'LabRequestNumber': str(row['LabRequestNumber']),
                'job_number': str(row['job_number']) if pd.notna(row['job_number']) else '',
                'pcn': str(row['pcn']) if pd.notna(row['pcn']) else '',
                'time_submitted': row['time_submitted'].strftime('%Y-%m-%d %H:%M') if pd.notna(row['time_submitted']) else '',
                'created_by': str(row['created_by']) if pd.notna(row['created_by']) else '',
                'request_type': str(row['request_type']) if pd.notna(row['request_type']) else '',
                'testing_area': str(row['testing_area']) if pd.notna(row['testing_area']) else '',
                'reactor': str(row['reactor']) if pd.notna(row['reactor']) else '',
                'load_start': row['load_start'].strftime('%Y-%m-%d %H:%M') if pd.notna(row['load_start']) else '',
                'load_end': row['load_end'].strftime('%Y-%m-%d %H:%M') if pd.notna(row['load_end']) else '',
                'load_status': str(row['load_status']) if pd.notna(row['load_status']) else '',
                'priority': int(row['priority']) if pd.notna(row['priority']) else 0,
                'sample_count': int(row['sample_count']) if pd.notna(row['sample_count']) else 0,
                'sample_numbers': str(row['sample_numbers']) if pd.notna(row['sample_numbers']) else '',
                'sample_types': str(row['sample_types']) if pd.notna(row['sample_types']) else '',
                'test_condition_count': int(row['test_condition_count']) if pd.notna(row['test_condition_count']) else 0,
                'NOx_Removal_count': int(row['NOx_Removal_count']) if pd.notna(row['NOx_Removal_count']) else 0,
                'SO2_Oxidation_count': int(row['SO2_Oxidation_count']) if pd.notna(row['SO2_Oxidation_count']) else 0,
                'CO_Oxidation_count': int(row['CO_Oxidation_count']) if pd.notna(row['CO_Oxidation_count']) else 0,
                'VOC_Oxidation_count': int(row['VOC_Oxidation_count']) if pd.notna(row['VOC_Oxidation_count']) else 0,
                'test_conditions': str(row['test_conditions']) if pd.notna(row['test_conditions']) else '',
                'testconditiondescription': str(row['testconditiondescription']) if pd.notna(row['testconditiondescription']) else '',
            }
            
            # Only add these fields if they exist in the dataframe
            if 'Hg_Oxidation_count' in df.columns:
                load_dict['Hg_Oxidation_count'] = int(row['Hg_Oxidation_count']) if pd.notna(row['Hg_Oxidation_count']) else 0
            else:
                load_dict['Hg_Oxidation_count'] = 0
                
            if 'CH2O_Oxidation_count' in df.columns:
                load_dict['CH2O_Oxidation_count'] = int(row['CH2O_Oxidation_count']) if pd.notna(row['CH2O_Oxidation_count']) else 0
            else:
                load_dict['CH2O_Oxidation_count'] = 0
            
            all_loads_list.append(load_dict)
        
        print(f"Data processing complete. Generated {len(all_loads_list)} load entries.")
        
        return {
            'metrics': metrics,
            'request_types': request_types,
            'test_conditions': test_conditions_count,
            'sample_types': sample_types_count,
            'status_counts': status_counts,
            'monthly_loads': monthly_loads_dict,
            'all_loads': all_loads_list,
            'update_time': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    except Exception as e:
        print(f"Error processing data: {e}")
        print(traceback.format_exc())
        return None

def generate_html(data, output_path):
    """Generate HTML file with embedded data."""
    try:
        # Convert data to JSON for embedding in JavaScript
        json_data = json.dumps(data)
        
        html_content = f'''<!DOCTYPE html>
<html lang="en" data-bs-theme="light">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Reactor Testing Dashboard</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.1/font/bootstrap-icons.css">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            transition: background-color 0.3s ease;
        }}
        .card {{
            border-radius: 10px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
            margin-bottom: 20px;
            border: none;
            transition: all 0.3s ease;
        }}
        .card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 8px 16px rgba(0,0,0,0.1);
        }}
        .card-header {{
            border-radius: 10px 10px 0 0 !important;
            font-weight: 600;
            padding: 12px 16px;
        }}
        .metric-card {{
            text-align: center;
            padding: 20px;
            height: 100%;
        }}
        .metric-value {{
            font-size: 2.5rem;
            font-weight: bold;
            margin-bottom: 5px;
        }}
        .metric-label {{
            font-size: 1rem;
            color: #6c757d;
            opacity: 0.8;
        }}
        .last-updated {{
            font-size: 12px;
            text-align: right;
            margin-bottom: 20px;
        }}
        .nav-link {{
            font-weight: 500;
            padding: 10px 15px;
            border-radius: 5px;
            margin-right: 5px;
            transition: all 0.2s ease;
        }}
        .nav-link.active {{
            font-weight: bold;
        }}
        .nav-link:hover:not(.active) {{
            background-color: rgba(13, 110, 253, 0.1);
        }}
        .chart-container {{
            position: relative;
            height: 400px;
            margin-bottom: 20px;
        }}
        .toggle-theme {{
            cursor: pointer;
            padding: 5px 10px;
            border-radius: 5px;
            display: inline-flex;
            align-items: center;
        }}
        #dashboard-container {{
            padding-top: 20px;
        }}
        #view-options .btn {{
            margin-right: 5px;
        }}
        .time-selector {{
            margin-bottom: 15px;
        }}
        .loader {{
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(255, 255, 255, 0.9);
            display: flex;
            justify-content: center;
            align-items: center;
            z-index: 9999;
        }}
        .spinner {{
            width: 50px;
            height: 50px;
            border: 5px solid #f3f3f3;
            border-top: 5px solid #3498db;
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }}
        @keyframes spin {{
            0% {{ transform: rotate(0deg); }}
            100% {{ transform: rotate(360deg); }}
        }}
    </style>
</head>
<body>
    <div id="loader" class="loader">
        <div class="spinner"></div>
    </div>

    <div class="container-fluid">
        <!-- Navigation Bar -->
        <nav class="navbar navbar-expand-lg navbar-light bg-body-tertiary">
            <div class="container-fluid">
                <a class="navbar-brand fw-bold" href="#">
                    <i class="bi bi-clipboard2-data"></i> Reactor Testing Dashboard
                </a>
                <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
                    <span class="navbar-toggler-icon"></span>
                </button>
                <div class="collapse navbar-collapse" id="navbarNav">
                    <ul class="navbar-nav">
                        <li class="nav-item">
                            <a class="nav-link active" id="all-tests-tab" href="#" onclick="changeView('all')">All Tests</a>
                        </li>
                        <li class="nav-item">
                            <a class="nav-link" id="quarter-bench-tab" href="#" onclick="changeView('quarter')">Quarter Bench</a>
                        </li>
                        <li class="nav-item">
                            <a class="nav-link" id="full-bench-tab" href="#" onclick="changeView('full')">Full Bench</a>
                        </li>
                    </ul>
                    <div class="ms-auto toggle-theme" onclick="toggleTheme()">
                        <i class="bi bi-moon-stars"></i> <span id="theme-text">Dark Mode</span>
                    </div>
                </div>
            </div>
        </nav>

        <!-- Dashboard Header -->
        <div class="d-flex justify-content-between align-items-center mt-3">
            <h2 id="dashboard-title">All Tests Dashboard</h2>
            <p class="last-updated mb-0">Last updated: <span id="update-time">{data["update_time"]}</span></p>
        </div>

        <!-- Time Period Selector -->
        <div class="row mb-3">
            <div class="col-md-6">
                <div class="btn-group time-selector" role="group">
                    <button type="button" class="btn btn-outline-primary active" onclick="setTimeRange('day')">Daily</button>
                    <button type="button" class="btn btn-outline-primary" onclick="setTimeRange('week')">Weekly</button>
                    <button type="button" class="btn btn-outline-primary" onclick="setTimeRange('month')">Monthly</button>
                    <button type="button" class="btn btn-outline-primary" onclick="setTimeRange('quarter')">Quarterly</button>
                    <button type="button" class="btn btn-outline-primary" onclick="setTimeRange('year')">Yearly</button>
                </div>
            </div>
            <div class="col-md-6 text-end">
                <button class="btn btn-outline-secondary" onclick="refreshData()">
                    <i class="bi bi-arrow-clockwise"></i> Refresh Data
                </button>
            </div>
        </div>

        <!-- Metrics Cards -->
        <div class="row" id="metrics-row">
            <!-- Will be populated by JavaScript -->
        </div>

        <!-- Charts Section -->
        <div class="row">
            <div class="col-lg-8 mb-4">
                <div class="card h-100">
                    <div class="card-header bg-primary text-white">
                        <i class="bi bi-graph-up"></i> <span id="trend-chart-title">Tests Over Time</span>
                    </div>
                    <div class="card-body">
                        <div class="chart-container">
                            <canvas id="timeSeriesChart"></canvas>
                        </div>
                    </div>
                </div>
            </div>
            <div class="col-lg-4 mb-4">
                <div class="card h-100">
                    <div class="card-header bg-success text-white">
                        <i class="bi bi-pie-chart"></i> Request Types
                    </div>
                    <div class="card-body">
                        <div class="chart-container">
                            <canvas id="requestTypesChart"></canvas>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <div class="row">
            <div class="col-lg-6 mb-4">
                <div class="card h-100">
                    <div class="card-header bg-info text-white">
                        <i class="bi bi-bar-chart"></i> Test Conditions
                    </div>
                    <div class="card-body">
                        <div class="chart-container">
                            <canvas id="testConditionsChart"></canvas>
                        </div>
                    </div>
                </div>
            </div>
            <div class="col-lg-6 mb-4">
                <div class="card h-100">
                    <div class="card-header bg-warning text-dark">
                        <i class="bi bi-diagram-3"></i> Sample Types
                    </div>
                    <div class="card-body">
                        <div class="chart-container">
                            <canvas id="sampleTypesChart"></canvas>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- JavaScript Libraries -->
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/moment@2.29.4/moment.min.js"></script>
    
    <script>
        // Dashboard data embedded directly
        const dashboardData = {json_data};
        
        // Global variables
        let currentView = 'all';
        let currentTimeRange = 'day';
        let charts = {{
            timeSeries: null,
            requestTypes: null,
            testConditions: null,
            sampleTypes: null
        }};
        const chartColors = [
            'rgba(54, 162, 235, 0.7)',  // Blue
            'rgba(255, 99, 132, 0.7)',  // Red
            'rgba(255, 206, 86, 0.7)',  // Yellow
            'rgba(75, 192, 192, 0.7)',  // Green
            'rgba(153, 102, 255, 0.7)', // Purple
            'rgba(255, 159, 64, 0.7)',  // Orange
            'rgba(199, 199, 199, 0.7)', // Gray
            'rgba(83, 102, 255, 0.7)',  // Indigo
            'rgba(255, 99, 71, 0.7)',   // Tomato
            'rgba(60, 179, 113, 0.7)'   // Medium Sea Green
        ];

        // Function to initialize the dashboard
        function initDashboard() {{
            // Hide the loader
            document.getElementById('loader').style.display = 'none';
            
            // Initialize the dashboard with the current view
            changeView(currentView);
        }}

        // Function to filter data by testing area
        function filterDataByView(data, view) {{
            if (view === 'all') {{
                return data;
            }} else if (view === 'quarter') {{
                return data.filter(item => item.testing_area === 'Quarter Bench');
            }} else if (view === 'full') {{
                return data.filter(item => item.testing_area === 'Full Bench');
            }}
            return [];
        }}

        // Function to filter data by time period
        function filterDataByTime(data, timeRange) {{
            const now = new Date();
            let startDate;

            switch (timeRange) {{
                case 'day':
                    startDate = new Date(now.setDate(now.getDate() - 1));
                    break;
                case 'week':
                    startDate = new Date(now.setDate(now.getDate() - 7));
                    break;
                case 'month':
                    startDate = new Date(now.setMonth(now.getMonth() - 1));
                    break;
                case 'quarter':
                    startDate = new Date(now.setMonth(now.getMonth() - 3));
                    break;
                case 'year':
                    startDate = new Date(now.setFullYear(now.getFullYear() - 1));
                    break;
                default:
                    startDate = new Date(0); // All time if no valid range
            }}

            return data.filter(item => {{
                if (!item.load_start) return true; // Include items without load_start
                const loadDate = new Date(item.load_start);
                return !isNaN(loadDate.getTime()) && loadDate >= startDate;
            }});
        }}

        // Function to change the current view
        function changeView(view) {{
            // Update current view
            currentView = view;
            
            // Update active tab
            document.querySelectorAll('.nav-link').forEach(link => link.classList.remove('active'));
            document.getElementById(`${{view}}-tests-tab`).classList.add('active');
            
            // Update dashboard title
            const titleMapping = {{
                'all': 'All Tests Dashboard',
                'quarter': 'Quarter Bench Dashboard',
                'full': 'Full Bench Dashboard'
            }};
            document.getElementById('dashboard-title').textContent = titleMapping[view];
            
            // Update dashboard content
            updateDashboard();
        }}

        // Function to update the dashboard based on current view and time range
        function updateDashboard() {{
            if (!dashboardData) return;
            
            // Filter data based on current view
            let filteredData = filterDataByView(dashboardData.all_loads, currentView);
            
            // Further filter based on time range
            filteredData = filterDataByTime(filteredData, currentTimeRange);
            
            // Update metrics
            updateMetrics(filteredData);
            
            // Update charts
            updateCharts(filteredData);
        }}

        // Function to update metrics cards
        function updateMetrics(data) {{
            // Calculate metrics
            const totalLoads = data.length;
            const loadsInBacklog = data.filter(item => item.load_status === 'Backlog').length;
            const loadsInReactor = data.filter(item => item.load_status === 'In Reactor').length;
            const loadsCompleted = data.filter(item => 
                ['Test Complete', 'QC Complete', 'Report Delivered'].includes(item.load_status)
            ).length;

            // Calculate test counts
            let noxTests = 0, so2Tests = 0, coTests = 0, vocTests = 0;
            data.forEach(item => {{
                noxTests += parseInt(item.NOx_Removal_count || 0);
                so2Tests += parseInt(item.SO2_Oxidation_count || 0);
                coTests += parseInt(item.CO_Oxidation_count || 0);
                vocTests += parseInt(item.VOC_Oxidation_count || 0);
            }});
            const totalTests = noxTests + so2Tests + coTests + vocTests;
            
            // Build metrics HTML
            const metricsHtml = `
                <div class="col-md-3 mb-4">
                    <div class="card h-100">
                        <div class="card-body metric-card">
                            <div class="metric-value text-primary">${{totalLoads}}</div>
                            <div class="metric-label">Total Loads</div>
                        </div>
                    </div>
                </div>
                <div class="col-md-3 mb-4">
                    <div class="card h-100">
                        <div class="card-body metric-card">
                            <div class="metric-value text-warning">${{loadsInBacklog}}</div>
                            <div class="metric-label">Loads in Backlog</div>
                        </div>
                    </div>
                </div>
                <div class="col-md-3 mb-4">
                    <div class="card h-100">
                        <div class="card-body metric-card">
                            <div class="metric-value text-info">${{loadsInReactor}}</div>
                            <div class="metric-label">Loads in Reactor</div>
                        </div>
                    </div>
                </div>
                <div class="col-md-3 mb-4">
                    <div class="card h-100">
                        <div class="card-body metric-card">
                            <div class="metric-value text-success">${{loadsCompleted}}</div>
                            <div class="metric-label">Completed Loads</div>
                        </div>
                    </div>
                </div>
                <div class="col-md-3 mb-4">
                    <div class="card h-100">
                        <div class="card-body metric-card">
                            <div class="metric-value">${{totalTests}}</div>
                            <div class="metric-label">Total Tests</div>
                        </div>
                    </div>
                </div>
                <div class="col-md-3 mb-4">
                    <div class="card h-100">
                        <div class="card-body metric-card">
                            <div class="metric-value text-primary">${{noxTests}}</div>
                            <div class="metric-label">NOx Removal Tests</div>
                        </div>
                    </div>
                </div>
                <div class="col-md-3 mb-4">
                    <div class="card h-100">
                        <div class="card-body metric-card">
                            <div class="metric-value text-danger">${{so2Tests}}</div>
                            <div class="metric-label">SO2 Oxidation Tests</div>
                        </div>
                    </div>
                </div>
                <div class="col-md-3 mb-4">
                    <div class="card h-100">
                        <div class="card-body metric-card">
                            <div class="metric-value text-success">${{coTests}}</div>
                            <div class="metric-label">CO Oxidation Tests</div>
                        </div>
                    </div>
                </div>
            `;
            
            document.getElementById('metrics-row').innerHTML = metricsHtml;
        }}

        // Function to update all charts
        function updateCharts(data) {{
            updateTimeSeriesChart(data);
            updateRequestTypesChart(data);
            updateTestConditionsChart(data);
            updateSampleTypesChart(data);
        }}

        // Function to update time series chart
        function updateTimeSeriesChart(data) {{
            // Group data by time period
            const timeData = groupDataByTime(data, currentTimeRange);
            
            // Prepare chart data
            const labels = timeData.map(item => item.period);
            const noxData = timeData.map(item => item.nox);
            const so2Data = timeData.map(item => item.so2);
            const coData = timeData.map(item => item.co);
            const vocData = timeData.map(item => item.voc);
            
            // Update chart title
            const titleMapping = {{
                'day': 'Daily Tests',
                'week': 'Weekly Tests',
                'month': 'Monthly Tests',
                'quarter': 'Quarterly Tests',
                'year': 'Yearly Tests'
            }};
            document.getElementById('trend-chart-title').textContent = titleMapping[currentTimeRange];
            
            // Create or update chart
            const ctx = document.getElementById('timeSeriesChart').getContext('2d');
            
            if (charts.timeSeries) {{
                charts.timeSeries.data.labels = labels;
                charts.timeSeries.data.datasets[0].data = noxData;
                charts.timeSeries.data.datasets[1].data = so2Data;
                charts.timeSeries.data.datasets[2].data = coData;
                charts.timeSeries.data.datasets[3].data = vocData;
                charts.timeSeries.update();
            }} else {{
                charts.timeSeries = new Chart(ctx, {{
                    type: 'line',
                    data: {{
                        labels: labels,
                        datasets: [
                            {{
                                label: 'NOx Removal',
                                data: noxData,
                                borderColor: 'rgba(54, 162, 235, 1)',
                                backgroundColor: 'rgba(54, 162, 235, 0.1)',
                                borderWidth: 2,
                                tension: 0.2,
                                fill: true
                            }},
                            {{
                                label: 'SO2 Oxidation',
                                data: so2Data,
                                borderColor: 'rgba(255, 99, 132, 1)',
                                backgroundColor: 'rgba(255, 99, 132, 0.1)',
                                borderWidth: 2,
                                tension: 0.2,
                                fill: true
                            }},
                            {{
                                label: 'CO Oxidation',
                                data: coData,
                                borderColor: 'rgba(75, 192, 192, 1)',
                                backgroundColor: 'rgba(75, 192, 192, 0.1)',
                                borderWidth: 2,
                                tension: 0.2,
                                fill: true
                            }},
                            {{
                                label: 'VOC Oxidation',
                                data: vocData,
                                borderColor: 'rgba(255, 206, 86, 1)',
                                backgroundColor: 'rgba(255, 206, 86, 0.1)',
                                borderWidth: 2,
                                tension: 0.2,
                                fill: true
                            }}
                        ]
                    }},
                    options: {{
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: {{
                            y: {{
                                beginAtZero: true,
                                title: {{
                                    display: true,
                                    text: 'Number of Tests'
                                }}
                            }},
                            x: {{
                                title: {{
                                    display: true,
                                    text: titleMapping[currentTimeRange]
                                }}
                            }}
                        }},
                        plugins: {{
                            legend: {{
                                position: 'bottom'
                            }}
                        }}
                    }}
                }});
            }}
        }}

        // Function to update request types chart
        function updateRequestTypesChart(data) {{
            // Count tests by request type
            const requestTypeCount = {{}};
            
            data.forEach(item => {{
                const requestType = item.request_type;
                if (!requestTypeCount[requestType]) {{
                    requestTypeCount[requestType] = 0;
                }}
                
                // Sum all test counts
                const testCount = 
                    (parseInt(item.NOx_Removal_count) || 0) +
                    (parseInt(item.SO2_Oxidation_count) || 0) +
                    (parseInt(item.CO_Oxidation_count) || 0) +
                    (parseInt(item.VOC_Oxidation_count) || 0) +
                    (parseInt(item.Hg_Oxidation_count) || 0) +
                    (parseInt(item.CH2O_Oxidation_count) || 0);
                
                requestTypeCount[requestType] += testCount;
            }});
            
            // Prepare chart data
            const labels = Object.keys(requestTypeCount);
            const values = Object.values(requestTypeCount);
            
            // Create or update chart
            const ctx = document.getElementById('requestTypesChart').getContext('2d');
            
            if (charts.requestTypes) {{
                charts.requestTypes.data.labels = labels;
                charts.requestTypes.data.datasets[0].data = values;
                charts.requestTypes.update();
            }} else {{
                charts.requestTypes = new Chart(ctx, {{
                    type: 'pie',
                    data: {{
                        labels: labels,
                        datasets: [{{
                            data: values,
                            backgroundColor: chartColors,
                            borderWidth: 1
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {{
                            legend: {{
                                position: 'right'
                            }}
                        }}
                    }}
                }});
            }}
        }}

        // Function to update test conditions chart
        function updateTestConditionsChart(data) {{
            // Count tests by condition type
            let noxCount = 0, so2Count = 0, coCount = 0, vocCount = 0, hgCount = 0, ch2oCount = 0;
            
            data.forEach(item => {{
                noxCount += parseInt(item.NOx_Removal_count || 0);
                so2Count += parseInt(item.SO2_Oxidation_count || 0);
                coCount += parseInt(item.CO_Oxidation_count || 0);
                vocCount += parseInt(item.VOC_Oxidation_count || 0);
                hgCount += parseInt(item.Hg_Oxidation_count || 0);
                ch2oCount += parseInt(item.CH2O_Oxidation_count || 0);
            }});
            
            // Prepare chart data
            const labels = ['NOx Removal', 'SO2 Oxidation', 'CO Oxidation', 'VOC Oxidation', 'Hg Oxidation', 'CH2O Oxidation'];
            const values = [noxCount, so2Count, coCount, vocCount, hgCount, ch2oCount];
            
            // Create or update chart
            const ctx = document.getElementById('testConditionsChart').getContext('2d');
            
            if (charts.testConditions) {{
                charts.testConditions.data.datasets[0].data = values;
                charts.testConditions.update();
            }} else {{
                charts.testConditions = new Chart(ctx, {{
                    type: 'bar',
                    data: {{
                        labels: labels,
                        datasets: [{{
                            label: 'Test Count',
                            data: values,
                            backgroundColor: chartColors,
                            borderColor: chartColors.map(color => color.replace('0.7', '1')),
                            borderWidth: 1
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: {{
                            y: {{
                                beginAtZero: true
                            }}
                        }},
                        plugins: {{
                            legend: {{
                                display: false
                            }}
                        }}
                    }}
                }});
            }}
        }}

        // Function to update sample types chart
        function updateSampleTypesChart(data) {{
            // Count samples by type
            const sampleTypeCount = {{}};
            
            data.forEach(item => {{
                const sampleTypes = item.sample_types ? item.sample_types.split(',') : [];
                
                sampleTypes.forEach(type => {{
                    const trimmedType = type.trim();
                    if (trimmedType) {{
                        if (!sampleTypeCount[trimmedType]) {{
                            sampleTypeCount[trimmedType] = 0;
                        }}
                        sampleTypeCount[trimmedType] += 1;
                    }}
                }});
            }});
            
            // Prepare chart data
            const labels = Object.keys(sampleTypeCount);
            const values = Object.values(sampleTypeCount);
            
            // Create or update chart
            const ctx = document.getElementById('sampleTypesChart').getContext('2d');
            
            if (charts.sampleTypes) {{
                charts.sampleTypes.data.labels = labels;
                charts.sampleTypes.data.datasets[0].data = values;
                charts.sampleTypes.update();
            }} else {{
                charts.sampleTypes = new Chart(ctx, {{
                    type: 'doughnut',
                    data: {{
                        labels: labels,
                        datasets: [{{
                            data: values,
                            backgroundColor: chartColors,
                            borderWidth: 1
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {{
                            legend: {{
                                position: 'right'
                            }}
                        }}
                    }}
                }});
            }}
        }}

        // Function to group data by time period for time series chart
        function groupDataByTime(data, timeRange) {{
            const groupedData = {{}};
            
            data.forEach(item => {{
                if (!item.load_start) return;
                
                const date = new Date(item.load_start);
                if (isNaN(date.getTime())) return;
                
                let period;
                
                switch (timeRange) {{
                    case 'day':
                        // Skip weekends
                        const day = date.getDay();
                        if (day === 0 || day === 6) return; // Sunday or Saturday
                        period = moment(date).format('YYYY-MM-DD');
                        break;
                    case 'week':
                        period = moment(date).format('YYYY-[W]WW');
                        break;
                    case 'month':
                        period = moment(date).format('YYYY-MM');
                        break;
                    case 'quarter':
                        const quarter = Math.floor(date.getMonth() / 3) + 1;
                        period = `${{date.getFullYear()}}-Q${{quarter}}`;
                        break;
                    case 'year':
                        period = date.getFullYear().toString();
                        break;
                    default:
                        period = moment(date).format('YYYY-MM-DD');
                }}
                
                if (!groupedData[period]) {{
                    groupedData[period] = {{ nox: 0, so2: 0, co: 0, voc: 0 }};
                }}
                
                groupedData[period].nox += parseInt(item.NOx_Removal_count || 0);
                groupedData[period].so2 += parseInt(item.SO2_Oxidation_count || 0);
                groupedData[period].co += parseInt(item.CO_Oxidation_count || 0);
                groupedData[period].voc += parseInt(item.VOC_Oxidation_count || 0);
            }});
            
            // Convert to array and sort by period
            const result = Object.entries(groupedData).map(([period, counts]) => ({{
                period,
                ...counts
            }}));
            
            return result.sort((a, b) => a.period.localeCompare(b.period));
        }}

        // Function to set time range for the time series chart
        function setTimeRange(range) {{
            currentTimeRange = range;
            
            // Update active button
            document.querySelectorAll('.time-selector .btn').forEach(btn => btn.classList.remove('active'));
            document.querySelector(`.time-selector .btn[onclick="setTimeRange('${{range}}')"]`).classList.add('active');
            
            // Update dashboard
            updateDashboard();
        }}

        // Function to toggle between light and dark theme
        function toggleTheme() {{
            const html = document.documentElement;
            const currentTheme = html.getAttribute('data-bs-theme');
            const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
            
            html.setAttribute('data-bs-theme', newTheme);
            
            // Update theme toggle text and icon
            const themeIcon = document.querySelector('.toggle-theme i');
            const themeText = document.getElementById('theme-text');
            
            if (newTheme === 'dark') {{
                themeIcon.className = 'bi bi-sun';
                themeText.textContent = 'Light Mode';
            }} else {{
                themeIcon.className = 'bi bi-moon-stars';
                themeText.textContent = 'Dark Mode';
            }}
        }}

        // Function to refresh data - in this embedded version, reloads the page
        function refreshData() {{
            window.location.reload();
        }}

        // Helper function to get test count
        function getTestCount(item) {{
            return (parseInt(item.NOx_Removal_count) || 0) +
                   (parseInt(item.SO2_Oxidation_count) || 0) +
                   (parseInt(item.CO_Oxidation_count) || 0) +
                   (parseInt(item.VOC_Oxidation_count) || 0) +
                   (parseInt(item.Hg_Oxidation_count) || 0) +
                   (parseInt(item.CH2O_Oxidation_count) || 0);
        }}

        // Initialize the dashboard when the page loads
        document.addEventListener('DOMContentLoaded', initDashboard);
    </script>
</body>
</html>'''
        
        # Write to the output file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"Dashboard generated successfully at {output_path}")
        return True
    except Exception as e:
        print(f"Error generating HTML: {e}")
        print(traceback.format_exc())
        return False

def load_csv_data(csv_path):
    """Load data from a CSV file as a fallback."""
    try:
        print(f"Attempting to load data from CSV at: {csv_path}")
        df = pd.read_csv(csv_path)
        print(f"Successfully loaded CSV data. Found {len(df)} records.")
        return df
    except Exception as e:
        print(f"Error loading CSV file: {e}")
        print(traceback.format_exc())
        return None

def main():
    # Configuration
    script_dir = os.path.dirname(os.path.abspath(__file__))
    print(f"Script directory: {script_dir}")
    
    # Set up possible paths
    db_path = "C:/Jarvis/Database/lemur_full_clone.db"
    csv_path = "DashboardData.csv"  # Look for CSV file in current directory
    output_path = os.path.join(script_dir, "dashboard.html")
    
    print(f"Looking for CSV data at: {csv_path}")
    print(f"Looking for database at: {db_path}")
    print(f"HTML output path: {output_path}")
    
    # Try CSV first since we know it's available
    processed_data = None
    if os.path.exists(csv_path):
        print(f"Found CSV file at {csv_path}")
        df = load_csv_data(csv_path)
        if df is not None and not df.empty:
            print("Successfully loaded data from CSV")
            processed_data = process_data(df)
    else:
        print(f"CSV file not found at {csv_path}, checking alternate locations...")
        # Try other common locations for the CSV
        alternate_paths = [
            os.path.join(script_dir, "DashboardData.csv"),
            os.path.join(os.getcwd(), "DashboardData.csv"),
            "data/DashboardData.csv",
            "../data/DashboardData.csv"
        ]
        
        for alt_path in alternate_paths:
            if os.path.exists(alt_path):
                print(f"Found CSV file at {alt_path}")
                df = load_csv_data(alt_path)
                if df is not None and not df.empty:
                    print("Successfully loaded data from CSV")
                    processed_data = process_data(df)
                    break
    
    # If CSV method failed, try database
    if processed_data is None:
        print("CSV method failed. Trying database...")
        conn = connect_to_db(db_path)
        
        if conn is not None:
            print("Connected to database, trying to fetch data...")
            df = get_dashboard_data(conn)
            conn.close()
            
            if df is not None and not df.empty:
                print("Successfully retrieved data from database")
                processed_data = process_data(df)
        else:
            print(f"Could not connect to database at {db_path}")
    
    # Generate the HTML file with embedded data
    if processed_data is not None:
        print("Generating HTML dashboard...")
        success = generate_html(processed_data, output_path)
        
        if success:
            print(f"Dashboard successfully created at {output_path}")
            
            # Open the dashboard in the default web browser
            try:
                file_url = 'file://' + os.path.realpath(output_path)
                print(f"Opening dashboard at: {file_url}")
                webbrowser.open(file_url)
                print("Dashboard opened in web browser.")
            except Exception as e:
                print(f"Could not open dashboard in browser: {e}")
                print(f"Please open {output_path} manually in your web browser.")
        else:
            print("Failed to generate dashboard.")
    else:
        print("No data to process. Cannot generate dashboard.")
        print("Error: No data was loaded. Please check the database or CSV file path.")
        
        # Generate a simple error HTML page
        with open(output_path, 'w', encoding='utf-8') as f:
            error_html = f'''<!DOCTYPE html>
<html>
<head>
    <title>Dashboard Error</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 40px;
            text-align: center;
        }}
        .error-container {{
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
            border: 1px solid #e74c3c;
            border-radius: 5px;
            background-color: #fef5f5;
        }}
        h1 {{
            color: #e74c3c;
        }}
        .details {{
            margin-top: 20px;
            text-align: left;
            background-color: #f9f9f9;
            padding: 15px;
            border-radius: 5px;
        }}
        code {{
            background-color: #f1f1f1;
            padding: 2px 4px;
            border-radius: 3px;
        }}
    </style>
</head>
<body>
    <div class="error-container">
        <h1><i>⚠️</i> Dashboard Error</h1>
        <p>No data was loaded. Please check the database or CSV file path.</p>
        
        <div class="details">
            <h3>Troubleshooting Steps:</h3>
            <ol>
                <li>Verify that the database exists at <code>{db_path}</code></li>
                <li>OR verify that the CSV file exists at <code>{csv_path}</code></li>
                <li>Make sure the file contains the required data columns</li>
                <li>Check the console output for more detailed error messages</li>
            </ol>
            
            <h3>Technical Details:</h3>
            <p>Attempted database path: <code>{db_path}</code></p>
            <p>Attempted CSV path: <code>{csv_path}</code></p>
            <p>Time of error: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
    </div>
</body>
</html>'''
            f.write(error_html)
            
        # Try to open the error page
        try:
            file_url = 'file://' + os.path.realpath(output_path)
            webbrowser.open(file_url)
        except:
            pass

if __name__ == "__main__":
    try:
        print("=== Reactor Testing Dashboard Generator ===")
        print(f"Started at: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Working directory: {os.getcwd()}")
        
        main()
        
        print(f"Completed at: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    except Exception as e:
        print(f"Unhandled exception: {e}")
        print(traceback.format_exc())