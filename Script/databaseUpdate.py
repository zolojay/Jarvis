import sqlite3
import os

# Database path
DB_PATH = r"C:\Jarvis\Database\lemur_full_clone.db"

def migrate_database():
    # Check if database file exists
    if not os.path.exists(DB_PATH):
        print(f"Database file not found at {DB_PATH}")
        return False
    
    try:
        # Connect to the database
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check if status column already exists to prevent errors
        cursor.execute("PRAGMA table_info(LoadBench)")
        columns = cursor.fetchall()
        column_names = [column[1] for column in columns]
        
        if 'status' not in column_names:
            # Add status column with default value 'Backlog'
            cursor.execute("ALTER TABLE LoadBench ADD COLUMN status TEXT NOT NULL DEFAULT 'Backlog'")
            print("Successfully added 'status' column to LoadBench table")
        else:
            print("Column 'status' already exists in LoadBench table")
        
        # Commit changes and close connection
        conn.commit()
        conn.close()
        return True
    
    except Exception as e:
        print(f"Error during database migration: {e}")
        return False

if __name__ == "__main__":
    success = migrate_database()
    if success:
        print("Database migration completed successfully")
    else:
        print("Database migration failed")