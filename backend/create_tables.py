# create_tables.py
from database import Base, engine
from models import (
    User, 
    Note, 
    EngagementSession, 
    EngagementPoint, 
    QuestionPaper,
    TokenBlacklist,
    DeviceLog,
    SessionAttendance,
    Attendance
)

print("🔨 Creating all tables...")

# This creates all tables defined in your models
Base.metadata.create_all(bind=engine)

print("✅ All tables created successfully!")

# Verify tables were created
import sqlite3
conn = sqlite3.connect('student_engagement.db')
cursor = conn.cursor()

cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = cursor.fetchall()

print(f"\n📊 Tables in database ({len(tables)}):")
for table in tables:
    cursor.execute(f"SELECT COUNT(*) FROM {table[0]}")
    count = cursor.fetchone()[0]
    print(f"  ✓ {table[0]:<30} ({count} rows)")

conn.close()