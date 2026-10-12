import sqlite3
import argparse
import pandas as pd
from db import DB_PATH

def query_logs(level=None, limit=10):
    conn = sqlite3.connect(DB_PATH)
    query = "SELECT ingested_at, log_level, service_name, message FROM logs"
    params = []
    
    if level:
        query += " WHERE log_level = ?"
        params.append(level.upper())
        
    query += " ORDER BY ingested_at DESC LIMIT ?"
    params.append(limit)
    
    # Use pandas to format the SQL output into a clean CLI table
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df

def get_summary():
    conn = sqlite3.connect(DB_PATH)
    query = "SELECT log_level, COUNT(*) as incident_count FROM logs GROUP BY log_level"
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Log Triage & Observability CLI")
    parser.add_argument("--level", type=str, help="Filter logs by severity (e.g., ERROR, INFO, WARN)")
    parser.add_argument("--summary", action="store_true", help="Show an aggregate count of all log levels")
    
    args = parser.parse_args()
    
    if args.summary:
        print("\n📊 TELEMETRY SUMMARY")
        print("-" * 30)
        print(get_summary().to_string(index=False))
    else:
        print(f"\n🔍 RECENT LOGS (Filter: {args.level or 'ALL'})")
        print("-" * 80)
        df = query_logs(level=args.level)
        if not df.empty:
            print(df.to_string(index=False))
        else:
            print("No logs found matching your criteria.")
    print("\n")