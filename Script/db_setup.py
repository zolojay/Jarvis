import os
import sqlite3

# Database path - using the same path as in the app
DB_PATH = r"C:\Jarvis\Database\lemur_full_clone.db"

def setup_database():
    """
    Connect to the SQLite database and create the LoadSchedules table
    and supporting index if they don't exist.
    """
    print(f"Connecting to database at {DB_PATH}...")
    
    # Check if database file exists
    if not os.path.exists(DB_PATH):
        print(f"Error: Database file not found at {DB_PATH}")
        return False
    
    try:
        # Connect to the database
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Create LoadSchedules table if it doesn't exist
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS LoadSchedules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            load_id INTEGER NOT NULL,
            bench_type TEXT NOT NULL,
            reactor TEXT,
            load_start TIMESTAMP NOT NULL,
            load_end TIMESTAMP NOT NULL,
            FOREIGN KEY (load_id) REFERENCES ReactorLoads(id)
        )
        ''')
        
        # Create unique index for upsert operations
        cursor.execute('''
        CREATE UNIQUE INDEX IF NOT EXISTS idx_loadschedules_unique
        ON LoadSchedules (load_id, bench_type)
        ''')
        
        # Check if the table was created successfully
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='LoadSchedules'")
        if cursor.fetchone():
            print("LoadSchedules table exists or was created successfully.")
        else:
            print("Failed to create LoadSchedules table.")
            return False
        
        # Check if the index was created successfully
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='idx_loadschedules_unique'")
        if cursor.fetchone():
            print("Unique index exists or was created successfully.")
        else:
            print("Failed to create unique index.")
            return False
        
        # Commit changes and close connection
        conn.commit()
        conn.close()
        
        print("Database setup completed successfully.")
        return True
    
    except sqlite3.Error as e:
        print(f"SQLite error: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error: {e}")
        return False

if __name__ == "__main__":
    setup_database()