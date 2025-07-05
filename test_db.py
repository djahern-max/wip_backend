from app.core.database import engine, SessionLocal
from app.models.user import User

# Test database connection
try:
    with SessionLocal() as db:
        print("✅ Database connection successful!")
        
        # Check if tables exist
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        print(f"📋 Tables in database: {tables}")
        
except Exception as e:
    print(f"❌ Database connection failed: {e}")
