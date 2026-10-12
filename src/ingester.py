import time
import logging
import os
import re
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from db import init_db, insert_log

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [DAEMON] - %(message)s')

class LogFileHandler(FileSystemEventHandler):
    def __init__(self):
        self.file_positions = {}
        init_db()

    def process_new_lines(self, file_path):
        if not file_path.endswith('.log'):
            return

        try:
            with open(file_path, 'r') as f:
                last_pos = self.file_positions.get(file_path, 0)
                f.seek(last_pos)
                
                new_lines = f.readlines()
                for line in new_lines:
                    line = line.strip()
                    if line:
                        match = re.search(r'^(ERROR|INFO|WARN|DEBUG):\s*(.*)', line)
                        level = match.group(1) if match else "UNKNOWN"
                        message = match.group(2) if match else line
                        service = os.path.basename(file_path)

                        insert_log(level, service, message)
                        print(f"💾 [STORED] [{level}] {service}: {message}")
                
                self.file_positions[file_path] = f.tell()
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
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    watch_dir = os.path.join(base_dir, "logs")
    os.makedirs(watch_dir, exist_ok=True)
    
    logging.info(f"Starting Log Ingestion Daemon. Watching: {watch_dir}")
    
    event_handler = LogFileHandler()
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