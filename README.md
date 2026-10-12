# 📡 Log Triage & Observability Platform

A real-time telemetry ingestion daemon and command-line observability tool built with Python. 

This platform simulates the core behavior of enterprise log forwarders (like Splunk Universal Forwarder or Filebeat) by utilizing file-system event monitoring to tail logs in real-time, parse unstructured strings into structured data, and provide instant CLI querying for incident triage.

## 🏗️ System Architecture

1. **The Ingestion Daemon (`watchdog`):** Monitors application directories for log file creation or modification. It tracks byte-read positions to ensure files are efficiently tailed without redundant reads, even if the daemon restarts.
2. **The Parsing Engine (`re`):** Extracts severity levels (INFO, WARN, ERROR) and unstructured messages via regex.
3. **The Storage Layer (`sqlite3`):** Routes structured telemetry into a local SQLite timeseries database for fast querying.
4. **The Query CLI (`pandas`, `argparse`):** A command-line interface that aggregates database records, allowing developers to filter production logs by severity or generate high-level incident summaries instantly.

## 🚀 Quick Start Guide

### 1. Installation
Clone the repository and install the dependencies:
```bash
git clone [https://github.com/YourUsername/log-triage-platform.git](https://github.com/YourUsername/log-triage-platform.git)
cd log-triage-platform
python3 -m venv venv
source venv/bin/activate
pip install watchdog pandas

2. Start the Daemon
Run the ingestion daemon in your first terminal. It will automatically create a logs/ directory and begin monitoring it.

python src/ingester.py

3. Simulate Production Logs
Open a second terminal and append raw strings into a log file to simulate an active application:

echo "ERROR: Database connection timeout on port 5432" >> logs/api_server.log
echo "WARN: CPU utilization exceeding 85%" >> logs/worker.log
echo "INFO: User session authenticated" >> logs/auth.log

4. Query the Telemetry
Use the CLI tool in your second terminal to query the SQLite database.

View an aggregate summary of all incidents:
python src/cli.py --summary

Filter for specific severity levels:
python src/cli.py --level ERROR

🔮 Future Enhancements
Remote Forwarding: Transition from local SQLite storage to forwarding logs via HTTP to a remote centralized database.

Log Rotation Handling: Implement graceful handling of logrotate events (detecting when a file is zipped and a new one is created).