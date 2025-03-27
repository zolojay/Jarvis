import os
import sys
import sqlite3
import pandas as pd
from datetime import datetime

# Database path - using the same path as in the app
DB_PATH = r"C:\Jarvis\Database\lemur_full_clone.db"

def check_dependencies():
    """
    Check if all required dependencies are installed.
    
    Returns:
    bool: True if all dependencies are available, False otherwise
    """
    try:
        import openpyxl
        return True
    except ImportError:
        print("ERROR: Missing required dependency 'openpyxl'.")
        print("Please install it using one of these commands:")
        print("  pip install openpyxl")
        print("  conda install openpyxl")
        print("\nIf you're using a virtual environment, make sure to activate it first.")
        return False

def import_excel_to_db(excel_path):
    """
    Read Excel file and import data into LoadSchedules table.
    
    Parameters:
    excel_path (str): Path to the Excel file
    
    Returns:
    bool: True if successful, False otherwise
    """
    # First check dependencies
    if not check_dependencies():
        return False
        
    print(f"Importing Excel data from {excel_path}...")
    
    # Check if Excel file exists
    if not os.path.exists(excel_path):
        print(f"Error: Excel file not found at {excel_path}")
        return False
    
    # Check if database file exists
    if not os.path.exists(DB_PATH):
        print(f"Error: Database file not found at {DB_PATH}")
        return False
    
    try:
        # Read Excel sheets
        print("Reading Excel sheets...")
        df_full = pd.read_excel(excel_path, sheet_name="FullBenchLoadSchedule", header=1)
        df_quarter = pd.read_excel(excel_path, sheet_name="QuarterBenchLoadSchedule", header=1)
        
        # Check if required columns exist in Full Bench sheet
        required_full_cols = ['LoadID', 'Reactor', 'Load', 'End']
        if not all(col in df_full.columns for col in required_full_cols):
            print(f"Error: Full Bench sheet is missing required columns. Expected: {required_full_cols}")
            print(f"Found: {df_full.columns.tolist()}")
            return False
        
        # Check if required columns exist in Quarter Bench sheet
        required_quarter_cols = ['LoadID', 'Load', 'End']
        if not all(col in df_quarter.columns for col in required_quarter_cols):
            print(f"Error: Quarter Bench sheet is missing required columns. Expected: {required_quarter_cols}")
            print(f"Found: {df_quarter.columns.tolist()}")
            return False
        
        # Connect to the database
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Create a function to handle datetime formatting
        def format_datetime(dt):
            """Convert various datetime formats to SQLite-compatible timestamp"""
            if pd.isna(dt):
                return None
            
            # Convert pandas Timestamp to Python datetime if needed
            if isinstance(dt, pd.Timestamp):
                dt = dt.to_pydatetime()
            
            if isinstance(dt, datetime):
                return dt.strftime('%Y-%m-%d %H:%M:%S')
            
            # If it's already a string, try to parse it
            try:
                dt_obj = pd.to_datetime(dt)
                return dt_obj.strftime('%Y-%m-%d %H:%M:%S')
            except:
                return None
        
        # Process Full Bench data
        print(f"Processing {len(df_full)} Full Bench records...")
        full_success_count = 0
        
        for _, row in df_full.iterrows():
            try:
                load_id = int(row['LoadID'])
                reactor = str(row['Reactor']) if not pd.isna(row['Reactor']) else None
                load_start = format_datetime(row['Load'])
                load_end = format_datetime(row['End'])
                
                # Skip rows with missing critical data
                if pd.isna(load_id) or load_start is None or load_end is None:
                    print(f"Skipping Full Bench record with missing data: {row.to_dict()}")
                    continue
                
                # Insert or update record
                cursor.execute('''
                INSERT INTO LoadSchedules (load_id, bench_type, reactor, load_start, load_end)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT (load_id, bench_type) 
                DO UPDATE SET 
                    reactor = excluded.reactor,
                    load_start = excluded.load_start,
                    load_end = excluded.load_end
                ''', (load_id, "Full Bench", reactor, load_start, load_end))
                
                full_success_count += 1
            except Exception as e:
                print(f"Error processing Full Bench row {_}: {e}")
                print(f"Row data: {row.to_dict()}")
        
        # Process Quarter Bench data
        print(f"Processing {len(df_quarter)} Quarter Bench records...")
        quarter_success_count = 0
        
        for _, row in df_quarter.iterrows():
            try:
                load_id = int(row['LoadID'])
                load_start = format_datetime(row['Load'])
                load_end = format_datetime(row['End'])
                
                # Skip rows with missing critical data
                if pd.isna(load_id) or load_start is None or load_end is None:
                    print(f"Skipping Quarter Bench record with missing data: {row.to_dict()}")
                    continue
                
                # Insert or update record
                cursor.execute('''
                INSERT INTO LoadSchedules (load_id, bench_type, reactor, load_start, load_end)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT (load_id, bench_type) 
                DO UPDATE SET 
                    reactor = excluded.reactor,
                    load_start = excluded.load_start,
                    load_end = excluded.load_end
                ''', (load_id, "Quarter Bench", None, load_start, load_end))
                
                quarter_success_count += 1
            except Exception as e:
                print(f"Error processing Quarter Bench row {_}: {e}")
                print(f"Row data: {row.to_dict()}")
        
        # Commit changes and close connection
        conn.commit()
        conn.close()
        
        print(f"Import completed: {full_success_count} Full Bench records, {quarter_success_count} Quarter Bench records")
        return True
    
    except pd.errors.EmptyDataError:
        print(f"Error: Excel file contains no data")
        return False
    except sqlite3.Error as e:
        print(f"SQLite error: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error: {e}")
        return False

if __name__ == "__main__":
    # Check if Excel path is provided as command-line argument
    if len(sys.argv) > 1:
        excel_path = sys.argv[1]
    else:
        # Default Excel path
        excel_path = r"C:\Users\s.jay\OneDrive - Cormetech\Hub\Reactor Loadsv1.xlsm"
    
    import_excel_to_db(excel_path)