# shutdown.py
import os
import signal
import logging
import subprocess
from pathlib import Path
import psutil

from dotenv import load_dotenv
from config import Config
from aws_resources import purge_queue, clear_bucket

# ==== Logging ====
from create_log import init_logging

log = init_logging("shutdowm", "shutdowm.log")

# ==== Load .env ====
load_dotenv()

# ==== Constants ====
PID_DIR = Path("pids")
WEB_PORT = int(os.getenv("WEB_PORT", 5000))
EXCLUDED_INSTANCE_ID = os.getenv("EXCLUDED_INSTANCE_ID")


# ==== Kill process on specific port ====
def kill_port(port):
    try:
        out = subprocess.check_output(["lsof", "-i", f":{port}"]).decode()
        lines = out.strip().split("\n")[1:]
        for line in lines:
            pid = int(line.split()[1])
            log.info(f"Killing PID {pid} on port {port}")
            os.kill(pid, signal.SIGKILL)
    except subprocess.CalledProcessError:
        log.info(f"No process on port {port}")
    except Exception as e:
        log.warning(f"Error killing port {port}: {e}")


# ==== Shutdown Logic ====
def shutdown():
    log.info("=== Shutting down system ===")

    # Flask port
    kill_port(WEB_PORT)

    # Clear queues
    try:
        purge_queue(Config.REQUEST_QUEUE)
        purge_queue(Config.RESPONSE_QUEUE)
        log.info("SQS queues purged.")
    except Exception as e:
        log.warning(f"Queue purge failed: {e}")

    # Clear buckets
    try:
        clear_bucket(Config.INPUT_BUCKET)
        clear_bucket(Config.OUTPUT_BUCKET)
        log.info("S3 buckets cleared.")
    except Exception as e:
        log.warning(f"S3 bucket cleanup failed: {e}")


# ==== Main Entrypoint ====
if __name__ == "__main__":
    shutdown()
