"""
Database migration script to add field columns to plant_history table.
Run this script if you have existing data in the plant_history table.
"""

import sqlite3
from pathlib import Path

def migrate_plant_history():
    """Add field columns to plant_history table."""
    # Determine database path
    db_path = Path(__file__).resolve().parents[2] / "soil_sensor.db"
    
    print(f"Connecting to database at: {db_path}")
    
    if not db_path.exists():
        print("Database does not exist yet. It will be created automatically on first run.")
        return
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    try:
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(plant_history)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'previous_field' not in columns:
            print("Adding previous_field column...")
            cursor.execute("ALTER TABLE plant_history ADD COLUMN previous_field VARCHAR")
            print("✓ Added previous_field column")
        else:
            print("✓ previous_field column already exists")
        
        if 'next_field' not in columns:
            print("Adding next_field column...")
            cursor.execute("ALTER TABLE plant_history ADD COLUMN next_field VARCHAR")
            print("✓ Added next_field column")
        else:
            print("✓ next_field column already exists")
        
        conn.commit()
        print("\n✅ Migration completed successfully!")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_plant_history()
