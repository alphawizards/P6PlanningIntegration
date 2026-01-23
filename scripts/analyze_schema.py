#!/usr/bin/env python3
"""Analyze P6 SQLite schema for schedule analysis features."""

import sqlite3
from pathlib import Path

db_path = r"C:\Program Files\Oracle\Primavera P6\P6 Professional\20.12.0\Data\S32DB001.db"
conn = sqlite3.connect(f"file:{db_path}?immutable=1", uri=True)
cursor = conn.cursor()

# Get all tables
print("=" * 60)
print("AVAILABLE P6 TABLES")
print("=" * 60)
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = [r[0] for r in cursor.fetchall()]
for t in tables:
    print(f"  {t}")

# Check key tables for schedule analysis
key_tables = ['PROJECT', 'TASK', 'TASKPRED', 'PROJWBS', 'CALENDAR', 'RSRC', 'TASKRSRC']
print("\n" + "=" * 60)
print("KEY TABLE SCHEMAS FOR SCHEDULE ANALYSIS")
print("=" * 60)

for table in key_tables:
    if table in tables:
        print(f"\n--- {table} ---")
        cursor.execute(f"PRAGMA table_info({table})")
        cols = cursor.fetchall()
        for col in cols[:20]:  # First 20 columns
            print(f"  {col[1]:30} {col[2]}")
        if len(cols) > 20:
            print(f"  ... and {len(cols) - 20} more columns")
        
        # Row count
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        print(f"  Total rows: {count}")
    else:
        print(f"\n--- {table} (NOT FOUND) ---")

# Check for constraint-related columns in TASK
print("\n" + "=" * 60)
print("CONSTRAINT & FLOAT COLUMNS IN TASK")
print("=" * 60)
cursor.execute("PRAGMA table_info(TASK)")
cols = cursor.fetchall()
constraint_cols = [c for c in cols if 'CSTR' in c[1] or 'FLOAT' in c[1] or 'STATUS' in c[1] or 'ACT_' in c[1]]
for col in constraint_cols:
    print(f"  {col[1]:30} {col[2]}")

conn.close()
print("\nDone!")
