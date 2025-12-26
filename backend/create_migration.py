# Run this script to update your database
from database import engine
from models import Base

print("Creating/updating database tables...")
Base.metadata.create_all(bind=engine)
print("✅ Database tables updated successfully!")