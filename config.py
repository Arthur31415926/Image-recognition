# config.py
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    REGION = os.getenv("REGION")

    INPUT_BUCKET = os.getenv("INPUT_BUCKET")
    OUTPUT_BUCKET = os.getenv("OUTPUT_BUCKET")

    REQUEST_QUEUE = os.getenv("REQUEST_QUEUE")
    RESPONSE_QUEUE = os.getenv("RESPONSE_QUEUE")

    INSTANCE_AMI = os.getenv("INSTANCE_AMI")
    INSTANCE_TYPE = os.getenv("INSTANCE_TYPE")
    SECURITY_GROUP = os.getenv("SECURITY_GROUP")
    IAM_ROLE = os.getenv("IAM_ROLE")

    MIN_WORKERS = int(os.getenv("MIN_WORKERS", 1))
    MAX_WORKERS = int(os.getenv("MAX_WORKERS", 20))
    WEB_TIMEOUT = int(os.getenv("WEB_TIMEOUT", 60))
    TASKS_PER_WORKER = int(os.getenv("TASKS_PER_WORKER", 60))
    SCALE_OUT_THRESHOLD = int(os.getenv("SCALE_OUT_THRESHOLD", 10))
    SCALE_IN_THRESHOLD = int(os.getenv("SCALE_IN_THRESHOLD", 2))
    CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", 30))
    SCALE_INTERVAL = int(os.getenv("SCALE_INTERVAL", 5))
    WORKER_TAG = str(os.getenv("WORKER_TAG", 'app-instance'))
    SECURITY_GROUP_NAME = str(os.getenv("SECURITY_GROUP_NAME"))
    IAM_INSTANCE_PROFILE = str(os.getenv("IAM_INSTANCE_PROFILE"))
    KEY_NAME = str(os.getenv("KEY_NAME"))

    RUN_ID = os.getenv("RUN_ID", "default")
    RESULT_CSV = f"result_{RUN_ID}.csv"
