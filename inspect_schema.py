
import sqlite3
import os

DB_PATH = 'S32DB001_copy.db'

def inspect_schema():
    if not os.path.exists(DB_PATH):
        print(f"Error: {DB_PATH} not found")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    tables_of_interest = ['TASK', 'PROJWBS', 'TASKRSRC', 'PROJECT', 'RSRC']
    
    print(f"--- Inspecting Tables: {tables_of_interest} ---")
    
    for table in tables_of_interest:
        print(f"\nTable: {table}")
        try:
            cursor.execute(f"PRAGMA table_info({table})")
            columns = cursor.fetchall()
            if not columns:
                print("  (Table not found)")
                continue
                
            # List columns, highlighting BLOBs
            blob_cols = []
            pk_cols = []
            for col in columns:
                # col format: (cid, name, type, notnull, dflt_value, pk)
                name = col[1]
                dtype = col[2]
                is_pk = col[5]
                
                if 'BLOB' in dtype.upper():
                    blob_cols.append(name)
                if is_pk:
                    pk_cols.append(name)
                    
            print(f"  Primary Keys: {pk_cols}")
            print(f"  BLOB Columns (DANGER ZONES): {blob_cols}")
            print(f"  Total Columns: {len(columns)}")
            
        except Exception as e:
            print(f"  Error inspecting: {e}")
            
    conn.close()

if __name__ == "__main__":
    inspect_schema()
