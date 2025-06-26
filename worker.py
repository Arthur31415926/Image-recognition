# worker.py
import os
import time
from create_log import init_logging

log = init_logging("worker", "worker.log")
import uuid
from config import Config
from aws_resources import (
    receive_sqs_message, delete_sqs_message,
    download_from_s3, upload_file_to_s3
)
from classifier.image_classification import classify


def start_worker():
    log.info("Worker started.")
    while True:
        try:
            msg = receive_sqs_message(Config.REQUEST_QUEUE)
            if msg is None:
                time.sleep(2)
                continue
            log.info(f"msg = {msg} (type: {type(msg)})")
            body, receipt = msg
            image_name = body.strip()

            tmp_path = f"/tmp/{uuid.uuid4()}_{image_name}"
            download_from_s3(Config.INPUT_BUCKET, image_name, tmp_path)

            log.info(f"Running prediction for {image_name}")
            label = classify(tmp_path)
            log.info(f"Prediction done: {image_name} → {label}")

            result_text = f"{image_name},{label}"
            output_key = os.path.splitext(image_name)[0] + ".txt"
            upload_file_to_s3(Config.OUTPUT_BUCKET, output_key, result_text)

            delete_sqs_message(Config.REQUEST_QUEUE, receipt)
            os.remove(tmp_path)

        except Exception as e:
            log.error(f"Worker error: {e}")
            time.sleep(3)


if __name__ == "__main__":
    start_worker()
