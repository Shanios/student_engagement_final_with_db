# backend/add_analytics_columns.py
import sqlite3
import os

# Path to your database
DB_PATH = "student_engagement.db"  # Adjust if your database has a different name/path

# SQL commands to add columns
SQL_COMMANDS = [
    "ALTER TABLE engagement_sessions ADD COLUMN analytics_computed BOOLEAN DEFAULT FALSE",
    "ALTER TABLE engagement_sessions ADD COLUMN analytics_computed_at TIMESTAMP",
    "ALTER TABLE engagement_sessions ADD COLUMN analytics_data JSON",
    "ALTER TABLE engagement_sessions ADD COLUMN report_generated_at TIMESTAMP",
    "ALTER TABLE engagement_sessions ADD COLUMN attention_score INTEGER",
    "ALTER TABLE engagement_sessions ADD COLUMN focus_time_percentage FLOAT",
    "ALTER TABLE engagement_sessions ADD COLUMN avg_engagement FLOAT",
    "ALTER TABLE engagement_sessions ADD COLUMN total_points INTEGER DEFAULT 0",
]

def update_database():
    try:
        # Check if database exists
        if not os.path.exists(DB_PATH):
            print(f"❌ Database not found at {DB_PATH}")
            print("Please check the database path.")
            return
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        print(f"📊 Updating database: {DB_PATH}")
        print("=" * 50)
        
        # Check existing columns
        cursor.execute("PRAGMA table_info(engagement_sessions)")
        existing_columns = [row[1] for row in cursor.fetchall()]
        print(f"Existing columns: {existing_columns}")
        
        # Add missing columns
        for sql in SQL_COMMANDS:
            column_name = sql.split()[4]  # Get column name from SQL
            if column_name not in existing_columns:
                try:
                    cursor.execute(sql)
                    print(f"✅ Added column: {column_name}")
                except sqlite3.OperationalError as e:
                    print(f"⚠️ Could not add {column_name}: {e}")
            else:
                print(f"✅ Column already exists: {column_name}")
        
        conn.commit()
        conn.close()
        print("=" * 50)
        print("✅ Database update complete!")
        
    except Exception as e:
        print(f"❌ Error updating database: {e}")

if __name__ == "__main__":
    update_database()