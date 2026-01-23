#!/usr/bin/env python3
"""Quick test script to verify SQLite database connection."""

import sqlite3
from pathlib import Path

# Original path - now works with immutable mode
db_path = r"C:\Program Files\Oracle\Primavera P6\P6 Professional\20.12.0\Data\S32DB001.db"

print(f"Testing connection to: {db_path}")
print(f"Path exists: {Path(db_path).exists()}")

# Method 1: Try immutable mode (no lock files needed)
try:
    print("\n1. Trying immutable mode connection...")
    uri = f"file:{db_path}?immutable=1"
    conn = sqlite3.connect(uri, uri=True)
    print("   Connected in immutable mode!")
    
    # Get table list
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name LIMIT 20")
    tables = [r[0] for r in cursor.fetchall()]
    print(f"   Tables (first 20): {tables}")
    
    # Try to get PROJECT table count
    cursor.execute("SELECT COUNT(*) FROM PROJECT")
    count = cursor.fetchone()[0]
    print(f"   PROJECT count: {count}")
    
    # Get sample project
    cursor.execute("SELECT proj_id, proj_short_name FROM PROJECT LIMIT 3")
    projects = cursor.fetchall()
    print(f"   Sample projects: {projects}")
    
    conn.close()
    print("   Connection closed.")
    
except sqlite3.Error as e:
    print(f"   SQLite Error: {e}")
except Exception as e:
    print(f"   Error: {type(e).__name__}: {e}")

# Method 2: Try standard connection (fallback)
try:
    print("\n2. Trying standard connection...")
    conn = sqlite3.connect(db_path)
    print("   Connected!")
    
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM PROJECT")
    count = cursor.fetchone()[0]
    print(f"   PROJECT count: {count}")
    
    conn.close()
    print("   Connection closed.")
    
except sqlite3.Error as e:
    print(f"   SQLite Error: {e}")
except Exception as e:
    print(f"   Error: {type(e).__name__}: {e}")
