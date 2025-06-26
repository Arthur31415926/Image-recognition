from flask import Flask, request, jsonify
from create_log import init_logging
import time
import tempfile, os
log = init_logging("controller", "controller.log")
from config import Config
from aws_resources import (
    ensure_bucket, upload_file_to_s3,
    send_sqs_message, get_queue_url, get_object_text
)

app = Flask(__name__)

# Initialize once
ensure_bucket(Config.INPUT_BUCKET)
ensure_bucket(Config.OUTPUT_BUCKET)
request_queue_url = get_queue_url(Config.REQUEST_QUEUE)
response_queue_url = get_queue_url(Config.RESPONSE_QUEUE)


@app.route("/", methods=["GET"])
def status():
    return "✅ Image classification controller is running."


@app.route("/predict", methods=["POST"])
def predict():
    if "myfile" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    image_file = request.files.get("myfile")
    if image_file is None or image_file.filename == "":
        return jsonify({"error": "No file uploaded"}), 400


    image_name = image_file.filename
    log.info("Received image: %s", image_name)

    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(image_file.read())
        tmp_path = tmp.name

    upload_file_to_s3(Config.INPUT_BUCKET, image_name, tmp_path, is_path=True)
    os.remove(tmp_path)

    log.info(f"Uploaded {image_name} to input bucket.")

    # Send message to request queue
    send_sqs_message(request_queue_url, image_name)
    log.info(f"Queued image {image_name} for processing.")

    start = time.time()
    while time.time() - start < Config.WEB_TIMEOUT:
        try:
            result = get_object_text(Config.OUTPUT_BUCKET, image_name.replace(".JPEG", ".txt"))
            log.info(f"Got result for {image_name}: {result}")
            return jsonify({"result": result}), 200
        except Exception:
            time.sleep(1)

    return jsonify({"error": "Timed out waiting for result"}), 504


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, threaded=True)
