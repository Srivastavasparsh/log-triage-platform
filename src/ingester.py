import logging
import os
import re
import sys
import threading
import time
from pathlib import Path
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from src.agent.graph import build_devops_agent
from src.agent.schemas import CrashContext
from src.db import init_db, insert_log, insert_remediation

logging.basicConfig(level=logging.INFO, format="%(asctime)s - [DAEMON] - %(message)s")

LOG_HEADER_PATTERN = re.compile(
    r"^(?:\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}(?:,\d+)?\s*\|\s*)?(ERROR|INFO|WARN|WARNING|DEBUG)(?:\s*\|\s*|:\s*)(.*)"
)
TRACE_FRAME_PATTERN = re.compile(r'File "([^"]+)", line (\d+), in (\w+)')
EXCEPTION_LINE_PATTERN = re.compile(r"^([A-Za-z_]\w*(?:Error|Exception)):\s*(.*)")


def parse_crash_context(service_name: str, block_text: str) -> CrashContext | None:
    frames = TRACE_FRAME_PATTERN.findall(block_text)
    if not frames:
        return None

    file_path, line_num, func_name = frames[-1]

    error_type = "RuntimeError"
    error_message = block_text.splitlines()[0]
    for line in reversed(block_text.splitlines()):
        exc_match = EXCEPTION_LINE_PATTERN.match(line.strip())
        if exc_match:
            error_type = exc_match.group(1)
            error_message = exc_match.group(2)
            break

    return CrashContext(
        service_name=service_name,
        file_path=file_path,
        line_number=int(line_num),
        function_name=func_name,
        error_type=error_type,
        error_message=error_message,
        stack_trace=block_text,
    )


class LogFileHandler(FileSystemEventHandler):
    def __init__(self, watch_dir: str):
        self.file_positions: dict[str, int] = {}
        self.active_incidents: set[tuple[str, int, str]] = set()
        self.lock = threading.Lock()
        self.execution_lock = threading.Lock()
        self.agent = build_devops_agent()
        init_db()

        for existing_file in Path(watch_dir).glob("*.log"):
            self.file_positions[str(existing_file)] = existing_file.stat().st_size

    def _run_autonomous_fix(self, crash: CrashContext, log_file_path: str):
        with self.execution_lock:
            rel_path = os.path.relpath(crash.file_path, BASE_DIR)
            print(f"🤖 [AGENT] Incident detected in {rel_path}:{crash.line_number} ({crash.error_type}). Starting triage...")

            try:
                result = self.agent.invoke({"crash": crash})
                diagnosis = result.get("diagnosis")
                root_cause = diagnosis.root_cause if diagnosis else "Unknown"

                if result.get("test_passed") and result.get("pr_url"):
                    pr_url = result["pr_url"]
                    insert_remediation(
                        service=crash.service_name,
                        file_path=rel_path,
                        error_type=crash.error_type,
                        root_cause=root_cause,
                        status="PR_OPENED",
                        pr_url=pr_url,
                    )
                    print(f"✅ [AGENT] Fix verified & Draft PR opened: {pr_url}")
                else:
                    insert_remediation(
                        service=crash.service_name,
                        file_path=rel_path,
                        error_type=crash.error_type,
                        root_cause=root_cause,
                        status="ESCALATED",
                    )
                    print("⚠️ [AGENT] Could not verify fix automatically. Incident escalated.")
            except Exception as exc:
                logging.error(f"Agent execution failed: {exc}")
            finally:
                if os.path.exists(log_file_path):
                    self.file_positions[log_file_path] = os.path.getsize(log_file_path)

    def process_new_lines(self, file_path: str):
        if not file_path.endswith(".log"):
            return

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                last_pos = self.file_positions.get(file_path, 0)
                f.seek(last_pos)
                new_lines = f.readlines()
                self.file_positions[file_path] = f.tell()

            if not new_lines:
                return

            service = Path(file_path).stem
            entries: list[tuple[str, list[str]]] = []

            for raw_line in new_lines:
                line = raw_line.rstrip("\n")
                if not line.strip():
                    continue

                header_match = LOG_HEADER_PATTERN.match(line)
                if header_match:
                    entries.append((header_match.group(1), [header_match.group(2)]))
                elif entries:
                    entries[-1][1].append(line)
                else:
                    entries.append(("UNKNOWN", [line]))

            for level, lines in entries:
                full_message = "\n".join(lines)
                summary_line = lines[0]

                insert_log(level, service, full_message)
                print(f"💾 [STORED] [{level}] {service}: {summary_line}")

                if level == "ERROR":
                    crash = parse_crash_context(service, full_message)
                    if crash:
                        rel_path = os.path.relpath(crash.file_path, BASE_DIR)
                        incident_key = (rel_path, crash.line_number, crash.error_type)

                        with self.lock:
                            if incident_key in self.active_incidents:
                                continue
                            self.active_incidents.add(incident_key)

                        thread = threading.Thread(
                            target=self._run_autonomous_fix,
                            args=(crash, file_path),
                            daemon=True,
                        )
                        thread.start()

        except Exception as e:
            logging.error(f"Failed to read {file_path}: {str(e)}")

    def on_created(self, event):
        if not event.is_directory:
            logging.info(f"New log file detected: {event.src_path}")
            self.process_new_lines(event.src_path)

    def on_modified(self, event):
        if not event.is_directory:
            self.process_new_lines(event.src_path)


def start_daemon():
    watch_dir = os.path.join(BASE_DIR, "logs")
    os.makedirs(watch_dir, exist_ok=True)

    logging.info(f"Starting Autonomous Log Ingestion Daemon. Watching: {watch_dir}")

    event_handler = LogFileHandler(watch_dir)
    observer = Observer()
    observer.schedule(event_handler, path=watch_dir, recursive=False)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logging.info("Shutting down daemon...")
        observer.stop()
    observer.join()


if __name__ == "__main__":
    start_daemon()