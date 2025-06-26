# manage.py
import time
import subprocess
from create_log import init_logging
log = init_logging('manage', "manage.log")
from config import Config
from aws_resources import ensure_bucket, ensure_queue
from auto_scaler import auto_scale


def setup_infra():
    log.info("Setting up S3 buckets and SQS queues...")
    ensure_bucket(Config.INPUT_BUCKET)
    ensure_bucket(Config.OUTPUT_BUCKET)
    ensure_queue(Config.REQUEST_QUEUE)
    ensure_queue(Config.RESPONSE_QUEUE)
    log.info("Infrastructure ready.")


def start_controller():
    log.info("Starting controller server...")
    subprocess.Popen(["python3", "web_controller.py"])
    time.sleep(3)


def start_worker():
    log.info("Starting initial worker...")
    subprocess.Popen(["python3", "worker.py"])


def main():
    setup_infra()
    start_controller()
    start_worker()
    log.info("Auto-scaler running...")
    auto_scale(Config.REQUEST_QUEUE)


if __name__ == "__main__":
    main()
