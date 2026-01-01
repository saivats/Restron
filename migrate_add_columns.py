"""
Migration script to add new columns to orders table
Run this once to update your database schema
"""
from sqlalchemy import text
from database import engine
import sys

def run_migration():
    print("Starting migration...")

    try:
        with engine.connect() as conn:
            # Add new columns to orders table
            migrations = [
                "ALTER TABLE orders ADD COLUMN IF NOT EXISTS gst_amount FLOAT DEFAULT 0.0",
                "ALTER TABLE orders ADD COLUMN IF NOT EXISTS payment_method VARCHAR",
                "ALTER TABLE orders ADD COLUMN IF NOT EXISTS paid_at TIMESTAMP",
                "ALTER TABLE orders ADD COLUMN IF NOT EXISTS table_status VARCHAR DEFAULT 'Occupied'"
            ]

            for migration_sql in migrations:
                print(f"   Running: {migration_sql}")
                conn.execute(text(migration_sql))
                conn.commit()

            print("Migration completed successfully!")
            print("\nNext steps:")
            print("   1. Restart your FastAPI server")
            print("   2. Test the kitchen display at /kitchen")
            print("   3. Test the manager dashboard at /manager")

    except Exception as e:
        print(f"Migration failed: {e}")
        print("\nIf columns already exist, this is safe to ignore.")
        sys.exit(1)

if __name__ == "__main__":
    run_migration()
